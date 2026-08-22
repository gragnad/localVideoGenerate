[CmdletBinding()]
param(
    [string]$TailscaleAddress = "100.78.202.37",
    [string]$LanAddress = "172.30.1.71",
    [string]$LinuxTailscaleAddress = "100.124.246.93",
    [int]$Port = 8765,
    [string]$BearerToken = ""
)

$ErrorActionPreference = "Stop"
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this installer from an elevated PowerShell window."
}

$python = Get-Command python.exe -ErrorAction Stop
$codex = Get-Command codex -All -ErrorAction Stop |
    Where-Object { $_.Source -match "\.(exe|cmd|bat)$" } |
    Select-Object -First 1
if (-not $codex) {
    throw "Codex CLI executable (.exe or .cmd) was not found in PATH"
}
$sourceAgent = Join-Path $PSScriptRoot "prompt_revision_agent.py"
if (-not (Test-Path $sourceAgent)) {
    throw "prompt_revision_agent.py is missing beside install.ps1"
}

$installDir = Join-Path $env:ProgramData "NALStudio\H3PromptAgent"
$stateDir = Join-Path $installDir "state"
$tokenPath = Join-Path $installDir "bearer-token.txt"
$agentPath = Join-Path $installDir "prompt_revision_agent.py"
Stop-ScheduledTask -TaskName "NAL Studio H3 Prompt Agent" -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
Copy-Item $sourceAgent $agentPath -Force

if ([string]::IsNullOrWhiteSpace($BearerToken)) {
    if (Test-Path $tokenPath) {
        $BearerToken = (Get-Content $tokenPath -Raw).Trim()
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

$ip = Get-NetIPAddress -IPAddress $LanAddress -AddressFamily IPv4 -ErrorAction Stop | Select-Object -First 1
$adapter = Get-NetAdapter -InterfaceIndex $ip.InterfaceIndex -ErrorAction Stop
try {
    Set-NetAdapterPowerManagement -Name $adapter.Name -WakeOnMagicPacket Enabled -ErrorAction Stop
} catch {
    Write-Warning "WakeOnMagicPacket power setting was not exposed by this driver: $($_.Exception.Message)"
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

$firewallName = "NAL Studio H3 Prompt Agent"
Remove-NetFirewallRule -DisplayName $firewallName -ErrorAction SilentlyContinue
New-NetFirewallRule `
    -DisplayName $firewallName `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalAddress $TailscaleAddress `
    -LocalPort $Port `
    -RemoteAddress $LinuxTailscaleAddress `
    -Profile Any | Out-Null

$arguments = @(
    ('"{0}"' -f $agentPath),
    "--bind", $TailscaleAddress,
    "--port", $Port,
    "--token-file", ('"{0}"' -f $tokenPath),
    "--state-dir", ('"{0}"' -f $stateDir),
    "--codex-command", ('"{0}"' -f $codex.Source)
) -join " "
$action = New-ScheduledTaskAction -Execute $python.Source -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Days 3) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)
$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Highest
Register-ScheduledTask `
    -TaskName "NAL Studio H3 Prompt Agent" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $taskPrincipal `
    -Force | Out-Null
Start-ScheduledTask -TaskName "NAL Studio H3 Prompt Agent"

Start-Sleep -Seconds 2
$health = Invoke-RestMethod -Uri "http://${TailscaleAddress}:${Port}/healthz" -TimeoutSec 5
Write-Host "Agent status: $($health.status)"
Write-Host "NIC: $($adapter.Name) / MAC $($adapter.MacAddress)"
Write-Host "Linux runtime token (store as H3_PROMPT_REVISION_REMOTE_TOKEN):"
Write-Host $BearerToken
Write-Host "A BIOS/UEFI Wake-on-LAN setting may still need to be enabled manually."
