"""
Ingestion Service — pipeline di indicizzazione email.

Orchestrazione pura: non conosce HTTP, file system o UI.
Coordina GraphClient -> OllamaClient -> VectorStore.

Supporta:
- Indicizzazione incrementale (default): aggiunge solo le nuove email
- Re-indicizzazione forzata (force=True): cancella il DB e reindicizza tutto
"""

import logging
import time
from dataclasses import dataclass

from src.clients.graph_client import GraphClient
from src.clients.ollama_client import OllamaClient
from src.clients.vectorstore import VectorStore
from src.config.settings import settings

logger = logging.getLogger(__name__)

_RATE_LIMIT_SLEEP = 0.05   # Secondi tra embedding per non sovraccaricare Ollama


@dataclass
class IngestionReport:
    """Risultato dell'indicizzazione, restituito all'entry point per la stampa finale."""
    total_fetched: int
    added: int
    skipped: int
    errors: int
    cleared: int = 0              # documenti rimossi prima della re-indicizzazione
    with_attachments: int = 0     # email che avevano allegati indicizzati


class IngestionService:
    def __init__(
        self,
        graph: GraphClient,
        ollama: OllamaClient,
        store: VectorStore,
    ) -> None:
        self._graph = graph
        self._ollama = ollama
        self._store = store

    def run(self, force: bool = False) -> IngestionReport:
        """
        Pipeline completa:
        1. Verifica Ollama e modello disponibile
        2. (force) Cancella l'indice esistente per re-indicizzazione
        3. Scarica email da Microsoft 365 (corpo completo + allegati)
        4. Filtra quelle gia indicizzate (idempotenza)
        5. Genera embedding e salva in ChromaDB
        6. Restituisce un report con le statistiche
        """
        self._ollama.check_model()

        cleared = 0
        if force:
            cleared = self._store.clear()
            logger.info("Re-indicizzazione forzata: %d documenti rimossi.", cleared)

        emails = self._graph.fetch_emails(settings.max_emails)
        existing_ids = self._store.get_existing_ids()
        new_emails = [e for e in emails if e.id not in existing_ids]
        skipped = len(emails) - len(new_emails)

        if not new_emails:
            logger.info("Tutte le email sono gia indicizzate. Nulla da fare.")
            return IngestionReport(
                total_fetched=len(emails),
                added=0,
                skipped=skipped,
                errors=0,
                cleared=cleared,
            )

        logger.info(
            "Indicizzazione di %d nuove email (%d gia presenti saltate)...",
            len(new_emails),
            skipped,
        )

        added, errors, with_att = 0, 0, 0
        embed_limit = settings.embed_char_limit

        for i, email in enumerate(new_emails, start=1):
            att_flag = " [+allegati]" if email.attachments_text else ""
            print(
                f"  [{i:>3}/{len(new_emails)}] {email.subject[:60]}{att_flag}",
                end="\r",
            )
            try:
                doc_text = email.to_document()[:embed_limit]
                embedding = self._ollama.embed(doc_text)
                self._store.add(email, embedding)
                added += 1
                if email.attachments_text:
                    with_att += 1
            except Exception as exc:
                errors += 1
                logger.error("Errore su '%s': %s", email.subject[:40], exc)
            time.sleep(_RATE_LIMIT_SLEEP)

        return IngestionReport(
            total_fetched=len(emails),
            added=added,
            skipped=skipped,
            errors=errors,
            cleared=cleared,
            with_attachments=with_att,
        )
