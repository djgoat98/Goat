"""Custom exception hierarchy for Goat."""


class GoatError(Exception):
    """Base exception for all Goat errors."""


class ProfileNotFoundError(GoatError):
    """No investor profile exists yet — user needs to run `goat setup`."""


class RobinhoodAuthError(GoatError):
    """Robinhood login failed."""


class RobinhoodDataError(GoatError):
    """Failed to retrieve data from Robinhood."""


class MissingCredentialsError(GoatError):
    """Required credentials are absent from env vars and keyring."""


class ClaudeAPIError(GoatError):
    """Claude API call failed."""
