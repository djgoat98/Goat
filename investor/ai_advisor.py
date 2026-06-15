"""Claude AI advisor — portfolio analysis and 10-year strategy generation."""

import os
import json
from typing import Optional
import anthropic
from dotenv import load_dotenv

from .profile import InvestorProfile

load_dotenv()

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a seasoned financial advisor and wealth-building strategist \
specializing in long-term growth through commission-free investing on platforms like Robinhood. \
Your philosophy draws on the democratizing spirit of Robin Hood — making wealth-building \
accessible to everyone regardless of starting capital.

Your core principles:
- Long-term compounding over speculation
- Low-cost index funds and ETFs as the foundation
- Diversification across sectors and asset classes
- Dollar-cost averaging to reduce timing risk
- Reinvesting dividends for exponential compounding
- Tax-efficient investing strategies
- Emotional discipline — ignore short-term noise

You give direct, actionable advice grounded in financial fundamentals. \
You always reference specific tickers when recommending investments. \
You quantify projections using realistic historical averages (S&P 500 ~10% annual, bonds ~4-5%). \
You never recommend gambling, meme stocks, or over-concentrated positions. \
Format responses with clear sections, bullet points, and dollar figures where relevant."""


def _client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
    return anthropic.Anthropic(api_key=api_key)


def analyze_portfolio(profile: InvestorProfile, snapshot: dict) -> str:
    """Analyze a Robinhood portfolio snapshot against the investor's profile."""
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
2. **Allocation Analysis** — am I over/under-concentrated anywhere? Sector gaps?
3. **Individual Position Review** — any holdings I should reconsider given my risk tolerance ({profile.risk_tolerance})?
4. **Top 3 Action Items** — the most impactful changes I can make right now
5. **Monthly Contribution Plan** — how should I deploy my ${profile.monthly_contribution:,.2f}/month contribution?

Be specific with ticker symbols and dollar amounts."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def generate_10_year_strategy(
    profile: InvestorProfile, snapshot: Optional[dict] = None
) -> str:
    """Generate a comprehensive 10-year wealth-building plan."""
    client = _client()

    portfolio_section = ""
    if snapshot:
        portfolio_section = f"""
## Current Portfolio
- Total equity: ${snapshot['total_equity']:,.2f}
- Holdings: {snapshot['holdings_count']} positions
- Top holdings: {", ".join(h["ticker"] for h in snapshot["holdings"][:5])}
"""

    user_message = f"""Create a comprehensive 10-year wealth-building strategy for me on Robinhood.

## My Investor Profile
{profile.summary()}
{portfolio_section}

Please build me a complete 10-year roadmap covering:

1. **Year-by-Year Milestones** — projected portfolio value at years 1, 3, 5, 7, and 10 \
(show conservative, base, and optimistic scenarios)

2. **Core Portfolio Blueprint** — my ideal target allocation by percentage:
   - Index funds / ETFs (which ones, why)
   - Growth stocks (sectors and example tickers)
   - Dividend stocks (for passive income)
   - Any bonds/fixed income given my risk tolerance

3. **Monthly Investment Cadence** — exact DCA schedule for my ${profile.monthly_contribution:,.2f}/month:
   - Which funds/stocks to buy each month
   - When to rebalance

4. **Compounding Calculator** — show the math:
   - Starting: ${profile.starting_capital:,.2f}
   - Monthly add: ${profile.monthly_contribution:,.2f}
   - At 7%, 10%, and 12% annual returns over {profile.time_horizon_years} years

5. **Wealth Milestones** — when I'll hit $50K, $100K, $250K, $500K, $1M

6. **Risk Management Rules** — when to sell, stop-loss discipline, rebalancing triggers

7. **Tax Strategy on Robinhood** — maximize returns by minimizing taxes

8. **Behavioral Rules** — the 5 rules I must never break during market downturns

Give me a concrete plan I can execute starting today."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def ask_advisor(profile: InvestorProfile, question: str, snapshot: Optional[dict] = None) -> str:
    """Ask a freeform question to the AI advisor."""
    client = _client()

    context = f"Investor profile: {profile.summary()}"
    if snapshot:
        context += f"\nCurrent portfolio equity: ${snapshot['total_equity']:,.2f}"

    messages = [
        {"role": "user", "content": f"{context}\n\nMy question: {question}"},
    ]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text
