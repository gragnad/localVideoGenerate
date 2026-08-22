[CmdletBinding()]
param(
    [int]$SinceHours = 24,
    [int]$TailLines = 250
)

$ErrorActionPreference = "Continue"
$taskName = "NAL Studio Windows Render Agent"
$installDir = Join-Path $env:ProgramData "NALStudio\H3RenderAgent"
$logPath = Join-Path $installDir "render-agent.log"
$statePath = Join-Path $installDir "runtime-state.json"
$crashPath = Join-Path $installDir "crash.log"
$from = (Get-Date).AddHours(-[Math]::Abs($SinceHours))

Write-Host "=== System ==="
Get-Date
Get-CimInstance Win32_OperatingSystem |
    Select-Object LastBootUpTime
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object LocalPort -in 8766, 8189 |
    Select-Object LocalAddress, LocalPort, OwningProcess
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "render_agent.py" } |
    Select-Object ProcessId, ParentProcessId, CreationDate, ExecutablePath, CommandLine

Write-Host "=== Scheduled task ==="
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
$task |
    Select-Object TaskName, State,
        @{N="ExecutionTimeLimit";E={$_.Settings.ExecutionTimeLimit}},
        @{N="RestartCount";E={$_.Settings.RestartCount}},
        @{N="RestartInterval";E={$_.Settings.RestartInterval}} |
    Format-List
Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue |
    Format-List LastRunTime, LastTaskResult, NextRunTime, NumberOfMissedRuns

Write-Host "=== Lifecycle state ==="
if (Test-Path $statePath) {
    Get-Content $statePath -Raw
} else {
    Write-Host "Missing: $statePath"
}

Write-Host "=== Agent log tail ==="
if (Test-Path $logPath) {
    Get-Content $logPath -Tail $TailLines
} else {
    Write-Host "Missing: $logPath"
}

Write-Host "=== Fatal crash log tail ==="
if (Test-Path $crashPath) {
    Get-Content $crashPath -Tail $TailLines
} else {
    Write-Host "Missing: $crashPath"
}

Write-Host "=== Task Scheduler events ==="
Get-WinEvent -FilterHashtable @{
    LogName = "Microsoft-Windows-TaskScheduler/Operational"
    StartTime = $from
} -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match [regex]::Escape($taskName) } |
    Select-Object TimeCreated, Id, LevelDisplayName, Message |
    Format-List

Write-Host "=== Python/Application crash events ==="
Get-WinEvent -FilterHashtable @{
    LogName = "Application"
    StartTime = $from
} -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match "python.exe|render_agent.py" } |
    Select-Object TimeCreated, Id, ProviderName, LevelDisplayName, Message |
    Format-List
