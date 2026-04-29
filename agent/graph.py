from langgraph.graph import StateGraph, END
from agent.state import AgentState, ConversationStep
from agent.nodes.menu import node_menu
from agent.nodes.flow1 import (node_f1_buscar, node_f1_confirmar,
                                 node_f1_pagamento, node_f1_comprovante,
                                 node_f1_finalizar)
from agent.nodes.flow2 import node_f2_coletar, node_f2_validar
from agent.nodes.ai_fallback import node_ai_fallback

STEP_TO_NODE = {
    ConversationStep.INITIAL: "menu",
    ConversationStep.MENU: "menu",
    ConversationStep.F1_AGUARDANDO_ID: "f1_buscar",
    ConversationStep.F1_CONFIRMANDO_RECEITA: "f1_confirmar",
    ConversationStep.F1_AGUARDANDO_PAGAMENTO: "f1_pagamento",
    ConversationStep.F1_AGUARDANDO_COMPROVANTE: "f1_comprovante",
    ConversationStep.F1_CONFIRMACAO_FINAL: "f1_finalizar",
    ConversationStep.F2_COLETANDO_DADOS: "f2_coletar",
    ConversationStep.F2_VALIDANDO_DADOS: "f2_validar",
    ConversationStep.AGUARDANDO_HUMANO: "menu",  # reset para novo atendimento
}

def router(state: AgentState) -> str:
    return STEP_TO_NODE.get(state["step"], "ai_fallback")

def build_graph(checkpointer=None) -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("menu", node_menu)
    g.add_node("f1_buscar", node_f1_buscar)
    g.add_node("f1_confirmar", node_f1_confirmar)
    g.add_node("f1_pagamento", node_f1_pagamento)
    g.add_node("f1_comprovante", node_f1_comprovante)
    g.add_node("f1_finalizar", node_f1_finalizar)
    g.add_node("f2_coletar", node_f2_coletar)
    g.add_node("f2_validar", node_f2_validar)
    g.add_node("ai_fallback", node_ai_fallback)

    g.set_conditional_entry_point(router)

    for node in ["menu","f1_buscar","f1_confirmar","f1_pagamento",
                 "f1_comprovante","f1_finalizar","f2_coletar","f2_validar","ai_fallback"]:
        g.add_edge(node, END)

    return g.compile(checkpointer=checkpointer)
