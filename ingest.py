#!/usr/bin/env python3
"""
STEP 1 — Scarica le email da Microsoft 365 e le indicizza in ChromaDB.

Esegui una volta (poi di nuovo per aggiornare l'indice con le nuove email):
    python ingest.py
"""

import os
import time
import requests
import chromadb
from msal import PublicClientApplication
from dotenv import load_dotenv

load_dotenv()

# ── Configurazione ──────────────────────────────────────────────────────────
CLIENT_ID   = os.getenv("AZURE_CLIENT_ID")
TENANT_ID   = os.getenv("AZURE_TENANT_ID", "consumers")
SCOPES      = ["https://graph.microsoft.com/Mail.Read"]
OLLAMA_URL  = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
MAX_EMAILS  = int(os.getenv("MAX_EMAILS", "300"))
CHROMA_PATH = "./chroma_db"


# ── Autenticazione Microsoft ─────────────────────────────────────────────────
def get_access_token() -> str:
    app = PublicClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}"
    )
    # Prova a usare il token dalla cache
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            print("✅ Token recuperato dalla cache.")
            return result["access_token"]

    # Login interattivo (apre il browser)
    print("🔐 Si apre il browser per l'autenticazione Microsoft...")
    result = app.acquire_token_interactive(scopes=SCOPES)
    if "access_token" not in result:
        raise Exception(f"Autenticazione fallita: {result.get('error_description', result)}")
    print("✅ Autenticazione completata.")
    return result["access_token"]


# ── Scaricamento email via Graph API ─────────────────────────────────────────
def fetch_emails(token: str, max_emails: int = 300) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    emails = []
    url = (
        "https://graph.microsoft.com/v1.0/me/messages"
        "?$select=id,subject,from,toRecipients,receivedDateTime,bodyPreview"
        "&$top=50"
        "&$orderby=receivedDateTime desc"
    )

    while url and len(emails) < max_emails:
        print(f"  📥 Scaricamento... {len(emails)}/{max_emails} email", end="\r")
        resp = requests.get(url, headers=headers)
        if not resp.ok:
            print(f"\n❌ Errore API ({resp.status_code}): {resp.json()}")
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("value", [])
        emails.extend(batch)
        url = data.get("@odata.nextLink")

    emails = emails[:max_emails]
    print(f"\n✅ Scaricate {len(emails)} email.")
    return emails


# ── Embedding via Ollama ──────────────────────────────────────────────────────
def embed_text(text: str) -> list[float]:
    """Genera un vettore di embedding per il testo dato."""
    resp = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": text[:4000]}
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


# ── Indicizzazione in ChromaDB ───────────────────────────────────────────────
def index_emails(emails: list[dict]):
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection("emails")

    # Salta email già indicizzate
    existing_ids = set(collection.get(include=[])["ids"])
    new_emails = [e for e in emails if e["id"] not in existing_ids]

    if not new_emails:
        print("✅ Tutte le email sono già indicizzate. Nulla da fare.")
        return

    print(f"🔄 Indicizzazione di {len(new_emails)} nuove email (le già presenti vengono saltate)...\n")

    errors = 0
    for i, email in enumerate(new_emails, start=1):
        # Estrai campi
        from_info = email.get("from", {}).get("emailAddress", {})
        sender    = f"{from_info.get('name', '')} <{from_info.get('address', '')}>"
        subject   = email.get("subject") or "(nessun oggetto)"
        date      = (email.get("receivedDateTime") or "")[:10]
        preview   = email.get("bodyPreview") or ""

        # Testo da indicizzare (verrà usato per la ricerca semantica)
        doc_text = f"Da: {sender}\nData: {date}\nOggetto: {subject}\n\n{preview}"

        # Metadata (visibili nell'UI come riferimento)
        metadata = {
            "from":    sender,
            "subject": subject,
            "date":    date,
            "preview": preview[:300]
        }

        print(f"  [{i:>3}/{len(new_emails)}] {subject[:65]}", end="\r")

        try:
            embedding = embed_text(doc_text)
            collection.add(
                ids=[email["id"]],
                embeddings=[embedding],
                documents=[doc_text],
                metadatas=[metadata]
            )
        except Exception as e:
            errors += 1
            print(f"\n  ⚠️  Errore su '{subject[:40]}': {e}")

        time.sleep(0.05)  # evita di sommergere Ollama

    print(f"\n\n✅ Indicizzazione completata!")
    print(f"   • Aggiunte: {len(new_emails) - errors}")
    print(f"   • Errori:   {errors}")
    print(f"   • Totale nel DB: {collection.count()}")
    print(f"\n🚀 Ora puoi avviare l'interfaccia chat con:\n   streamlit run app.py\n")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  EMAIL AI POC — Fase 1: Indicizzazione")
    print("=" * 55 + "\n")

    if not CLIENT_ID:
        print("❌ Errore: AZURE_CLIENT_ID non trovato nel file .env")
        print("   Segui le istruzioni nel README.md per registrare l'app Azure.")
        raise SystemExit(1)

    token  = get_access_token()
    emails = fetch_emails(token, MAX_EMAILS)
    index_emails(emails)
