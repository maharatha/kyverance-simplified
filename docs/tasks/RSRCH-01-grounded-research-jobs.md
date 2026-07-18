# RSRCH-01 — Grounded canonical research jobs

Rebuild the first bounded research scheduler/worker slice in Kyverance Simplified, preserving the original Kyverance contracts while integrating with MRKT-01 internal market data and AGENT-01 facts packets.

Read before coding:

- Simplified: `docs/01-product-foundation.md`, `docs/06-ai-agents-and-background-jobs.md`, `docs/08-master-delivery-roadmap.md`
- Original: `C:/SourceCode/kyverance/docs/research/RESEARCH_JOB_DESIGN.md`
- Original: `C:/SourceCode/kyverance/docs/research/AI_RESEARCH_ARCHITECTURE.md`
- Original: `C:/SourceCode/kyverance/docs/research/RESEARCH_DATA_MODEL.md`
- Original: `C:/SourceCode/kyverance/docs/research/RESEARCH_API_CONTRACT.md`
- Original ADRs 0005–0008 under `C:/SourceCode/kyverance/docs/adr/`
- Original implementation under `C:/SourceCode/kyverance/backend/src/kyverance/research/` and its research tests

Adapt the proven contracts to the simplified model. Do not wholesale-copy the original module.

## Outcome

The application can build, validate, persist, and serve one reusable canonical research package per internal security using deterministic grounded evidence. Generation runs asynchronously through durable jobs. AI remains disabled/default-off in this slice; no external model or data-provider call is required.

## Required implementation

- Canonical research security mapping to MRKT-01 instruments/listings.
- Immutable research versions, latest-published pointer, sections, evidence references/checksums, freshness, validation status, publication state, prior-version lineage, and material-change record.
- Deterministic metrics/section assembly for a restrained initial set: company/market snapshot, valuation-data availability, trend/technical context, risks, evidence gaps, and executive summary. Missing evidence must produce `insufficient_data`, never invented facts.
- Every section exposes status, confidence, reasoning summary, evidence coverage, evidence references, data-as-of time, source/provider, and limitations.
- Durable research jobs with idempotent enqueue, safe claim, bounded retries/backoff/dead-letter, correlation IDs, health/last-success, and `--once` worker entrypoint. Include initial job types for full rebuild, validate, publish, freshness check, and cache repair contract.
- Exchange-aware scheduler that enqueues based on the latest completed market session and research freshness; scheduler must not generate research inline.
- Atomic Postgres-first publication: only validated versions may become latest. Cache/object-store ports may use local/in-memory adapters but cannot be sources of truth. Failed publication never exposes an unpublished version.
- Internal/customer API to read latest published research with truthful stale/revalidating/unavailable states. A cold miss may enqueue a bounded rebuild and return an explicit accepted/revalidating response; request handlers must not perform deep generation.
- Integrate an authorized canonical research reference into AGENT-01 facts packets without allowing research jobs or agents to mutate portfolios, wallets, orders, holdings, executions, or ledger entries.
- Feature flags and kill switches. Default local/CI mode is deterministic and AI-off.

## Safety and product invariants

- No external model calls, Azure OpenAI, live provider calls, personalized investment recommendations, certainty claims, trade execution, broker/copy/mirror behavior, cloud deployment, or secret changes.
- Deterministic calculations own numeric metrics. Research output cannot invent market values, filings, news, citations, or company claims.
- Canonical research is reusable and versioned; private portfolio/Plaid data must not enter it.
- Agent facts may reference only published canonical research plus owner-authorized portfolio facts.

## Tests and verification

- Migration upgrade to head locally.
- Tests for evidence grounding/gaps, deterministic metrics, immutable version lineage, validation failures, atomic publication/latest-pointer safety, scheduler and queue idempotency, retries/dead-letter, freshness/revalidation, cold-miss behavior, cache mismatch fallback, owner/private-data exclusion, and financial-table non-mutation.
- Bounded deterministic rebuild → validate → publish → read worker smoke.
- Full backend and frontend regression suites plus frontend production build.
- Local readiness and research API smoke.

## Delivery

Work only on RSRCH-01 and preserve unrelated untracked files. Commit and push to the current branch. Final report must list changed files, migration, job entrypoints, tests/build/smokes, grounding and safety evidence, commit hash, push result, and genuine limitations. Do not alter Azure, Entra, Plaid, DNS, CI/CD, production data, secrets, or original Kyverance.
