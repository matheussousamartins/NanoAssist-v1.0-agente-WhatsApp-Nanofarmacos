from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- CRM / WhatsApp ---
    crm_provider: str = "dix"
    crm_token: str = ""
    crm_base_url: str = ""
    crm_send_message_path: str = "/api/messages/send"

    dix_token: str = ""
    dix_base_url: str = ""
    dix_send_message_path: str = "/api/messages/send"

    medipharma_token: str = ""
    medipharma_base_url: str = "https://api.medipharma.com.br"

    # --- NanoCare Receitas API (integração oficial) ---
    nanocare_api_url: str = ""      # Ex: https://api.nanocare.com.br/api  (sem barra final)
    nanocare_api_token: str = ""    # Token Bearer (prefixo nck_...)

    # Mock (ative apenas em desenvolvimento — desative em produção)
    receitaface_mock_enabled: bool = False
    receitaface_mock_delay_ms: int = 0

    # Fallback: modo sessão web (workaround — manter enquanto API oficial não cobrir todos os casos)
    receitaface_use_session: bool = False
    receitaface_session_cookie: str = ""
    receitaface_csrf_token: str = ""
    receitaface_base_url: str = "https://app.receitaface.com.br"
    receitaface_list_path: str = "/receita/data/todas"
    receitaface_details_path: str = "/receita/visualizar/detalhes"
    receitaface_referer_path: str = "/receita/visualizar/todas"
    receitaface_page_length: int = 10

    # --- IA ---
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # --- Pagamento (Rede) ---
    rede_pv: str = ""                    # Número de filiação (PV)
    rede_integration_token: str = ""     # Token de integração e.Rede
    # Valor padrão da receita quando o CRM não retorna o preço (configurável por .env)
    payment_default_amount: float = 150.00
    # Percentual de desconto no PIX (ex: 5.0 = 5%)
    pix_discount_pct: float = 5.0

    # --- WhatsApp resilência ---
    # Número máximo de tentativas de envio antes de desistir
    whatsapp_max_retries: int = 3

    # --- Segurança ---
    # Segredo para validar assinatura HMAC-SHA256 do webhook do CRM
    # Se vazio, a verificação é ignorada (útil em desenvolvimento)
    webhook_secret: str = ""
    # Limite de requisições ao /webhook por IP por minuto em produção
    webhook_rate_limit: str = "60/minute"

    # --- Banco de dados ---
    database_url: str = "sqlite:///nanoassist.db"

    # --- Ambiente ---
    app_env: str = "development"
    log_level: str = "INFO"
    # Origens permitidas no CORS — separadas por vírgula
    # Desenvolvimento: * (qualquer origem)
    # Produção: "https://seudominio.com.br,https://www.seudominio.com.br"
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
