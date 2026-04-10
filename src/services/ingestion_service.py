"""
Ingestion Service — pipeline di indicizzazione email.

Orchestrazione pura: non conosce HTTP, file system o UI.
Coordina GraphClient → OllamaClient → VectorStore.

Il service è testabile in isolamento passando client mockati nel costruttore
(Dependency Injection): nessuna chiamata di rete necessaria nei test unitari.
"""

import logging
import time
from dataclasses import dataclass

from src.clients.graph_client import GraphClient
from src.clients.ollama_client import OllamaClient
from src.clients.vectorstore import VectorStore
from src.config.settings import settings

logger = logging.getLogger(__name__)

_EMBED_CHAR_LIMIT = 4000   # Limite caratteri per l'embedding
_RATE_LIMIT_SLEEP = 0.05   # Secondi di pausa tra embed per non sovraccaricare Ollama


@dataclass
class IngestionReport:
    """Risultato dell'indicizzazione, restituito all'entry point per la stampa finale."""
    total_fetched: int
    added: int
    skipped: int
    errors: int


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

    def run(self) -> IngestionReport:
        """
        Esegue la pipeline completa:
        1. Verifica Ollama e modello disponibile
        2. Scarica email da Microsoft 365
        3. Filtra quelle già indicizzate (idempotenza)
        4. Genera embedding e salva in ChromaDB
        5. Restituisce un report con le statistiche
        """
        self._ollama.check_model()

        emails = self._graph.fetch_emails(settings.max_emails)
        existing_ids = self._store.get_existing_ids()
        new_emails = [e for e in emails if e.id not in existing_ids]
        skipped = len(emails) - len(new_emails)

        if not new_emails:
            logger.info("Tutte le email sono già indicizzate. Nulla da fare.")
            return IngestionReport(
                total_fetched=len(emails),
                added=0,
                skipped=skipped,
                errors=0,
            )

        logger.info(
            "Indicizzazione di %d nuove email (%d già presenti saltate)...",
            len(new_emails),
            skipped,
        )

        added, errors = 0, 0
        for i, email in enumerate(new_emails, start=1):
            print(f"  [{i:>3}/{len(new_emails)}] {email.subject[:65]}", end="\r")
            try:
                embedding = self._ollama.embed(email.to_document()[:_EMBED_CHAR_LIMIT])
                self._store.add(email, embedding)
                added += 1
            except Exception as exc:
                errors += 1
                logger.error("Errore su '%s': %s", email.subject[:40], exc)
            time.sleep(_RATE_LIMIT_SLEEP)

        return IngestionReport(
            total_fetched=len(emails),
            added=added,
            skipped=skipped,
            errors=errors,
        )
