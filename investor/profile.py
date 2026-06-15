"""Investor profile — stores and loads user goals and preferences."""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

PROFILE_DIR = Path.home() / ".goat"
PROFILE_PATH = PROFILE_DIR / "profile.json"


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

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        goals_str = ", ".join(self.goals)
        return (
            f"Investor: {self.name}\n"
            f"Risk: {self.risk_tolerance} | Goals: {goals_str}\n"
            f"Starting capital: ${self.starting_capital:,.2f} | "
            f"Monthly contribution: ${self.monthly_contribution:,.2f}\n"
            f"Time horizon: {self.time_horizon_years} years"
        )


def save_profile(profile: InvestorProfile) -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile.to_dict(), f, indent=2)


def load_profile() -> Optional[InvestorProfile]:
    if not PROFILE_PATH.exists():
        return None
    with open(PROFILE_PATH) as f:
        data = json.load(f)
    return InvestorProfile(**data)


def profile_exists() -> bool:
    return PROFILE_PATH.exists()
