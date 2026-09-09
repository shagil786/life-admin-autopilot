"""Gmail REST connector: import life-admin emails via Gmail API.

Used with a Firebase Google Sign-In OAuth token (gmail.readonly).
The token and messages stay in memory / on the local machine.
"""
import base64
from pathlib import Path
from typing import Optional

import httpx

from src.ingestion.email_connector import subject_matches, LIFE_ADMIN_KEYWORDS

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
MAX_EMAIL_BYTES = 2 * 1024 * 1024


def _api_url(path: str) -> str:
    return f"{GMAIL_API}{path}"

# Gmail search query: life-admin-ish subjects, recent only
DEFAULT_QUERY = (
    "(" + " OR ".join(LIFE_ADMIN_KEYWORDS) + ") in:inbox newer_than:7d"
)


class GmailAuthError(Exception):
    """Token invalid/expired or Gmail API refused."""


def import_gmail(
    access_token: str,
    save_dir: str,
    client: Optional[httpx.Client] = None,
    days: int = 30,
    max_emails: int = 50,
) -> dict:
    """Fetch life-admin emails via Gmail API, save as .eml.

    Idempotent: Gmail message ids already imported are skipped.
    Returns {fetched, skipped, saved_names}.
    """
    own_client = client is None
    if client is None:
        client = httpx.Client(timeout=30)
    headers = {"Authorization": f"Bearer {access_token}"}

    savedir = Path(save_dir)
    savedir.mkdir(parents=True, exist_ok=True)
    dedup_file = savedir / ".imported_ids"
    imported_ids = set()
    if dedup_file.exists():
        imported_ids = set(dedup_file.read_text().splitlines())

    query = DEFAULT_QUERY if "newer_than" not in DEFAULT_QUERY else (
        "(" + " OR ".join(LIFE_ADMIN_KEYWORDS) + f") in:inbox newer_than:{days}d"
    )

    try:
        resp = client.get(
            _api_url("/messages"),
            params={"q": query, "maxResults": max_emails * 2},
            headers=headers,
        )
        if resp.status_code == 401:
            raise GmailAuthError("Google token rejected (401) — re-sign-in.")
        resp.raise_for_status()
        payload = resp.json()
    except GmailAuthError:
        raise
    except httpx.HTTPError as e:
        raise GmailAuthError(f"Gmail API error: {e}") from e

    messages = payload.get("messages", [])
    fetched = 0
    skipped = 0
    saved_names = []

    for item in messages[: max_emails * 2]:
        mid = item["id"]
        if mid in imported_ids:
            skipped += 1
            continue
        try:
            mresp = client.get(
                _api_url(f"/messages/{mid}"),
                params={"format": "raw"},
                headers=headers,
            )
            mresp.raise_for_status()
            raw_b64 = mresp.json().get("raw", "")
            raw = base64.urlsafe_b64decode(raw_b64)
        except httpx.HTTPError:
            skipped += 1
            continue
        if len(raw) > MAX_EMAIL_BYTES:
            skipped += 1
            continue

        # subject check (double filter: Gmail query may over-match)
        import email as email_lib
        from email import policy
        msg = email_lib.message_from_bytes(raw, policy=policy.default)
        subject = str(msg.get("Subject", "") or "")
        if not subject_matches(subject):
            imported_ids.add(mid)  # never reconsider
            skipped += 1
            continue

        name = f"gmail_{mid}_{_safe_name(subject)}.eml"
        (savedir / name).write_bytes(raw)
        saved_names.append(name)
        imported_ids.add(mid)
        fetched += 1
        if fetched >= max_emails:
            break

    dedup_file.write_text("\n".join(sorted(imported_ids)))

    if own_client:
        client.close()
    return {"fetched": fetched, "skipped": skipped, "saved_names": saved_names}


def _safe_name(text: str) -> str:
    keep = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in text.lower()
    )
    return keep[:40].strip("_") or "email"
