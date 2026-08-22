from __future__ import annotations

"""Promote the explicitly reviewed EP00 V8 project; never queues or generates video."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_projects


EPISODE_DIR = ROOT / "projects" / "RaisingaDragonSeason01"
PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_ACTION_CAUSALITY_V8"
PROJECT_DIR = ROOT / "prompt_projects" / PROJECT_ID
SPEC_PATH = EPISODE_DIR / "EP00_H3_R2V_ACTION_CAUSALITY_V8_SPEC.json"
AUDIT_PATH = EPISODE_DIR / "EP00_H3_R2V_ACTION_CAUSALITY_V8_AUDIT.json"
CONTACT_MANIFEST_PATH = (
    EPISODE_DIR
    / "storyboards_ep00_action_v2"
    / "EP00_ACTION_CAUSALITY_V8_CONTACT_SHEET_MANIFEST.json"
)
DECISION_PATH = EPISODE_DIR / "EP00_H3_R2V_ACTION_CAUSALITY_V8_REVIEW_DECISION.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewer-confirmed-visual-pass", action="store_true")
    args = parser.parse_args()
    if not args.reviewer_confirmed_visual_pass:
        raise ValueError("14개 원본의 명시적 시각 검수 없이는 verified로 승격할 수 없습니다.")

    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    if not audit.get("passed") or int(audit.get("failed_count") or 0) != 0:
        raise ValueError("29/29 PASS 감사 기록 없이는 verified로 승격할 수 없습니다.")
    contact = json.loads(CONTACT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if contact.get("source_count") != 14:
        raise ValueError("14개 스토리보드 원본을 포함한 접촉 시트가 필요합니다.")

    for row in contact["sources"]:
        row["visual_review"] = "agent_passed_full_sheet"
    contact["review_status"] = "verified"
    contact["visual_review_scope"] = (
        "all_14_original_storyboards_at_original_detail_and_full_contact_sheet"
    )
    contact["visual_review_checks"] = [
        "four_panel_chronology_and_causal_readability",
        "persistent_Heartstone_Chamber_environment",
        "Lua_and_AbyssKing_identity_scale_and_silhouette",
        "single_spear_and_single_shield_state_continuity",
        "camera_and_emotional_progression",
        "no_production_ids_labels_or_explanatory_text",
        "no_character_duplication_or_scene3_spear_regrab",
    ]
    CONTACT_MANIFEST_PATH.write_text(
        json.dumps(contact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    audit_label = f"action_v8_audit_{audit['passed_count']}_of_{audit['check_count']}_passed"
    promoted: list[str] = []
    for path in sorted(PROJECT_DIR.glob("EP00-S*/EP00-*.md")):
        text = path.read_text(encoding="utf-8")
        payload = h3_prompt_projects.extract_payload(text)
        if payload.get("status") not in {"pending_review", "verified"}:
            raise ValueError(f"검수 가능한 상태가 아닌 clip은 승격하지 않습니다: {path}")
        payload["status"] = "verified"
        payload["visual_review"] = "agent_passed_all_14_original_storyboards"
        payload["semantic_review"] = audit_label
        payload["review_decision"] = {
            "decision": "verified",
            "reviewer": "Codex agent explicit visual and semantic review",
            "date": "2026-08-16",
            "audit": AUDIT_PATH.name,
            "contact_sheet_manifest": CONTACT_MANIFEST_PATH.name,
            "queue_authorized": False,
            "video_generation_authorized": False,
            "queue_registration_performed": False,
            "video_generation_performed": False,
        }
        markdown = (
            f"# {payload['clip_id']} · MiniMax H3 R2V\n\n"
            "## Machine Payload\n\n```json\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
            + "\n```\n"
        )
        path.write_text(markdown, encoding="utf-8")
        promoted.append(payload["clip_id"])

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    for clip in spec["clips"]:
        clip["status"] = "verified"
        clip["visual_review"] = "agent_passed_all_14_original_storyboards"
        clip["semantic_review"] = audit_label
    spec["review_decision"] = "verified_after_explicit_visual_and_semantic_review"
    SPEC_PATH.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_path = PROJECT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["review_status"] = "verified"
    manifest["review_decision"] = DECISION_PATH.name
    manifest["queue_authorized"] = False
    manifest["video_generation_authorized"] = False
    manifest["queue_registration_performed"] = False
    manifest["video_generation_performed"] = False
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    decision = {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "decision": "verified",
        "date": "2026-08-16",
        "reviewer": "Codex agent explicit visual and semantic review",
        "visual_review": {
            "contact_sheet_manifest": CONTACT_MANIFEST_PATH.name,
            "source_count": 14,
            "result": "pass_after_full_contact_sheet_and_all_original_storyboards_review",
        },
        "semantic_review": {
            "audit": AUDIT_PATH.name,
            "passed": audit["passed"],
            "passed_count": audit["passed_count"],
            "check_count": audit["check_count"],
            "failed_count": audit["failed_count"],
        },
        "promoted_clip_ids": promoted,
        "queue_authorized": False,
        "video_generation_authorized": False,
        "queue_registration_performed": False,
        "video_generation_performed": False,
    }
    DECISION_PATH.write_text(
        json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
