from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ui_backend
from job_queue import atomic_write_json


class WindowsManualPowerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _write_job(self, job_id: str, *, lane: str, status: str) -> None:
        directory = self.root / "runtime/h3/jobs" / job_id
        directory.mkdir(parents=True)
        atomic_write_json(directory / "request.json", {"queue_lane": lane})
        atomic_write_json(directory / "status.json", {"status": status})

    def _manager(self):
        manager = mock.Mock()
        manager.manual_wake.return_value = {"status": "wake_sent"}
        manager.manual_hibernate.return_value = {"status": "hibernate_scheduled"}
        return manager

    def test_confirmation_is_required_for_both_power_actions(self):
        for payload in (
            {"action": "wake"},
            {"action": "hibernate", "confirm": "wake"},
            {"action": "shutdown", "confirm": "shutdown"},
        ):
            with self.subTest(payload=payload), self.assertRaisesRegex(
                ValueError, "확인 값"
            ):
                ui_backend.control_windows_render_power(payload)

    def test_manual_wake_calls_only_wol_path(self):
        manager = self._manager()
        with mock.patch.object(ui_backend, "ROOT", self.root), mock.patch.object(
            ui_backend.RemoteRenderPowerConfig, "from_env", return_value=object()
        ), mock.patch.object(
            ui_backend, "RemoteRenderPowerManager", return_value=manager
        ):
            result = ui_backend.control_windows_render_power(
                {"action": "wake", "confirm": "wake"}
            )
        self.assertEqual("wake_sent", result["status"])
        manager.manual_wake.assert_called_once_with()
        manager.manual_hibernate.assert_not_called()

    def test_hibernate_blocks_unfinished_windows_jobs_but_not_local_jobs(self):
        self._write_job("windows-running", lane="windows_candidate", status="running")
        self._write_job("local-running", lane="local_generation", status="running")
        manager = self._manager()
        with mock.patch.object(ui_backend, "ROOT", self.root), mock.patch.object(
            ui_backend.RemoteRenderPowerConfig, "from_env", return_value=object()
        ), mock.patch.object(
            ui_backend, "RemoteRenderPowerManager", return_value=manager
        ):
            with self.assertRaisesRegex(ValueError, "미완료 작업 1개"):
                ui_backend.control_windows_render_power(
                    {"action": "hibernate", "confirm": "hibernate"}
                )
        manager.manual_hibernate.assert_not_called()

        atomic_write_json(
            self.root / "runtime/h3/jobs/windows-running/status.json",
            {"status": "completed"},
        )
        with mock.patch.object(ui_backend, "ROOT", self.root), mock.patch.object(
            ui_backend.RemoteRenderPowerConfig, "from_env", return_value=object()
        ), mock.patch.object(
            ui_backend, "RemoteRenderPowerManager", return_value=manager
        ):
            result = ui_backend.control_windows_render_power(
                {"action": "hibernate", "confirm": "hibernate"}
            )
        self.assertEqual("hibernate_scheduled", result["status"])
        manager.manual_hibernate.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
