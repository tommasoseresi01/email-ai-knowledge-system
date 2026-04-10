"""
Wrapper ChromaDB (Vector Store).

Responsabilità singola: astrae l'accesso al database vettoriale.
Nessun altro modulo importa chromadb direttamente — tutto passa da qui.

Vantaggi:
- Se si cambia ChromaDB con Qdrant o Pinecone, si modifica solo questo file
- I services vedono solo list[Email], mai oggetti ChromaDB
- La logica di serializzazione/deserializzazione è centralizzata qui
"""

import logging

import chromadb

from src.config.settings import settings
from src.models.email import Email

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "emails"


class VectorStore:
    def __init__(self) -> None:
        client = chromadb.PersistentClient(path=settings.chroma_path)
        self._collection = client.get_or_create_collection(_COLLECTION_NAME)
        logger.debug(
            "VectorStore inizializzato — collezione '%s', %d documenti.",
            _COLLECTION_NAME,
            self._collection.count(),
        )

    # ── Lettura ──────────────────────────────────────────────────────────────

    def get_existing_ids(self) -> set[str]:
        """Restituisce l'insieme degli ID già presenti nel DB (per deduplicazione)."""
        return set(self._collection.get(include=[])["ids"])

    def count(self) -> int:
        """Numero totale di email indicizzate."""
        return self._collection.count()

    def search(self, embedding: list[float], k: int) -> list[Email]:
        """
        Ricerca semantica: restituisce le k email più simili all'embedding dato.
        Ricostruisce oggetti Email dai metadata salvati.
        """
        n = min(k, self.count())
        if n == 0:
            return []

        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=n,
            include=["metadatas"],
        )

        emails = []
        for doc_id, meta in zip(results["ids"][0], results["metadatas"][0]):
            emails.append(
                Email(
                    id=doc_id,
                    sender=meta.get("from", ""),
                    subject=meta.get("subject", "(nessun oggetto)"),
                    date=meta.get("date", ""),
                    body=meta.get("preview", ""),
                    preview=meta.get("preview", ""),
                )
            )
        return emails

    # ── Scrittura ────────────────────────────────────────────────────────────

    def add(self, email: Email, embedding: list[float]) -> None:
        """Aggiunge una singola email al vector store."""
        self._collection.add(
            ids=[email.id],
            embeddings=[embedding],
            documents=[email.to_document()],
            metadatas=[email.to_metadata()],
        )
