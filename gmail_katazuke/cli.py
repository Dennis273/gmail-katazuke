"""CLI entry point for gmail-katazuke."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from .auth import get_gmail_service
from .fetcher import fetch_emails, fetch_labels
from .analyzer import analyze, print_report
from .organizer import (
    archive_old_emails,
    batch_mark_read,
    apply_label,
    batch_trash,
    show_subscription_actions,
)

console = Console()


@click.group()
@click.option(
    "--credentials",
    type=click.Path(exists=True, path_type=Path),
    default="credentials.json",
    help="Path to OAuth credentials JSON file.",
)
@click.option(
    "--token",
    type=click.Path(path_type=Path),
    default="token.json",
    help="Path to save/load the auth token.",
)
@click.pass_context
def main(ctx, credentials: Path, token: Path):
    """Gmail Katazuke - Analyze and organize your Gmail inbox."""
    ctx.ensure_object(dict)
    ctx.obj["credentials"] = credentials
    ctx.obj["token"] = token


@main.command()
@click.option("--query", "-q", default="", help="Gmail search query to filter emails.")
@click.option(
    "--max-emails", "-n", default=500, show_default=True,
    help="Maximum number of emails to analyze.",
)
@click.pass_context
def analyze_cmd(ctx, query: str, max_emails: int):
    """Analyze your Gmail inbox and show a detailed report."""
    console.print("[bold blue]Gmail Katazuke - Inbox Analysis[/bold blue]\n")

    service = _get_service(ctx)
    console.print("Fetching labels...")
    label_map = fetch_labels(service)

    console.print(f"Fetching emails (max {max_emails})...")
    emails = fetch_emails(service, query=query, max_results=max_emails)

    if not emails:
        console.print("[yellow]No emails found.[/yellow]")
        return

    console.print(f"Analyzing {len(emails)} emails...\n")
    report = analyze(emails, label_map)
    print_report(report, console)


@main.command()
@click.option("--query", "-q", default="", help="Gmail search query to filter emails.")
@click.option(
    "--max-emails", "-n", default=500, show_default=True,
    help="Maximum number of emails to process.",
)
@click.pass_context
def organize(ctx, query: str, max_emails: int):
    """Interactive organize mode: analyze then clean up your inbox."""
    console.print("[bold blue]Gmail Katazuke - Inbox Organizer[/bold blue]\n")

    service = _get_service(ctx)

    console.print("Fetching labels...")
    label_map = fetch_labels(service)

    console.print(f"Fetching emails (max {max_emails})...")
    emails = fetch_emails(service, query=query, max_results=max_emails)

    if not emails:
        console.print("[yellow]No emails found.[/yellow]")
        return

    console.print(f"Analyzing {len(emails)} emails...\n")
    report = analyze(emails, label_map)
    print_report(report, console)

    # Interactive organization menu
    console.print("\n[bold]--- Organization Actions ---[/bold]\n")

    while True:
        console.print("[bold]Choose an action:[/bold]")
        console.print("  [cyan]1[/cyan] Archive old emails (>N days)")
        console.print("  [cyan]2[/cyan] Mark emails as read")
        console.print("  [cyan]3[/cyan] Apply label to emails from a sender")
        console.print("  [cyan]4[/cyan] Trash emails from a sender")
        console.print("  [cyan]5[/cyan] Manage subscriptions / newsletters")
        console.print("  [cyan]q[/cyan] Quit")
        console.print()

        choice = console.input("[bold]> [/bold]").strip().lower()

        if choice == "q":
            break
        elif choice == "1":
            days = int(console.input("Archive emails older than how many days? [365]: ").strip() or "365")
            archive_old_emails(service, emails, older_than_days=days, console=console)
        elif choice == "2":
            sender = console.input(
                "Filter by sender email (leave empty for all unread): "
            ).strip() or None
            batch_mark_read(service, emails, sender_email=sender, console=console)
        elif choice == "3":
            sender = console.input("Sender email to filter: ").strip()
            label = console.input("Label name to apply: ").strip()
            if sender and label:
                apply_label(service, emails, label, sender_email=sender, console=console)
        elif choice == "4":
            sender = console.input("Sender email to trash: ").strip()
            if sender:
                batch_trash(service, emails, sender_email=sender, console=console)
        elif choice == "5":
            show_subscription_actions(
                service, emails, report.subscriptions, console=console
            )
        else:
            console.print("[dim]Invalid choice.[/dim]")

        console.print()

    console.print("[bold green]Done! Your inbox is tidier now.[/bold green]")


@main.command()
@click.option("--query", "-q", default="", help="Gmail search query.")
@click.option("--older-than", default=365, help="Archive emails older than N days.")
@click.option(
    "--max-emails", "-n", default=500, show_default=True,
    help="Maximum number of emails to process.",
)
@click.pass_context
def archive(ctx, query: str, older_than: int, max_emails: int):
    """Quick action: archive old emails."""
    service = _get_service(ctx)
    emails = fetch_emails(service, query=query, max_results=max_emails)
    archive_old_emails(service, emails, older_than_days=older_than, console=console)


@main.command()
@click.option("--query", "-q", default="", help="Gmail search query.")
@click.option("--sender", "-s", default=None, help="Filter by sender email.")
@click.option(
    "--max-emails", "-n", default=500, show_default=True,
    help="Maximum number of emails to process.",
)
@click.pass_context
def mark_read(ctx, query: str, sender: str | None, max_emails: int):
    """Quick action: mark emails as read."""
    service = _get_service(ctx)
    emails = fetch_emails(service, query=query, max_results=max_emails)
    batch_mark_read(service, emails, sender_email=sender, console=console)


@main.command()
@click.option("--query", "-q", default="", help="Gmail search query.")
@click.option("--sender", "-s", required=True, help="Sender email to trash.")
@click.option(
    "--max-emails", "-n", default=500, show_default=True,
    help="Maximum number of emails to process.",
)
@click.pass_context
def trash(ctx, query: str, sender: str, max_emails: int):
    """Quick action: trash emails from a specific sender."""
    service = _get_service(ctx)
    emails = fetch_emails(service, query=query, max_results=max_emails)
    batch_trash(service, emails, sender_email=sender, console=console)


def _get_service(ctx):
    """Get authenticated Gmail service from context."""
    return get_gmail_service(ctx.obj["credentials"], ctx.obj["token"])


if __name__ == "__main__":
    main()
