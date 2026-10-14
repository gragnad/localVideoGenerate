from __future__ import annotations

import os
import unittest
from unittest import mock

from remote_render_power import Config, RemoteRenderPowerManager, RemoteRenderUnavailable


class _Client:
    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.calls = 0

    def health(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise OSError("offline")
        return {"system": {}}


class RemoteRenderPowerTests(unittest.TestCase):
    @staticmethod
    def config(**updates):
        values = {
            "comfy_url": "http://100.78.202.37:8189",
            "agent_url": "http://100.78.202.37:8766",
            "agent_token": "secret",
            "wol_mac": "b0:82:e2:37:a1:8a",
            "wol_broadcast": "172.30.1.255",
        }
        values.update(updates)
        return Config(**values)

    def test_config_uses_candidate_render_and_dedicated_power_values(self):
        with mock.patch.dict(os.environ, {
            "H3_CANDIDATE_COMFY_URL": "http://100.78.202.37:8189/",
            "H3_RENDER_AGENT_URL": "http://100.78.202.37:8766/",
            "H3_RENDER_AGENT_TOKEN": "secret",
            "H3_RENDER_WOL_MAC": "b0:82:e2:37:a1:8a",
            "H3_RENDER_WOL_BROADCAST": "172.30.1.255",
        }, clear=True):
            config = Config.from_env()
        self.assertIsNotNone(config)
        self.assertEqual("http://100.78.202.37:8189", config.comfy_url)
        self.assertEqual("http://100.78.202.37:8766", config.agent_url)
        self.assertEqual("secret", config.agent_token)
        self.assertEqual(60, config.hibernate_confirm_timeout_seconds)

    def test_ensure_comfy_wakes_offline_managed_host(self):
        config = Config(
            comfy_url="http://100.78.202.37:8189",
            agent_url="http://100.78.202.37:8766",
            agent_token="secret",
            wol_mac="b0:82:e2:37:a1:8a",
            wol_broadcast="172.30.1.255",
            poll_seconds=0,
        )
        manager = RemoteRenderPowerManager(config)
        client = _Client(failures=1)
        with mock.patch.object(manager, "agent_awake", return_value=False), mock.patch(
            "remote_render_power.send_wake_on_lan"
        ) as wake:
            self.assertTrue(manager.ensure_comfy(client))
        self.assertTrue(manager.wake_owned)
        self.assertEqual(5, wake.call_count)

    def test_manual_wake_sends_five_packets_without_waiting(self):
        manager = RemoteRenderPowerManager(self.config())
        with mock.patch.object(manager, "agent_awake", return_value=False), mock.patch(
            "remote_render_power.send_wake_on_lan"
        ) as wake:
            result = manager.manual_wake()
        self.assertEqual("wake_sent", result["status"])
        self.assertEqual(5, result["wake_packets_sent"])
        self.assertEqual(5, wake.call_count)

    def test_manual_wake_is_idempotent_when_agent_is_awake(self):
        manager = RemoteRenderPowerManager(self.config())
        with mock.patch.object(manager, "agent_awake", return_value=True), mock.patch(
            "remote_render_power.send_wake_on_lan"
        ) as wake:
            result = manager.manual_wake()
        self.assertEqual("already_awake", result["status"])
        wake.assert_not_called()

    def test_manual_hibernate_blocks_busy_comfy_and_sends_authenticated_request(self):
        manager = RemoteRenderPowerManager(self.config())
        with mock.patch.object(manager, "agent_awake", return_value=True), mock.patch.object(
            manager, "_comfy_busy", return_value=True
        ), mock.patch.object(manager, "_agent_request") as request:
            with self.assertRaisesRegex(RemoteRenderUnavailable, "ComfyUI"):
                manager.manual_hibernate()
        request.assert_not_called()

        with mock.patch.object(manager, "agent_awake", return_value=True), mock.patch.object(
            manager, "_comfy_busy", return_value=False
        ), mock.patch.object(
            manager,
            "_agent_request",
            return_value={"status": "hibernate_scheduled", "scheduled_in_seconds": 2},
        ) as request:
            result = manager.manual_hibernate()
        self.assertEqual("hibernate_scheduled", result["status"])
        request.assert_called_once_with(
            "POST",
            "/v1/power/hibernate",
            {"confirm": "hibernate"},
            authenticated=True,
            timeout=10.0,
        )

    def test_healthy_host_arms_hibernation_without_wol_ownership(self):
        config = Config(
            comfy_url="http://100.78.202.37:8189",
            agent_url="http://100.78.202.37:8766",
            agent_token="secret",
            wol_mac="b0:82:e2:37:a1:8a",
            wol_broadcast="172.30.1.255",
        )
        manager = RemoteRenderPowerManager(config)
        self.assertFalse(manager.ensure_comfy(_Client()))
        self.assertFalse(manager.wake_owned)
        self.assertTrue(manager.hibernate_armed)

    def test_active_host_hibernates_after_idle_regardless_of_wake_method(self):
        config = Config(
            comfy_url="http://100.78.202.37:8189",
            agent_url="http://100.78.202.37:8766",
            agent_token="secret",
            wol_mac="b0:82:e2:37:a1:8a",
            wol_broadcast="172.30.1.255",
            hibernate_idle_seconds=1,
        )
        manager = RemoteRenderPowerManager(config)
        manager.hibernate_armed = True
        manager.last_activity = 0
        with mock.patch("remote_render_power.time.monotonic", return_value=10), mock.patch.object(
            manager, "_comfy_busy", return_value=False
        ), mock.patch.object(
            manager,
            "_agent_request",
            return_value={"status": "hibernate_scheduled"},
        ) as request, mock.patch.object(
            manager,
            "_wait_for_agent_offline",
            return_value=7.5,
        ) as wait_for_offline:
            self.assertTrue(manager.maybe_hibernate())
        request.assert_called_once_with(
            "POST",
            "/v1/power/hibernate",
            {"confirm": "hibernate"},
            authenticated=True,
            timeout=10.0,
        )
        wait_for_offline.assert_called_once_with()
        self.assertFalse(manager.wake_owned)
        self.assertFalse(manager.hibernate_armed)

    def test_accepted_hibernate_that_stays_online_is_reported_and_remains_armed(self):
        config = Config(
            comfy_url="http://100.78.202.37:8189",
            agent_url="http://100.78.202.37:8766",
            agent_token="secret",
            wol_mac="b0:82:e2:37:a1:8a",
            wol_broadcast="172.30.1.255",
            hibernate_idle_seconds=1,
        )
        manager = RemoteRenderPowerManager(config)
        manager.hibernate_armed = True
        manager.last_activity = 0
        with mock.patch("remote_render_power.time.monotonic", return_value=10), mock.patch.object(
            manager, "_comfy_busy", return_value=False
        ), mock.patch.object(
            manager, "_agent_request", return_value={"status": "hibernate_scheduled"}
        ), mock.patch.object(
            manager,
            "_wait_for_agent_offline",
            side_effect=RuntimeError("still online"),
        ):
            with self.assertRaisesRegex(RuntimeError, "still online"):
                manager.maybe_hibernate()
        self.assertTrue(manager.hibernate_armed)

    def test_hibernate_confirmation_requires_three_consecutive_offline_checks(self):
        config = Config(
            comfy_url="http://100.78.202.37:8189",
            agent_url="http://100.78.202.37:8766",
            agent_token="secret",
            wol_mac="b0:82:e2:37:a1:8a",
            wol_broadcast="172.30.1.255",
            poll_seconds=0,
        )
        manager = RemoteRenderPowerManager(config)
        with mock.patch.object(
            manager,
            "agent_awake",
            side_effect=[False, True, False, False, False],
        ) as awake, mock.patch(
            "remote_render_power.time.monotonic",
            side_effect=[0, 0, 1, 2, 3, 4, 5],
        ), mock.patch("remote_render_power.time.sleep"):
            self.assertEqual(5, manager._wait_for_agent_offline())
        self.assertEqual(5, awake.call_count)

    def test_host_does_not_hibernate_before_candidate_activity(self):
        config = Config(
            comfy_url="http://100.78.202.37:8189",
            agent_url="http://100.78.202.37:8766",
            agent_token="secret",
            wol_mac="b0:82:e2:37:a1:8a",
            wol_broadcast="172.30.1.255",
            hibernate_idle_seconds=1,
        )
        manager = RemoteRenderPowerManager(config)
        manager.last_activity = 0
        with mock.patch("remote_render_power.time.monotonic", return_value=10), mock.patch.object(
            manager, "_agent_request"
        ) as request:
            self.assertFalse(manager.maybe_hibernate())
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
