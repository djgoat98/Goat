"""Robinhood integration — fetch portfolio data via robin_stocks."""

import os
from typing import Optional

import keyring

from .config import (
    ENV_RH_USERNAME, ENV_RH_PASSWORD, ENV_RH_MFA,
    KEYRING_SERVICE, KEYRING_RH_USER, KEYRING_RH_PASS,
)
from .exceptions import MissingCredentialsError, RobinhoodAuthError, RobinhoodDataError


def get_credentials() -> tuple[str, str]:
    """Resolve Robinhood credentials: env vars first, then keyring."""
    username = os.environ.get(ENV_RH_USERNAME) or keyring.get_password(KEYRING_SERVICE, KEYRING_RH_USER)
    password = os.environ.get(ENV_RH_PASSWORD) or keyring.get_password(KEYRING_SERVICE, KEYRING_RH_PASS)
    if not username or not password:
        raise MissingCredentialsError(
            f"Robinhood credentials not found.\n"
            f"Set {ENV_RH_USERNAME} and {ENV_RH_PASSWORD} as environment variables,\n"
            f"or run `goat connect --save-keyring` after setting them once."
        )
    return username, password


def save_to_keyring(username: str, password: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_RH_USER, username)
    keyring.set_password(KEYRING_SERVICE, KEYRING_RH_PASS, password)


def clear_keyring() -> None:
    for key in (KEYRING_RH_USER, KEYRING_RH_PASS):
        try:
            keyring.delete_password(KEYRING_SERVICE, key)
        except keyring.errors.PasswordDeleteError:
            pass


def login() -> None:
    """Log in to Robinhood. Session token cached by robin_stocks."""
    try:
        import robin_stocks.robinhood as rh
        username, password = get_credentials()
        mfa = os.environ.get(ENV_RH_MFA) or None
        rh.login(username, password, mfa_code=mfa, store_session=True)
    except MissingCredentialsError:
        raise
    except Exception as e:
        raise RobinhoodAuthError(f"Robinhood login failed: {e}") from e


def logout() -> None:
    try:
        import robin_stocks.robinhood as rh
        rh.logout()
    except Exception:
        pass


def get_portfolio_value() -> dict:
    try:
        import robin_stocks.robinhood as rh
        profile = rh.load_portfolio_profile()
        return {
            "equity": float(profile.get("equity") or 0),
            "extended_hours_equity": float(profile.get("extended_hours_equity") or 0),
            "market_value": float(profile.get("market_value") or 0),
            "withdrawable_amount": float(profile.get("withdrawable_amount") or 0),
        }
    except Exception as e:
        raise RobinhoodDataError(f"Failed to load portfolio profile: {e}") from e


def get_holdings() -> list[dict]:
    try:
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
    except Exception as e:
        raise RobinhoodDataError(f"Failed to load holdings: {e}") from e


def get_total_return() -> dict:
    try:
        import robin_stocks.robinhood as rh
        profile = rh.load_portfolio_profile()
        equity = float(profile.get("equity") or 0)
        adjusted = float(profile.get("adjusted_equity_previous_close") or equity)
        return {
            "equity": equity,
            "daily_change": equity - adjusted,
            "daily_change_pct": ((equity - adjusted) / adjusted * 100) if adjusted else 0,
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
