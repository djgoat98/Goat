"""Claude AI advisor — streaming portfolio analysis and strategy generation."""

import os
import json
from collections.abc import Generator
from typing import Optional

import anthropic

from .config import ENV_ANTHROPIC_API_KEY, MODEL, MAX_TOKENS
from .exceptions import MissingCredentialsError, ClaudeAPIError
from .profile import InvestorProfile

SYSTEM_PROMPT = """You are a seasoned financial advisor and wealth-building strategist \
specializing in long-term growth through commission-free investing on platforms like Robinhood. \
Your philosophy draws on the democratizing spirit of Robin Hood — making wealth-building \
accessible to everyone regardless of starting capital.

Your core principles:
- Long-term compounding over speculation
- Low-cost index funds and ETFs as the foundation (VTI, VOO, SCHD, QQQ, VXUS)
- Diversification across sectors and asset classes
- Dollar-cost averaging to reduce timing risk
- Reinvesting dividends for exponential compounding
- Tax-efficient investing: hold >1 year for long-term capital gains rates
- Emotional discipline — ignore short-term noise, stay the course

You give direct, actionable advice grounded in financial fundamentals. \
Always reference specific tickers when recommending investments. \
Quantify projections using realistic historical averages (S&P 500 ~10% annual, bonds ~4-5%). \
Never recommend gambling, meme stocks, or over-concentrated single positions. \
Format responses with clear sections using markdown headers, bullet points, and dollar figures."""


def _client() -> anthropic.Anthropic:
    api_key = os.environ.get(ENV_ANTHROPIC_API_KEY)
    if not api_key:
        raise MissingCredentialsError(
            f"{ENV_ANTHROPIC_API_KEY} environment variable is not set."
        )
    return anthropic.Anthropic(api_key=api_key)


def analyze_portfolio(
    profile: InvestorProfile, snapshot: dict
) -> Generator[str, None, None]:
    """Stream AI analysis of a Robinhood portfolio against the investor's profile."""
    client = _client()

    user_message = f"""Please analyze my current Robinhood portfolio against my investor profile.

## My Investor Profile
{profile.summary()}

## Current Portfolio Snapshot
- Total equity: ${snapshot['total_equity']:,.2f}
- Market value: ${snapshot['market_value']:,.2f}
- Daily change: ${snapshot['daily_change']:+,.2f} ({snapshot['daily_change_pct']:+.2f}%)
- Number of holdings: {snapshot['holdings_count']}

## Current Holdings (sorted by value)
{json.dumps(snapshot['holdings'], indent=2)}

Please provide:
1. **Portfolio Health Assessment** — strengths and weaknesses vs my {profile.time_horizon_years}-year goals
2. **Allocation Analysis** — am I over/under-concentrated? Any sector gaps?
3. **Individual Position Review** — any holdings to reconsider given my {profile.risk_tolerance} risk tolerance?
4. **Top 3 Action Items** — most impactful changes I can make right now
5. **Monthly Contribution Plan** — how to deploy my ${profile.monthly_contribution:,.2f}/month

Be specific with ticker symbols and dollar amounts."""

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.APIError as e:
        raise ClaudeAPIError(f"Claude API error: {e}") from e


def generate_10_year_strategy(
    profile: InvestorProfile, snapshot: Optional[dict] = None
) -> Generator[str, None, None]:
    """Stream a comprehensive 10-year wealth-building plan."""
    client = _client()

    portfolio_section = ""
    if snapshot:
        portfolio_section = (
            f"\n## Current Portfolio\n"
            f"- Total equity: ${snapshot['total_equity']:,.2f}\n"
            f"- Holdings: {snapshot['holdings_count']} positions\n"
            f"- Top holdings: {', '.join(h['ticker'] for h in snapshot['holdings'][:5])}\n"
        )

    user_message = f"""Create a comprehensive 10-year wealth-building strategy for me on Robinhood.

## My Investor Profile
{profile.summary()}
{portfolio_section}
Please build a complete 10-year roadmap covering:

1. **Year-by-Year Milestones** — projected portfolio value at years 1, 3, 5, 7, and 10 \
(show conservative, base, and optimistic scenarios)

2. **Core Portfolio Blueprint** — ideal target allocation by percentage:
   - Index funds / ETFs (which ones, why, exact tickers)
   - Growth stocks (sectors and example tickers)
   - Dividend stocks (for passive income compounding)
   - Bonds/fixed income given my {profile.risk_tolerance} risk tolerance

3. **Monthly Investment Cadence** — exact DCA schedule for my ${profile.monthly_contribution:,.2f}/month:
   - Which funds/stocks to buy each month
   - Rebalancing schedule

4. **Compounding Math** — show the numbers:
   - Starting: ${profile.starting_capital:,.2f}
   - Monthly add: ${profile.monthly_contribution:,.2f}
   - At 7%, 10%, and 12% annual returns over {profile.time_horizon_years} years

5. **Wealth Milestones** — when I'll hit $50K, $100K, $250K, $500K, $1M

6. **Risk Management Rules** — when to sell, stop-loss discipline, rebalancing triggers

7. **Tax Strategy on Robinhood** — maximize returns by minimizing taxes (long-term gains, wash sales)

8. **5 Behavioral Rules** — rules I must never break during market downturns

Give me a concrete plan I can execute starting today."""

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.APIError as e:
        raise ClaudeAPIError(f"Claude API error: {e}") from e


def generate_report(
    profile: InvestorProfile, snapshot: dict
) -> Generator[str, None, None]:
    """Stream a progress report: current trajectory vs 10-year goals."""
    client = _client()

    user_message = f"""Generate a progress report for my investment journey.

## My Investor Profile
{profile.summary()}

## Current Portfolio
- Total equity: ${snapshot['total_equity']:,.2f}
- Holdings: {snapshot['holdings_count']} positions
- Daily change: ${snapshot['daily_change']:+,.2f} ({snapshot['daily_change_pct']:+.2f}%)
- Top 5 holdings: {json.dumps(snapshot['holdings'][:5], indent=2)}

Please give me:

1. **Trajectory Assessment** — am I on track for my {profile.time_horizon_years}-year goals? \
Where should I be at this stage?

2. **What's Working** — positions and habits that are serving my long-term goals

3. **What Needs Attention** — gaps or risks that could derail my 10-year plan

4. **90-Day Priorities** — the 3 most important actions for the next 90 days

5. **Motivation** — brief reminder of what this wealth means at the 10-year finish line

Keep it honest and actionable."""

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.APIError as e:
        raise ClaudeAPIError(f"Claude API error: {e}") from e


def ask_advisor(
    profile: InvestorProfile, question: str, snapshot: Optional[dict] = None
) -> Generator[str, None, None]:
    """Stream an answer to a freeform investment question."""
    client = _client()

    context = f"Investor profile: {profile.summary()}"
    if snapshot:
        context += f"\nCurrent portfolio equity: ${snapshot['total_equity']:,.2f}"

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"{context}\n\nMy question: {question}"}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.APIError as e:
        raise ClaudeAPIError(f"Claude API error: {e}") from e
