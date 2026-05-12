import pytest
from unittest.mock import AsyncMock, patch

from agent.state import ConversationStep
from agent.nodes.menu import node_menu
from agent.nodes.flow1 import (
    _extract_cpf_and_recipe_code,
    node_f1_buscar,
    node_f1_confirmar,
    node_f1_pagamento,
    node_f1_comprovante,
    node_f1_finalizar,
)
from agent.nodes.flow2 import node_f2_coletar, node_f2_validar


def s(step, message, user_data=None):
    return {
        "phone": "5511999999999",
        "message": message,
        "step": step,
        "user_data": user_data or {},
        "response": "",
        "media_url": None,
    }


@pytest.mark.asyncio
async def test_initial_shows_greeting():
    result = await node_menu(s(ConversationStep.INITIAL, "oi"))
    assert "NanoAssist" in result["response"]
    assert result["step"] == ConversationStep.MENU


@pytest.mark.asyncio
async def test_menu_option1_goes_to_f1():
    result = await node_menu(s(ConversationStep.MENU, "1"))
    assert result["step"] == ConversationStep.F1_AGUARDANDO_ID
    assert "Codigo/ID da Receita" in result["response"]
    assert "CPF do Titular" in result["response"]


@pytest.mark.asyncio
async def test_menu_option2_goes_to_f2():
    result = await node_menu(s(ConversationStep.MENU, "2"))
    assert result["step"] == ConversationStep.F2_COLETANDO_DADOS


@pytest.mark.asyncio
async def test_menu_invalid_stays_on_menu():
    result = await node_menu(s(ConversationStep.MENU, "xyz"))
    assert result["step"] == ConversationStep.MENU


@pytest.mark.asyncio
async def test_f1_buscar_found():
    mock_result = {
        "found": True,
        "recipe": {
            "id": "RX-001",
            "patient": "Joao",
            "formula": "Prog 100mg",
            "dosage": "1/dia",
        },
    }
    with patch(
        "agent.nodes.flow1.crm_client.search_recipe_by_cpf_and_code",
        AsyncMock(return_value=mock_result),
    ) as search_mock:
        result = await node_f1_buscar(
            s(ConversationStep.F1_AGUARDANDO_ID, "Codigo: RX-001\nCPF: 123.456.789-00")
        )
    assert result["step"] == ConversationStep.F1_CONFIRMANDO_RECEITA
    assert "RX-001" in result["response"]
    search_mock.assert_awaited_once_with("12345678900", "RX-001")


@pytest.mark.asyncio
async def test_f1_buscar_not_found():
    with patch(
        "agent.nodes.flow1.crm_client.search_recipe_by_cpf_and_code",
        AsyncMock(return_value={"found": False}),
    ):
        result = await node_f1_buscar(
            s(ConversationStep.F1_AGUARDANDO_ID, "Codigo: RX-999\nCPF: 12345678900")
        )
    assert result["step"] == ConversationStep.F1_AGUARDANDO_ID


@pytest.mark.asyncio
async def test_f1_buscar_requires_cpf_and_recipe_code():
    with patch("agent.nodes.flow1.crm_client.search_recipe_by_cpf_and_code", AsyncMock()) as search_mock:
        result = await node_f1_buscar(s(ConversationStep.F1_AGUARDANDO_ID, "Joao Silva"))
    assert result["step"] == ConversationStep.F1_AGUARDANDO_ID
    assert "CPF" in result["response"]
    assert search_mock.await_count == 0


def test_extract_cpf_and_recipe_code_from_single_message():
    assert _extract_cpf_and_recipe_code("CPF 123.456.789-00 Codigo RX-001") == (
        "12345678900",
        "RX-001",
    )


