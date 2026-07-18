"""Deterministic grounded research report assembly (restrained sections)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from kyverance.research.constants import (
    METHODOLOGY_VERSION,
    MODEL_VERSION,
    PROMPT_VERSION,
    SECTION_EVIDENCE_REQUIREMENTS,
    SECTION_KEYS,
)
from kyverance.research.evidence import EvidenceBundle
from kyverance.research.material_change import MaterialChangeResult
from kyverance.research.metrics import compute_deterministic_metrics

STATUS_GROUNDED = "grounded"
STATUS_INSUFFICIENT = "insufficient_data"
STATUS_STALE = "stale"
STATUS_UNAVAILABLE = "unavailable"


def _coverage_for(section_key: str, available: set[str]) -> dict[str, list[str]]:
    required = list(SECTION_EVIDENCE_REQUIREMENTS.get(section_key, []))
    have = [r for r in required if r in available]
    missing = [r for r in required if r not in available]
    return {"required": required, "available": have, "missing": missing}


def _section(
    text: str,
    *,
    section_key: str,
    bundle: EvidenceBundle,
    available: set[str],
    confidence: float,
    sources: list[str],
    reasoning: str,
    data_as_of: str | None,
    limitations: str,
    status_override: str | None = None,
) -> dict[str, Any]:
    coverage = _coverage_for(section_key, available)
    status = status_override
    if status is None:
        if coverage["required"] and not coverage["available"]:
            status = STATUS_INSUFFICIENT
        elif "stale_price" in bundle.gaps and section_key != "evidence_gaps":
            status = STATUS_STALE
        else:
            status = STATUS_GROUNDED if sources else STATUS_INSUFFICIENT

    if status in {STATUS_INSUFFICIENT, STATUS_UNAVAILABLE}:
        if not text.startswith(("insufficient_data", "unavailable")):
            text = (
                f"{status}: required evidence missing for "
                f"{section_key.replace('_', ' ')} "
                f"({', '.join(coverage['missing']) or 'n/a'})."
            )
        confidence = min(confidence, 0.35)
        sources = list(sources)

    if status == STATUS_GROUNDED and not sources:
        status = STATUS_INSUFFICIENT
        text = f"insufficient_data: grounded claim requires cited sources for {section_key}."
        confidence = min(confidence, 0.35)

    return {
        "status": status,
        "summary": text,
        "confidence": confidence,
        "reasoning_summary": reasoning,
        "evidence_coverage": coverage,
        "evidence_references": [
            {"kind": "source", "ref": s, "label": s} for s in sources
        ],
        "sources": sources,
        "data_as_of": data_as_of,
        "source_provider": bundle.provider_name,
        "limitations": limitations,
    }


def _src(bundle: EvidenceBundle, *extra: str) -> list[str]:
    out = [bundle.provider_name, f"data_mode:{bundle.data_mode}"]
    out.extend(extra)
    return out


def generate_canonical_report(
    bundle: EvidenceBundle,
    assessment: MaterialChangeResult,
) -> dict[str, Any]:
    metrics = compute_deterministic_metrics(bundle)
    available = bundle.available_evidence()
    data_as_of = (
        bundle.source_data_timestamp.isoformat()
        if bundle.source_data_timestamp
        else bundle.market_date.isoformat()
    )
    limitations_base = (
        "Deterministic grounded research from internal market warehouse only. "
        "No filings, news, fundamentals, or AI synthesis in this slice. "
        "Not investment advice."
    )

    sections: dict[str, Any] = {}

    # Company / market snapshot
    if bundle.close is not None:
        snap = (
            f"{bundle.ticker} ({bundle.exchange}) closed at {metrics['close']} "
            f"on {bundle.market_date.isoformat()} with volume {metrics['volume']}. "
            f"Instrument: {bundle.instrument_name or bundle.ticker}."
        )
        sections["company_market_snapshot"] = _section(
            snap,
            section_key="company_market_snapshot",
            bundle=bundle,
            available=available,
            confidence=0.8,
            sources=_src(bundle, "eod_bar", "instrument"),
            reasoning="Snapshot assembled from published internal EOD bar and instrument record.",
            data_as_of=data_as_of,
            limitations=limitations_base,
        )
    else:
        sections["company_market_snapshot"] = _section(
            "insufficient_data: no EOD close available.",
            section_key="company_market_snapshot",
            bundle=bundle,
            available=available,
            confidence=0.2,
            sources=[],
            reasoning="Missing published close prevents market snapshot.",
            data_as_of=data_as_of,
            limitations=limitations_base,
            status_override=STATUS_INSUFFICIENT,
        )

    # Valuation data availability — never invent PE/EPS
    val = metrics.get("valuation_ratios") or {}
    val_text = (
        "insufficient_data: valuation inputs from internal warehouse — "
        f"pe_ttm={val.get('pe_ttm')}, eps_ttm={val.get('eps_ttm')}, "
        f"gross_margin={val.get('gross_margin')}. "
        "Fundamentals are not present in MRKT-01 warehouse; ratios are not invented."
    )
    sections["valuation_data_availability"] = _section(
        val_text,
        section_key="valuation_data_availability",
        bundle=bundle,
        available=available,
        confidence=0.55,
        sources=_src(bundle, "eod_bar") if bundle.close is not None else [],
        reasoning="Reports availability of valuation fields without inventing ratios.",
        data_as_of=data_as_of,
        limitations=limitations_base + " No PE/EPS/fundamentals in evidence set.",
        status_override=STATUS_INSUFFICIENT,
    )

    # Trend / technical context
    trend = metrics.get("trend") or {}
    if trend.get("available"):
        tech_text = (
            f"Five-bar window return {trend.get('window_return')} "
            f"({trend.get('direction')}) from internal daily history "
            f"({trend.get('bars')} bars). Session return {metrics.get('pct_return')}."
        )
        sections["trend_technical_context"] = _section(
            tech_text,
            section_key="trend_technical_context",
            bundle=bundle,
            available=available,
            confidence=0.7,
            sources=_src(bundle, "eod_bar", "history"),
            reasoning="Trend derived only from published daily closes.",
            data_as_of=data_as_of,
            limitations=limitations_base,
        )
    else:
        sections["trend_technical_context"] = _section(
            f"insufficient_data: {trend.get('reason', 'history unavailable')}.",
            section_key="trend_technical_context",
            bundle=bundle,
            available=available,
            confidence=0.3,
            sources=_src(bundle, "eod_bar") if bundle.close is not None else [],
            reasoning="Insufficient history bars for trend calculation.",
            data_as_of=data_as_of,
            limitations=limitations_base,
            status_override=STATUS_INSUFFICIENT,
        )

    # Risks — grounded only on observed price move / gaps
    risk_bits: list[str] = []
    pct = metrics.get("pct_return")
    if pct is not None:
        risk_bits.append(f"Observed session return {pct} from internal EOD bars.")
    if bundle.gaps:
        risk_bits.append(f"Evidence gaps: {', '.join(bundle.gaps)}.")
    risk_bits.append("No filings, news, or fundamentals available to assess company-specific risks.")
    sections["risks"] = _section(
        " ".join(risk_bits),
        section_key="risks",
        bundle=bundle,
        available=available,
        confidence=0.55 if bundle.close is not None else 0.25,
        sources=_src(bundle, "eod_bar") if bundle.close is not None else [],
        reasoning="Risk notes limited to observed market evidence and explicit gaps.",
        data_as_of=data_as_of,
        limitations=limitations_base,
        status_override=STATUS_GROUNDED if bundle.close is not None else STATUS_INSUFFICIENT,
    )

    # Evidence gaps
    gap_list = list(bundle.gaps) + ["filings", "news", "fundamentals", "ai_synthesis"]
    sections["evidence_gaps"] = _section(
        "Missing or unavailable evidence: " + ", ".join(sorted(set(gap_list))) + ".",
        section_key="evidence_gaps",
        bundle=bundle,
        available=available,
        confidence=0.9,
        sources=_src(bundle, "gap_inventory"),
        reasoning="Explicit inventory of missing evidence; never invents substitutes.",
        data_as_of=data_as_of,
        limitations=limitations_base,
        status_override=STATUS_GROUNDED,
    )

    # Executive summary
    grounded_n = sum(
        1 for k, s in sections.items() if k != "executive_summary" and s.get("status") == STATUS_GROUNDED
    )
    if bundle.close is not None:
        exec_text = (
            f"Canonical research for {bundle.ticker} as of {bundle.market_date.isoformat()}: "
            f"close {metrics['close']}, session return {metrics.get('pct_return')}. "
            f"{grounded_n} of {len(SECTION_KEYS) - 1} body sections grounded. "
            "Valuation fundamentals unavailable; AI synthesis disabled."
        )
        sections["executive_summary"] = _section(
            exec_text,
            section_key="executive_summary",
            bundle=bundle,
            available=available,
            confidence=0.65,
            sources=_src(bundle, "eod_bar"),
            reasoning="Executive summary restates deterministic metrics and grounding counts.",
            data_as_of=data_as_of,
            limitations=limitations_base,
        )
    else:
        sections["executive_summary"] = _section(
            "insufficient_data: no published close available for executive summary.",
            section_key="executive_summary",
            bundle=bundle,
            available=available,
            confidence=0.2,
            sources=[],
            reasoning="Cannot summarize without EOD evidence.",
            data_as_of=data_as_of,
            limitations=limitations_base,
            status_override=STATUS_INSUFFICIENT,
        )

    confidences = [float(s.get("confidence") or 0) for s in sections.values()]
    confidence_score = sum(confidences) / len(confidences) if confidences else 0.0

    evidence_refs = [
        {
            "kind": "instrument",
            "ref": str(bundle.instrument_id) if bundle.instrument_id else "",
            "label": bundle.instrument_name or bundle.ticker,
        },
        {
            "kind": "listing",
            "ref": str(bundle.listing_id) if bundle.listing_id else "",
            "label": f"{bundle.ticker}:{bundle.exchange}",
        },
        {
            "kind": "evidence_hash",
            "ref": bundle.evidence_hash(),
            "label": "sha256",
        },
    ]

    return {
        "ticker": bundle.ticker,
        "exchange": bundle.exchange,
        "market_date": bundle.market_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": sections["executive_summary"]["summary"],
        "confidence_score": float(Decimal(str(confidence_score)).quantize(Decimal("0.0001"))),
        "change_summary": (
            f"decision={assessment.decision} band={assessment.band} "
            f"score={assessment.score}"
        ),
        "changed_sections": list(assessment.changed_sections),
        "sections": sections,
        "deterministic_metrics": metrics,
        "evidence_hash": bundle.evidence_hash(),
        "evidence_refs": evidence_refs,
        "model_version": MODEL_VERSION,
        "prompt_version": PROMPT_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "data_mode": bundle.data_mode,
        "dataMode": bundle.data_mode,
        "provider_name": bundle.provider_name,
        "ai_enabled": False,
        "source_data_timestamp": data_as_of,
        "material_change": {
            "score": str(assessment.score),
            "band": assessment.band,
            "decision": assessment.decision,
            "factors": assessment.factors,
        },
    }
