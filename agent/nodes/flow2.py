from agent.state import AgentState, ConversationStep

TRANSFER_MSG = """✅ Dados validados com sucesso!

Estou transferindo para um *especialista humano* que irá:
• Analisar sua receita
• Informar o valor final
• Apresentar condições de pagamento

O atendimento automatizado foi encerrado. A *Nanofármacos* agradece! 🌿"""

async def node_f2_coletar(state: AgentState) -> AgentState:
    response = "✅ Dados recebidos!\n\nPor favor, *revise as informações* enviadas.\n\nEstão corretas?\n\nDigite *SIM, TUDO CORRETO* para confirmar.\nDigite *ALTERAR* para corrigir algum campo."
    return {**state,
            "response": response,
            "step": ConversationStep.F2_VALIDANDO_DADOS,
            "user_data": {**state["user_data"], "raw_data": state["message"],
                          "media_url": state.get("media_url")}}

async def node_f2_validar(state: AgentState) -> AgentState:
    msg = state["message"].strip().upper()
    if "SIM" in msg and "CORRETO" in msg:
        return {**state, "response": TRANSFER_MSG, "step": ConversationStep.AGUARDANDO_HUMANO}
    elif "ALTERAR" in msg:
        return {**state,
                "response": "Reenvie os dados corrigidos junto com a receita em PDF.",
                "step": ConversationStep.F2_COLETANDO_DADOS}
    else:
        return {**state,
                "response": "Digite *SIM, TUDO CORRETO* para confirmar ou *ALTERAR* para corrigir.",
                "step": ConversationStep.F2_VALIDANDO_DADOS}
