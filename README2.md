# Email AI — Corporate Knowledge System

> Sistema RAG (Retrieval-Augmented Generation) che trasforma le email Microsoft 365 di un'azienda in una base di conoscenza interrogabile in linguaggio naturale. Tutto gira in locale, costo zero.

---

## Il problema

Nelle aziende, una parte enorme delle informazioni operative vive esclusivamente nelle caselle email dei singoli dipendenti: accordi con fornitori, decisioni prese, scadenze, comunicazioni con clienti, risoluzioni di problemi, trattative in corso.

Questo crea tre problemi concreti e costosi:

**1. Tempo perso nella ricerca**
Trovare un'email specifica tra centinaia richiede ricerche manuali per parole chiave, spesso imprecise. Un dipendente può perdere ore a cercare una comunicazione di sei mesi fa con un cliente, o a ricostruire il contesto di una trattativa.

**2. Conoscenza come silo personale**
Le informazioni non sono condivise: se un collega ha gestito un cliente per anni, quella storia è intrappolata nella sua casella. Il resto del team non ha accesso a quel contesto.

**3. Perdita di know-how alla partenza di un dipendente**
Quando un dipendente lascia l'azienda, porta con sé anni di comunicazioni, relazioni e conoscenza operativa. Il nuovo assunto riparte da zero, senza sapere cosa è successo con il cliente X, qual era l'accordo con il fornitore Y, o come era stata risolta quella crisi l'anno scorso.

---

## La soluzione

**Email AI** indicizza automaticamente le email aziendali Microsoft 365 e le rende interrogabili in linguaggio naturale. Un dipendente — nuovo o storico — può semplicemente chiedere:

> *"Cosa è successo negli ultimi 6 mesi con il cliente Rossi?"*
> *"Quali accordi abbiamo in essere con il fornitore Bianchi?"*
> *"C'erano problemi aperti sulla commessa 2024-47?"*
> *"Chi stava seguendo il progetto di espansione al Nord?"*

Il sistema risponde citando le email sorgente, con mittente e data, senza inventare nulla.

---

## Come funziona

```
┌─────────────────────────────────────────────────────────────┐
│                    FASE 1 — INDICIZZAZIONE                  │
│                                                             │
│  Microsoft 365 → Graph API → email scaricate               │
│       ↓                                                     │
│  Ollama (nomic-embed-text) → embedding semantico            │
│       ↓                                                     │
│  ChromaDB (locale) → archivio vettoriale persistente        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    FASE 2 — RICERCA E RISPOSTA              │
│                                                             │
│  Dipendente scrive domanda in chat                          │
│       ↓                                                     │
│  Ollama → embedding della domanda                           │
│       ↓                                                     │
│  ChromaDB → trova le email semanticamente più rilevanti     │
│       ↓                                                     │
│  Ollama LLM (llama3.2 / mistral) → risposta in italiano     │
│  con citazione delle email sorgente                         │
└─────────────────────────────────────────────────────────────┘
```

**Punto chiave:** la ricerca è *semantica*, non per parole chiave. Se chiedi "problemi con la spedizione" trova anche email che parlano di "ritardo consegna" o "merce non arrivata", anche se non contengono la parola esatta.

---

## Stack tecnologico — tutto locale, costo zero

| Componente | Tecnologia | Scopo |
|---|---|---|
| Fonte dati | Microsoft Graph API + MSAL | Accesso autenticato alle email M365 |
| Embedding | Ollama + `nomic-embed-text` (~274MB) | Trasforma testo in vettori semantici |
| Vector DB | ChromaDB (locale su disco) | Archivia e interroga gli embedding |
| LLM | Ollama + `llama3.2` o `mistral` | Genera risposte in linguaggio naturale |
| UI | Streamlit | Interfaccia chat web |
| Infrastruttura | Docker Compose | Gestione del container Ollama |

Nessuna API cloud a pagamento. Nessun dato inviato a terzi. Tutto il processing avviene sul server aziendale locale.

---

## Stato attuale — PoC

Il progetto è in fase di **Proof of Concept** attivo. L'architettura core è funzionante:

- [x] Autenticazione Microsoft 365 via MSAL
- [x] Download email tramite Graph API (fino a 300, espandibile)
- [x] Indicizzazione idempotente (le email già presenti vengono saltate)
- [x] Ricerca semantica su ChromaDB
- [x] Chat in linguaggio naturale con risposta contestuale
- [x] Mostra le email sorgente usate per ogni risposta
- [x] Orchestrazione Docker Compose per Ollama

---

## Roadmap — Sviluppi futuri

### Qualità dei dati

