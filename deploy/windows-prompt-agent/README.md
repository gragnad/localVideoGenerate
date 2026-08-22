# Windows H3 prompt authoring agent

This companion runs structured `codex exec` jobs on the Windows PC and exposes
only one authenticated API on its Tailscale address. The Linux video engine
sends Wake-on-LAN before a job when the agent is unreachable. A hibernation
lease is armed only when Linux had to wake the PC; an already-running PC is not
hibernated by the dispatcher.

`172.30.1.71:41641` is Tailscale's UDP transport endpoint, not the HTTP API.
The application endpoint is `http://100.78.202.37:8765`.

## Windows installation

Prerequisites:

- Python 3 available as `python.exe`
- Codex CLI installed and authenticated (`codex login`)
- BIOS/UEFI Wake-on-LAN enabled for the wired NIC
- An elevated PowerShell window

From this directory on the Windows PC:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

The installer enables Windows hibernation, attempts to enable the NIC's magic
packet settings, installs a logon scheduled task, and creates a firewall rule
that allows TCP 8765 only from Linux Tailscale IP `100.124.246.93`. Copy the
printed token to the Linux runtime environment.

Confirm Windows power support with:

```powershell
powercfg /a
Get-NetAdapterPowerManagement -Name (Get-NetAdapter -Physical | Where-Object Status -eq Up).Name
```

## Linux configuration

Add these values to `~/.config/h3-video-engine/runtime.env` without committing
the token:

```dotenv
H3_PROMPT_REVISION_REMOTE_URL=http://100.78.202.37:8765
H3_PROMPT_REVISION_REMOTE_TOKEN=<token printed by install.ps1>
H3_PROMPT_REVISION_WOL_MAC=b0:82:e2:37:a1:8a
H3_PROMPT_REVISION_WOL_BROADCAST=172.30.1.255
H3_PROMPT_REVISION_WOL_PORT=9
H3_PROMPT_REVISION_WAKE_TIMEOUT_SECONDS=180
H3_PROMPT_REVISION_HIBERNATE_IDLE_SECONDS=300
```

Install and start `deploy/h3-prompt-revision-dispatcher.service` as a user
service, then restart the H3 UI so it sees the remote authoring configuration.

## Power behavior

- If `/healthz` is already reachable, the dispatcher does not arm hibernation.
- If it is unreachable, Linux broadcasts a magic packet to the wired NIC and
  waits for the API.
- A successfully woken agent receives a five-minute idle hibernation lease.
- Every request resets the idle timer, so multiple queued revisions finish
  before Windows runs `shutdown.exe /h`.
- Tailscale alone cannot wake a sleeping PC; WOL works because the Linux server
  remains on the same `172.30.1.0/24` LAN.

## Explicit power-cycle test from Linux

Agent version 3 authors every candidate from the scenario contract without
receiving the previous prompt text. It also keeps the authenticated
`POST /v1/power/hibernate` endpoint introduced in version 2. The endpoint
requires `{"confirm":"hibernate"}` and refuses to hibernate while a Codex job
is active. Run the complete S4/WOL round trip from `ltx-ai` with:

```bash
set -a
source ~/.config/h3-video-engine/runtime.env
set +a
.venv/bin/python prompt_revision_power.py cycle
```

The command verifies the hibernate acknowledgement, waits for three failed
health checks, allows S4 to settle, broadcasts five magic packets, and waits for
the authenticated agent host to become healthy again.
