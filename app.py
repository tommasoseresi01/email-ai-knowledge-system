#!/usr/bin/env python3
"""
STEP 2 — Interfaccia chat per interrogare le email indicizzate.

Avvia con:
    streamlit run app.py
"""
#prova
import os
import requests
import chromadb
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Configurazione ──────────────────────────────────────────────────────────
OLLAMA_URL  = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
LLM_MODEL   = os.getenv("LLM_MODEL", "llama3.2")
CHROMA_PATH = "./chroma_db"
DEFAULT_K   = 5


# ── Funzioni core ────────────────────────────────────────────────────────────
def embed_query(text: str) -> list[float]:
    resp = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": text}
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


@st.cache_resource
def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection("emails")


def search_emails(query: str, k: int = DEFAULT_K) -> tuple[list[str], list[dict]]:
    """Ritorna (documenti, metadati) delle k email più rilevanti."""
    embedding  = embed_query(query)
    collection = get_collection()
    results    = collection.query(
        query_embeddings=[embedding],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas"]
    )
    return results["documents"][0], results["metadatas"][0]


def ask_llm(question: str, context_docs: list[str], model: str) -> str:
    context = "\n\n---\n\n".join(context_docs)

    system_msg = (
        "Sei un assistente aziendale esperto. "
        "Rispondi alle domande basandoti ESCLUSIVAMENTE sulle email aziendali fornite nel contesto. "
        "Se la risposta non è nelle email, dichiaralo chiaramente senza inventare. "
        "Cita sempre la data e il mittente delle email che usi come fonte. "
        "Rispondi sempre in italiano, in modo professionale e conciso."
    )
    user_msg = f"""EMAIL RILEVANTI:
{context}

DOMANDA: {question}"""

    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model":    model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg}
            ],
            "stream": False
        }
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ── Pagina Streamlit ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📧 Email AI Assistant",
    page_icon="📧",
    layout="wide"
)

# Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📧 Email AI")
    st.caption("Powered by Ollama + ChromaDB")
    st.divider()

    st.subheader("⚙️ Impostazioni")
    llm_model = st.text_input("Modello LLM (Ollama)", value=LLM_MODEL)
    top_k     = st.slider("Email da considerare per risposta", min_value=3, max_value=10, value=DEFAULT_K)

    st.divider()

    # Statistiche indice
    st.subheader("📊 Statistiche")
    try:
        coll  = get_collection()
        count = coll.count()
        st.metric("Email indicizzate", count)
        if count == 0:
            st.warning("Nessuna email trovata.\nEsegui prima:\n`python ingest.py`")
    except Exception as e:
        st.error(f"Errore ChromaDB:\n{e}")

    st.divider()
    st.subheader("💡 Domande di esempio")
    examples = [
        "C'è qualcosa sullo stato degli ordini in sospeso?",
        "Quali fornitori ci hanno scritto questo mese?",
        "Ci sono email riguardanti scadenze o urgenze?",
        "Riassumi le comunicazioni più recenti con i clienti.",
        "C'è qualcosa sul bando o sulla contrattualistica?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["prefill"] = ex

# Chat principale ──────────────────────────────────────────────────────────
st.title("📧 Email AI Assistant")
st.caption("Fai domande sulle tue email aziendali in linguaggio naturale — le risposte sono basate solo sulle tue email.")

# Inizializza cronologia
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostra cronologia
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"📎 {len(msg['sources'])} email di riferimento"):
                for src in msg["sources"]:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{src['subject']}**")
                        st.caption(f"Da: {src['from']}")
                    with col2:
                        st.caption(src['date'])
                    st.caption(src['preview'][:250] + ("..." if len(src['preview']) > 250 else ""))
                    st.divider()

# Input chat
prefill = st.session_state.pop("prefill", "")
question = st.chat_input(
    placeholder="Es: 'Quali accordi abbiamo con il fornitore Rossi?'",
) or prefill

if question:
    # Messaggio utente
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Risposta assistente
    with st.chat_message("assistant"):
        try:
            with st.spinner("🔍 Cerco nelle email..."):
                docs, metas = search_emails(question, k=top_k)

            with st.spinner("🤔 Elaboro la risposta..."):
                answer = ask_llm(question, docs, model=llm_model)

            st.markdown(answer)

            sources = [
                {
                    "subject": m.get("subject", "(nessun oggetto)"),
                    "from":    m.get("from", ""),
                    "date":    m.get("date", ""),
                    "preview": m.get("preview", "")
                }
                for m in metas
            ]

            with st.expander(f"📎 {len(sources)} email di riferimento"):
                for src in sources:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{src['subject']}**")
                        st.caption(f"Da: {src['from']}")
                    with col2:
                        st.caption(src['date'])
                    st.caption(src['preview'][:250] + ("..." if len(src['preview']) > 250 else ""))
                    st.divider()

            st.session_state.messages.append({
                "role":    "assistant",
                "content": answer,
                "sources": sources
            })

        except requests.exceptions.ConnectionError:
            err = "❌ Impossibile connettersi a Ollama. Assicurati che sia in esecuzione con `ollama serve`."
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "content": err})
        except Exception as e:
            err = f"❌ Errore: {e}"
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "content": err})
