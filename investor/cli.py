"""Goat CLI — investor AI commands."""

import datetime
from collections.abc import Generator
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich import box

from .config import APP_NAME, APP_VERSION
from .profile import InvestorProfile, save_profile, load_profile, profile_exists
from .exceptions import (
    ProfileNotFoundError, RobinhoodAuthError, RobinhoodDataError,
    MissingCredentialsError, ClaudeAPIError,
)
from . import robinhood as rh
from . import ai_advisor

app = typer.Typer(
    name="goat",
    help=f"[bold green]{APP_NAME}[/bold green] — Robin Hood 10-year wealth engine",
    rich_markup_mode="rich",
)
console = Console()


def _require_profile() -> InvestorProfile:
    try:
        return load_profile()
    except ProfileNotFoundError as e:
        console.print(f"[bold red]No profile found.[/bold red] Run [cyan]goat setup[/cyan] first.")
        raise typer.Exit(1)


def _banner() -> None:
    console.print(
        Panel.fit(
            f"[bold green] {APP_NAME} v{APP_VERSION} [/bold green]\n"
            "[dim]Robin Hood 10-Year Wealth Engine[/dim]",
            border_style="green",
        )
    )


def _stream_to_console(title: str, generator: Generator[str, None, None]) -> str:
    """Stream AI output live to the terminal, then render final markdown."""
    accumulated = ""
    console.print(f"\n[bold green]{title}[/bold green]")
    console.print("─" * 60)
    with Live(console=console, refresh_per_second=15, vertical_overflow="visible") as live:
        for chunk in generator:
            accumulated += chunk
            live.update(Text(accumulated))
    console.print("─" * 60)
    console.print(Panel(Markdown(accumulated), border_style="green", padding=(1, 2)))
    return accumulated


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command()
def setup() -> None:
    """Create or update your investor profile."""
    _banner()
    if profile_exists():
        existing = load_profile()
        console.print(f"[yellow]Existing profile found for {existing.name}.[/yellow]")
        if not Confirm.ask("Update it?"):
            raise typer.Exit()

    console.print("\n[bold]Let's build your investor profile.[/bold]\n")

    name = Prompt.ask("Your name")
    age_str = Prompt.ask("Your age (optional, press Enter to skip)", default="")
    age = int(age_str) if age_str.strip().isdigit() else None

    console.print("\nRisk tolerance:")
    console.print("  [cyan]1[/cyan] Conservative — capital preservation, slow steady growth")
    console.print("  [cyan]2[/cyan] Moderate — balanced growth and stability")
    console.print("  [cyan]3[/cyan] Aggressive — maximum growth, comfortable with volatility")
    risk_choice = Prompt.ask("Choose", choices=["1", "2", "3"], default="2")
    risk_map = {"1": "conservative", "2": "moderate", "3": "aggressive"}
    risk = risk_map[risk_choice]

    console.print("\nInvestment goals (select all that apply):")
    console.print("  [cyan]1[/cyan] Wealth building")
    console.print("  [cyan]2[/cyan] Retirement")
    console.print("  [cyan]3[/cyan] Passive income (dividends)")
    goals_input = Prompt.ask("Enter numbers separated by commas", default="1,2")
    goal_map = {"1": "wealth_building", "2": "retirement", "3": "passive_income"}
    goals = [goal_map[g.strip()] for g in goals_input.split(",") if g.strip() in goal_map]
    if not goals:
        goals = ["wealth_building"]

    starting_capital = float(Prompt.ask("Starting/current capital ($)", default="5000"))
    monthly_contribution = float(Prompt.ask("Monthly contribution ($)", default="500"))
    time_horizon = int(Prompt.ask("Time horizon (years)", default="10"))
    notes = Prompt.ask("Any notes about your situation (optional)", default="")

    profile = InvestorProfile(
        name=name,
        age=age,
        risk_tolerance=risk,
        goals=goals,
        starting_capital=starting_capital,
        monthly_contribution=monthly_contribution,
        time_horizon_years=time_horizon,
        notes=notes or None,
    )
    save_profile(profile)

    console.print(
        Panel(
            f"[green]Profile saved![/green]\n\n{profile.summary()}",
            title="Your Investor Profile",
            border_style="green",
        )
    )
    console.print("\nNext steps:")
    console.print("  [cyan]goat connect[/cyan]  — link your Robinhood account")
    console.print("  [cyan]goat strategy[/cyan] — generate your 10-year wealth plan (works without Robinhood too)")


@app.command()
def connect(
    save_keyring: bool = typer.Option(False, "--save-keyring", help="Save credentials to system keyring"),
    do_logout: bool = typer.Option(False, "--logout", help="Log out and clear saved credentials"),
) -> None:
    """Connect to your Robinhood account and verify access."""
    _banner()

    if do_logout:
        rh.logout()
        rh.clear_keyring()
        console.print("[yellow]Logged out and cleared saved credentials.[/yellow]")
        raise typer.Exit()

    console.print("Connecting to Robinhood…")
    try:
        with console.status("[bold green]Logging in…"):
            rh.login()
        if save_keyring:
            username, password = rh.get_credentials()
            rh.save_to_keyring(username, password)
            console.print("[green]Credentials saved to system keyring.[/green]")
        with console.status("[bold green]Fetching portfolio…"):
            snap = rh.build_portfolio_snapshot()
    except (MissingCredentialsError, RobinhoodAuthError, RobinhoodDataError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[green]Connected![/green]\n"
            f"Portfolio equity: [bold]${snap['total_equity']:,.2f}[/bold]\n"
            f"Holdings: {snap['holdings_count']} positions",
            title="Robinhood Account",
            border_style="green",
        )
    )
    console.print("\nRun [cyan]goat analyze[/cyan] to get AI analysis of your portfolio.")
    console.print("Run [cyan]goat connect --logout[/cyan] to log out.")


