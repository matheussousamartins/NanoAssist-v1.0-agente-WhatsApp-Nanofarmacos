from enum import Enum
from typing import Optional, TypedDict

class ConversationStep(str, Enum):
    INITIAL = "INITIAL"
    MENU = "MENU"
    F1_AGUARDANDO_ID = "F1_AGUARDANDO_ID"
    F1_CONFIRMANDO_RECEITA = "F1_CONFIRMANDO_RECEITA"
    F1_AGUARDANDO_PAGAMENTO = "F1_AGUARDANDO_PAGAMENTO"
    F1_AGUARDANDO_COMPROVANTE = "F1_AGUARDANDO_COMPROVANTE"
    F1_CONFIRMACAO_FINAL = "F1_CONFIRMACAO_FINAL"
    F2_COLETANDO_DADOS = "F2_COLETANDO_DADOS"
    F2_VALIDANDO_DADOS = "F2_VALIDANDO_DADOS"
    AGUARDANDO_HUMANO = "AGUARDANDO_HUMANO"

class AgentState(TypedDict):
    phone: str
    message: str
    step: ConversationStep
    user_data: dict
    response: str
    media_url: Optional[str]
