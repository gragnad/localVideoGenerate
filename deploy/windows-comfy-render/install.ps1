[CmdletBinding()]
param(
    [string]$ComfyRoot = "",
    [string]$BaseDirectory = "",
    [string]$UserDirectory = "",
    [string]$ExtraModelsConfig = "",
    [string]$PythonExecutable = "",
    [string]$TailscaleAddress = "100.78.202.37",
    [string]$LinuxTailscaleAddress = "100.124.246.93",
    [int]$Port = 8189
)

$ErrorActionPreference = "Stop"
$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this installer from an elevated PowerShell window."
}

function Resolve-ComfyRoot {
    param([string]$RequestedRoot)
    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($RequestedRoot)) {
        $candidates += $RequestedRoot
    }
    $candidates += @(
        (Join-Path $env:LOCALAPPDATA "Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"),
        (Join-Path $env:USERPROFILE "ComfyUI"),
        (Join-Path $env:USERPROFILE "ai-workspace\apps\ComfyUI"),
        (Join-Path $env:USERPROFILE "ComfyUI_windows_portable\ComfyUI"),
        "C:\ComfyUI",
        "C:\ComfyUI_windows_portable\ComfyUI"
    )
    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        $resolved = Resolve-Path $candidate -ErrorAction SilentlyContinue
        if ($resolved -and (Test-Path (Join-Path $resolved.Path "main.py"))) {
            return $resolved.Path
        }
    }
    throw "ComfyUI main.py was not found. Pass -ComfyRoot with the ComfyUI directory."
}

$resolvedComfyRoot = Resolve-ComfyRoot $ComfyRoot
$mainPath = Join-Path $resolvedComfyRoot "main.py"
$desktopBase = Join-Path $env:USERPROFILE "Documents\ComfyUI"
$desktopExtraModels = Join-Path $env:APPDATA "ComfyUI\extra_models_config.yaml"
if ([string]::IsNullOrWhiteSpace($BaseDirectory) -and (Test-Path $desktopBase)) {
    $BaseDirectory = $desktopBase
}
if ([string]::IsNullOrWhiteSpace($UserDirectory) -and -not [string]::IsNullOrWhiteSpace($BaseDirectory)) {
    $UserDirectory = Join-Path $BaseDirectory "user-render"
}
if ([string]::IsNullOrWhiteSpace($ExtraModelsConfig) -and (Test-Path $desktopExtraModels)) {
    $ExtraModelsConfig = $desktopExtraModels
}

if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    $portablePythonCandidates = @(
        (Join-Path (Split-Path $resolvedComfyRoot -Parent) "python_embeded\python.exe"),
        (Join-Path $resolvedComfyRoot "python_embeded\python.exe")
    )
    $portablePython = $portablePythonCandidates |
        Where-Object { Test-Path $_ } |
        Select-Object -First 1
    if ($portablePython) {
        $PythonExecutable = $portablePython
    } else {
        $PythonExecutable = (Get-Command python.exe -ErrorAction Stop).Source
    }
}
$resolvedPython = (Resolve-Path $PythonExecutable -ErrorAction Stop).Path

$taskName = "NAL Studio Windows Comfy Render"
$firewallName = "NAL Studio Windows Comfy Render"
Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

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
    ('"{0}"' -f $mainPath),
    "--listen", $TailscaleAddress,
    "--port", $Port,
    "--disable-auto-launch"
)
if (-not [string]::IsNullOrWhiteSpace($BaseDirectory)) {
    $resolvedBaseDirectory = (Resolve-Path $BaseDirectory -ErrorAction Stop).Path
    $arguments += @("--base-directory", ('"{0}"' -f $resolvedBaseDirectory))
}
if (-not [string]::IsNullOrWhiteSpace($UserDirectory)) {
    New-Item -ItemType Directory -Path $UserDirectory -Force | Out-Null
    $resolvedUserDirectory = (Resolve-Path $UserDirectory -ErrorAction Stop).Path
    $arguments += @("--user-directory", ('"{0}"' -f $resolvedUserDirectory))
}
if (-not [string]::IsNullOrWhiteSpace($ExtraModelsConfig)) {
    $resolvedExtraModelsConfig = (Resolve-Path $ExtraModelsConfig -ErrorAction Stop).Path
    $arguments += @(
        "--extra-model-paths-config",
        ('"{0}"' -f $resolvedExtraModelsConfig)
    )
}
$arguments = $arguments -join " "
$action = New-ScheduledTaskAction `
    -Execute $resolvedPython `
    -Argument $arguments `
    -WorkingDirectory $resolvedComfyRoot
$trigger = New-ScheduledTaskTrigger `
    -AtLogOn `
    -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
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
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $taskPrincipal `
    -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

$healthUrl = "http://${TailscaleAddress}:${Port}/system_stats"
$deadline = [DateTime]::UtcNow.AddMinutes(3)
$health = $null
while ([DateTime]::UtcNow -lt $deadline) {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5
        break
    } catch {
        Start-Sleep -Seconds 3
    }
}
if (-not $health) {
    throw "ComfyUI did not become ready at ${healthUrl}. Check the scheduled task history and ComfyUI console logs."
}

$minimumVersion = [Version]"0.30.0"
$actualVersion = [Version]$health.system.comfyui_version
if ($actualVersion -lt $minimumVersion) {
    throw "ComfyUI $actualVersion is too old for MiniMax H3. Version 0.30.0 or later is required."
}

$objectInfo = Invoke-RestMethod `
    -Uri "http://${TailscaleAddress}:${Port}/object_info" `
    -TimeoutSec 60
$requiredNodes = @("MiniMaxH3ReferenceToVideo", "ModelAttentionBackend")
$missingNodes = @($requiredNodes | Where-Object {
    $objectInfo.PSObject.Properties.Name -notcontains $_
})
if ($missingNodes.Count -gt 0) {
    throw "Required MiniMax H3 nodes are missing: $($missingNodes -join ', ')"
}

$requiredModels = @(
    @("UNETLoader", "unet_name", "minimax_h3_ref2va_pruned_int8_convrot.safetensors"),
    @("CLIPLoader", "clip_name", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
    @("VAELoader", "vae_name", "minimax_h3_video_vae_fp16.safetensors"),
    @("VAELoader", "vae_name", "minimax_h3_audio_vae_fp32.safetensors")
)
$missingModels = @()
foreach ($item in $requiredModels) {
    $node = $objectInfo.PSObject.Properties[$item[0]].Value
    $choices = $node.input.required.PSObject.Properties[$item[1]].Value[0]
    if ($choices -notcontains $item[2]) { $missingModels += $item[2] }
}
if ($missingModels.Count -gt 0) {
    throw "Required MiniMax H3 models are missing: $($missingModels -join ', ')"
}

Write-Host "Windows ComfyUI render API is ready: $healthUrl"
Write-Host "ComfyUI version: $actualVersion"
Write-Host "ComfyUI root: $resolvedComfyRoot"
Write-Host "Python: $resolvedPython"
if ($resolvedExtraModelsConfig) {
    Write-Host "Desktop extra model paths: $resolvedExtraModelsConfig"
}
Write-Host "Firewall source restricted to: $LinuxTailscaleAddress"
Write-Host "The process resumes with Windows after hibernation."
