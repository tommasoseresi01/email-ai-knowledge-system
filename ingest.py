"""
STEP 1 — Indicizzazione email Microsoft 365.

Entry point minimale: istanzia i client e avvia la pipeline.
Tutta la logica è in src/services/ingestion_service.py.

Esegui con:
    python ingest.py
"""

import logging

from src.clients.graph_client import GraphClient
from src.clients.ollama_client import OllamaClient
from src.clients.vectorstore import VectorStore
from src.services.ingestion_service import IngestionService

if __name__ == "__main__":
    print("=" * 55)
    print("  EMAIL AI — Fase 1: Indicizzazione")
    print("=" * 55 + "\n")

    service = IngestionService(
        graph=GraphClient(),
        ollama=OllamaClient(),
        store=VectorStore(),
    )
    report = service.run()

    print(f"\n\n✅ Indicizzazione completata!")
    print(f"   • Scaricate: {report.total_fetched}")
    print(f"   • Aggiunte:  {report.added}")
    print(f"   • Saltate:   {report.skipped}  (già presenti)")
    print(f"   • Errori:    {report.errors}")
    print(f"   • Totale DB: {report.added + report.skipped}")
    print(f"\n🚀 Ora puoi avviare la chat con:\n   streamlit run app.py\n")
