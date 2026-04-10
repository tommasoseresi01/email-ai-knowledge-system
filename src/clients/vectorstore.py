"""
Wrapper ChromaDB (Vector Store).

Responsabilità singola: astrae l'accesso al database vettoriale.
Nessun altro modulo importa chromadb direttamente — tutto passa da qui.
"""

import logging

import chromadb

from src.config.settings import settings
from src.models.email import Email

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "emails"


class VectorStore:
    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=settings.chroma_path)
        self._collection = self._client.get_or_create_collection(_COLLECTION_NAME)

    # ── Lettura ──────────────────────────────────────────────────────────────

    def get_existing_ids(self) -> set[str]:
        """Restituisce l'insieme degli ID già presenti nel DB (per deduplicazione)."""
        return set(self._collection.get(include=[])["ids"])

    def count(self) -> int:
        """Numero totale di email indicizzate."""
        return self._collection.count()

    def search(
        self,
        embedding: list[float],
        k: int,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[Email]:
        """
        Ricerca semantica con filtro opzionale per intervallo di date.
        Restituisce le k email più simili all'embedding dato.
        """
        n = min(k, self.count())
        if n == 0:
            return []

        # Costruisci filtro ChromaDB per date se specificato
        where_filter = self._build_date_filter(date_from, date_to)

        query_params: dict = {
            "query_embeddings": [embedding],
            "n_results": n,
            "include": ["metadatas"],
        }
        if where_filter:
            query_params["where"] = where_filter

        results = self._collection.query(**query_params)

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

    def get_date_range(self) -> tuple[str, str]:
        """Restituisce (data_min, data_max) delle email indicizzate."""
        all_meta = self._collection.get(include=["metadatas"])["metadatas"]
        if not all_meta:
            return ("", "")
        dates = sorted(m.get("date", "") for m in all_meta if m.get("date"))
        if not dates:
            return ("", "")
        return (dates[0], dates[-1])

    def get_unique_senders(self) -> list[str]:
        """Restituisce la lista dei mittenti unici ordinati."""
        all_meta = self._collection.get(include=["metadatas"])["metadatas"]
        senders = sorted({m.get("from", "") for m in all_meta if m.get("from")})
        return senders

    # ── Scrittura ────────────────────────────────────────────────────────────

    def add(self, email: Email, embedding: list[float]) -> None:
        """Aggiunge una singola email al vector store."""
        self._collection.add(
            ids=[email.id],
            embeddings=[embedding],
            documents=[email.to_document()],
            metadatas=[email.to_metadata()],
        )

    def clear(self) -> int:
        """
        Elimina tutti i documenti dalla collezione. Restituisce il numero eliminato.
        Usato per la re-indicizzazione forzata (--force).
        """
        count = self.count()
        if count > 0:
            self._client.delete_collection(_COLLECTION_NAME)
            self._collection = self._client.get_or_create_collection(_COLLECTION_NAME)
            logger.info("Collezione cancellata: %d documenti rimossi.", count)
        return count

    # ── Utility ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_date_filter(
        date_from: str | None, date_to: str | None
    ) -> dict | None:
        """Costruisce un filtro ChromaDB $and per intervallo date."""
        conditions: list[dict] = []
        if date_from:
            conditions.append({"date": {"$gte": date_from}})
        if date_to:
            conditions.append({"date": {"$lte": date_to}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}
