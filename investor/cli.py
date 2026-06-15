"""Goat CLI — investor AI commands."""

import sys
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box
from rich.text import Text
from rich.markdown import Markdown

from .profile import InvestorProfile, save_profile, load_profile, profile_exists
from . import robinhood as rh
from . import ai_advisor

app = typer.Typer(
    name="goat",
    help="[bold green]Goat Investor AI[/bold green] — Robin Hood 10-year wealth engine",
    rich_markup_mode="rich",
)
console = Console()


def _require_profile() -> InvestorProfile:
    profile = load_profile()
    if not profile:
        console.print(
            "[bold red]No profile found.[/bold red] Run [cyan]goat setup[/cyan] first."
        )
        raise typer.Exit(1)
    return profile


def _banner() -> None:
    console.print(
        Panel.fit(
            "[bold green] GOAT Investor AI [/bold green]\n"
            "[dim]Robin Hood 10-Year Wealth Engine[/dim]",
            border_style="green",
        )
    )


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command()
def setup() -> None:
    """Create or update your investor profile."""
    _banner()
    existing = load_profile()
    if existing:
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

    starting_capital = float(
        Prompt.ask("Starting/current capital ($)", default="5000")
    )
    monthly_contribution = float(
        Prompt.ask("Monthly contribution ($)", default="500")
    )
    time_horizon = int(
        Prompt.ask("Time horizon (years)", default="10")
    )
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
    console.print("  [cyan]goat strategy[/cyan] — generate your 10-year wealth plan (no Robinhood needed)")


@app.command()
def connect() -> None:
    """Connect to your Robinhood account and verify access."""
    _banner()
    console.print("Connecting to Robinhood…")
    with console.status("[bold green]Logging in…"):
        try:
            rh.login()
        except Exception as e:
            console.print(f"[red]Login failed:[/red] {e}")
            console.print(
                "Make sure [cyan]ROBINHOOD_USERNAME[/cyan] and "
                "[cyan]ROBINHOOD_PASSWORD[/cyan] are set in your .env file."
            )
            raise typer.Exit(1)

    with console.status("[bold green]Fetching portfolio…"):
        try:
            snap = rh.build_portfolio_snapshot()
        except Exception as e:
            console.print(f"[red]Failed to fetch portfolio:[/red] {e}")
            raise typer.Exit(1)
        finally:
            rh.logout()

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


@app.command()
def analyze() -> None:
    """Analyze your Robinhood portfolio with AI."""
    _banner()
    profile = _require_profile()

    console.print("Fetching your Robinhood portfolio…")
    with console.status("[bold green]Connecting to Robinhood…"):
        try:
            rh.login()
            snap = rh.build_portfolio_snapshot()
            rh.logout()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    _print_holdings_table(snap)

    console.print("\n[bold]Running AI analysis…[/bold] (this may take 15–30 seconds)")
    with console.status("[bold green]Consulting your AI advisor…"):
        try:
            analysis = ai_advisor.analyze_portfolio(profile, snap)
        except Exception as e:
            console.print(f"[red]AI analysis failed:[/red] {e}")
            raise typer.Exit(1)

    console.print(
        Panel(
            Markdown(analysis),
            title="[bold green]AI Portfolio Analysis[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


@app.command()
def strategy() -> None:
    """Generate your personalized 10-year wealth-building plan."""
    _banner()
    profile = _require_profile()

    snap = None
    if Confirm.ask("Include your current Robinhood portfolio in the strategy?", default=True):
        with console.status("[bold green]Fetching Robinhood data…"):
            try:
                rh.login()
                snap = rh.build_portfolio_snapshot()
                rh.logout()
            except Exception as e:
                console.print(f"[yellow]Could not fetch Robinhood data ({e}). Continuing without it.[/yellow]")

    console.print("\n[bold]Generating your 10-year strategy…[/bold] (this may take 30–60 seconds)")
    with console.status("[bold green]Your AI advisor is building your wealth plan…"):
        try:
            plan = ai_advisor.generate_10_year_strategy(profile, snap)
        except Exception as e:
            console.print(f"[red]Strategy generation failed:[/red] {e}")
            raise typer.Exit(1)

    console.print(
        Panel(
            Markdown(plan),
            title="[bold green]Your 10-Year Wealth Strategy[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )

    if Confirm.ask("\nSave this strategy to a file?", default=True):
        import datetime
        filename = f"strategy_{datetime.date.today()}.md"
        with open(filename, "w") as f:
            f.write(f"# Goat 10-Year Wealth Strategy\n")
            f.write(f"Generated: {datetime.date.today()}\n\n")
            f.write(f"## Investor Profile\n{profile.summary()}\n\n")
            f.write(plan)
        console.print(f"[green]Strategy saved to[/green] [cyan]{filename}[/cyan]")


@app.command()
def ask(question: str = typer.Argument(..., help="Your investment question")) -> None:
    """Ask your AI advisor any investment question."""
    _banner()
    profile = _require_profile()

    snap = None
    with console.status("[bold green]Thinking…"):
        try:
            answer = ai_advisor.ask_advisor(profile, question, snap)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    console.print(
        Panel(
            Markdown(answer),
            title=f"[bold green]Advisor Response[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


@app.command()
def report() -> None:
    """Show your investor profile and portfolio snapshot."""
    _banner()
    profile = _require_profile()

    console.print(
        Panel(profile.summary(), title="Your Investor Profile", border_style="cyan")
    )

    if Confirm.ask("\nFetch live Robinhood data?", default=True):
        with console.status("[bold green]Fetching portfolio…"):
            try:
                rh.login()
                snap = rh.build_portfolio_snapshot()
                rh.logout()
                _print_holdings_table(snap)
            except Exception as e:
                console.print(f"[yellow]Could not fetch Robinhood data: {e}[/yellow]")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_holdings_table(snap: dict) -> None:
    table = Table(
        title=f"Portfolio — ${snap['total_equity']:,.2f} total equity",
        box=box.ROUNDED,
        border_style="green",
        show_footer=False,
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
        change_str = f"{change:+.1f}%"
        change_style = "green" if change >= 0 else "red"
        table.add_row(
            h["ticker"],
            h["name"][:22],
            f"{h['quantity']:.4f}",
            f"${h['average_buy_price']:.2f}",
            f"${h['current_price']:.2f}",
            f"${h['equity']:,.2f}",
            Text(change_str, style=change_style),
            f"{h['portfolio_pct']:.1f}%",
        )

    console.print(table)
    daily = snap["daily_change"]
    daily_pct = snap["daily_change_pct"]
    color = "green" if daily >= 0 else "red"
    console.print(
        f"Daily P&L: [{color}]{daily:+,.2f} ({daily_pct:+.2f}%)[/{color}]"
    )
