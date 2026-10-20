"""Pricing and inventory helpers for custom token address endings."""

from settings import CUSTOM_ADDRESS_PRICES


def calculate_custom_price(ending: str) -> float:
    """Return the configured price for an ending based on its character count."""
    if not isinstance(ending, str):
        raise TypeError("Custom address ending must be a string")

    try:
        return CUSTOM_ADDRESS_PRICES[len(ending)]
    except KeyError as error:
        raise ValueError(
            f"Unsupported custom address ending length: {len(ending)}"
        ) from error


def get_available_custom_endings() -> list:
    """Return available endings; none are configured in the current database."""
    return []
