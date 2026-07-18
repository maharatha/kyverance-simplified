"""Research report validation — schema, grounding, prohibited language."""

from __future__ import annotations

from typing import Any

from kyverance.research.constants import (
    PROHIBITED_PHRASES,
    SECTION_KEYS,
    SECTION_STATUSES,
    UNSUPPORTED_CLAIM_PHRASES,
)


class ResearchValidationError(ValueError):
    pass


def validate_research_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("ticker", "exchange", "market_date", "evidence_hash", "sections", "executive_summary"):
        if field not in report or report[field] in (None, ""):
            errors.append(f"missing_field:{field}")

    sections = report.get("sections") or {}
    for key in SECTION_KEYS:
        if key not in sections:
            errors.append(f"missing_section:{key}")
            continue
        section = sections[key]
        if not isinstance(section, dict):
            errors.append(f"invalid_section:{key}")
            continue
        status = section.get("status")
        if status not in SECTION_STATUSES:
            errors.append(f"missing_or_invalid_status:{key}")
        for required in (
            "summary",
            "confidence",
            "sources",
            "reasoning_summary",
            "evidence_coverage",
            "evidence_references",
            "data_as_of",
            "source_provider",
            "limitations",
        ):
            if required not in section:
                errors.append(f"missing_{required}:{key}")
        coverage = section.get("evidence_coverage")
        if isinstance(coverage, dict):
            for ck in ("required", "available", "missing"):
                if ck not in coverage or not isinstance(coverage[ck], list):
                    errors.append(f"invalid_evidence_coverage:{key}:{ck}")
        else:
            errors.append(f"missing_evidence_coverage:{key}")
        if status == "grounded" and not (section.get("sources") or []):
            errors.append(f"grounded_without_sources:{key}")

    metrics = report.get("deterministic_metrics") or {}
    if "close" not in metrics:
        errors.append("missing_metric:close")

    blob = str(report.get("executive_summary", "")).lower()
    for section in sections.values():
        if isinstance(section, dict):
            blob += " " + str(section.get("summary", "")).lower()
    for phrase in PROHIBITED_PHRASES:
        if phrase in blob:
            errors.append(f"prohibited_language:{phrase}")
    for phrase in UNSUPPORTED_CLAIM_PHRASES:
        if phrase in blob:
            errors.append(f"unsupported_claim:{phrase}")

    conf = report.get("confidence_score")
    try:
        if conf is not None and not (0 <= float(conf) <= 1):
            errors.append("confidence_out_of_range")
    except (TypeError, ValueError):
        errors.append("confidence_invalid")

    if report.get("ai_enabled") is True:
        errors.append("ai_must_remain_disabled")

    return errors


def assert_valid(report: dict[str, Any]) -> None:
    errors = validate_research_report(report)
    if errors:
        raise ResearchValidationError(",".join(errors))
