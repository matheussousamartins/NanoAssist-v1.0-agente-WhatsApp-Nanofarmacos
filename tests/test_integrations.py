import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app
from config.settings import settings
from agent.tools.crm import crm_client
from agent.tools.payment import payment_client
from agent.tools.whatsapp import whatsapp_client


def test_health_endpoint():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "NanoAssist"


def test_chat_test_page_available():
    with TestClient(app) as client:
        resp = client.get("/chat-test")
    assert resp.status_code == 200
    assert "NanoAssist Chat Test" in resp.text


def test_webhook_rejects_blank_payload():
    with TestClient(app) as client:
        resp = client.post("/webhook", json={"number": "  ", "body": "  "})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "number e body são obrigatórios"


def test_webhook_accepts_dix_message_received_payload():
    dix_payload = {
        "eventType": "MESSAGE_RECEIVED",
        "content": {
            "text": "oi",
            "direction": "TO_HUB",
            "details": {"from": "5511999991111", "to": "5511999990000", "file": None},
        },
    }
    with patch("main.whatsapp_client.send_message", AsyncMock(return_value=True)) as send_mock:
        with TestClient(app) as client:
            resp = client.post("/webhook", json=dix_payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert send_mock.await_count == 1


def test_webhook_ignores_dix_outbound_payload():
    dix_payload = {
        "eventType": "MESSAGE_SENT",
        "content": {
            "text": "mensagem do agente",
            "direction": "TO_HUB",
            "details": {"from": "5511999990000", "to": "5511999991111"},
        },
    }
    with patch("main.whatsapp_client.send_message", AsyncMock(return_value=True)) as send_mock:
        with TestClient(app) as client:
            resp = client.post("/webhook", json=dix_payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert "ignored_event_type" in resp.json()["reason"]
    assert send_mock.await_count == 0


def test_webhook_ignores_non_message_received_events():
    dix_payload = {
        "eventType": "MESSAGE_UPDATED",
        "content": {
            "text": "status update",
            "direction": "TO_HUB",
            "details": {"from": "5511999990000", "to": "5511999991111"},
        },
    }
    with patch("main.whatsapp_client.send_message", AsyncMock(return_value=True)) as send_mock:
        with TestClient(app) as client:
            resp = client.post("/webhook", json=dix_payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert "ignored_event_type" in resp.json()["reason"]
    assert send_mock.await_count == 0


def test_webhook_persists_state_between_messages():
    with patch("main.whatsapp_client.send_message", AsyncMock(return_value=True)) as send_mock:
        with TestClient(app) as client:
            first = client.post("/webhook", json={"number": "5511999991111", "body": "oi"})
            second = client.post("/webhook", json={"number": "5511999991111", "body": "1"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert send_mock.await_count == 2
    first_msg = send_mock.await_args_list[0].args[1]
    second_msg = send_mock.await_args_list[1].args[1]
    assert "NanoAssist" in first_msg
    assert "ID da Receita" in second_msg


def test_webhook_test_returns_agent_response_without_whatsapp_send():
    with patch("main.whatsapp_client.send_message", AsyncMock(return_value=True)) as send_mock:
        with TestClient(app) as client:
            resp = client.post("/webhook/test", json={"number": "5511999991112", "body": "oi"})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert "NanoAssist" in payload["response"]
    assert send_mock.await_count == 0


@pytest.mark.asyncio
async def test_crm_search_recipe_by_name(httpx_mock, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "receitaface_mock_enabled", False)
    monkeypatch.setattr(crm_client, "nanocare_url", "https://api.nanocare.com.br/api")
    monkeypatch.setattr(crm_client, "nanocare_token", "nck_token-valido")
    monkeypatch.setattr(crm_client, "session_cookie", "")

    recipe_id = "822c9af2-c073-482b-9294-e23d18fb4002"
    httpx_mock.add_response(
        method="GET",
        url=f"https://api.nanocare.com.br/api/integrations/recipes?patientName=Maria",
        json={
            "found": True,
            "recipes": [{"id": recipe_id, "patient_name": "Maria Silva", "status": "active"}],
            "pagination": {"page": 1, "page_size": 20, "total": 1},
        },
        status_code=200,
    )
    httpx_mock.add_response(
        method="GET",
        url=f"https://api.nanocare.com.br/api/integrations/recipes/{recipe_id}",
        json={
            "found": True,
            "recipe": {
                "id": recipe_id,
                "patient": {"name": "Maria Silva", "cpf": None},
                "status": "active",
                "formula": "Progesterona 100mg",
                "dosage": "1 capsula/dia",
                "items": [],
                "prescriber": {"name": "Dra. Camila Souza", "registry": "CRM-SC 100001"},
                "created_at": "2026-04-24T05:48:05Z",
                "expires_at": "2026-05-24T13:48:05Z",
            },
        },
        status_code=200,
    )

    result = await crm_client.search_recipe("Maria")
    assert result["found"] is True
    assert result["recipe"]["id"] == recipe_id
    assert result["recipe"]["patient"] == "Maria Silva"
    assert result["recipe"]["formula"] == "Progesterona 100mg"


@pytest.mark.asyncio
async def test_crm_search_recipe_by_uuid(httpx_mock, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "receitaface_mock_enabled", False)
    monkeypatch.setattr(crm_client, "nanocare_url", "https://api.nanocare.com.br/api")
    monkeypatch.setattr(crm_client, "nanocare_token", "nck_token-valido")
    monkeypatch.setattr(crm_client, "session_cookie", "")

    recipe_id = "822c9af2-c073-482b-9294-e23d18fb4002"
    httpx_mock.add_response(
        method="GET",
        url=f"https://api.nanocare.com.br/api/integrations/recipes/{recipe_id}",
        json={
            "found": True,
            "recipe": {
                "id": recipe_id,
                "patient": {"name": "Eduardo Nunes", "cpf": None},
                "status": "active",
                "formula": "Formula Relax Nano",
                "dosage": "1 sachê/dia",
                "items": [],
                "prescriber": {"name": "Dra. Camila Souza", "registry": "CRM-SC 100001"},
                "created_at": "2026-04-24T05:48:05Z",
                "expires_at": "2026-05-24T13:48:05Z",
            },
        },
        status_code=200,
    )

    result = await crm_client.search_recipe(recipe_id)
    assert result["found"] is True
    assert result["recipe"]["patient"] == "Eduardo Nunes"


@pytest.mark.asyncio
async def test_crm_search_recipe_expired_returns_error(httpx_mock, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "receitaface_mock_enabled", False)
    monkeypatch.setattr(crm_client, "nanocare_url", "https://api.nanocare.com.br/api")
    monkeypatch.setattr(crm_client, "nanocare_token", "nck_token-valido")
    monkeypatch.setattr(crm_client, "session_cookie", "")

    recipe_id = "822c9af2-c073-482b-9294-e23d18fb4099"
    httpx_mock.add_response(
        method="GET",
        url=f"https://api.nanocare.com.br/api/integrations/recipes/{recipe_id}",
        json={
            "found": True,
            "recipe": {
                "id": recipe_id,
                "patient": {"name": "Carlos Viana", "cpf": None},
                "status": "expired",
                "formula": "Vitamina D",
                "dosage": "1 capsula/dia",
                "items": [],
                "prescriber": None,
                "created_at": "2026-03-01T00:00:00Z",
                "expires_at": "2026-04-01T00:00:00Z",
            },
        },
        status_code=200,
    )

    result = await crm_client.search_recipe(recipe_id)
    assert result["found"] is False
    assert result["error"] == "recipe_expired"


@pytest.mark.asyncio
async def test_payment_create_pix_success(httpx_mock, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "pix_discount_pct", 5.0)
    monkeypatch.setattr(payment_client, "pv", "1234567")
    monkeypatch.setattr(payment_client, "token", "rede-integration-token")
    httpx_mock.add_response(
        method="POST",
        url="https://api.userede.com.br/erede/v1/transactions",
        json={
            "returnCode": "00",
            "returnMessage": "SUCCESS",
            "tid": "TID-001",
            "amount": 14250,
            "pix": {
                "qrCode": "00020126580014BR.GOV.BCB.PIX",
                "qrCodeUrl": "https://pix.userede.com.br/qr/001",
            },
        },
        status_code=200,
    )

    result = await payment_client.create_charge("Maria Silva", 150.0, "PIX")
    assert result.get("error") is None
    assert result["pix_code"] == "00020126580014BR.GOV.BCB.PIX"
    assert result["amount"] == 142.5  # 150 com 5% de desconto
    assert result["tid"] == "TID-001"


@pytest.mark.asyncio
async def test_payment_create_link_success(httpx_mock, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(payment_client, "pv", "1234567")
    monkeypatch.setattr(payment_client, "token", "rede-integration-token")
    httpx_mock.add_response(
        method="POST",
        url="https://api.userede.com.br/erede/v1/transactions/links",
        json={
            "returnCode": "00",
            "returnMessage": "SUCCESS",
            "paymentUrl": "https://checkout.userede.com.br/link/abc123",
            "amount": 15000,
        },
        status_code=200,
    )

    result = await payment_client.create_charge("Maria Silva", 150.0, "LINK")
    assert result.get("error") is None
    assert result["payment_url"] == "https://checkout.userede.com.br/link/abc123"
    assert result["amount"] == 150.0


@pytest.mark.asyncio
async def test_payment_rede_error_code_returns_error(httpx_mock, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(payment_client, "pv", "1234567")
    monkeypatch.setattr(payment_client, "token", "rede-integration-token")
    httpx_mock.add_response(
        method="POST",
        url="https://api.userede.com.br/erede/v1/transactions",
        json={"returnCode": "57", "returnMessage": "Transaction not permitted"},
        status_code=200,
    )

    result = await payment_client.create_charge("Maria Silva", 150.0, "PIX")
    assert result.get("error") == "rede_57"


@pytest.mark.asyncio
async def test_payment_invalid_amount_returns_error(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(payment_client, "pv", "1234567")
    monkeypatch.setattr(payment_client, "token", "rede-integration-token")

    result = await payment_client.create_charge("Maria Silva", 0.0, "PIX")
    assert result.get("error") == "amount_zero_or_negative"


@pytest.mark.asyncio
async def test_whatsapp_send_message_success(httpx_mock, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(whatsapp_client, "provider", "dix")
    monkeypatch.setattr(whatsapp_client, "token", "wa-token")
    monkeypatch.setattr(whatsapp_client, "base_url", "https://api.dixcrm.example")
    monkeypatch.setattr(whatsapp_client, "send_path", "/api/messages/send")
    httpx_mock.add_response(
        method="POST",
        url="https://api.dixcrm.example/api/messages/send",
        status_code=200,
    )

    ok = await whatsapp_client.send_message("5511999999999", "Teste")
    assert ok is True


@pytest.mark.asyncio
async def test_crm_mock_search_recipe_match(monkeypatch):
    monkeypatch.setattr(settings, "receitaface_mock_enabled", True)
    result = await crm_client.search_recipe("maria")
    assert result["found"] is True
    assert result["recipe"]["id"] == "RX-MOCK-001"


@pytest.mark.asyncio
async def test_crm_mock_search_recipe_timeout_scenario(monkeypatch):
    monkeypatch.setattr(settings, "receitaface_mock_enabled", True)
    result = await crm_client.search_recipe("timeout")
    assert result["found"] is False
    assert result["error"] == "timeout"


@pytest.mark.asyncio
async def test_crm_search_recipe_session_mode_success(httpx_mock, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "receitaface_mock_enabled", False)
    monkeypatch.setattr(crm_client, "use_session", True)
    monkeypatch.setattr(crm_client, "session_cookie", "_csrf=abc; _session_id=def")
    monkeypatch.setattr(crm_client, "base_url", "https://app.receitaface.com.br")
    monkeypatch.setattr(crm_client, "list_path", "/receita/data/todas")
    monkeypatch.setattr(crm_client, "details_path", "/receita/visualizar/detalhes")
    monkeypatch.setattr(crm_client, "page_length", 10)

    httpx_mock.add_response(
        method="GET",
        json={
            "data": [
                {"id": "65", "paciente": "Maria aparecida Alves da Silva"},
            ]
        },
        status_code=200,
    )
    httpx_mock.add_response(
        method="GET",
        url="https://app.receitaface.com.br/receita/visualizar/detalhes?id=65",
        text="""
        <html>
          <p>Paciente: <span>Maria aparecida Alves da Silva</span></p>
          <div id="itens-content">
            <h4 class="font-semibold text-lg text-base-content">PROGESTERONA 100mg</h4>
            <p class="text-sm text-base-content/60">Tipo: Creme</p>
            <p class="text-sm text-base-content/60">Aplicar 1 dose ao dia.</p>
          </div>
        </html>
        """,
        headers={"Content-Type": "text/html; charset=UTF-8"},
        status_code=200,
    )

    result = await crm_client.search_recipe("Maria")
    assert result["found"] is True
    assert result["recipe"]["id"] == "65"
    assert "Maria" in result["recipe"]["patient"]
    assert "PROGESTERONA" in result["recipe"]["formula"]
    assert "Aplicar 1 dose ao dia." in result["recipe"]["dosage"]


@pytest.mark.asyncio
async def test_crm_search_recipe_session_mode_not_found(httpx_mock, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "receitaface_mock_enabled", False)
    monkeypatch.setattr(crm_client, "use_session", True)
    monkeypatch.setattr(crm_client, "session_cookie", "_csrf=abc; _session_id=def")
    monkeypatch.setattr(crm_client, "base_url", "https://app.receitaface.com.br")
    monkeypatch.setattr(crm_client, "list_path", "/receita/data/todas")

    httpx_mock.add_response(
        method="GET",
        json={"data": []},
        status_code=200,
    )

    result = await crm_client.search_recipe("Paciente inexistente")
    assert result["found"] is False
    assert result["recipe"] is None
