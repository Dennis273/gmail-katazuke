"""Organize Gmail: archive, label, delete, and batch operations."""

from __future__ import annotations

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Confirm
from rich.table import Table

from .fetcher import EmailMeta


def archive_old_emails(
    service,
    emails: list[EmailMeta],
    older_than_days: int = 365,
    console: Console | None = None,
) -> int:
    """Archive emails older than a given number of days.

    Removes 'INBOX' label, effectively archiving them.
    Returns the number of emails archived.
    """
    console = console or Console()
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    candidates = [
        em for em in emails
        if em.date and (now - em.date).days > older_than_days
        and "INBOX" in em.labels
    ]

    if not candidates:
        console.print("[yellow]No emails found to archive.[/yellow]")
        return 0

    console.print(
        f"Found [bold]{len(candidates)}[/bold] emails older than "
        f"{older_than_days} days in inbox."
    )

    if not Confirm.ask("Proceed with archiving?", default=False):
        console.print("[dim]Skipped.[/dim]")
        return 0

    return _batch_modify(
        service,
        [em.id for em in candidates],
        remove_labels=["INBOX"],
        description="Archiving",
        console=console,
    )


def batch_mark_read(
    service,
    emails: list[EmailMeta],
    sender_email: str | None = None,
    console: Console | None = None,
) -> int:
    """Mark emails as read. Optionally filter by sender."""
    console = console or Console()
    candidates = [em for em in emails if em.is_unread]
    if sender_email:
        candidates = [em for em in candidates if em.sender_email == sender_email]

    if not candidates:
        console.print("[yellow]No unread emails found matching criteria.[/yellow]")
        return 0

    desc = f"from {sender_email}" if sender_email else ""
    console.print(f"Found [bold]{len(candidates)}[/bold] unread emails {desc}.")

    if not Confirm.ask("Mark all as read?", default=False):
        console.print("[dim]Skipped.[/dim]")
        return 0

    return _batch_modify(
        service,
        [em.id for em in candidates],
        remove_labels=["UNREAD"],
        description="Marking as read",
        console=console,
    )


def apply_label(
    service,
    emails: list[EmailMeta],
    label_name: str,
    sender_email: str | None = None,
    console: Console | None = None,
) -> int:
    """Apply a label to emails. Optionally filter by sender.

    Creates the label if it doesn't exist.
    """
    console = console or Console()

    candidates = emails
    if sender_email:
        candidates = [em for em in candidates if em.sender_email == sender_email]

    if not candidates:
        console.print("[yellow]No emails found matching criteria.[/yellow]")
        return 0

    # Find or create label
    label_id = _get_or_create_label(service, label_name)

    desc = f"from {sender_email}" if sender_email else ""
    console.print(
        f"Will apply label '[bold]{label_name}[/bold]' to "
        f"[bold]{len(candidates)}[/bold] emails {desc}."
    )

    if not Confirm.ask("Proceed?", default=False):
        console.print("[dim]Skipped.[/dim]")
        return 0

    return _batch_modify(
        service,
        [em.id for em in candidates],
        add_labels=[label_id],
        description=f"Applying label '{label_name}'",
        console=console,
    )


def batch_trash(
    service,
    emails: list[EmailMeta],
    sender_email: str | None = None,
    console: Console | None = None,
) -> int:
    """Move emails to trash. Optionally filter by sender."""
    console = console or Console()

    candidates = emails
    if sender_email:
        candidates = [em for em in candidates if em.sender_email == sender_email]

    if not candidates:
        console.print("[yellow]No emails found matching criteria.[/yellow]")
        return 0

    desc = f"from {sender_email}" if sender_email else ""
    console.print(
        f"[bold red]Will move {len(candidates)} emails {desc} to trash.[/bold red]"
    )

    if not Confirm.ask("Are you sure?", default=False):
        console.print("[dim]Skipped.[/dim]")
        return 0

    return _batch_modify(
        service,
        [em.id for em in candidates],
        add_labels=["TRASH"],
        remove_labels=["INBOX"],
        description="Moving to trash",
        console=console,
    )


def show_subscription_actions(
    service,
    emails: list[EmailMeta],
    subscriptions: list[tuple[str, str, int]],
    console: Console | None = None,
) -> None:
    """Interactive menu for handling subscriptions."""
    console = console or Console()

    if not subscriptions:
        console.print("[yellow]No subscriptions detected.[/yellow]")
        return

    table = Table(title="Subscription Actions", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Sender", style="yellow")
    table.add_column("Email", style="dim")
    table.add_column("Count", justify="right")
    table.add_column("Actions")

    for i, (addr, name, count) in enumerate(subscriptions, 1):
        table.add_row(
            str(i),
            name,
            addr,
            str(count),
            "[dim]trash | archive | label | skip[/dim]",
        )

    console.print(table)
    console.print()

    for i, (addr, name, count) in enumerate(subscriptions, 1):
        console.print(f"\n[bold]({i}/{len(subscriptions)}) {name}[/bold] <{addr}> — {count} emails")
        action = console.input(
            "[dim]Action (t=trash, a=archive, l=label, s=skip, q=quit): [/dim]"
        ).strip().lower()

        if action == "q":
            break
        elif action == "t":
            sender_emails = [em for em in emails if em.sender_email == addr]
            _batch_modify(
                service,
                [em.id for em in sender_emails],
                add_labels=["TRASH"],
                remove_labels=["INBOX"],
                description=f"Trashing emails from {name}",
                console=console,
            )
        elif action == "a":
            sender_emails = [
                em for em in emails
                if em.sender_email == addr and "INBOX" in em.labels
            ]
            _batch_modify(
                service,
                [em.id for em in sender_emails],
                remove_labels=["INBOX"],
                description=f"Archiving emails from {name}",
                console=console,
            )
        elif action == "l":
            label_name = console.input("[dim]Label name: [/dim]").strip()
            if label_name:
                label_id = _get_or_create_label(service, label_name)
                sender_emails = [em for em in emails if em.sender_email == addr]
                _batch_modify(
                    service,
                    [em.id for em in sender_emails],
                    add_labels=[label_id],
                    description=f"Labeling emails from {name}",
                    console=console,
                )
        else:
            console.print("[dim]Skipped.[/dim]")


def _batch_modify(
    service,
    message_ids: list[str],
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
    description: str = "Modifying",
    console: Console | None = None,
) -> int:
    """Batch modify messages using Gmail API batchModify."""
    console = console or Console()
    if not message_ids:
        return 0

    batch_size = 1000  # Gmail API limit
    modified = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"{description}...", total=len(message_ids))

        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i : i + batch_size]
            body = {"ids": batch}
            if add_labels:
                body["addLabelIds"] = add_labels
            if remove_labels:
                body["removeLabelIds"] = remove_labels

            service.users().messages().batchModify(
                userId="me", body=body
            ).execute()
            modified += len(batch)
            progress.update(task, completed=modified)

    console.print(f"[green]Done. {modified} emails modified.[/green]")
    return modified


def _get_or_create_label(service, label_name: str) -> str:
    """Get label ID by name, creating it if it doesn't exist."""
    result = service.users().labels().list(userId="me").execute()
    for label in result.get("labels", []):
        if label["name"].lower() == label_name.lower():
            return label["id"]

    # Create new label
    body = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId="me", body=body).execute()
    return created["id"]
