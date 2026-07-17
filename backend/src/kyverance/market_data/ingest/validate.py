"""Validate normalized EOD batches before publication."""

from __future__ import annotations

from decimal import Decimal

from kyverance.config import Settings, get_settings
from kyverance.market_data.dto import NormalizedDailyPrice, ValidationIssue


def validate_batch(
    rows: list[NormalizedDailyPrice],
    *,
    expected_min_count: int | None = None,
    settings: Settings | None = None,
) -> tuple[list[NormalizedDailyPrice], list[ValidationIssue], bool]:
    """Returns (accepted, issues, publish_ok)."""
    s = settings or get_settings()
    accepted: list[NormalizedDailyPrice] = []
    issues: list[ValidationIssue] = []
    seen: set[tuple[str, str]] = set()

    for row in rows:
        ident = f"{row.provider_symbol}:{row.trading_date.isoformat()}"
        dup_key = (row.instrument_listing_id, row.trading_date.isoformat())
        if dup_key in seen:
            issues.append(ValidationIssue("duplicate", f"Duplicate {ident}", ident, severity="error"))
            continue
        seen.add(dup_key)

        if row.close is None or row.close <= 0:
            issues.append(ValidationIssue("invalid_close", f"Non-positive close {ident}", ident))
            continue
        if row.volume < 0:
            issues.append(ValidationIssue("invalid_volume", f"Negative volume {ident}", ident))
            continue
        if row.high < row.low:
            issues.append(ValidationIssue("high_below_low", f"High < low {ident}", ident))
            continue
        if row.open < row.low or row.open > row.high:
            issues.append(
                ValidationIssue(
                    "open_out_of_range", f"Open outside H/L {ident}", ident, severity="warning"
                )
            )
        if row.close < row.low or row.close > row.high:
            issues.append(ValidationIssue("close_out_of_range", f"Close outside H/L {ident}", ident))
            continue
        if not row.currency_code or len(row.currency_code) != 3:
            issues.append(ValidationIssue("invalid_currency", f"Bad currency {ident}", ident))
            continue
        if row.adjusted_close is None:
            issues.append(
                ValidationIssue(
                    "missing_adj_close", f"Missing adjusted_close {ident}", ident, severity="warning"
                )
            )
        if row.volume == 0:
            issues.append(
                ValidationIssue("zero_volume", f"Zero volume {ident}", ident, severity="warning")
            )

        if row.open > 0:
            move = abs(row.close - row.open) / row.open
            if move > Decimal("0.25"):
                issues.append(
                    ValidationIssue(
                        "large_move",
                        f"Intraday move {move:.2%} {ident}",
                        ident,
                        severity="warning",
                    )
                )

        accepted.append(row)

    errors = [i for i in issues if i.severity == "error"]
    publish_ok = len(accepted) > 0 and len(errors) == 0
    if expected_min_count and expected_min_count > 0:
        pct = 100.0 * len(accepted) / expected_min_count
        if pct < s.market_data_completeness_threshold_percent:
            issues.append(
                ValidationIssue(
                    "incomplete_batch",
                    f"Completeness {pct:.1f}% < {s.market_data_completeness_threshold_percent}%",
                    severity="error",
                )
            )
            publish_ok = False

    return accepted, issues, publish_ok
