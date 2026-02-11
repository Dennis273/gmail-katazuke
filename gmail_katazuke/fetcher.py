"""Fetch email metadata from Gmail API."""

from __future__ import annotations

import email.utils
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generator

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID


@dataclass
class EmailMeta:
    """Lightweight representation of an email's metadata."""

    id: str
    thread_id: str
    subject: str = ""
    sender: str = ""
    sender_email: str = ""
    date: datetime | None = None
    labels: list[str] = field(default_factory=list)
    size_bytes: int = 0
    has_attachments: bool = False
    is_unread: bool = False
    snippet: str = ""
    list_unsubscribe: str = ""


def _parse_header(headers: list[dict], name: str) -> str:
    """Extract a header value by name."""
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _parse_sender(from_header: str) -> tuple[str, str]:
    """Parse 'From' header into (display_name, email_address)."""
    display_name, addr = email.utils.parseaddr(from_header)
    return display_name or addr, addr


def _parse_date(date_str: str) -> datetime | None:
    """Parse email date header into a datetime."""
    if not date_str:
        return None
    parsed = email.utils.parsedate_to_datetime(date_str)
    return parsed.astimezone(timezone.utc)


def _has_attachments(payload: dict) -> bool:
    """Check if the email has attachments by inspecting parts."""
    parts = payload.get("parts", [])
    for part in parts:
        disposition = part.get("headers", [])
        filename = part.get("filename", "")
        if filename:
            return True
        if _has_attachments(part):
            return True
    return False


def fetch_emails(
    service,
    query: str = "",
    max_results: int = 500,
) -> list[EmailMeta]:
    """Fetch email metadata from Gmail.

    Args:
        service: Authenticated Gmail API service.
        query: Gmail search query (e.g. 'is:unread', 'from:example.com').
        max_results: Maximum number of emails to fetch.

    Returns:
        List of EmailMeta objects.
    """
    emails: list[EmailMeta] = []
    message_ids: list[str] = []

    # Phase 1: collect message IDs
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Listing messages...", total=None)

        page_token = None
        while len(message_ids) < max_results:
            page_size = min(500, max_results - len(message_ids))
            result = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=page_size,
                    pageToken=page_token,
                )
                .execute()
            )
            messages = result.get("messages", [])
            if not messages:
                break
            message_ids.extend(m["id"] for m in messages)
            page_token = result.get("nextPageToken")
            if not page_token:
                break

    if not message_ids:
        return emails

    # Phase 2: fetch metadata for each message
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
    ) as progress:
        task = progress.add_task("Fetching email details...", total=len(message_ids))

        # Use batch requests for efficiency
        batch_size = 50
        for i in range(0, len(message_ids), batch_size):
            batch_ids = message_ids[i : i + batch_size]
            batch_emails = _fetch_batch(service, batch_ids)
            emails.extend(batch_emails)
            progress.update(task, completed=min(i + batch_size, len(message_ids)))

    return emails


def _fetch_batch(service, message_ids: list[str]) -> list[EmailMeta]:
    """Fetch a batch of messages using individual requests.

    Uses Gmail API batch endpoint for efficiency.
    """
    results: list[EmailMeta] = []

    def callback(request_id, response, exception):
        if exception is not None:
            return
        meta = _parse_message(response)
        if meta:
            results.append(meta)

    batch = service.new_batch_http_request(callback=callback)
    for msg_id in message_ids:
        batch.add(
            service.users()
            .messages()
            .get(userId="me", id=msg_id, format="metadata",
                 metadataHeaders=["From", "Subject", "Date", "List-Unsubscribe"])
        )
    batch.execute()
    return results


def _parse_message(msg: dict) -> EmailMeta | None:
    """Parse a Gmail API message response into EmailMeta."""
    headers = msg.get("payload", {}).get("headers", [])
    from_header = _parse_header(headers, "From")
    display_name, email_addr = _parse_sender(from_header)

    label_ids = msg.get("labelIds", [])

    try:
        date = _parse_date(_parse_header(headers, "Date"))
    except Exception:
        date = None

    return EmailMeta(
        id=msg["id"],
        thread_id=msg.get("threadId", ""),
        subject=_parse_header(headers, "Subject"),
        sender=display_name,
        sender_email=email_addr.lower(),
        date=date,
        labels=label_ids,
        size_bytes=msg.get("sizeEstimate", 0),
        has_attachments="ATTACHMENT" in str(msg.get("payload", {}).get("parts", [])),
        is_unread="UNREAD" in label_ids,
        snippet=msg.get("snippet", ""),
        list_unsubscribe=_parse_header(headers, "List-Unsubscribe"),
    )


def fetch_labels(service) -> dict[str, str]:
    """Fetch all labels and return a mapping of label_id -> label_name."""
    result = service.users().labels().list(userId="me").execute()
    labels = result.get("labels", [])
    return {label["id"]: label["name"] for label in labels}