@app.command()
def analyze() -> None:
    """Analyze your Robinhood portfolio with AI."""
    _banner()
    profile = _require_profile()

    try:
        with console.status("[bold green]Connecting to Robinhood…"):
            rh.login()
            snap = rh.build_portfolio_snapshot()
    except (MissingCredentialsError, RobinhoodAuthError, RobinhoodDataError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    _print_holdings_table(snap)

    console.print("\n[bold]Running AI portfolio analysis…[/bold]")
    try:
        _stream_to_console("AI Portfolio Analysis", ai_advisor.analyze_portfolio(profile, snap))
    except (MissingCredentialsError, ClaudeAPIError) as e:
        console.print(f"[red]AI error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def strategy() -> None:
    """Generate your personalized 10-year wealth-building plan."""
    _banner()
    profile = _require_profile()

    snap = None
    if Confirm.ask("Include your current Robinhood portfolio in the strategy?", default=True):
        try:
            with console.status("[bold green]Fetching Robinhood data…"):
                rh.login()
                snap = rh.build_portfolio_snapshot()
        except Exception as e:
            console.print(f"[yellow]Could not fetch Robinhood data ({e}). Continuing without it.[/yellow]")

    console.print("\n[bold]Generating your 10-year wealth strategy…[/bold]")
    try:
        plan = _stream_to_console(
            "Your 10-Year Wealth Strategy",
            ai_advisor.generate_10_year_strategy(profile, snap),
        )
    except (MissingCredentialsError, ClaudeAPIError) as e:
        console.print(f"[red]AI error:[/red] {e}")
        raise typer.Exit(1)

    if Confirm.ask("\nSave this strategy to a file?", default=True):
        filename = f"strategy_{datetime.date.today()}.md"
        with open(filename, "w") as f:
            f.write(f"# Goat 10-Year Wealth Strategy\n")
            f.write(f"Generated: {datetime.date.today()}\n\n")
            f.write(f"## Investor Profile\n{profile.summary()}\n\n")
            f.write(plan)
        console.print(f"[green]Strategy saved to[/green] [cyan]{filename}[/cyan]")


@app.command()
def report() -> None:
    """Show portfolio snapshot and AI progress report vs your 10-year goals."""
    _banner()
    profile = _require_profile()

    console.print(Panel(profile.summary(), title="Your Investor Profile", border_style="cyan"))

    try:
        with console.status("[bold green]Fetching Robinhood data…"):
            rh.login()
            snap = rh.build_portfolio_snapshot()
    except (MissingCredentialsError, RobinhoodAuthError, RobinhoodDataError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    _print_holdings_table(snap)

    console.print("\n[bold]Generating progress report…[/bold]")
    try:
        _stream_to_console("Progress vs 10-Year Goals", ai_advisor.generate_report(profile, snap))
    except (MissingCredentialsError, ClaudeAPIError) as e:
        console.print(f"[red]AI error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def ask(question: str = typer.Argument(..., help="Your investment question")) -> None:
    """Ask your AI advisor any investment question."""
    _banner()
    profile = _require_profile()

    try:
        _stream_to_console("Advisor Response", ai_advisor.ask_advisor(profile, question))
    except (MissingCredentialsError, ClaudeAPIError) as e:
        console.print(f"[red]AI error:[/red] {e}")
        raise typer.Exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_holdings_table(snap: dict) -> None:
    table = Table(
        title=f"Portfolio  —  ${snap['total_equity']:,.2f} total equity",
        box=box.ROUNDED,
        border_style="green",
    )
    table.add_column("Ticker", style="bold cyan", width=8)
    table.add_column("Name", style="dim", max_width=22)
    table.add_column("Qty", justify="right")
    table.add_column("Avg Cost", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Value", justify="right", style="bold")
    table.add_column("Change", justify="right")
    table.add_column("% Port", justify="right")

    for h in snap["holdings"]:
        change = h["percent_change"]
        change_style = "green" if change >= 0 else "red"
        table.add_row(
            h["ticker"],
            h["name"][:22],
            f"{h['quantity']:.4f}",
            f"${h['average_buy_price']:.2f}",
            f"${h['current_price']:.2f}",
            f"${h['equity']:,.2f}",
            Text(f"{change:+.1f}%", style=change_style),
            f"{h['portfolio_pct']:.1f}%",
        )

    console.print(table)
    daily = snap["daily_change"]
    daily_pct = snap["daily_change_pct"]
    color = "green" if daily >= 0 else "red"
    console.print(f"Daily P&L: [{color}]{daily:+,.2f} ({daily_pct:+.2f}%)[/{color}]")
