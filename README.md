# Email AI — Corporate Knowledge System

> Local RAG system that turns Microsoft 365 corporate email into a searchable knowledge base, enabling natural-language question answering over operational communications.

## Overview

Email AI is a Proof of Concept focused on enterprise knowledge retrieval from Microsoft 365 mailboxes.

The system downloads emails through Microsoft Graph API, creates semantic embeddings, stores them in a local vector database, and lets users query the information through a chat interface. Responses are generated using local LLMs and grounded on retrieved source emails.

This project explores how internal company communication can be transformed into an accessible and reusable knowledge layer without relying on paid cloud AI APIs.

## Why this project matters

In many companies, a large part of operational knowledge lives only inside personal inboxes:
- agreements with suppliers
- customer communications
- project decisions
- issue resolutions
- deadline updates

This creates three major problems:
- slow manual search across old emails
- knowledge silos tied to individual employees
- loss of business context when a colleague leaves the company

Email AI addresses this problem by enabling semantic retrieval over email history.

## Main features

- Microsoft 365 authentication with MSAL
- Email ingestion through Microsoft Graph API
- Idempotent indexing pipeline
- Semantic search with embeddings
- Local vector storage with ChromaDB
- Natural-language Q&A over retrieved email context
- Source-grounded answers with sender/date references
- Streamlit chat interface
- Fully local execution with Docker + Ollama

## Architecture

### Indexing phase
Microsoft 365 → Graph API → email extraction → embeddings → ChromaDB

### Query phase
User question → query embedding → semantic retrieval → LLM answer generation → source-backed response

## Tech stack

- **Python**
- **Microsoft Graph API**
- **MSAL**
- **Ollama**
- **nomic-embed-text**
- **llama3.2 / mistral**
- **ChromaDB**
- **Streamlit**
- **Docker Compose**

## Skills demonstrated

This repository showcases practical skills in:
- Retrieval-Augmented Generation (RAG)
- semantic search pipelines
- enterprise email/data integration
- local LLM deployment
- vector databases
- Python backend development
- AI application prototyping
- privacy-first / on-prem AI architecture

## Current status

This project is currently a working Proof of Concept.

Implemented:
- Microsoft 365 authentication
- email download and indexing
- semantic retrieval
- contextual answer generation
- source citation in responses
- Ollama orchestration with Docker Compose

## Roadmap

Planned next steps include:
- full email body ingestion
- attachment extraction and indexing
- thread reconstruction
- multi-mailbox knowledge base
- department-level segmentation
- entity extraction
- time-aware querying
- automated offboarding knowledge transfer
- role-based access control
- SharePoint / Teams integration

## Project structure

```text
email-ai-poc/
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── ingest.py
├── app.py
└── chroma_db/
```

## Notes

This repository is intended as a technical Proof of Concept for enterprise AI knowledge systems.

Sensitive data, credentials, real emails, and local generated databases should never be committed to the repository.

## Author

**Tommaso Seresi**  
Junior Software Engineer / AI Engineer  
Focus: AI systems, enterprise automation, cloud and retrieval architectures