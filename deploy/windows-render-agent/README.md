# Windows H3 render power agent

This is the minimal Windows companion for H3 candidate rendering. It has no
prompt-authoring or Codex dependency. It only exposes:

- `GET /healthz`: awake state and current NVIDIA GPU power from `nvidia-smi`
- `POST /v1/power/hibernate`: authenticated Windows hibernation

The UI displays GPU board power, not whole-PC wall power. When the agent cannot
be reached, the UI reports `최대 절전/오프라인` and does not invent a wattage.

Installer v3 disables the Windows AC standby and hibernation timers. This keeps
a long headless H3 render from sleeping merely because there was no keyboard or
mouse input. Linux-managed `shutdown.exe /h` remains enabled and is still sent
after the Windows candidate queue finishes and its configured idle grace period
expires.

Agent v4 clears its in-memory hibernation lock after every `shutdown.exe /h`
attempt, including failures and resume from S4. `/healthz` reports the last
request time, exit code, and error. The Linux worker treats the request as
successful only after the agent is actually unreachable for three consecutive
checks; an accepted command that leaves the PC awake is recorded as a failure
and retried after the configured idle interval.

Agent v4 also records enough durable diagnostics to distinguish a Python crash,
a Windows Task Scheduler termination, and a suspend/resume stall:

- `C:\ProgramData\NALStudio\H3RenderAgent\render-agent.log`: rotating lifecycle,
  exception, HTTP-error, and hibernation-command log (5 MiB × 6 files)
- `C:\ProgramData\NALStudio\H3RenderAgent\runtime-state.json`: PID, start time,
  30-second heartbeat, clean-shutdown flag, and exit reason
- `C:\ProgramData\NALStudio\H3RenderAgent\crash.log`: Python fatal-fault dump
- Windows `Microsoft-Windows-TaskScheduler/Operational`: enabled by the installer

The scheduled task no longer has the old 72-hour execution limit. It runs with
an unlimited execution time and retries a failed process up to ten times at
one-minute intervals (the minimum accepted by Windows Task Scheduler).

## Install or update

Run in an elevated PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

Defaults match the current render desktop:

- Tailscale: `100.78.202.37`
- LAN: `172.30.1.71`
- Agent port: `8766`
- Allowed Linux peer: `100.124.246.93`

The installer reuses the existing render-agent token. When only the legacy H3
prompt agent exists, it imports that token before removing the legacy scheduled
task, so the Linux runtime token remains valid.

The scheduled task is named `NAL Studio Windows Render Agent`. The firewall
allows TCP 8766 only from the Linux Tailscale address.

## Collect diagnostics after a recurrence

Do not restart the task first. Open an elevated PowerShell window and run:

```powershell
& "$env:ProgramData\NALStudio\H3RenderAgent\diagnose.ps1" | Out-File `
  "$env:USERPROFILE\Desktop\windows-render-agent-diagnostics.txt" -Encoding utf8
```

The report contains no bearer-token contents. Capture it before restarting the
task so `LastTaskResult` and the last heartbeat remain intact.

The Linux worker defaults to a 60-second confirmation window. It can be
overridden with `H3_RENDER_HIBERNATE_CONFIRM_TIMEOUT_SECONDS` when a Windows
host needs longer to disappear from Tailscale after entering S4.
