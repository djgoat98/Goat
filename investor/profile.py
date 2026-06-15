"""Investor profile — stores and loads user goals and preferences."""

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional

from .config import GOAT_DIR, PROFILE_PATH
from .exceptions import ProfileNotFoundError


@dataclass
class InvestorProfile:
    name: str
    risk_tolerance: str          # conservative | moderate | aggressive
    goals: list[str]             # wealth_building | retirement | passive_income
    starting_capital: float
    monthly_contribution: float
    time_horizon_years: int
    age: Optional[int] = None
    notes: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        goals_str = ", ".join(g.replace("_", " ") for g in self.goals)
        return (
            f"Investor: {self.name}\n"
            f"Risk: {self.risk_tolerance} | Goals: {goals_str}\n"
            f"Starting capital: ${self.starting_capital:,.2f} | "
            f"Monthly contribution: ${self.monthly_contribution:,.2f}\n"
            f"Time horizon: {self.time_horizon_years} years"
        )


def save_profile(profile: InvestorProfile) -> None:
    GOAT_DIR.mkdir(parents=True, exist_ok=True)
    existing = _load_raw()
    if existing:
        profile.created_at = existing.get("created_at", profile.created_at)
    profile.updated_at = datetime.now().isoformat()
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile.to_dict(), f, indent=2)
    os.chmod(PROFILE_PATH, 0o600)


def load_profile() -> InvestorProfile:
    data = _load_raw()
    if data is None:
        raise ProfileNotFoundError(
            "No investor profile found. Run `goat setup` to create one."
        )
    return InvestorProfile(**data)


def profile_exists() -> bool:
    return PROFILE_PATH.exists()


def _load_raw() -> Optional[dict]:
    if not PROFILE_PATH.exists():
        return None
    with open(PROFILE_PATH) as f:
        return json.load(f)
