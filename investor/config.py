"""Central configuration — all constants live here."""

from pathlib import Path

# Paths
GOAT_DIR = Path.home() / ".goat"
PROFILE_PATH = GOAT_DIR / "profile.json"

# Environment variable names
ENV_ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
ENV_RH_USERNAME = "ROBINHOOD_USERNAME"
ENV_RH_PASSWORD = "ROBINHOOD_PASSWORD"
ENV_RH_MFA = "ROBINHOOD_MFA"

# Keyring
KEYRING_SERVICE = "goat-investor-ai"
KEYRING_RH_USER = "robinhood_username"
KEYRING_RH_PASS = "robinhood_password"

# Claude model
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192

APP_NAME = "Goat Investor AI"
APP_VERSION = "0.1.0"
