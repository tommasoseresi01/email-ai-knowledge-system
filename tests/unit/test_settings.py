"""
Test unitari per src/config/settings.py

Verifica che le Settings carichino correttamente i valori di default
e che i tipi siano validati (Pydantic).
"""

from src.config.settings import Settings


class TestSettingsDefaults:
    def test_default_tenant_id(self):
        # Con solo AZURE_CLIENT_ID fornito, gli altri hanno i default corretti
        s = Settings(azure_client_id="test-client-id")
        assert s.azure_tenant_id == "consumers"

    def test_default_ollama_url(self):
        s = Settings(azure_client_id="test-client-id")
        assert s.ollama_url == "http://localhost:11434"

    def test_default_embed_model(self):
        s = Settings(azure_client_id="test-client-id")
        assert s.embed_model == "nomic-embed-text"

    def test_default_max_emails_is_int(self):
        s = Settings(azure_client_id="test-client-id")
        assert isinstance(s.max_emails, int)
        assert s.max_emails == 300

    def test_default_top_k(self):
        s = Settings(azure_client_id="test-client-id")
        assert s.top_k == 5

    def test_override_values(self):
        s = Settings(
            azure_client_id="my-id",
            max_emails=100,
            llm_model="mixtral",
        )
        assert s.max_emails == 100
        assert s.llm_model == "mixtral"
