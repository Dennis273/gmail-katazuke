"""Analyze fetched email metadata and produce reports."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .fetcher import EmailMeta


@dataclass
class AnalysisReport:
    """Container for all analysis results."""

    total_emails: int = 0
    unread_count: int = 0
    total_size_mb: float = 0.0

    # Top senders: email -> count
    top_senders: list[tuple[str, str, int]] = field(default_factory=list)

    # Label distribution: label_name -> count
    label_distribution: list[tuple[str, int]] = field(default_factory=list)

    # Monthly volume: "YYYY-MM" -> count
    monthly_volume: list[tuple[str, int]] = field(default_factory=list)

    # Large emails: list of (subject, sender, size_mb)
    large_emails: list[tuple[str, str, str, float]] = field(default_factory=list)

    # Likely newsletters/subscriptions: sender_email -> count
    subscriptions: list[tuple[str, str, int]] = field(default_factory=list)

    # Old unread emails older than 1 year
    old_unread_count: int = 0

    # Emails by age bucket
    age_buckets: list[tuple[str, int]] = field(default_factory=list)


def analyze(emails: list[EmailMeta], label_map: dict[str, str]) -> AnalysisReport:
    """Analyze email metadata and return a report."""
    report = AnalysisReport()
    report.total_emails = len(emails)

    if not emails:
        return report

    now = datetime.now(timezone.utc)
    sender_counter: Counter[str] = Counter()
    sender_names: dict[str, str] = {}
    label_counter: Counter[str] = Counter()
    month_counter: Counter[str] = Counter()
    subscription_counter: Counter[str] = Counter()
    subscription_names: dict[str, str] = {}

    age_buckets_map = {
        "< 1 month": 0,
        "1-3 months": 0,
        "3-6 months": 0,
        "6-12 months": 0,
        "1-2 years": 0,
        "> 2 years": 0,
    }

    total_size = 0

    for em in emails:
        # Unread
        if em.is_unread:
            report.unread_count += 1

        # Size
        total_size += em.size_bytes

        # Sender
        if em.sender_email:
            sender_counter[em.sender_email] += 1
            if em.sender_email not in sender_names:
                sender_names[em.sender_email] = em.sender

        # Labels
        for label_id in em.labels:
            label_name = label_map.get(label_id, label_id)
            label_counter[label_name] += 1

        # Monthly volume
        if em.date:
            month_key = em.date.strftime("%Y-%m")
            month_counter[month_key] += 1

        # Subscriptions (has List-Unsubscribe header or looks like newsletter)
        if em.list_unsubscribe or _looks_like_newsletter(em):
            if em.sender_email:
                subscription_counter[em.sender_email] += 1
                if em.sender_email not in subscription_names:
                    subscription_names[em.sender_email] = em.sender

        # Age buckets
        if em.date:
            age_days = (now - em.date).days
            if age_days < 30:
                age_buckets_map["< 1 month"] += 1
            elif age_days < 90:
                age_buckets_map["1-3 months"] += 1
            elif age_days < 180:
                age_buckets_map["3-6 months"] += 1
            elif age_days < 365:
                age_buckets_map["6-12 months"] += 1
            elif age_days < 730:
                age_buckets_map["1-2 years"] += 1
            else:
                age_buckets_map["> 2 years"] += 1

            # Old unread
            if em.is_unread and age_days > 365:
                report.old_unread_count += 1

    report.total_size_mb = total_size / (1024 * 1024)

    # Top 20 senders
    report.top_senders = [
        (addr, sender_names.get(addr, addr), count)
        for addr, count in sender_counter.most_common(20)
    ]

    # Label distribution (top 15)
    report.label_distribution = label_counter.most_common(15)

    # Monthly volume (sorted by month)
    report.monthly_volume = sorted(month_counter.items())

    # Large emails (top 20 by size)
    large = sorted(emails, key=lambda e: e.size_bytes, reverse=True)[:20]
    report.large_emails = [
        (em.id, em.subject[:60], em.sender, em.size_bytes / (1024 * 1024))
        for em in large
    ]

    # Subscriptions (top 20)
    report.subscriptions = [
        (addr, subscription_names.get(addr, addr), count)
        for addr, count in subscription_counter.most_common(20)
    ]

    # Age buckets
    report.age_buckets = list(age_buckets_map.items())

    return report


def _looks_like_newsletter(em: EmailMeta) -> bool:
    """Heuristic: detect newsletter/marketing emails."""
    indicators = [
        "unsubscribe" in em.snippet.lower(),
        "noreply" in em.sender_email,
        "no-reply" in em.sender_email,
        "newsletter" in em.sender_email,
        "marketing" in em.sender_email,
        "notification" in em.sender_email,
        "digest" in em.sender_email,
    ]
    return any(indicators)


def print_report(report: AnalysisReport, console: Console | None = None) -> None:
    """Print the analysis report to the console using Rich."""
    console = console or Console()

    # Overview panel
    overview = Table(show_header=False, box=None, padding=(0, 2))
    overview.add_column(style="bold cyan")
    overview.add_column()
    overview.add_row("Total emails", f"{report.total_emails:,}")
    overview.add_row("Unread emails", f"{report.unread_count:,}")
    overview.add_row("Total size", f"{report.total_size_mb:.1f} MB")
    overview.add_row("Old unread (>1yr)", f"{report.old_unread_count:,}")

    console.print(Panel(overview, title="[bold]Mailbox Overview", border_style="blue"))
    console.print()

    # Top senders
    if report.top_senders:
        table = Table(title="Top Senders", show_lines=False)
        table.add_column("#", style="dim", width=4)
        table.add_column("Sender", style="cyan")
        table.add_column("Email", style="dim")
        table.add_column("Count", justify="right", style="bold")
        for i, (addr, name, count) in enumerate(report.top_senders, 1):
            table.add_row(str(i), name, addr, str(count))
        console.print(table)
        console.print()

    # Subscriptions / newsletters
    if report.subscriptions:
        table = Table(title="Detected Subscriptions / Newsletters", show_lines=False)
        table.add_column("#", style="dim", width=4)
        table.add_column("Sender", style="yellow")
        table.add_column("Email", style="dim")
        table.add_column("Count", justify="right", style="bold")
        for i, (addr, name, count) in enumerate(report.subscriptions, 1):
            table.add_row(str(i), name, addr, str(count))
        console.print(table)
        console.print()

    # Label distribution
    if report.label_distribution:
        table = Table(title="Label Distribution", show_lines=False)
        table.add_column("Label", style="green")
        table.add_column("Count", justify="right", style="bold")
        for label, count in report.label_distribution:
            table.add_row(label, str(count))
        console.print(table)
        console.print()

    # Age distribution
    if report.age_buckets:
        table = Table(title="Email Age Distribution", show_lines=False)
        table.add_column("Age", style="magenta")
        table.add_column("Count", justify="right", style="bold")
        table.add_column("Bar")
        max_count = max(c for _, c in report.age_buckets) if report.age_buckets else 1
        for bucket, count in report.age_buckets:
            bar_len = int(count / max(max_count, 1) * 30)
            bar = "█" * bar_len
            table.add_row(bucket, str(count), f"[blue]{bar}[/blue]")
        console.print(table)
        console.print()

    # Monthly volume (last 12 months)
    if report.monthly_volume:
        recent = report.monthly_volume[-12:]
        table = Table(title="Monthly Volume (Last 12 Months)", show_lines=False)
        table.add_column("Month", style="cyan")
        table.add_column("Count", justify="right", style="bold")
        table.add_column("Bar")
        max_count = max(c for _, c in recent) if recent else 1
        for month, count in recent:
            bar_len = int(count / max(max_count, 1) * 30)
            bar = "█" * bar_len
            table.add_row(month, str(count), f"[green]{bar}[/green]")
        console.print(table)
        console.print()

    # Largest emails
    if report.large_emails:
        table = Table(title="Largest Emails (Top 20)", show_lines=False)
        table.add_column("#", style="dim", width=4)
        table.add_column("Subject", style="cyan", max_width=50)
        table.add_column("Sender", style="dim")
        table.add_column("Size (MB)", justify="right", style="bold red")
        for i, (msg_id, subject, sender, size_mb) in enumerate(report.large_emails, 1):
            table.add_row(str(i), subject or "(no subject)", sender, f"{size_mb:.2f}")
        console.print(table)
        console.print()
