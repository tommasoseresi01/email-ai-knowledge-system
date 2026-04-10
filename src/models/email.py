"""
Modello dati Email.

Unica definizione di cosa è un'Email in tutto il sistema.
Ogni livello (clients, services, ui) usa questo dataclass —
nessun dict grezzo dalla Graph API circola oltre il GraphClient.

Vantaggi:
- Type safety: niente più .get("from", {}).get("emailAddress", {})
- Fase 1.1 (corpo completo): si aggiorna solo questo file
- Testabilità: si creano Email di test in una riga
"""

from dataclasses import dataclass, field


@dataclass
class Email:
    id: str                          # Microsoft Graph message ID (chiave di deduplicazione)
    sender: str                      # "Nome <email@dominio.com>"
    subject: str                     # Oggetto dell'email
    date: str                        # "YYYY-MM-DD"
    body: str                        # Testo per l'embedding semantico
    preview: str                     # Anteprima breve per la UI
    conversation_id: str | None = field(default=None)  # Per raggruppare thread (Fase 1.2)

    def to_document(self) -> str:
        """
        Testo indicizzato in ChromaDB e usato per la ricerca semantica.
        Modificare qui per cambiare cosa viene indicizzato (es. Fase 1.1: body completo).
        """
        return (
            f"Da: {self.sender}\n"
            f"Data: {self.date}\n"
            f"Oggetto: {self.subject}\n\n"
            f"{self.body}"
        )

    def to_metadata(self) -> dict:
        """
        Metadata salvato accanto all'embedding in ChromaDB.
        Visibile nell'UI come riferimento sorgente della risposta.
        """
        return {
            "from": self.sender,
            "subject": self.subject,
            "date": self.date,
            "preview": self.preview[:300],
        }
