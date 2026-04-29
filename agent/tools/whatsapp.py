import asyncio

import httpx
from loguru import logger

from config.settings import settings


class WhatsAppClient:
    def __init__(self):
        self.provider = (settings.crm_provider or "dix").strip().lower()

        # Generic CRM settings (preferential for new integrations)
        self.base_url = (settings.crm_base_url or "").strip()
        self.token = (settings.crm_token or "").strip()
        self.send_path = (settings.crm_send_message_path or "/api/messages/send").strip()

        # Provider-specific compatibility/fallbacks
        if self.provider == "dix":
            self.base_url = self.base_url or (settings.dix_base_url or "").strip()
            self.token = self.token or (settings.dix_token or "").strip()
            self.send_path = self.send_path or (settings.dix_send_message_path or "/api/messages/send").strip()
        elif self.provider == "medipharma":
            self.base_url = self.base_url or (settings.medipharma_base_url or "").strip()
            self.token = self.token or (settings.medipharma_token or "").strip()

        # Legacy fallback to avoid breaking old environments
        self.base_url = self.base_url or (settings.medipharma_base_url or "").strip()
        self.token = self.token or (settings.medipharma_token or "").strip()

        if not self.send_path:
            self.send_path = "/api/messages/send"
        if not self.send_path.startswith("/"):
            self.send_path = f"/{self.send_path}"

    async def send_message(self, phone: str, text: str) -> bool:
        if settings.app_env == "development" and not self.token:
            logger.info(f"[MOCK WA:{self.provider}] -> {phone}: {text[:80]}...")
            return True

        if not self.base_url:
            logger.error("WhatsApp base URL vazia. Verifique CRM_BASE_URL / DIX_BASE_URL.")
            return False

        url = f"{self.base_url.rstrip('/')}{self.send_path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        body = {"number": phone, "body": text}
        max_retries = settings.whatsapp_max_retries

        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, headers=headers, json=body)
                    resp.raise_for_status()
                    logger.info(
                        f"[{self.provider}] Mensagem enviada para {phone} "
                        f"(tentativa {attempt + 1}/{max_retries})"
                    )
                    return True
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    wait = 2 ** attempt  # 1s → 2s → 4s
                    logger.warning(
                        f"[{self.provider}] Tentativa {attempt + 1}/{max_retries} falhou "
                        f"para {phone}: {exc}. Próxima em {wait}s..."
                    )
                    await asyncio.sleep(wait)

        logger.error(
            f"[{self.provider}] Todas as {max_retries} tentativas falharam "
            f"para {phone}. Último erro: {last_exc}"
        )
        return False


whatsapp_client = WhatsAppClient()
