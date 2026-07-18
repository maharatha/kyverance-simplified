"""Research job types, statuses, and restrained section contracts (RSRCH-01)."""

from __future__ import annotations

MODEL_VERSION = "deterministic-research-v1"
PROMPT_VERSION = "none-ai-off"
METHODOLOGY_VERSION = "grounded-internal-market-v1"

# Restrained initial section set — not the full original 32-section committee.
SECTION_KEYS = (
    "executive_summary",
    "company_market_snapshot",
    "valuation_data_availability",
    "trend_technical_context",
    "risks",
    "evidence_gaps",
)

SECTION_STATUSES = (
    "grounded",
    "insufficient_data",
    "stale",
    "unavailable",
    "mock",
)

SECTION_EVIDENCE_REQUIREMENTS: dict[str, list[str]] = {
    "executive_summary": ["eod_bar"],
    "company_market_snapshot": ["eod_bar", "instrument"],
    "valuation_data_availability": ["eod_bar"],
    "trend_technical_context": ["eod_bar", "history"],
    "risks": ["eod_bar"],
    "evidence_gaps": [],
}

PROHIBITED_PHRASES = (
    "buy now",
    "sell now",
    "guaranteed",
    "risk-free",
    "certain winner",
    "you should buy",
    "you should sell",
)

UNSUPPORTED_CLAIM_PHRASES = (
    "strong ecosystem",
    "consumer-device franchise",
    "mega-cap",
    "strong free cash flow",
)

JOB_FULL_REBUILD = "RESEARCH_FULL_REBUILD"
JOB_VALIDATE = "RESEARCH_VALIDATE"
JOB_PUBLISH = "RESEARCH_PUBLISH"
JOB_FRESHNESS_CHECK = "DATA_FRESHNESS_CHECK"
JOB_CACHE_REPAIR = "CACHE_REPAIR"
JOB_COLD_ON_DEMAND = "COLD_STOCK_ON_DEMAND"

ALL_JOB_TYPES = {
    JOB_FULL_REBUILD,
    JOB_VALIDATE,
    JOB_PUBLISH,
    JOB_FRESHNESS_CHECK,
    JOB_CACHE_REPAIR,
    JOB_COLD_ON_DEMAND,
}

JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_DONE = "done"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_DEAD = "dead"

PUB_STATUS_VALIDATED = "validated"
PUB_STATUS_ARTIFACT_PENDING = "artifact_pending"
PUB_STATUS_ARTIFACT_READY = "artifact_ready"
PUB_STATUS_ARTIFACT_FAILED = "artifact_failed"
PUB_STATUS_PUBLISHED = "published"
PUB_STATUS_PUBLISH_FAILED = "publish_failed"

FRESHNESS_CURRENT = "CURRENT"
FRESHNESS_STALE = "STALE"
FRESHNESS_REVALIDATING = "REVALIDATING"
FRESHNESS_SUPERSEDED = "SUPERSEDED"
FRESHNESS_FAILED_REFRESH = "FAILED_REFRESH"

TIER_HOT = "hot"
TIER_ACTIVE = "active"
TIER_COLD = "cold"

BACKOFF_BASE_SECONDS = 30
DEFAULT_MAX_ATTEMPTS = 5
