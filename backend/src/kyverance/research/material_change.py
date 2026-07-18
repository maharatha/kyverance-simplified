"""Material-change scoring for rebuild decisions (deterministic, AI-off)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from kyverance.research.constants import SECTION_KEYS
from kyverance.research.evidence import EvidenceBundle
from kyverance.research.metrics import compute_deterministic_metrics


@dataclass
class MaterialChangeResult:
    score: Decimal
    band: str  # none | moderate | major
    decision: str  # metrics_only | full_rebuild
    factors: dict[str, Any]
    changed_sections: list[str]


def evaluate_material_change(
    bundle: EvidenceBundle,
    *,
    prior_evidence_hash: str | None = None,
) -> MaterialChangeResult:
    current_hash = bundle.evidence_hash()
    if prior_evidence_hash and prior_evidence_hash == current_hash:
        return MaterialChangeResult(
            score=Decimal("0"),
            band="none",
            decision="metrics_only",
            factors={"identical_evidence": True, "evidence_hash": current_hash},
            changed_sections=[],
        )

    metrics = compute_deterministic_metrics(bundle)
    pct_raw = metrics.get("pct_return")
    pct = abs(Decimal(str(pct_raw))) if pct_raw is not None else Decimal("0")
    score = min(pct / Decimal("0.05"), Decimal("1")) * Decimal("0.7")
    if "history" in bundle.gaps or "prior_close" in bundle.gaps:
        score = max(score, Decimal("0.35"))
    if prior_evidence_hash is None:
        score = Decimal("1")

    if score >= Decimal("0.55") or prior_evidence_hash is None:
        band, decision = "major", "full_rebuild"
        changed = list(SECTION_KEYS)
    elif score >= Decimal("0.2"):
        band, decision = "moderate", "full_rebuild"
        changed = list(SECTION_KEYS)
    else:
        band, decision = "none", "metrics_only"
        changed = []

    return MaterialChangeResult(
        score=score.quantize(Decimal("0.0001")),
        band=band,
        decision=decision,
        factors={
            "pct_return": str(pct),
            "prior_evidence_hash": prior_evidence_hash,
            "evidence_hash": current_hash,
            "gaps": list(bundle.gaps),
            "identical_evidence": False,
        },
        changed_sections=changed,
    )
