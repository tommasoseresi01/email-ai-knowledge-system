# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Pull required Ollama models
ollama pull nomic-embed-text
ollama pull llama3.2

# Step 1: Download and index emails from Microsoft 365
python ingest.py

# Step 2: Launch the chat UI
streamlit run app.py
# Opens at http://localhost:8501
```

## Architecture

```
Outlook/M365 (Graph API) → ingest.py → ChromaDB (./chroma_db/)
                                              ↓
                               app.py (Streamlit) ← Ollama (LLM + Embeddings)
```

**Two-step pipeline:**

1. **`ingest.py`** — authenticates with Microsoft Graph API via MSAL (interactive browser login), fetches up to `MAX_EMAILS` emails, generates embeddings via Ollama, and stores them in ChromaDB. Skips already-indexed emails (idempotent).

2. **`app.py`** — Streamlit chat UI. On each user question: embeds the query with Ollama, retrieves the top-k most similar emails from ChromaDB, then sends the email context + question to an Ollama LLM for a grounded answer. Shows source email metadata in expandable sections.

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `AZURE_CLIENT_ID` | required | Azure app registration client ID |
| `AZURE_TENANT_ID` | `consumers` | `consumers` for personal accounts, tenant ID for org accounts |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `LLM_MODEL` | `llama3.2` | Ollama LLM for answering |
| `MAX_EMAILS` | `300` | Max emails to fetch during ingestion |

## ChromaDB collection

Both scripts use a single collection named `"emails"` in `./chroma_db/`. Each document stores:
- **document**: `"Da: {sender}\nData: {date}\nOggetto: {subject}\n\n{preview}"` (used for semantic search)
- **metadata**: `from`, `subject`, `date`, `preview` (shown in UI sources)
- **id**: Microsoft Graph message ID (used to deduplicate on re-ingestion)

The embedding text is truncated to 4000 characters before being sent to Ollama.
