# Windows ComfyUI candidate render target

This installs the existing Windows ComfyUI as the render-only target for the
video engine. Prompt authoring remains in the video production workflow. The
Linux H3 worker uploads reference images and the compiled API workflow, waits
for A/B/C rendering, and downloads each output video back to Linux.

Port `8189` is used because `8188` is occupied by another HTTP service on this
PC. The firewall rule accepts the API only on Tailscale IP `100.78.202.37` and
only from Linux Tailscale IP `100.124.246.93`.

The MiniMax H3 native nodes require ComfyUI `0.30.0` or later. The installer
auto-detects the current Comfy Desktop installation and inherits Desktop's
`%APPDATA%\ComfyUI\extra_models_config.yaml`, so models already used by the
Desktop app are also visible to the remote `8189` process.

Run from an elevated PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

For the portable Windows package, the root is commonly:

```powershell
.\install.ps1 -ComfyRoot "$env:USERPROFILE\ComfyUI_windows_portable\ComfyUI"
```

The installer finds the portable embedded Python when present, otherwise it
uses `python.exe` from `PATH`. It validates ComfyUI version, the two H3 core
nodes, and all four exact model filenames. It creates a scheduled task named
`NAL Studio Windows Comfy Render`, starts ComfyUI with
`--listen 100.78.202.37 --port 8189`, and verifies `/system_stats`.

The Windows ComfyUI installation must contain the same models and custom nodes
referenced by the H3 workflow registered in the Linux video engine. A healthy
API alone does not guarantee workflow compatibility; the first submission will
report any missing model or node through the existing H3 job error display.
