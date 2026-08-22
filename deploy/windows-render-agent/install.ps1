[CmdletBinding()]
param(
    [string]$TailscaleAddress = "100.78.202.37",
    [string]$LanAddress = "172.30.1.71",
    [string]$LinuxTailscaleAddress = "100.124.246.93",
    [int]$Port = 8766,
    [string]$BearerToken = ""
)

$ErrorActionPreference = "Stop"
$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this installer from an elevated PowerShell window."
}

$python = Get-Command python.exe -ErrorAction Stop
$sourceAgent = Join-Path $PSScriptRoot "render_agent.py"
$sourceDiagnose = Join-Path $PSScriptRoot "diagnose.ps1"
if (-not (Test-Path $sourceAgent)) {
    throw "render_agent.py is missing beside install.ps1"
}
if (-not (Test-Path $sourceDiagnose)) {
    throw "diagnose.ps1 is missing beside install.ps1"
}

$taskName = "NAL Studio Windows Render Agent"
$legacyTaskName = "NAL Studio H3 Prompt Agent"
$firewallName = "NAL Studio Windows Render Agent"
$legacyFirewallName = "NAL Studio H3 Prompt Agent"
$installDir = Join-Path $env:ProgramData "NALStudio\H3RenderAgent"
$tokenPath = Join-Path $installDir "bearer-token.txt"
$agentPath = Join-Path $installDir "render_agent.py"
$diagnosePath = Join-Path $installDir "diagnose.ps1"
$logPath = Join-Path $installDir "render-agent.log"
$statePath = Join-Path $installDir "runtime-state.json"
$crashPath = Join-Path $installDir "crash.log"
$legacyTokenPath = Join-Path $env:ProgramData "NALStudio\H3PromptAgent\bearer-token.txt"

Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Stop-ScheduledTask -TaskName $legacyTaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $legacyTaskName -Confirm:$false -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 700
New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Copy-Item $sourceAgent $agentPath -Force
Copy-Item $sourceDiagnose $diagnosePath -Force

if ([string]::IsNullOrWhiteSpace($BearerToken)) {
    if (Test-Path $tokenPath) {
        $BearerToken = (Get-Content $tokenPath -Raw).Trim()
    } elseif (Test-Path $legacyTokenPath) {
        $BearerToken = (Get-Content $legacyTokenPath -Raw).Trim()
    } else {
        $bytes = New-Object byte[] 32
        $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        $BearerToken = -join ($bytes | ForEach-Object { $_.ToString("x2") })
    }
}
if ($BearerToken.Length -lt 32) {
    throw "BearerToken must contain at least 32 characters"
}
Set-Content -Path $tokenPath -Value $BearerToken -Encoding ASCII -NoNewline
& icacls.exe $tokenPath /inheritance:r /grant:r "SYSTEM:(F)" "${env:USERNAME}:(R,W)" | Out-Null

& powercfg.exe /hibernate on
if ($LASTEXITCODE -ne 0) {
    throw "Windows hibernation could not be enabled"
}
& powercfg.exe /change standby-timeout-ac 0
if ($LASTEXITCODE -ne 0) {
    throw "Could not disable the Windows AC standby timer"
}
& powercfg.exe /change hibernate-timeout-ac 0
if ($LASTEXITCODE -ne 0) {
    throw "Could not disable the Windows AC hibernation timer"
}

$ip = Get-NetIPAddress -IPAddress $LanAddress -AddressFamily IPv4 -ErrorAction Stop |
    Select-Object -First 1
$adapter = Get-NetAdapter -InterfaceIndex $ip.InterfaceIndex -ErrorAction Stop
try {
    Set-NetAdapterPowerManagement -Name $adapter.Name -WakeOnMagicPacket Enabled -ErrorAction Stop
} catch {
    Write-Warning "WakeOnMagicPacket setting was not exposed by this driver: $($_.Exception.Message)"
}
$wakeProperties = Get-NetAdapterAdvancedProperty -Name $adapter.Name -AllProperties -ErrorAction SilentlyContinue |
    Where-Object { $_.RegistryKeyword -match "WakeOnMagicPacket|EnablePME" }
foreach ($property in $wakeProperties) {
    try {
        Set-NetAdapterAdvancedProperty -Name $adapter.Name -RegistryKeyword $property.RegistryKeyword -RegistryValue 1 -NoRestart -ErrorAction Stop
    } catch {
        Write-Warning "Could not enable NIC property $($property.RegistryKeyword): $($_.Exception.Message)"
    }
}

Remove-NetFirewallRule -DisplayName $firewallName -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName $legacyFirewallName -ErrorAction SilentlyContinue
New-NetFirewallRule `
    -DisplayName $firewallName `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalAddress $TailscaleAddress `
    -LocalPort $Port `
    -RemoteAddress $LinuxTailscaleAddress `
    -Profile Any | Out-Null

& wevtutil.exe sl "Microsoft-Windows-TaskScheduler/Operational" /e:true /ms:33554432
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Could not enable the Task Scheduler Operational event log."
}

$arguments = @(
    ('"{0}"' -f $agentPath),
    "--bind", $TailscaleAddress,
    "--port", $Port,
    "--token-file", ('"{0}"' -f $tokenPath),
    "--log-file", ('"{0}"' -f $logPath),
    "--state-file", ('"{0}"' -f $statePath),
    "--crash-file", ('"{0}"' -f $crashPath)
) -join " "
$action = New-ScheduledTaskAction -Execute $python.Source -Argument $arguments
$trigger = New-ScheduledTaskTrigger `
    -AtLogOn `
    -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 10 `
    -RestartInterval (New-TimeSpan -Minutes 1)
$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Highest
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $taskPrincipal `
    -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

$healthUrl = "http://${TailscaleAddress}:${Port}/healthz"
$deadline = [DateTime]::UtcNow.AddSeconds(30)
$health = $null
while ([DateTime]::UtcNow -lt $deadline) {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5
        break
    } catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $health -or $health.status -ne "ok") {
    throw "Windows render agent did not become ready at ${healthUrl}"
}
if ([int]$health.agent_version -ne 4) {
    throw "Windows render agent version mismatch: expected v4, received v$($health.agent_version)"
}

Write-Host "Windows render agent: $($health.status) / v$($health.agent_version)"
Write-Host "Power state: $($health.power_state)"
Write-Host "AC automatic standby/hibernate timers: disabled (Linux managed)"
if ($null -ne $health.gpu_power_w) {
    Write-Host "GPU power: $($health.gpu_power_w) W"
} else {
    Write-Warning "nvidia-smi GPU power measurement is unavailable."
}
Write-Host "NIC: $($adapter.Name) / MAC $($adapter.MacAddress)"
Write-Host "API: $healthUrl"
Write-Host "Agent log: $logPath"
Write-Host "Lifecycle state: $statePath"
Write-Host "Fatal crash dump: $crashPath"
Write-Host "Diagnostic collector: $diagnosePath"
Write-Host "Task Scheduler Operational log: enabled"
Write-Host "The existing token was reused when found; Linux configuration normally needs no change."
