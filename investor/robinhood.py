"""Robinhood integration — fetch portfolio data via robin_stocks."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def _get_credentials() -> tuple[str, str]:
    username = os.getenv("ROBINHOOD_USERNAME", "")
    password = os.getenv("ROBINHOOD_PASSWORD", "")
    if not username or not password:
        raise ValueError(
            "Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD in your .env file "
            "or environment variables."
        )
    return username, password


def login() -> bool:
    """Log in to Robinhood. Returns True on success."""
    try:
        import robin_stocks.robinhood as rh
        username, password = _get_credentials()
        mfa = os.getenv("ROBINHOOD_MFA", None) or None
        rh.login(username, password, mfa_code=mfa, store_session=True)
        return True
    except Exception as e:
        raise RuntimeError(f"Robinhood login failed: {e}") from e


def logout() -> None:
    try:
        import robin_stocks.robinhood as rh
        rh.logout()
    except Exception:
        pass


def get_portfolio_value() -> dict:
    """Return total portfolio value and equity breakdown."""
    import robin_stocks.robinhood as rh
    profile = rh.load_portfolio_profile()
    return {
        "equity": float(profile.get("equity") or 0),
        "extended_hours_equity": float(profile.get("extended_hours_equity") or 0),
        "market_value": float(profile.get("market_value") or 0),
        "withdrawable_amount": float(profile.get("withdrawable_amount") or 0),
    }


def get_holdings() -> list[dict]:
    """Return current stock/ETF holdings with quantity, price, and gain."""
    import robin_stocks.robinhood as rh
    raw = rh.build_holdings()
    holdings = []
    for ticker, data in raw.items():
        holdings.append({
            "ticker": ticker,
            "name": data.get("name", ticker),
            "quantity": float(data.get("quantity", 0)),
            "average_buy_price": float(data.get("average_buy_price", 0)),
            "current_price": float(data.get("price", 0)),
            "equity": float(data.get("equity", 0)),
            "percent_change": float(data.get("percentage", 0)),
            "equity_change": float(data.get("equity_change", 0)),
            "type": data.get("type", "stock"),
            "pe_ratio": data.get("pe_ratio"),
        })
    return sorted(holdings, key=lambda x: x["equity"], reverse=True)


def get_dividends() -> list[dict]:
    """Return dividend payment history (last 20 entries)."""
    import robin_stocks.robinhood as rh
    raw = rh.get_dividends()
    dividends = []
    for d in (raw or [])[:20]:
        dividends.append({
            "ticker": d.get("instrument", ""),
            "amount": float(d.get("amount") or 0),
            "paid_at": d.get("paid_at", ""),
            "state": d.get("state", ""),
        })
    return dividends


def get_total_return() -> dict:
    """Return total portfolio return metrics."""
    import robin_stocks.robinhood as rh
    try:
        profile = rh.load_portfolio_profile()
        equity = float(profile.get("equity") or 0)
        adjusted_equity = float(profile.get("adjusted_equity_previous_close") or equity)
        return {
            "equity": equity,
            "daily_change": equity - adjusted_equity,
            "daily_change_pct": ((equity - adjusted_equity) / adjusted_equity * 100)
            if adjusted_equity
            else 0,
        }
    except Exception:
        return {"equity": 0, "daily_change": 0, "daily_change_pct": 0}


def build_portfolio_snapshot() -> dict:
    """Assemble a full portfolio snapshot for AI analysis."""
    portfolio = get_portfolio_value()
    holdings = get_holdings()
    total_return = get_total_return()

    total_equity = portfolio["equity"]
    allocation = []
    for h in holdings:
        pct = (h["equity"] / total_equity * 100) if total_equity else 0
        allocation.append({**h, "portfolio_pct": round(pct, 2)})

    return {
        "total_equity": total_equity,
        "market_value": portfolio["market_value"],
        "withdrawable_amount": portfolio["withdrawable_amount"],
        "daily_change": total_return["daily_change"],
        "daily_change_pct": total_return["daily_change_pct"],
        "holdings": allocation,
        "holdings_count": len(holdings),
    }
