"""
Test unitari per src/models/email.py

Questi test non richiedono connessioni di rete né dipendenze esterne.
Verificano che il dataclass Email produca i formati corretti per
l'indicizzazione (to_document) e la UI (to_metadata).
"""

from src.models.email import Email


def make_email(**kwargs) -> Email:
    """Factory per creare Email di test con valori di default sensati."""
    defaults = {
        "id": "test-id-123",
        "sender": "Mario Rossi <mario@example.com>",
        "subject": "Oggetto di test",
        "date": "2024-01-15",
        "body": "Corpo dell'email di test con contenuto rilevante.",
        "preview": "Corpo dell'email di test...",
    }
    return Email(**{**defaults, **kwargs})


class TestEmailToDocument:
    def test_contains_all_fields(self):
        email = make_email()
        doc = email.to_document()
        assert "Mario Rossi" in doc
        assert "Oggetto di test" in doc
        assert "2024-01-15" in doc
        assert "Corpo dell'email" in doc

    def test_format_structure(self):
        email = make_email()
        doc = email.to_document()
        assert doc.startswith("Da:")
        assert "Data:" in doc
        assert "Oggetto:" in doc

    def test_empty_body(self):
        email = make_email(body="")
        doc = email.to_document()
        assert "Oggetto di test" in doc  # deve funzionare anche con body vuoto


class TestEmailToMetadata:
    def test_keys_present(self):
        email = make_email()
        meta = email.to_metadata()
        assert set(meta.keys()) == {"from", "subject", "date", "preview"}

    def test_preview_truncated_at_300(self):
        long_preview = "x" * 500
        email = make_email(preview=long_preview)
        meta = email.to_metadata()
        assert len(meta["preview"]) == 300

    def test_short_preview_not_truncated(self):
        email = make_email(preview="breve")
        meta = email.to_metadata()
        assert meta["preview"] == "breve"

    def test_sender_mapped_to_from_key(self):
        email = make_email(sender="Luca Bianchi <luca@example.com>")
        meta = email.to_metadata()
        assert meta["from"] == "Luca Bianchi <luca@example.com>"
