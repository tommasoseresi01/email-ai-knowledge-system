"""
Configurazione centralizzata dell'applicazione.

Tutti i parametri sono letti dal file .env e validati al boot.
Se una variabile obbligatoria manca, il programma termina immediatamente
con un messaggio chiaro — mai a runtime dopo minuti di esecuzione.

Uso in tutti gli altri moduli:
    from src.config.settings import settings
    url = settings.ollama_url
"""

import logging
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Microsoft Azure ──────────────────────────────────────────────────────
    azure_client_id: str
    azure_tenant_id: str = "consumers"

    # ── Ollama ───────────────────────────────────────────────────────────────
    ollama_url: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"
    llm_model: str = "mistral"

    # ── Indicizzazione ───────────────────────────────────────────────────────
    max_emails: int = 300
    chroma_path: str = "./chroma_db"
    embed_char_limit: int = 8000        # caratteri max inviati a Ollama per embedding
    fetch_attachments: bool = True       # scarica e indicizza allegati (PDF, Word, Excel)

    # ── Ricerca ──────────────────────────────────────────────────────────────
    top_k: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton: importato da tutti i moduli, caricato una volta sola
settings = Settings()

# ── Logging centralizzato ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
