"""
Interfaccia chat Streamlit — versione enterprise.

Principio: questo file conosce solo Streamlit e SearchService.
Zero chiamate HTTP dirette, zero logica di business.

Funzionalita:
- Chat in linguaggio naturale
- Filtro per intervallo date
- Statistiche indice nella sidebar
- Domande di esempio cliccabili
- Riferimenti email sorgente espandibili
"""

from datetime import datetime, timedelta

import streamlit as st

from src.clients.ollama_client import OllamaClient
from src.clients.vectorstore import VectorStore
from src.config.settings import settings
from src.services.search_service import SearchService


# ── Inizializzazione (cached) ────────────────────────────────────────────────

@st.cache_resource
def get_search_service() -> SearchService:
    return SearchService(ollama=OllamaClient(), store=VectorStore())


@st.cache_resource
def get_store() -> VectorStore:
    return VectorStore()


# ── Pagina principale ────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Email AI — Knowledge System",
        page_icon="📧",
        layout="wide",
    )

    store = get_store()
    email_count = store.count()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("📧 Email AI")
        st.caption(f"Modello: {settings.llm_model} | Embedding: {settings.embed_model}")
        st.divider()

        # ── Statistiche ──────────────────────────────────────────────────────
        st.subheader("📊 Statistiche indice")
        if email_count > 0:
            col1, col2 = st.columns(2)
            col1.metric("Email indicizzate", email_count)
            date_min, date_max = store.get_date_range()
            if date_min and date_max:
                col2.metric("Periodo", f"{date_min} / {date_max}")
        else:
            st.warning(
                "Nessuna email indicizzata.\n\n"
                "Esegui:\n```\npython ingest.py\n```"
            )

        st.divider()

        # ── Filtri di ricerca ────────────────────────────────────────────────
        st.subheader("🔍 Filtri di ricerca")

        top_k = st.slider(
            "Email da considerare",
            min_value=3,
            max_value=15,
            value=settings.top_k,
        )

        use_date_filter = st.checkbox("Filtra per periodo")
        date_from_str = None
        date_to_str = None

        if use_date_filter:
            today = datetime.now().date()
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                date_from = st.date_input("Da", value=today - timedelta(days=365))
            with col_d2:
                date_to = st.date_input("A", value=today)
            date_from_str = date_from.isoformat()
            date_to_str = date_to.isoformat()

        st.divider()

        # ── Domande di esempio ───────────────────────────────────────────────
        st.subheader("💡 Domande di esempio")
        examples = [
            "Riassumi le comunicazioni piu recenti",
            "Ci sono email riguardanti scadenze o urgenze?",
            "Quali sono gli argomenti principali delle email?",
            "Ci sono comunicazioni importanti che richiedono azione?",
        ]
        for example in examples:
            if st.button(example, use_container_width=True):
                st.session_state["prefill"] = example

        st.divider()
        st.caption(
            "**Comandi utili:**\n"
            "- `python ingest.py` — aggiorna indice\n"
            "- `python ingest.py --force` — reindicizza tutto\n"
            "- `python ingest.py --clear` — svuota indice"
        )

    # ── Chat principale ───────────────────────────────────────────────────────
    st.title("📧 Email AI — Knowledge System")
    st.caption(
        "Interroga le email aziendali in linguaggio naturale. "
        "Le risposte sono basate esclusivamente sulle email indicizzate, con citazione delle fonti."
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
        placeholder="Scrivi la tua domanda sulle email aziendali..."
    ) or prefill

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            try:
                with st.spinner("🔍 Cerco nelle email e genero la risposta..."):
                    result = get_search_service().ask(
                        question,
                        k=top_k,
                        date_from=date_from_str,
                        date_to=date_to_str,
                    )

                st.markdown(result.answer)

                if result.sources:
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
                    "Impossibile connettersi a Ollama. "
                    "Assicurati che sia in esecuzione con `ollama serve`."
                )
            except Exception as exc:
                _show_error(f"Errore: {exc}")


# ── Componenti UI riutilizzabili ──────────────────────────────────────────────

def _render_sources(sources: list) -> None:
    """Mostra le email sorgente in un expander collassabile."""
    if not sources:
        return
    with st.expander(f"📎 {len(sources)} email di riferimento"):
        for src in sources:
            if isinstance(src, dict):
                subject = src.get("subject", "")
                sender = src.get("from", "")
                date = src.get("date", "")
                preview = src.get("preview", "")
            else:
                subject = src.subject
                sender = src.sender
                date = src.date
                preview = src.preview

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{subject}**")
                st.caption(f"Da: {sender}")
            with col2:
                st.caption(date)
            st.caption(preview[:300] + ("..." if len(preview) > 300 else ""))
            st.divider()


def _show_error(message: str) -> None:
    st.error(message)
    st.session_state.messages.append({"role": "assistant", "content": message})
