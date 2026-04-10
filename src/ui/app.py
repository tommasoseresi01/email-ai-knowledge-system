"""
Interfaccia chat Streamlit.

Principio: questo file conosce solo Streamlit e SearchService.
Zero chiamate HTTP dirette, zero logica di business.
Tutto ciò che riguarda embedding, LLM e ChromaDB passa dal SearchService.
"""

import streamlit as st

from src.clients.ollama_client import OllamaClient
from src.clients.vectorstore import VectorStore
from src.config.settings import settings
from src.services.search_service import SearchService


# ── Inizializzazione (cached — eseguita una volta sola per sessione) ──────────

@st.cache_resource
def get_service() -> SearchService:
    return SearchService(ollama=OllamaClient(), store=VectorStore())


# ── Pagina ────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="📧 Email AI Assistant",
        page_icon="📧",
        layout="wide",
    )

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("📧 Email AI")
        st.caption("Powered by Ollama + ChromaDB")
        st.divider()

        st.subheader("⚙️ Impostazioni")
        top_k = st.slider(
            "Email da considerare per risposta",
            min_value=3,
            max_value=10,
            value=settings.top_k,
        )

        st.divider()

        # Statistiche indice
        st.subheader("📊 Statistiche")
        try:
            store = VectorStore()
            count = store.count()
            st.metric("Email indicizzate", count)
            if count == 0:
                st.warning("Nessuna email trovata.\nEsegui prima:\n`python ingest.py`")
        except Exception as exc:
            st.error(f"Errore ChromaDB:\n{exc}")

        st.divider()
        st.subheader("💡 Domande di esempio")
        examples = [
            "C'è qualcosa sullo stato degli ordini in sospeso?",
            "Quali fornitori ci hanno scritto questo mese?",
            "Ci sono email riguardanti scadenze o urgenze?",
            "Riassumi le comunicazioni più recenti con i clienti.",
            "C'è qualcosa sul bando o sulla contrattualistica?",
        ]
        for example in examples:
            if st.button(example, use_container_width=True):
                st.session_state["prefill"] = example

    # ── Chat principale ───────────────────────────────────────────────────────
    st.title("📧 Email AI Assistant")
    st.caption(
        "Fai domande sulle tue email in linguaggio naturale — "
        "le risposte sono basate solo sulle tue email."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Mostra cronologia
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                _render_sources(msg["sources"])

    # Input
    prefill = st.session_state.pop("prefill", "")
    question = st.chat_input(
        placeholder="Es: 'Quali accordi abbiamo con il fornitore Rossi?'"
    ) or prefill

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            try:
                with st.spinner("🔍 Cerco nelle email..."):
                    result = get_service().ask(question, k=top_k)

                st.markdown(result.answer)
                _render_sources(result.sources)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result.answer,
                    "sources": [
                        {
                            "subject": e.subject,
                            "from": e.sender,
                            "date": e.date,
                            "preview": e.preview,
                        }
                        for e in result.sources
                    ],
                })

            except ConnectionError:
                _show_error(
                    "❌ Impossibile connettersi a Ollama. "
                    "Assicurati che sia in esecuzione con `ollama serve`."
                )
            except Exception as exc:
                _show_error(f"❌ Errore: {exc}")


# ── Componenti UI riutilizzabili ──────────────────────────────────────────────

def _render_sources(sources: list) -> None:
    """Mostra le email sorgente in un expander collassabile."""
    if not sources:
        return
    with st.expander(f"📎 {len(sources)} email di riferimento"):
        for src in sources:
            col1, col2 = st.columns([3, 1])
            subject = src["subject"] if isinstance(src, dict) else src.subject
            sender = src["from"] if isinstance(src, dict) else src.sender
            date = src["date"] if isinstance(src, dict) else src.date
            preview = src["preview"] if isinstance(src, dict) else src.preview
            with col1:
                st.markdown(f"**{subject}**")
                st.caption(f"Da: {sender}")
            with col2:
                st.caption(date)
            st.caption(preview[:250] + ("..." if len(preview) > 250 else ""))
            st.divider()


def _show_error(message: str) -> None:
    st.error(message)
    st.session_state.messages.append({"role": "assistant", "content": message})