- [ ] **Corpo email completo** — attualmente viene indicizzata solo l'anteprima (~255 caratteri); passare al corpo HTML/testo completo migliora drasticamente la qualità delle risposte
- [ ] **Indicizzazione allegati** — estrarre e indicizzare il testo da PDF, Word, Excel allegati alle email
- [ ] **Thread email** — ricostruire le conversazioni complete (domanda + risposte) invece di email singole

### Knowledge base aziendale

- [ ] **Multi-casella** — indicizzare le caselle di più dipendenti (con permessi delegati Azure) per costruire una base di conoscenza condivisa di reparto o aziendale
- [ ] **Organizzazione per reparto** — segmentare la knowledge base per area aziendale (commerciale, tecnico, amministrativo)
- [ ] **Estrazione entità** — identificare automaticamente clienti, fornitori, progetti citati nelle email e creare un indice strutturato
- [ ] **Relazioni temporali** — query come "cosa è successo con X nell'ultimo anno" con filtri per periodo

### Continuità operativa (il problema della partenza dei dipendenti)

- [ ] **Offboarding workflow** — procedura automatica che, quando un dipendente lascia, archivia e consolida la sua casella nella knowledge base aziendale prima della disattivazione dell'account
- [ ] **Profili di conoscenza** — per ogni cliente/fornitore/progetto, ricostruire automaticamente la storia delle comunicazioni indipendentemente da chi le ha gestite
- [ ] **Trasferimento contestuale** — quando un nuovo dipendente prende in carico un cliente, può chiedere "dimmi tutto quello che è successo con questo cliente" e ricevere un briefing strutturato basato sulle email storiche

### Infrastruttura e accesso

- [ ] **Indicizzazione automatica** — cron job notturno per mantenere l'indice aggiornato senza intervento manuale
- [ ] **Accesso multi-utente** — più dipendenti possono interrogare la stessa knowledge base contemporaneamente
- [ ] **Integrazione SharePoint e Teams** — estendere l'indicizzazione oltre le email a documenti condivisi e chat Teams
- [ ] **Controllo accessi per ruolo** — ogni dipendente vede solo le email del suo reparto o quelle per cui ha i permessi

---

## Prerequisiti

- Python 3.10+
- Docker Desktop
- Account Microsoft 365 (personale o aziendale)

---

## Setup — 4 passi

### Passo 1 — Registra l'app su Azure (5 minuti, gratuito)

1. Vai su [https://portal.azure.com](https://portal.azure.com) e accedi con il tuo account Microsoft
2. Cerca **"App registrations"** → **"New registration"**
3. Compila:
   - **Name**: `Email AI PoC`
   - **Supported account types**: account personale → *"Accounts in any organizational directory and personal Microsoft accounts"* / account aziendale → *"Accounts in this organizational directory only"*
   - **Redirect URI**: `Public client/native` → `http://localhost`
4. Clicca **Register** e copia **Application (client) ID** e **Directory (tenant) ID**
5. Vai su **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated** → `Mail.Read`

### Passo 2 — Configura l'ambiente

```bash
git clone <repo>
cd email-ai-poc
pip install -r requirements.txt
cp .env.example .env
```

Apri `.env` e inserisci i valori del Passo 1:

```env
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### Passo 3 — Avvia Ollama

```bash
docker compose up -d
```

### Passo 4 — Indicizza le email e avvia la chat

```bash
# Scarica e indicizza le email (si apre il browser per il login Microsoft)
python ingest.py

# Avvia l'interfaccia chat
streamlit run app.py
# → http://localhost:8501
```

---

## Struttura del progetto

```
email-ai-poc/
├── docker-compose.yml   # Orchestrazione Ollama
├── .env.example         # Template configurazione
├── .env                 # Tua configurazione (non committare)
├── requirements.txt     # Dipendenze Python
├── ingest.py            # Fase 1: scarica e indicizza le email
├── app.py               # Fase 2: interfaccia chat Streamlit
└── chroma_db/           # Database vettoriale locale (auto-generato)
```

---

## Troubleshooting

**"Autenticazione fallita"**
→ Verifica `AZURE_CLIENT_ID` e `AZURE_TENANT_ID` nel `.env`
→ Controlla che il permesso `Mail.Read` sia presente in Azure

**"Impossibile connettersi a Ollama"**
→ Esegui `docker compose up -d` e riprova

**"Modello non trovato"**
→ I modelli vengono caricati automaticamente dal volume Docker. Se è la prima volta: `docker exec ollama-mistral ollama pull nomic-embed-text && ollama pull llama3.2`

**Risposte lente (CPU only)**
→ Usa `LLM_MODEL=llama3.2:1b` nel `.env` per un modello più leggero
