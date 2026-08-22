$ErrorActionPreference = "Stop"
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this uninstaller from an elevated PowerShell window."
}

Unregister-ScheduledTask -TaskName "NAL Studio H3 Prompt Agent" -Confirm:$false -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "NAL Studio H3 Prompt Agent" -ErrorAction SilentlyContinue
$installDir = Join-Path $env:ProgramData "NALStudio\H3PromptAgent"
if (Test-Path $installDir) {
    Remove-Item $installDir -Recurse -Force
}
Write-Host "H3 Prompt Agent task, firewall rule, cached results, and token were removed."
Write-Host "Windows hibernation and NIC Wake-on-LAN settings were left unchanged."
