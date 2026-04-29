"""
Cliente de pagamento — gateway Rede (e.Rede REST API v1).

Autenticação: Basic Auth com PV (número de filiação) + Integration Token.
Sandbox:    https://sandbox.userede.com.br/erede/v1
Produção:   https://api.userede.com.br/erede/v1

Modos de cobrança suportados:
  - PIX   → POST /transactions  (kind=pix, retorna qrCode copia-e-cola)
  - LINK  → POST /transactions/links  (link de pagamento multicanal)

Obs: o endpoint de link de pagamento deve ser validado com a documentação
oficial que a Rede entregar junto às credenciais de sandbox.
"""

import base64
import time
from typing import Any

import httpx
from loguru import logger

from config.settings import settings

# ---------------------------------------------------------------------------
# Constantes de mock — usados apenas em desenvolvimento sem credenciais
# ---------------------------------------------------------------------------
_MOCK_PIX_CODE = (
    "00020126580014BR.GOV.BCB.PIX0136"
    "mock-uuid-nanoassist-rede-0000000000"
    "5204000053039865802BR5925Nanofarmacos"
    "6009Sao Paulo62070503***6304ABCD"
)
_MOCK_PAYMENT_URL = "https://checkout.userede.com.br/mock/pagamento"

_REDE_SANDBOX_URL = "https://sandbox.userede.com.br/erede/v1"
_REDE_PRODUCTION_URL = "https://api.userede.com.br/erede/v1"

# Rede retorna "00" como returnCode de sucesso
_REDE_SUCCESS_CODE = "00"

# Valor máximo aceito por transação (R$ 50.000) — barreira de segurança local
_MAX_AMOUNT = 50_000.00


def _make_reference() -> str:
    """Referência única por transação (20 chars max aceito pela Rede)."""
    return f"NANO{int(time.time() * 1000)}"[-20:]


def _to_centavos(amount: float) -> int:
    """Converte reais para centavos sem erro de ponto flutuante."""
    return int(round(amount * 100))