@pytest.mark.asyncio
async def test_f1_buscar_session_expired_transfers():
    with patch(
        "agent.nodes.flow1.crm_client.search_recipe_by_cpf_and_code",
        AsyncMock(return_value={"found": False, "recipe": None, "error": "session_expired"}),
    ):
        result = await node_f1_buscar(
            s(ConversationStep.F1_AGUARDANDO_ID, "Codigo: RX-001\nCPF: 12345678900")
        )
    assert result["step"] == ConversationStep.AGUARDANDO_HUMANO
    assert "especialista humano" in result["response"]


@pytest.mark.asyncio
async def test_f1_buscar_service_unavailable_transfers():
    with patch(
        "agent.nodes.flow1.crm_client.search_recipe_by_cpf_and_code",
        AsyncMock(return_value={"found": False, "recipe": None, "error": "service_unavailable"}),
    ):
        result = await node_f1_buscar(
            s(ConversationStep.F1_AGUARDANDO_ID, "Codigo: RX-001\nCPF: 12345678900")
        )
    assert result["step"] == ConversationStep.AGUARDANDO_HUMANO
    assert "indisponivel" in result["response"].lower()


@pytest.mark.asyncio
async def test_f1_buscar_security_validation_unavailable_transfers():
    with patch(
        "agent.nodes.flow1.crm_client.search_recipe_by_cpf_and_code",
        AsyncMock(return_value={"found": False, "recipe": None, "error": "security_validation_unavailable"}),
    ):
        result = await node_f1_buscar(
            s(ConversationStep.F1_AGUARDANDO_ID, "Codigo: RX-001\nCPF: 12345678900")
        )
    assert result["step"] == ConversationStep.AGUARDANDO_HUMANO
    assert "validar o CPF" in result["response"]


@pytest.mark.asyncio
async def test_f1_confirmar_sim():
    result = await node_f1_confirmar(s(ConversationStep.F1_CONFIRMANDO_RECEITA, "SIM"))
    assert result["step"] == ConversationStep.F1_AGUARDANDO_PAGAMENTO


@pytest.mark.asyncio
async def test_f1_confirmar_nao():
    result = await node_f1_confirmar(s(ConversationStep.F1_CONFIRMANDO_RECEITA, "NAO"))
    assert result["step"] == ConversationStep.INITIAL


@pytest.mark.asyncio
async def test_f1_pagamento_pix():
    mock_payment = {"payment_url": "https://pay.ex", "pix_code": "00020126...", "amount": 142.50}
    with patch("agent.nodes.flow1.payment_client.create_charge", AsyncMock(return_value=mock_payment)):
        result = await node_f1_pagamento(
            s(ConversationStep.F1_AGUARDANDO_PAGAMENTO, "1", {"recipe": {"patient": "Joao"}})
        )
    assert result["step"] == ConversationStep.F1_AGUARDANDO_COMPROVANTE
    assert "PIX" in result["response"]


@pytest.mark.asyncio
async def test_f1_finalizar_confirmar():
    result = await node_f1_finalizar(s(ConversationStep.F1_CONFIRMACAO_FINAL, "CONFIRMAR"))
    assert result["step"] == ConversationStep.INITIAL
    assert "Pedido confirmado" in result["response"]


@pytest.mark.asyncio
async def test_f2_coletar_stores_data():
    result = await node_f2_coletar(s(ConversationStep.F2_COLETANDO_DADOS, "Nome: Joao\nCPF: 123"))
    assert result["step"] == ConversationStep.F2_VALIDANDO_DADOS
    assert result["user_data"]["raw_data"] != ""


@pytest.mark.asyncio
async def test_f2_validar_sim_transfers():
    result = await node_f2_validar(s(ConversationStep.F2_VALIDANDO_DADOS, "SIM, TUDO CORRETO"))
    assert result["step"] == ConversationStep.AGUARDANDO_HUMANO


@pytest.mark.asyncio
async def test_f2_validar_alterar():
    result = await node_f2_validar(s(ConversationStep.F2_VALIDANDO_DADOS, "ALTERAR"))
    assert result["step"] == ConversationStep.F2_COLETANDO_DADOS
