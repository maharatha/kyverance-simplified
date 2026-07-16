# Contributing to Kyverance Simplified

Kyverance Simplified should be built with the discipline of a financial infrastructure company, not a prototype trading app. Contributions should preserve trust, explainability, auditability, and user control.

## Documentation first

- Product and delivery docs live in [`docs/`](docs/README.md).
- Architecture decisions use [`docs/adr/`](docs/adr/README.md).
- Each Cursor implementation slice has a task under `docs/tasks/`.

## Pull request checklist

- The change has a clear user or platform outcome.
- Relevant docs are updated.
- New behavior is testable.
- Risk and money calculations are deterministic, not LLM-generated.
- AI-generated user-facing content is grounded in structured inputs.
- Sensitive data handling is explicit.
- No live trading or financial action is added without explicit governance review.

## Branch naming

Prefer short descriptive names, for example:

```text
codex/plat-01-foundation
feature/home-shell
docs/adr-modular-monolith
```

## Commit style

Prefer clear, boring messages:

```text
plat: add repository foundation scaffold
docs: approve home UX
fix: health check redis timeout
```
