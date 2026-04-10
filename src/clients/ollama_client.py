"""
Client Ollama — embedding e generazione testo.

Isola completamente la dipendenza da Ollama.
Se in futuro si passa a OpenAI o un altro provider, si modifica solo questo file.

Funzionalità:
- check_model(): verifica che Ollama sia attivo e il modello installato
- embed(): genera embedding (con fallback automatico tra API v2 e v1)
- generate(): chiama il LLM e restituisce la risposta testuale

Fallback versioni Ollama:
  >= 0.1.24 → POST /api/embed     con {"input": text}  → {"embeddings": [[...]]}
  <  0.1.24 → POST /api/embeddings con {"prompt": text} → {"embedding": [...]}
"""

import logging

import requests

from src.config.settings import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self) -> None:
        self._base_url = settings.ollama_url
        self._embed_model = settings.embed_model
        self._llm_model = settings.llm_model

    # ── Validazione ──────────────────────────────────────────────────────────

    def check_model(self) -> None:
        """
        Verifica che Ollama sia raggiungibile e che il modello di embedding
        sia installato. Solleva SystemExit con istruzioni chiare se qualcosa manca.
        Chiamare prima di avviare qualsiasi pipeline di indicizzazione.
        """
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=5)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise SystemExit(
                f"❌ Ollama non raggiungibile su {self._base_url}.\n"
                f"   Avvialo con: ollama serve  (oppure: docker compose up -d)"
            )

        installed = [
            m["name"].split(":")[0]
            for m in resp.json().get("models", [])
        ]
        if self._embed_model not in installed:
            raise SystemExit(
                f"❌ Modello '{self._embed_model}' non installato in Ollama.\n"
                f"   Esegui: ollama pull {self._embed_model}\n"
                f"   Modelli installati: {installed or '(nessuno)'}"
            )
        logger.info("Ollama attivo — modello '%s' disponibile.", self._embed_model)

    # ── Embedding ────────────────────────────────────────────────────────────

    def embed(self, text: str) -> list[float]:
        """
        Genera un vettore di embedding per il testo dato.
        Prova prima l'API moderna (>= 0.1.24); se l'endpoint non esiste
        (404 senza errore di modello) cade automaticamente sull'API legacy.
        """
        resp = requests.post(
            f"{self._base_url}/api/embed",
            json={"model": self._embed_model, "input": text},
        )

        if resp.status_code == 404:
            err_msg = self._parse_error(resp)
            if "model" in err_msg.lower():
                raise RuntimeError(
                    f"Modello '{self._embed_model}' non trovato. "
                    f"Esegui: ollama pull {self._embed_model}"
                )
            # Endpoint non trovato → versione Ollama < 0.1.24, prova API legacy
            logger.debug("Fallback a /api/embeddings (Ollama < 0.1.24)")
            resp = requests.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._embed_model, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]

        resp.raise_for_status()
        return resp.json()["embeddings"][0]

    # ── Generazione testo ────────────────────────────────────────────────────

    def generate(self, system_prompt: str, user_message: str) -> str:
        """
        Invia una richiesta chat al LLM e restituisce la risposta come stringa.
        Usa il modello configurato in LLM_MODEL (.env).
        """
        resp = requests.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self._llm_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
            },
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    # ── Utility ──────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_error(resp: requests.Response) -> str:
        """Estrae il messaggio di errore dal body JSON di una risposta Ollama."""
        try:
            return resp.json().get("error", "")
        except ValueError:
            return ""
