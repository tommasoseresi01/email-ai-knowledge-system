"""
STEP 1 — Indicizzazione email Microsoft 365.

Entry point minimale: parsa argomenti CLI e avvia la pipeline.
Tutta la logica e in src/services/ingestion_service.py.

Uso:
    python ingest.py                 # incrementale (aggiunge solo le nuove)
    python ingest.py --force         # cancella l'indice e reindicizza tutto
    python ingest.py --clear         # cancella l'indice senza reindicizzare
"""

import argparse
import sys

from src.clients.graph_client import GraphClient
from src.clients.ollama_client import OllamaClient
from src.clients.vectorstore import VectorStore
from src.services.ingestion_service import IngestionService


def main() -> None:
    parser = argparse.ArgumentParser(description="Indicizza email Microsoft 365")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Cancella l'indice esistente e reindicizza tutto da zero",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Cancella l'indice senza reindicizzare (utile per reset)",
    )
    args = parser.parse_args()

    print("=" * 55)
    print("  EMAIL AI — Fase 1: Indicizzazione")
    print("=" * 55 + "\n")

    store = VectorStore()

    if args.clear:
        removed = store.clear()
        print(f"Indice cancellato: {removed} documenti rimossi.")
        sys.exit(0)

    service = IngestionService(
        graph=GraphClient(),
        ollama=OllamaClient(),
        store=store,
    )
    report = service.run(force=args.force)

    print(f"\n\nIndicizzazione completata!")
    if report.cleared:
        print(f"   Re-indicizzazione: {report.cleared} documenti precedenti rimossi")
    print(f"   Scaricate:      {report.total_fetched}")
    print(f"   Aggiunte:       {report.added}")
    print(f"   Con allegati:   {report.with_attachments}")
    print(f"   Saltate:        {report.skipped}  (gia presenti)")
    print(f"   Errori:         {report.errors}")
    print(f"   Totale nel DB:  {store.count()}")
    print(f"\nOra puoi avviare la chat con:\n   streamlit run app.py\n")


if __name__ == "__main__":
    main()
