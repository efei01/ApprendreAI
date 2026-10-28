from decimal import Decimal

from app.services.pricing import estimate_cost_usd


def test_estimates_cost_from_configured_prices() -> None:
    # 1M input tokens at $0.25 + 0.5M output tokens at $2.00 = $1.25
    cost = estimate_cost_usd(1_000_000, 500_000, Decimal("0.25"), Decimal("2.00"))
    assert cost == Decimal("1.250000")


def test_returns_none_when_prices_not_configured() -> None:
    assert estimate_cost_usd(100, 50, None, None) is None


def test_returns_none_when_token_counts_unknown() -> None:
    assert estimate_cost_usd(None, 50, Decimal("0.25"), Decimal("2.00")) is None
