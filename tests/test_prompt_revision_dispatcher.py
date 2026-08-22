from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import prompt_revision_dispatcher as dispatcher
import h3_prompt_contract


def config(root: Path) -> dispatcher.Config:
    return dispatcher.Config(
        root=root,
        remote_url="http://100.78.202.37:8765",
        token="x" * 64,
        wol_mac="b0:82:e2:37:a1:8a",
        wol_broadcast="172.30.1.255",
        poll_seconds=0.01,
        wake_timeout_seconds=1,
        request_timeout_seconds=10,
    )


class PromptRevisionDispatcherTests(unittest.TestCase):
    def test_magic_packet_targets_lan_broadcast(self):
        fake_socket = mock.MagicMock()
        fake_socket.__enter__.return_value = fake_socket
        with mock.patch.object(dispatcher.socket, "socket", return_value=fake_socket):
            dispatcher.send_wake_on_lan(
                "b0:82:e2:37:a1:8a", "172.30.1.255", 9
            )
        packet, address = fake_socket.sendto.call_args.args
        self.assertEqual(("172.30.1.255", 9), address)
        self.assertEqual(b"\xff" * 6, packet[:6])
        self.assertEqual(102, len(packet))
        self.assertEqual(bytes.fromhex("b082e237a18a"), packet[6:12])

    def test_wake_is_owned_only_when_health_needed_wol(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = config(Path(temp))
            with (
                mock.patch.object(
                    dispatcher,
                    "remote_health",
                    side_effect=[None, None, {"status": "ok", "agent_version": "1"}],
                ),
                mock.patch.object(dispatcher, "send_wake_on_lan") as wake,
                mock.patch.object(dispatcher.time, "sleep"),
            ):
                health, wake_owned = dispatcher.ensure_remote_awake(cfg)
        self.assertEqual("ok", health["status"])
        self.assertTrue(wake_owned)
        wake.assert_called_once_with("b0:82:e2:37:a1:8a", "172.30.1.255", 9)

    def test_existing_manual_request_is_migrated_to_remote_dispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = config(Path(temp))
            payload = {
                "prompt_revision_request_id": "h3rev_test",
                "status": "awaiting_codex_authoring",
                "remote_attempts": 0,
            }
            with (
                mock.patch.object(
                    dispatcher.h3_queue,
                    "list_prompt_revision_requests",
                    return_value=[payload],
                ),
                mock.patch.object(
                    dispatcher, "process_request", return_value={}
                ) as process,
            ):
                processed = dispatcher.process_once(cfg)
        self.assertTrue(processed)
        process.assert_called_once_with(cfg, payload)

    def test_remote_payload_arms_hibernate_only_for_managed_wake(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = config(Path(temp))
            request = {
                "prompt_revision_request_id": "h3rev_test",
                "feedback": "f",
                "expected_variant_ids": ["D", "E", "F"],
                "source_prompt_variants": [{"video_prompt": "old"}] * 3,
                "clip_context": {"scenario_ko": "루아가 달리며 창으로 공격한다."},
            }
            awake = dispatcher._remote_payload(request, False, cfg)
            woken = dispatcher._remote_payload(request, True, cfg)
        self.assertNotIn("source_prompt_variants", awake)
        self.assertEqual("fresh_from_scenario", awake["authoring_mode"])
        self.assertEqual(h3_prompt_contract.CONTRACT_VERSION, awake["prompt_contract_version"])
        self.assertNotIn("power_lease", awake)
        self.assertEqual(
            cfg.hibernate_after_idle_seconds,
            woken["power_lease"]["hibernate_after_idle_seconds"],
        )


if __name__ == "__main__":
    unittest.main()
