"""
Client Microsoft Graph API.

Responsabilità singola: tutto ciò che riguarda Microsoft 365 sta qui.
- Autenticazione via MSAL (token cache + browser interattivo)
- Download email tramite Graph API con paginazione automatica
- Conversione dict grezzo → dataclass Email

Il resto del sistema non conosce MSAL, Graph API o la struttura JSON
dei messaggi Microsoft — vede solo list[Email].
"""

import logging

import requests
from msal import PublicClientApplication

from src.config.settings import settings
from src.models.email import Email

logger = logging.getLogger(__name__)

_GRAPH_SCOPES = ["https://graph.microsoft.com/Mail.Read"]
_MESSAGES_URL = (
    "https://graph.microsoft.com/v1.0/me/messages"
    "?$select=id,subject,from,toRecipients,receivedDateTime,bodyPreview,conversationId"
    "&$top=50"
    "&$orderby=receivedDateTime desc"
)


class GraphClient:
    def __init__(self) -> None:
        self._app = PublicClientApplication(
            settings.azure_client_id,
            authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
        )

    # ── Autenticazione ───────────────────────────────────────────────────────

    def authenticate(self) -> str:
        """
        Restituisce un access token valido.
        Prova prima il token in cache (silenzioso); se non disponibile
        apre il browser per il login interattivo.
        """
        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(_GRAPH_SCOPES, account=accounts[0])
            if result and "access_token" in result:
                logger.info("Token recuperato dalla cache.")
                return result["access_token"]

        logger.info("Apertura browser per autenticazione Microsoft...")
        result = self._app.acquire_token_interactive(scopes=_GRAPH_SCOPES)
        if "access_token" not in result:
            raise RuntimeError(
                f"Autenticazione fallita: {result.get('error_description', result)}"
            )
        logger.info("Autenticazione completata.")
        return result["access_token"]

    # ── Fetch email ──────────────────────────────────────────────────────────

    def fetch_emails(self, max_emails: int | None = None) -> list[Email]:
        """
        Scarica le email dalla casella Microsoft 365 dell'utente autenticato.
        Gestisce automaticamente la paginazione via @odata.nextLink.
        Restituisce list[Email] (mai dict grezzi).
        """
        limit = max_emails or settings.max_emails
        token = self.authenticate()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        raw_emails: list[dict] = []
        url: str | None = _MESSAGES_URL

        while url and len(raw_emails) < limit:
            logger.info(
                "Download... %d/%d email", len(raw_emails), limit
            )
            resp = requests.get(url, headers=headers)
            if not resp.ok:
                logger.error("Errore Graph API (%d): %s", resp.status_code, resp.text)
            resp.raise_for_status()

            data = resp.json()
            raw_emails.extend(data.get("value", []))
            url = data.get("@odata.nextLink")

        raw_emails = raw_emails[:limit]
        logger.info("Scaricate %d email.", len(raw_emails))
        return [self._parse(e) for e in raw_emails]

    # ── Conversione ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse(raw: dict) -> Email:
        """
        Converte il dict grezzo della Graph API in un dataclass Email.
        Tutta la logica di estrazione campi è centralizzata qui.
        """
        from_info = raw.get("from", {}).get("emailAddress", {})
        sender = (
            f"{from_info.get('name', '')} <{from_info.get('address', '')}>"
        ).strip()
        subject = raw.get("subject") or "(nessun oggetto)"
        date = (raw.get("receivedDateTime") or "")[:10]
        preview = raw.get("bodyPreview") or ""

        return Email(
            id=raw["id"],
            sender=sender,
            subject=subject,
            date=date,
            body=preview,           # Fase 1.1: sostituire con body HTML stripped
            preview=preview,
            conversation_id=raw.get("conversationId"),
        )
