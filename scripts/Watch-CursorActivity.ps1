param(
    [int]$RefreshSeconds = 3
)

$ErrorActionPreference = 'SilentlyContinue'
$workspace = 'C:\SourceCode\kyverance-simplified'

while ($true) {
    Clear-Host
    Write-Host 'KYVERANCE SIMPLIFIED - CURSOR DELIVERY MONITOR' -ForegroundColor Cyan
    Write-Host ('Updated: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) -ForegroundColor DarkGray
    Write-Host ''

    $cursorProcesses = Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -match 'cursor-agent|cursor-agent\\cursor-agent.cmd'
    }
    if ($cursorProcesses) {
        Write-Host 'Cursor processes: ACTIVE' -ForegroundColor Green
        $cursorProcesses | Select-Object ProcessId, ParentProcessId, Name, CommandLine | Format-Table -Wrap
    } else {
        Write-Host 'Cursor processes: NONE' -ForegroundColor Yellow
    }

    Set-Location $workspace
    Write-Host ('Git branch: {0}' -f (git branch --show-current)) -ForegroundColor White
    Write-Host ('Latest commit: {0}' -f (git log -1 '--pretty=format:%h %s')) -ForegroundColor White
    $changes = git status --short
    if ($changes) {
        Write-Host 'Working changes:' -ForegroundColor Yellow
        $changes
    } else {
        Write-Host 'Working changes: clean' -ForegroundColor Green
    }

    $latestFiles = Get-ChildItem -Recurse -File frontend, backend, docs -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 8 LastWriteTime, FullName
    Write-Host 'Recent file activity:' -ForegroundColor White
    $latestFiles | Format-Table -AutoSize

    try {
        $response = Invoke-WebRequest 'http://127.0.0.1:3001' -UseBasicParsing -TimeoutSec 3
        Write-Host ('Preview: HTTP {0}' -f $response.StatusCode) -ForegroundColor Green
    } catch {
        Write-Host 'Preview: unavailable' -ForegroundColor Red
    }

    Write-Host ''
    Write-Host ('Refreshing every {0} seconds. Close this window to stop monitoring.' -f $RefreshSeconds) -ForegroundColor DarkGray
    Start-Sleep -Seconds $RefreshSeconds
}
