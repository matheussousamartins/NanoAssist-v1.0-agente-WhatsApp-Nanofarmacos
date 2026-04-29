import pytest


@pytest.fixture(autouse=True)
def clear_webhook_secret(monkeypatch):
    """Disable HMAC signature verification in all tests."""
    from config.settings import settings
    monkeypatch.setattr(settings, "webhook_secret", "")
