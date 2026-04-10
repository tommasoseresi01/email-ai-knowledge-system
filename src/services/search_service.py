"""
Search Service — pipeline di ricerca e risposta.

Orchestrazione pura: non conosce HTTP ne UI.
Coordina OllamaClient -> VectorStore -> OllamaClient (LLM).

Il prompt di sistema e ottimizzato per:
- Risposte basate SOLO sulle email fornite (no allucinazioni)
- Citazione esplicita di mittente e data
- Risposta strutturata in italiano professionale
"""

import logging
from dataclasses import dataclass, field

from src.clients.ollama_client import OllamaClient
from src.clients.vectorstore import VectorStore
from src.config.settings import settings
from src.models.email import Email

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Sei un assistente aziendale che analizza email aziendali.

REGOLE TASSATIVE:
1. Rispondi ESCLUSIVAMENTE usando le informazioni contenute nelle email fornite.
2. Per ogni affermazione, cita la fonte: mittente, data e oggetto dell'email.
3. Se le email non contengono l'informazione richiesta, rispondi: \
"Non ho trovato informazioni rilevanti nelle email indicizzate."
4. NON inventare, NON dedurre, NON aggiungere informazioni esterne.
5. Rispondi in italiano, in modo professionale e conciso.
6. Se ci sono piu email rilevanti, organizza la risposta per punti.
7. Indica sempre il periodo temporale coperto dalle email che citi.\
"""


@dataclass
class SearchResult:
    """Risposta del sistema: testo generato dal LLM + email sorgente usate."""
    answer: str
    sources: list[Email] = field(default_factory=list)


class SearchService:
    def __init__(self, ollama: OllamaClient, store: VectorStore) -> None:
        self._ollama = ollama
        self._store = store

    def ask(
        self,
        question: str,
        k: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> SearchResult:
        """
        Pipeline completa domanda -> risposta:
        1. Embed della domanda
        2. Ricerca semantica con filtro opzionale per date
        3. Generazione risposta con LLM
        4. Restituisce risposta + email sorgente
        """
        k = k or settings.top_k

        if self._store.count() == 0:
            return SearchResult(
                answer="Nessuna email indicizzata. Esegui prima: `python ingest.py`",
                sources=[],
            )

        embedding = self._ollama.embed(question)
        sources = self._store.search(
            embedding, k, date_from=date_from, date_to=date_to
        )

        if not sources:
            return SearchResult(
                answer="Nessuna email trovata nel periodo selezionato.",
                sources=[],
            )

        context = "\n\n---\n\n".join(e.to_document() for e in sources)
        user_message = (
            f"EMAIL RILEVANTI ({len(sources)} trovate):\n\n"
            f"{context}\n\n"
            f"---\n\n"
            f"DOMANDA: {question}"
        )

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
