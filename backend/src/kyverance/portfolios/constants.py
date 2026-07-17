"""Portfolio version / publish / fork constants (FORK-01)."""

from __future__ import annotations

VERSION_STATUS_DRAFT = "draft"
VERSION_STATUS_PUBLISHED = "published"
VERSION_STATUS_UNPUBLISHED = "unpublished"

VERSION_VISIBILITY_PRIVATE = "private"
VERSION_VISIBILITY_PUBLIC = "public"

LICENSE_VIEW_ONLY = "view_only"
LICENSE_PUBLIC_FORK_ALLOWED = "public_fork_allowed"

FORK_ENTITLEMENT_PUBLIC_VERSION = "public_version_fork"

CONSENT_TYPE_PORTFOLIO_VERSION_PUBLISH = "portfolio_version_publish"
CONSENT_TEXT_VERSION = "fork-01-v1"

DISCLOSURE_SIMULATED_PUBLISH = (
    "This published version is a simulated portfolio snapshot. "
    "It is not broker-verified, not investment advice, and does not grant "
    "access to the publisher's private Plaid data or future trades."
)

FORK_NOTICE = (
    "Forks are independent simulated portfolios. They do not sync with the source, "
    "mirror trades, expose Plaid data, or enable real trading or creator payment."
)

SOURCE_FORK_SEED_ALLOCATION = "FORK_SEED_ALLOCATION"
SOURCE_FORK_SEED_POSITION = "FORK_SEED_POSITION"

AUDIT_VERSION_CREATE = "portfolio.version.create"
AUDIT_VERSION_PUBLISH = "portfolio.version.publish"
AUDIT_PORTFOLIO_FORK = "portfolio.fork"
AUDIT_PORTFOLIO_PATCH = "portfolio.patch"

ALLOWED_PUBLISH_VISIBILITIES = frozenset({VERSION_VISIBILITY_PRIVATE, VERSION_VISIBILITY_PUBLIC})
ALLOWED_PUBLISH_LICENSES = frozenset({LICENSE_VIEW_ONLY, LICENSE_PUBLIC_FORK_ALLOWED})
ALLOWED_PROVENANCE = frozenset({"simulated"})
