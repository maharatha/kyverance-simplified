"""Deterministic research metrics — AI must never invent these numbers."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from kyverance.research.evidence import EvidenceBundle


def compute_deterministic_metrics(bundle: EvidenceBundle) -> dict[str, Any]:
    close = bundle.close
    prior = bundle.prior_close if bundle.prior_close is not None else close
    if close is None or prior is None:
        return {
            "close": None,
            "prior_close": None,
            "absolute_return": None,
            "pct_return": None,
            "volume": bundle.volume,
            "history_bars": len(bundle.history),
            "gaps": list(bundle.gaps),
            "valuation_ratios": {},
            "trend": {"available": False, "reason": "insufficient_price_history"},
        }

    abs_move = close - prior
    pct_move = (abs_move / prior) if prior != 0 else Decimal("0")

    closes = [Decimal(str(h["close"])) for h in bundle.history if h.get("close") is not None]
    trend: dict[str, Any] = {"available": False, "reason": "insufficient_price_history"}
    if len(closes) >= 5:
        window = closes[-5:]
        first, last = window[0], window[-1]
        window_ret = ((last - first) / first) if first != 0 else Decimal("0")
        direction = "up" if window_ret > 0 else "down" if window_ret < 0 else "flat"
        trend = {
            "available": True,
            "bars": len(window),
            "window_return": str(window_ret.quantize(Decimal("0.0001"))),
            "direction": direction,
        }

    return {
        "close": str(close),
        "prior_close": str(prior),
        "absolute_return": str(abs_move.quantize(Decimal("0.0001"))),
        "pct_return": str(pct_move.quantize(Decimal("0.0001"))),
        "volume": bundle.volume,
        "history_bars": len(bundle.history),
        "gaps": list(bundle.gaps),
        "valuation_ratios": {
            # Fundamentals not in MRKT-01 warehouse — explicitly unavailable.
            "pe_ttm": None,
            "eps_ttm": None,
            "gross_margin": None,
            "availability": "insufficient_data",
        },
        "trend": trend,
    }
