from decimal import Decimal

TOKENS_PER_PRICE_UNIT = Decimal(1_000_000)  # prices are quoted per 1M tokens


def estimate_cost_usd(
    input_tokens: int | None,
    output_tokens: int | None,
    input_price_per_1m: Decimal | None,
    output_price_per_1m: Decimal | None,
) -> Decimal | None:
    """Return the estimated cost in USD, or None if any ingredient is unknown.

    Prices come from configuration (env vars), never from code, because they
    differ per model and change over time.
    """
    if (
        input_tokens is None
        or output_tokens is None
        or input_price_per_1m is None
        or output_price_per_1m is None
    ):
        return None
    cost = (input_tokens * input_price_per_1m + output_tokens * output_price_per_1m) / TOKENS_PER_PRICE_UNIT
    return cost.quantize(Decimal("0.000001"))
