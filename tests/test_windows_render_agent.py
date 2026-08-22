from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
AGENT_PATH = ROOT / "deploy/windows-render-agent/render_agent.py"
SPEC = importlib.util.spec_from_file_location("windows_render_agent", AGENT_PATH)
assert SPEC and SPEC.loader
AGENT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AGENT
SPEC.loader.exec_module(AGENT)


class WindowsRenderAgentTests(unittest.TestCase):
    def test_gpu_power_sums_nvidia_devices(self):
        completed = subprocess.CompletedProcess(
            args=["nvidia-smi"],
            returncode=0,
            stdout="31.25\n47.84\n",
        )
        with (
            mock.patch.object(AGENT, "_nvidia_smi_command", return_value="nvidia-smi.exe"),
            mock.patch.object(AGENT.subprocess, "run", return_value=completed) as run,
        ):
            self.assertEqual(79.1, AGENT.gpu_power_w())
        self.assertIn("--query-gpu=power.draw", run.call_args.args[0])
        self.assertIn("--format=csv,noheader,nounits", run.call_args.args[0])

    def test_gpu_power_is_none_when_nvidia_smi_is_unavailable(self):
        with mock.patch.object(AGENT, "_nvidia_smi_command", return_value=None):
            self.assertIsNone(AGENT.gpu_power_w())

    def test_agent_is_render_power_only(self):
        source = AGENT_PATH.read_text(encoding="utf-8")
        self.assertIn('"/v1/power/hibernate"', source)
        self.assertNotIn("prompt-revisions", source)
        self.assertNotIn("codex", source.lower())
        self.assertEqual("4", AGENT.AGENT_VERSION)

    def test_hibernate_attempt_always_releases_lock_and_records_failure(self):
        state = AGENT.AgentState("x" * 32)
        state.hibernate_scheduled = True
        completed = subprocess.CompletedProcess(
            args=["shutdown.exe", "/h"],
            returncode=1,
            stdout="",
            stderr="denied",
        )
        with (
            mock.patch.object(AGENT.time, "sleep"),
            mock.patch.object(AGENT.subprocess, "run", return_value=completed),
        ):
            AGENT._hibernate_after_response(state)
        self.assertFalse(state.hibernate_scheduled)
        self.assertEqual(1, state.last_hibernate_exit_code)
        self.assertEqual("denied", state.last_hibernate_error)
        self.assertIsNotNone(state.last_hibernate_finished_at)

    def test_installer_disables_only_ac_idle_sleep_timers(self):
        installer = (
            ROOT / "deploy/windows-render-agent/install.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("/change standby-timeout-ac 0", installer)
        self.assertIn("/change hibernate-timeout-ac 0", installer)
        self.assertNotIn("standby-timeout-dc", installer)
        self.assertNotIn("hibernate-timeout-dc", installer)
        self.assertIn("powercfg.exe /hibernate on", installer)
        self.assertIn("expected v4", installer)

    def test_agent_persists_heartbeat_and_clean_shutdown_state(self):
        with tempfile.TemporaryDirectory() as temp:
            state_file = Path(temp) / "runtime-state.json"
            diagnostics = AGENT.LifecycleDiagnostics(state_file)
            diagnostics.start()
            active = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual("4", active["agent_version"])
            self.assertFalse(active["clean_shutdown"])
            self.assertEqual(diagnostics.started_at, active["started_at_epoch"])
            self.assertIn("heartbeat_at_epoch", active)

            diagnostics.stop("unit_test", clean=True)
            stopped = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertTrue(stopped["clean_shutdown"])
            self.assertEqual("unit_test", stopped["exit_reason"])
            self.assertIn("stopped_at_epoch", stopped)

    def test_agent_reports_previous_unclean_run(self):
        with tempfile.TemporaryDirectory() as temp:
            state_file = Path(temp) / "runtime-state.json"
            state_file.write_text(
                json.dumps({
                    "pid": 123,
                    "started_at_epoch": 100.0,
                    "heartbeat_at_epoch": 200.0,
                    "clean_shutdown": False,
                    "exit_reason": None,
                }),
                encoding="utf-8",
            )
            diagnostics = AGENT.LifecycleDiagnostics(state_file)
            with self.assertLogs(AGENT.LOGGER, level="WARNING") as captured:
                diagnostics.start()
            diagnostics.stop("unit_test", clean=True)
            self.assertIn("previous_run_unclean", "\n".join(captured.output))

    def test_installer_enables_durable_diagnostics_and_removes_time_limit(self):
        installer = (
            ROOT / "deploy/windows-render-agent/install.ps1"
        ).read_text(encoding="utf-8")
        diagnose = (
            ROOT / "deploy/windows-render-agent/diagnose.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn('"--log-file"', installer)
        self.assertIn('"--state-file"', installer)
        self.assertIn('"--crash-file"', installer)
        self.assertIn('TaskScheduler/Operational" /e:true', installer)
        self.assertIn("-ExecutionTimeLimit ([TimeSpan]::Zero)", installer)
        self.assertNotIn("New-TimeSpan -Days 3", installer)
        self.assertIn("-RestartCount 10", installer)
        self.assertIn("-RestartInterval (New-TimeSpan -Minutes 1)", installer)
        self.assertNotIn("-RestartInterval (New-TimeSpan -Seconds 30)", installer)
        self.assertIn("runtime-state.json", diagnose)
        self.assertIn("render-agent.log", diagnose)
        self.assertIn("crash.log", diagnose)
        self.assertIn("Get-WinEvent", diagnose)


if __name__ == "__main__":
    unittest.main()
