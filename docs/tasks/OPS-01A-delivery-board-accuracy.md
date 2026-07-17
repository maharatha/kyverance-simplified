# OPS-01A — Delivery board accuracy correction

Correct the reviewed defects in the local-only delivery board.

1. The preview health probe must report the actual local preview at `http://127.0.0.1:3001/` as healthy when this workspace is running on the documented development port. Prefer a narrowly scoped environment override with `http://127.0.0.1:3001/` as the local default.
2. Cursor CLI activity must not count PowerShell launcher/wrapper processes as independent agents. Count only live Cursor Agent Node processes (the CLI process and worker child processes), and label the result honestly as process presence—not proof that the agent is actively editing.
3. Add or update tests for both corrections.
4. Run the focused tests and the full frontend test suite. Inspect `/delivery-status` and `/api/delivery-status` locally.
5. Commit and push only these OPS-01A changes. Do not change Azure, Entra, CI, secrets, product behavior, or production infrastructure.

Final report must include changed files, test results, local HTTP results, commit hash, and push result.
