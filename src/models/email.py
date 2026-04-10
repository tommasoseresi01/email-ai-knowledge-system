"""
Modello dati Email.

Unica definizione di cosa è un'Email in tutto il sistema.
Ogni livello (clients, services, ui) usa questo dataclass —
nessun dict grezzo dalla Graph API circola oltre il GraphClient.
"""

from dataclasses import dataclass, field


@dataclass
class Email:
    id: str                          # Microsoft Graph message ID (deduplicazione)
    sender: str                      # "Nome <email@dominio.com>"
    subject: str                     # Oggetto dell'email
    date: str                        # "YYYY-MM-DD"
    body: str                        # Corpo completo (testo pulito, HTML strippato)
    preview: str                     # Anteprima breve per la UI (~255 char)
    conversation_id: str | None = field(default=None)
    attachments_text: str = field(default="")  # Testo estratto dagli allegati

    def to_document(self) -> str:
        """
        Testo indicizzato in ChromaDB e usato per la ricerca semantica.
        Include corpo completo + testo allegati se presenti.
        """
        parts = [
            f"Da: {self.sender}",
            f"Data: {self.date}",
            f"Oggetto: {self.subject}",
            "",
            self.body,
        ]
        if self.attachments_text:
            parts.append(f"\n[ALLEGATI]\n{self.attachments_text}")
        return "\n".join(parts)

    def to_metadata(self) -> dict:
        """
        Metadata salvato accanto all'embedding in ChromaDB.
        Visibile nell'UI come riferimento sorgente della risposta.
        """
        return {
            "from": self.sender,
            "subject": self.subject,
            "date": self.date,
            "preview": self.preview[:500],
            "has_attachments": "true" if self.attachments_text else "false",
        }
