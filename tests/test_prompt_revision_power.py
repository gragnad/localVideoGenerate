from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import prompt_revision_dispatcher as dispatcher
import prompt_revision_power as power


def config(root: Path) -> dispatcher.Config:
    return dispatcher.Config(
        root=root,
        remote_url="http://100.78.202.37:8766",
        token="x" * 64,
        wol_mac="b0:82:e2:37:a1:8a",
        wol_broadcast="172.30.1.255",
        poll_seconds=0.01,
        wake_timeout_seconds=30,
    )


class PromptRevisionPowerTests(unittest.TestCase):
    def test_hibernate_requires_ack_then_three_offline_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = config(Path(temp))
            with (
                mock.patch.object(
                    power,
                    "remote_health",
                    side_effect=[{"status": "ok"}, None, None, None],
                ),
                mock.patch.object(
                    power,
                    "_json_request",
                    return_value={"status": "hibernate_scheduled"},
                ) as request,
                mock.patch.object(power.time, "sleep"),
            ):
                power.hibernate(cfg)
        request.assert_called_once_with(
            cfg,
            "POST",
            "/v1/power/hibernate",
            {"confirm": "hibernate"},
            timeout=10,
        )

    def test_send_wake_broadcasts_five_packets(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = config(Path(temp))
            with (
                mock.patch.object(power, "send_wake_on_lan") as send,
                mock.patch.object(power.time, "sleep"),
            ):
                power.send_wake(cfg)
        self.assertEqual(5, send.call_count)
        send.assert_called_with("b0:82:e2:37:a1:8a", "172.30.1.255", 9)

    def test_wait_for_online_returns_after_health_recovers(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = config(Path(temp))
            with (
                mock.patch.object(
                    power,
                    "remote_health",
                    side_effect=[None, None, {"status": "ok"}],
                ),
                mock.patch.object(power.time, "sleep"),
            ):
                elapsed = power.wait_for_online(cfg)
        self.assertGreaterEqual(elapsed, 0)


if __name__ == "__main__":
    unittest.main()
