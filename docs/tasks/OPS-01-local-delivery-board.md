# OPS-01 — Local live delivery board

> Status: Implemented on `codex/ops-01-local-delivery-board`.

Build a local-development-only `/delivery-status` page for the Kyverance Simplified workspace. It must auto-refresh and visibly show: current branch, latest commits, dirty files, recent file activity, active Cursor CLI process presence, local preview health, and last check timestamp. Use a server-side local-only route; never expose process information, filesystem paths, Git metadata, or environment data in production builds/deployments. Include a clear unavailable state outside local development, tests for status serialization/rendering, and a link from the local developer header only. Do not change business product behavior, Azure, Entra, secrets, or CI deployment.
