"""
Search Service — pipeline di ricerca e risposta.

Orchestrazione pura: non conosce HTTP né UI.
Coordina OllamaClient → VectorStore → OllamaClient (LLM).

Il prompt di sistema è definito qui, separato dalla logica applicativa.
Per modificare il comportamento del modello basta cambiare SYSTEM_PROMPT.
"""

import logging
from dataclasses import dataclass, field

from src.clients.ollama_client import OllamaClient
from src.clients.vectorstore import VectorStore
from src.config.settings import settings
from src.models.email import Email

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Sei un assistente aziendale esperto. "
    "Rispondi alle domande basandoti ESCLUSIVAMENTE sulle email aziendali fornite nel contesto. "
    "Se la risposta non è nelle email, dichiaralo chiaramente senza inventare. "
    "Cita sempre la data e il mittente delle email che usi come fonte. "
    "Rispondi sempre in italiano, in modo professionale e conciso."
)


@dataclass
class SearchResult:
    """Risposta del sistema: testo generato dal LLM + email sorgente usate."""
    answer: str
    sources: list[Email] = field(default_factory=list)


class SearchService:
    def __init__(self, ollama: OllamaClient, store: VectorStore) -> None:
        self._ollama = ollama
        self._store = store

    def ask(self, question: str, k: int | None = None) -> SearchResult:
        """
        Pipeline completa domanda → risposta:
        1. Embed della domanda
        2. Ricerca semantica delle k email più rilevanti
        3. Generazione risposta con LLM usando le email come contesto
        4. Restituisce risposta + email sorgente
        """
        k = k or settings.top_k

        if self._store.count() == 0:
            return SearchResult(
                answer="❌ Nessuna email indicizzata. Esegui prima: `python ingest.py`",
                sources=[],
            )

        embedding = self._ollama.embed(question)
        sources = self._store.search(embedding, k)

        context = "\n\n---\n\n".join(e.to_document() for e in sources)
        user_message = f"EMAIL RILEVANTI:\n{context}\n\nDOMANDA: {question}"

        logger.info(
            "Generazione risposta con %d email di contesto (modello: %s)...",
            len(sources),
            self._ollama._llm_model,
        )
        answer = self._ollama.generate(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
        )

        return SearchResult(answer=answer, sources=sources)
