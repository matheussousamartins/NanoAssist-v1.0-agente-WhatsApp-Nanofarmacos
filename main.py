import hashlib
import hmac as hmac_lib
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from agent.graph import build_graph
from persistence.store import get_checkpointer, get_initial_state
from agent.tools.whatsapp import whatsapp_client
from config.settings import settings


# ---------------------------------------------------------------------------
# Rate limiter
# Em produção, o limite vem de WEBHOOK_RATE_LIMIT no .env (padrão: 60/minute).
# Em desenvolvimento, usa limite alto para não atrapalhar testes locais.
# ---------------------------------------------------------------------------
def _effective_rate_limit() -> str:
    if settings.app_env != "production":
        return "10000/minute"
    return settings.webhook_rate_limit


limiter = Limiter(key_func=get_remote_address)

checkpointer = None
graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global checkpointer, graph
    checkpointer = get_checkpointer()
    graph = build_graph(checkpointer=checkpointer)
    logger.info(f"NanoAssist iniciado — ambiente: {settings.app_env}")
    yield
    logger.info("NanoAssist encerrado")


app = FastAPI(title="NanoAssist", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class WebhookPayload(BaseModel):
    number: str
    body: str
    media_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Segurança: verificação de assinatura HMAC-SHA256
# ---------------------------------------------------------------------------
async def _verify_webhook_signature(request: Request) -> bool:
    """
    Verifica a assinatura HMAC-SHA256 enviada pelo CRM no header.

    - Se WEBHOOK_SECRET não estiver configurado → verificação ignorada (dev).
    - Se o header de assinatura estiver ausente em produção → rejeita.
    - Usa compare_digest para evitar timing attacks.

    Headers aceitos (em ordem de preferência):
        X-Webhook-Signature, X-Hub-Signature-256, X-Signature
    """
    secret = settings.webhook_secret.strip()
    if not secret:
        # Sem segredo configurado: permite em desenvolvimento, loga aviso em produção
        if settings.app_env == "production":
            logger.warning("WEBHOOK_SECRET não configurado em produção — assinatura não verificada")
        return True

    body = await request.body()
    expected = "sha256=" + hmac_lib.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    received = (
        request.headers.get("X-Webhook-Signature")
        or request.headers.get("X-Hub-Signature-256")
        or request.headers.get("X-Signature")
        or ""
    ).strip()

    if not received:
        logger.warning(
            f"Webhook recebido sem header de assinatura de {request.client.host if request.client else '?'}"
        )
        return False

    return hmac_lib.compare_digest(expected, received)


# ---------------------------------------------------------------------------
# Parsing de payload
# ---------------------------------------------------------------------------
def _extract_payload(raw_payload: dict[str, Any]) -> tuple[str | None, str | None, str | None, str | None]:
    # Legacy flat format.
    if "number" in raw_payload or "body" in raw_payload:
        number = str(raw_payload.get("number", "")).strip()
        body = str(raw_payload.get("body", "")).strip()
        media_url = raw_payload.get("media_url")
        if isinstance(media_url, str):
            media_url = media_url.strip() or None
        else:
            media_url = None
        return number, body, media_url, None

    # Dix webhook format.
    event_type = str(raw_payload.get("eventType", "")).strip().upper()
    if event_type and event_type != "MESSAGE_RECEIVED":
        return None, None, None, f"ignored_event_type:{event_type}"

    content = raw_payload.get("content") if isinstance(raw_payload.get("content"), dict) else {}
    details = content.get("details") if isinstance(content.get("details"), dict) else {}

    direction = str(content.get("direction", "")).strip().upper()
    if event_type.startswith("MESSAGE") and direction and direction != "TO_HUB":
        return None, None, None, "ignored_outbound_message"

    message = str(content.get("text", "")).strip()
    phone = str(details.get("from", "")).strip()

    media_url = None
    file_url = details.get("file")
    if isinstance(file_url, str) and file_url.strip():
        media_url = file_url.strip()

    if not phone or not message:
        return None, None, None, "unsupported_payload"

    return phone, message, media_url, None


# ---------------------------------------------------------------------------
# Invocação do agente
# ---------------------------------------------------------------------------
async def _invoke_agent(phone: str, message: str, media_url: str | None) -> dict[str, Any]:
    config = {"configurable": {"thread_id": phone}}

    try:
        current = checkpointer.get(config)
        if current and current.get("channel_values"):
            persisted = current["channel_values"]
            if isinstance(persisted, dict) and persisted.get("step"):
                state = {**persisted, "message": message, "media_url": media_url}
            else:
                logger.warning(f"Checkpoint sem step válido para {phone} — reiniciando conversa")
                state = get_initial_state(phone, message, media_url)
        else:
            state = get_initial_state(phone, message, media_url)
    except Exception:
        state = get_initial_state(phone, message, media_url)

    return await graph.ainvoke(state, config=config)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/webhook")
@limiter.limit(_effective_rate_limit())
async def webhook(request: Request, payload: dict[str, Any]):
    """Endpoint principal — recebe mensagens do CRM em produção."""
    if not await _verify_webhook_signature(request):
        return JSONResponse(
            status_code=401,
            content={"status": "error", "detail": "Assinatura inválida"},
        )

    phone, message, media_url, ignore_reason = _extract_payload(payload)

    if ignore_reason:
        logger.info(f"Webhook ignorado: {ignore_reason}")
        return {"status": "ignored", "reason": ignore_reason}

    if not phone or not message:
        raise HTTPException(status_code=400, detail="number e body são obrigatórios")

    logger.info(f"Recebido de {phone}: {message[:60]}")
    result = await _invoke_agent(phone, message, media_url)

    if result.get("response"):
        await whatsapp_client.send_message(phone, result["response"])

    return {"status": "ok"}


@app.post("/webhook/test")
@limiter.limit("120/minute")
async def webhook_test(request: Request, payload: dict[str, Any]):
    """
    Endpoint de testes — processa a mensagem e retorna a resposta do agente
    sem enviar nada ao WhatsApp real.
    """
    phone, message, media_url, ignore_reason = _extract_payload(payload)

    if ignore_reason:
        return {"status": "ignored", "reason": ignore_reason}

    if not phone or not message:
        raise HTTPException(status_code=400, detail="number e body são obrigatórios")

    result = await _invoke_agent(phone, message, media_url)
    return {
        "status": "ok",
        "phone": phone,
        "response": result.get("response", ""),
        "step": str(result.get("step", "")),
    }


@app.get("/health")
async def health():
    """Health check com verificação do banco de dados."""
    db_status = "ok"
    try:
        checkpointer.get({"configurable": {"thread_id": "__health__"}})
    except Exception as exc:
        logger.error(f"Health check — falha no checkpointer: {exc}")
        db_status = "error"

    overall = "healthy" if db_status == "ok" else "degraded"
    return {
        "status": overall,
        "service": "NanoAssist",
        "version": "1.0.0",
        "env": settings.app_env,
        "checks": {
            "database": db_status,
            "whatsapp_provider": settings.crm_provider,
        },
    }


@app.get("/chat-test", response_class=HTMLResponse)
async def chat_test_page():
    return """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NanoAssist Chat Test</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #f4f7fb; color: #1a1a1a; }
    .wrap { max-width: 900px; margin: 24px auto; padding: 16px; }
    .card { background: #fff; border: 1px solid #dce3ee; border-radius: 12px; padding: 16px; }
    .row { display: flex; gap: 8px; margin-bottom: 12px; }
    input, button { padding: 10px 12px; border: 1px solid #c9d4e5; border-radius: 8px; font-size: 14px; }
    input { flex: 1; }
    button { background: #2f6feb; color: #fff; border: none; cursor: pointer; }
    button:hover { background: #245bc0; }
    #chat { height: 55vh; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; background: #fbfdff; }
    .msg { max-width: 80%; padding: 10px 12px; border-radius: 10px; margin: 8px 0; white-space: pre-wrap; }
    .user { margin-left: auto; background: #dbeafe; }
    .bot { margin-right: auto; background: #e9fbe8; }
    .meta { font-size: 12px; color: #60708a; margin-top: 4px; }
  </style>
</head>
<body>
  <div class="wrap">
    <h2>NanoAssist Chat Test (Seguro)</h2>
    <div class="card">
      <div class="row">
        <input id="phone" value="5511999990001" placeholder="Telefone para simular sessão" />
      </div>
      <div id="chat"></div>
      <div class="row" style="margin-top:12px;">
        <input id="message" placeholder="Digite sua mensagem..." />
        <button id="send">Enviar</button>
      </div>
      <div class="meta">Este chat usa <code>/webhook/test</code> e nao envia mensagem real para clientes.</div>
    </div>
  </div>
  <script>
    const chat = document.getElementById("chat");
    const phoneInput = document.getElementById("phone");
    const messageInput = document.getElementById("message");

    function addBubble(text, who) {
      const div = document.createElement("div");
      div.className = "msg " + who;
      div.textContent = text;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
    }

    async function send() {
      const number = (phoneInput.value || "").trim();
      const body = (messageInput.value || "").trim();
      if (!number || !body) return;

      addBubble(body, "user");
      messageInput.value = "";

      const res = await fetch("/webhook/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ number, body }),
      });

      const json = await res.json();
      if (json.status === "ok") {
        addBubble(json.response || "(sem resposta)", "bot");
      } else {
        addBubble("Ignorado: " + (json.reason || "sem motivo"), "bot");
      }
    }

    document.getElementById("send").addEventListener("click", send);
    messageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") send();
    });
  </script>
</body>
</html>
"""
