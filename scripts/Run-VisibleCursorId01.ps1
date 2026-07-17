$ErrorActionPreference = 'Stop'

$cursorCommand = Join-Path $env:LOCALAPPDATA 'cursor-agent\cursor-agent.cmd'
$workspace = 'C:\SourceCode\kyverance-simplified'
$taskPrompt = @'
Implement only ID-01: Entra authentication, RBAC, and protected application shell. The authoritative task is C:\SourceCode\kyverance-simplified\docs\tasks\ID-01-entra-auth-rbac.md. Read it and all listed documents before acting. Create the required focused branch, implement the approved scope, run all required verification, commit/push only after all local gates pass, and leave a detailed final report. Do not alter Azure, Entra, DNS, GitHub secrets/settings, Key Vault, original Kyverance, Plaid, payments, deployment, or any non-simplified database.
'@

Write-Host 'Starting Cursor ID-01 Entra/RBAC session...' -ForegroundColor Cyan
& $cursorCommand -p --trust --auto-review --stream-partial-output --output-format stream-json --workspace $workspace $taskPrompt
Write-Host 'Cursor session ended. Codex will review the final report and verification.' -ForegroundColor Yellow
