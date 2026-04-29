import pytest
from agent.state import ConversationStep
from agent.graph import router

def make_state(step):
    return {"phone": "5511999999999", "message": "", "step": step,
            "user_data": {}, "response": "", "media_url": None}

def test_router_initial():
    assert router(make_state(ConversationStep.INITIAL)) == "menu"

def test_router_menu():
    assert router(make_state(ConversationStep.MENU)) == "menu"

def test_router_f1_id():
    assert router(make_state(ConversationStep.F1_AGUARDANDO_ID)) == "f1_buscar"

def test_router_f1_confirm():
    assert router(make_state(ConversationStep.F1_CONFIRMANDO_RECEITA)) == "f1_confirmar"

def test_router_f1_payment():
    assert router(make_state(ConversationStep.F1_AGUARDANDO_PAGAMENTO)) == "f1_pagamento"

def test_router_f1_comprovante():
    assert router(make_state(ConversationStep.F1_AGUARDANDO_COMPROVANTE)) == "f1_comprovante"

def test_router_f1_final():
    assert router(make_state(ConversationStep.F1_CONFIRMACAO_FINAL)) == "f1_finalizar"

def test_router_f2_coletar():
    assert router(make_state(ConversationStep.F2_COLETANDO_DADOS)) == "f2_coletar"

def test_router_f2_validar():
    assert router(make_state(ConversationStep.F2_VALIDANDO_DADOS)) == "f2_validar"