class RedePaymentClient:
    def __init__(self) -> None:
        self.pv = (settings.rede_pv or "").strip()
        self.token = (settings.rede_integration_token or "").strip()

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @property
    def _base_url(self) -> str:
        return _REDE_SANDBOX_URL if settings.app_env != "production" else _REDE_PRODUCTION_URL

    def _auth_header(self) -> str:
        raw = f"{self.pv}:{self.token}".encode()
        return "Basic " + base64.b64encode(raw).decode()

    def _is_mock(self) -> bool:
        return settings.app_env == "development" and not self.pv

    def _default_headers(self) -> dict[str, str]:
        return {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
        }

    def _validate_amount(self, amount: float) -> str | None:
        if amount <= 0:
            return "amount_zero_or_negative"
        if amount > _MAX_AMOUNT:
            return f"amount_exceeds_limit_{_MAX_AMOUNT}"
        return None

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    async def create_charge(self, patient: str, amount: float, payment_type: str) -> dict[str, Any]:
        """
        Cria cobrança na Rede.

        Args:
            patient:      Nome do paciente (para o link de pagamento).
            amount:       Valor em reais (sem desconto — o desconto PIX é
                          aplicado internamente).
            payment_type: "PIX" ou "LINK".

        Returns:
            dict com campos: pix_code, payment_url, amount, reference.
            Em caso de erro: {"error": "<código>"}.
        """
        if self._is_mock():
            return self._mock_response(amount, payment_type)

        err = self._validate_amount(amount)
        if err:
            logger.error(f"[REDE] Valor inválido: {err} (amount={amount})")
            return {"error": err}

        if payment_type == "PIX":
            return await self._create_pix(amount)
        return await self._create_payment_link(patient, amount)

    # ------------------------------------------------------------------
    # Mock — desenvolvimento sem credenciais
    # ------------------------------------------------------------------

    def _mock_response(self, amount: float, payment_type: str) -> dict[str, Any]:
        discount = settings.pix_discount_pct / 100.0
        final = round(amount * (1.0 - discount), 2) if payment_type == "PIX" else amount
        logger.info(f"[MOCK REDE] {payment_type} R${final:.2f}")
        return {
            "pix_code": _MOCK_PIX_CODE if payment_type == "PIX" else "",
            "payment_url": _MOCK_PAYMENT_URL,
            "amount": final,
            "reference": _make_reference(),
            "tid": "MOCK-TID-0000",
        }

    # ------------------------------------------------------------------
    # PIX — POST /transactions (kind=pix)
    # ------------------------------------------------------------------

    async def _create_pix(self, amount: float) -> dict[str, Any]:
        discount = settings.pix_discount_pct / 100.0
        final_amount = round(amount * (1.0 - discount), 2)
        reference = _make_reference()

        payload: dict[str, Any] = {
            "kind": "pix",
            "amount": _to_centavos(final_amount),
            "reference": reference,
            "expiresIn": 3600,  # 1 hora
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self._base_url}/transactions",
                    headers=self._default_headers(),
                    json=payload,
                )
                resp.raise_for_status()
                data: dict = resp.json()

            return_code = str(data.get("returnCode", "")).strip()
            if return_code != _REDE_SUCCESS_CODE:
                msg = data.get("returnMessage", "sem mensagem")
                logger.error(f"[REDE PIX] returnCode={return_code} — {msg}")
                return {"error": f"rede_{return_code}"}

            pix = data.get("pix") or {}
            pix_code = (pix.get("qrCode") or pix.get("emv") or "").strip()

            if not pix_code:
                logger.error(f"[REDE PIX] qrCode ausente. returnCode={return_code}")
                return {"error": "pix_code_missing"}

            logger.info(
                f"[REDE PIX] OK — ref={reference} tid={data.get('tid', '?')} "
                f"valor=R${final_amount:.2f}"
            )
            return {
                "pix_code": pix_code,
                "payment_url": pix.get("qrCodeUrl", ""),
                "amount": final_amount,
                "reference": reference,
                "tid": data.get("tid", ""),
            }

        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            logger.error(f"[REDE PIX] HTTP {code} — ref={reference}")
            return {"error": f"http_{code}"}
        except httpx.TimeoutException:
            logger.error(f"[REDE PIX] Timeout — ref={reference}")
            return {"error": "timeout"}
        except Exception as exc:
            logger.error(f"[REDE PIX] Erro inesperado — ref={reference}: {exc}")
            return {"error": "unexpected"}

    # ------------------------------------------------------------------
    # Link de Pagamento — POST /transactions/links
    # Endpoint a confirmar com documentação oficial da Rede.
    # ------------------------------------------------------------------

    async def _create_payment_link(self, patient: str, amount: float) -> dict[str, Any]:
        reference = _make_reference()

        payload: dict[str, Any] = {
            "amount": _to_centavos(amount),
            "reference": reference,
            "customer": {"name": patient},
            "expiresIn": 86400,  # 24 horas
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self._base_url}/transactions/links",
                    headers=self._default_headers(),
                    json=payload,
                )
                resp.raise_for_status()
                data: dict = resp.json()

            return_code = str(data.get("returnCode", "")).strip()
            if return_code and return_code != _REDE_SUCCESS_CODE:
                msg = data.get("returnMessage", "sem mensagem")
                logger.error(f"[REDE LINK] returnCode={return_code} — {msg}")
                return {"error": f"rede_{return_code}"}

            payment_url = (
                data.get("paymentUrl")
                or data.get("checkoutUrl")
                or data.get("url")
                or ""
            ).strip()

            if not payment_url:
                logger.error(f"[REDE LINK] URL ausente. ref={reference}")
                return {"error": "payment_url_missing"}

            logger.info(
                f"[REDE LINK] OK — ref={reference} valor=R${amount:.2f}"
            )
            return {
                "pix_code": "",
                "payment_url": payment_url,
                "amount": amount,
                "reference": reference,
                "tid": data.get("tid", ""),
            }

        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            logger.error(f"[REDE LINK] HTTP {code} — ref={reference}")
            return {"error": f"http_{code}"}
        except httpx.TimeoutException:
            logger.error(f"[REDE LINK] Timeout — ref={reference}")
            return {"error": "timeout"}
        except Exception as exc:
            logger.error(f"[REDE LINK] Erro inesperado — ref={reference}: {exc}")
            return {"error": "unexpected"}


payment_client = RedePaymentClient()
