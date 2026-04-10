"""
Test unitari per src/models/email.py
"""

from src.models.email import Email


def make_email(**kwargs) -> Email:
    """Factory per creare Email di test con valori di default sensati."""
    defaults = {
        "id": "test-id-123",
        "sender": "Mario Rossi <mario@example.com>",
        "subject": "Oggetto di test",
        "date": "2024-01-15",
        "body": "Corpo completo dell'email di test con contenuto rilevante.",
        "preview": "Corpo completo dell'email di test...",
    }
    return Email(**{**defaults, **kwargs})


class TestEmailToDocument:
    def test_contains_all_fields(self):
        email = make_email()
        doc = email.to_document()
        assert "Mario Rossi" in doc
        assert "Oggetto di test" in doc
        assert "2024-01-15" in doc
        assert "Corpo completo" in doc

    def test_format_structure(self):
        email = make_email()
        doc = email.to_document()
        assert doc.startswith("Da:")
        assert "Data:" in doc
        assert "Oggetto:" in doc

    def test_empty_body(self):
        email = make_email(body="")
        doc = email.to_document()
        assert "Oggetto di test" in doc

    def test_includes_attachment_text(self):
        email = make_email(attachments_text="Contenuto del PDF allegato")
        doc = email.to_document()
        assert "[ALLEGATI]" in doc
        assert "Contenuto del PDF allegato" in doc

    def test_no_attachment_section_when_empty(self):
        email = make_email(attachments_text="")
        doc = email.to_document()
        assert "[ALLEGATI]" not in doc


class TestEmailToMetadata:
    def test_keys_present(self):
        email = make_email()
        meta = email.to_metadata()
        assert set(meta.keys()) == {"from", "subject", "date", "preview", "has_attachments"}

    def test_preview_truncated_at_500(self):
        long_preview = "x" * 700
        email = make_email(preview=long_preview)
        meta = email.to_metadata()
        assert len(meta["preview"]) == 500

    def test_short_preview_not_truncated(self):
        email = make_email(preview="breve")
        meta = email.to_metadata()
        assert meta["preview"] == "breve"

    def test_sender_mapped_to_from_key(self):
        email = make_email(sender="Luca Bianchi <luca@example.com>")
        meta = email.to_metadata()
        assert meta["from"] == "Luca Bianchi <luca@example.com>"

    def test_has_attachments_flag(self):
        email_with = make_email(attachments_text="testo allegato")
        assert email_with.to_metadata()["has_attachments"] == "true"

        email_without = make_email(attachments_text="")
        assert email_without.to_metadata()["has_attachments"] == "false"
