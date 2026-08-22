from __future__ import annotations

"""Fail-closed structural and semantic audit for the locked EP00 V7 project."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract
import h3_prompt_projects


EPISODE_DIR = ROOT / "projects" / "RaisingaDragonSeason01"
PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_STORYBOARD_ADE_V7_LOCKED"
PROJECT_DIR = ROOT / "prompt_projects" / PROJECT_ID
LOCK_PATH = EPISODE_DIR / "EP00_LOCKED_PRODUCTION_RULES_V1.json"
CANONICAL_PATH = EPISODE_DIR / "EP00_CANONICAL_CLIPS_V1.json"
EVENTS_PATH = EPISODE_DIR / "EP00_H3_R2V_STORYBOARD_ADE_V7_LOCKED_EVENT_CONTRACTS.json"
SPEC_PATH = EPISODE_DIR / "EP00_H3_R2V_STORYBOARD_ADE_V7_LOCKED_SPEC.json"
CONTACT_SHEET_PATH = (
    EPISODE_DIR / "storyboards_ep00_ade_v1" / "EP00_STORYBOARD_CONTACT_SHEET_V4_LOCKED.png"
)
CONTACT_MANIFEST_PATH = (
    EPISODE_DIR / "storyboards_ep00_ade_v1" / "EP00_STORYBOARD_CONTACT_SHEET_V4_LOCKED_MANIFEST.json"
)
REPORT_JSON_PATH = EPISODE_DIR / "EP00_H3_R2V_STORYBOARD_ADE_V7_LOCKED_AUDIT.json"
REPORT_MD_PATH = EPISODE_DIR / "EP00_H3_R2V_STORYBOARD_ADE_V7_LOCKED_AUDIT.md"
POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"PNG가 아닙니다: {path}")
    return struct.unpack(">II", header[16:24])


class Audit:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, condition: bool, detail: str) -> None:
        self.checks.append({"name": name, "passed": bool(condition), "detail": detail})

    @property
    def passed(self) -> bool:
        return all(row["passed"] for row in self.checks)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "project_id": PROJECT_ID,
            "passed": self.passed,
            "check_count": len(self.checks),
            "passed_count": sum(1 for row in self.checks if row["passed"]),
            "failed_count": sum(1 for row in self.checks if not row["passed"]),
            "checks": self.checks,
        }


def _write_contact_manifest(canonical: dict[str, Any]) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for sequence, clip in enumerate(canonical["clips"], start=1):
        path = EPISODE_DIR / "storyboards_ep00_ade_v1" / clip["storyboard"]
        width, height = _png_size(path)
        sources.append({
            "sequence": sequence,
            "clip_id": clip["clip"],
            "path": path.relative_to(EPISODE_DIR).as_posix(),
            "sha256": _sha256(path),
            "width": width,
            "height": height,
            "visual_review": "agent_passed_full_sheet",
        })
    payload = {
        "schema_version": 1,
        "contact_sheet": CONTACT_SHEET_PATH.relative_to(EPISODE_DIR).as_posix(),
        "contact_sheet_sha256": _sha256(CONTACT_SHEET_PATH),
        "contact_sheet_size": list(_png_size(CONTACT_SHEET_PATH)),
        "ordering": "sequence row-major, four storyboard sheets per row",
        "source_count": len(sources),
        "sources": sources,
    }
    CONTACT_MANIFEST_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def run(require_status: str) -> Audit:
    audit = Audit()
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    canonical = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    events = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    manifest = json.loads((PROJECT_DIR / "manifest.json").read_text(encoding="utf-8"))
    overview = h3_prompt_projects.project_clips(ROOT, PROJECT_ID)
    canonical_clips = canonical["clips"]
    expected_ids = [row["clip"] for row in canonical_clips]
    clips = overview["clips"]
    clip_by_id = {row["clip_id"]: row for row in clips}
    payloads: dict[str, dict[str, Any]] = {}
    for path in sorted(PROJECT_DIR.glob("EP00-S*/EP00-*.md")):
        payload = h3_prompt_projects.extract_payload(path.read_text(encoding="utf-8"))
        payloads[payload["clip_id"]] = payload

    audit.check(
        "canonical_source_lineage",
        manifest.get("source_policy") == "locked_canonical_sources_only_no_v1_v6_prompt_lineage"
        and manifest.get("canonical_source_lineage") == spec.get("canonical_source_lineage")
        and all(
            not re.search(r"_V[1-6].*(?:_SPEC|EVENT_CONTRACTS)", source, re.IGNORECASE)
            for source in manifest.get("canonical_source_lineage") or []
        ),
        "manifest와 spec이 잠금 정본 문서만 가리키고 과거 prompt spec/event 계약을 가리키지 않음",
    )
    build_source = (ROOT / "scripts/build_ep00_locked_storyboard_v7.py").read_text(encoding="utf-8")
    audit.check(
        "no_legacy_builder_import",
        not re.search(r"EP00_H3_R2V_STORYBOARD_ADE_V[1-6].*(?:SPEC|EVENT)", build_source)
        and "rebuild_ep00_independent" not in build_source,
        "V7 빌더에 V1-V6 명세·이벤트·재작성 빌더 import가 없음",
    )
    audit.check(
        "locked_identity",
        manifest.get("locked_rule_id") == lock["lock_id"]
        and canonical.get("locked_rule_id") == lock["lock_id"]
        and events.get("locked_rule_id") == lock["lock_id"],
        f"lock_id={lock['lock_id']}",
    )
    audit.check(
        "project_contract_versions",
        manifest.get("prompt_contract_version") == h3_prompt_contract.CONTRACT_VERSION
        and manifest.get("candidate_semantics") == h3_prompt_projects.EVENT_CONTRACT_VERSION
        and events.get("version") == h3_prompt_projects.EVENT_CONTRACT_VERSION,
        "h3_ref_storyboard_v2 + locked_storyboard_shot_plans_v3",
    )
    audit.check(
        "clip_identity_and_order",
        [row["clip_id"] for row in clips] == expected_ids
        and list(payloads) == expected_ids,
        f"expected={len(expected_ids)}, loaded={len(clips)}, payloads={len(payloads)}",
    )
    audit.check(
        "clip_and_prompt_counts",
        len(clips) == lock["clip_contract"]["clip_count"]
        and sum(len(row["prompt_variants"]) for row in clips)
        == lock["clip_contract"]["prompt_count"],
        f"clips={len(clips)}, prompts={sum(len(row['prompt_variants']) for row in clips)}",
    )
    audit.check(
        "duration_lock",
        sum(float(row["duration_seconds"]) for row in clips)
        == float(lock["clip_contract"]["total_duration_seconds"])
        and all(
            float(clip_by_id[row["clip"]]["duration_seconds"]) == float(row["duration"])
            for row in canonical_clips
        ),
        f"total={sum(float(row['duration_seconds']) for row in clips):g}s",
    )
    audit.check(
        "initial_review_status",
        manifest.get("review_status") == require_status
        and all(payload.get("status") == require_status for payload in payloads.values()),
        f"required_status={require_status}",
    )
    build_facts = manifest.get("build_facts") or {}
    execution_contract = lock.get("execution_contract") or {}
    audit.check(
        "manifest_safety_and_counts",
        build_facts.get("clip_count") == lock["clip_contract"]["clip_count"]
        and build_facts.get("prompt_count") == lock["clip_contract"]["prompt_count"]
        and float(build_facts.get("total_duration_seconds") or -1)
        == float(lock["clip_contract"]["total_duration_seconds"])
        and manifest.get("queue_authorized") is False
        and manifest.get("video_generation_authorized") is False
        and manifest.get("queue_registration_performed") is False
        and manifest.get("video_generation_performed") is False
        and execution_contract.get("queue_requires_new_explicit_user_authorization") is True
        and execution_contract.get("video_generation_requires_new_explicit_user_authorization") is True,
        "14 Clip·42 Prompt·133초 기록, 큐 등록과 영상 생성은 별도 사용자 승인 전 금지·미수행",
    )
    audit.check(
        "all_clips_technically_ready",
        all(row["ready"] for row in clips),
        "14개 clip의 공식 H3 계약·자산 연결 검증 통과",
    )

    asset_hash_ok = True
    for name, row in lock["asset_locks"].items():
        asset_hash_ok &= _sha256(EPISODE_DIR / row["path"]) == row["sha256"]
    audit.check("locked_asset_hashes", asset_hash_ok, "Lua, AbyssKing, physical spear SHA-256 일치")
    workflow = Path(lock["workflow_lock"]["path"])
    audit.check(
        "workflow_hash",
        _sha256(workflow) == lock["workflow_lock"]["sha256"],
        f"sha256={_sha256(workflow)}",
    )
    workflow_payload = json.loads(workflow.read_text(encoding="utf-8"))
    node_names: list[str] = []
    for node in workflow_payload.values() if isinstance(workflow_payload, dict) else []:
        if not isinstance(node, dict):
            continue
        node_names.extend(str(node.get(key) or "").lower() for key in ("class_type", "type"))
        meta = node.get("_meta") or {}
        if isinstance(meta, dict):
            node_names.append(str(meta.get("title") or "").lower())
    forbidden_nodes = [
        fragment
        for fragment in lock["workflow_lock"]["forbidden_node_name_fragments"]
        if any(fragment.lower() in name for name in node_names)
    ]
    audit.check("workflow_forbidden_nodes", not forbidden_nodes, f"found={forbidden_nodes}")

    contract_reports_ok = True
    four_shot_ok = True
    current_anchor_ok = True
    next_anchor_ok = True
    standalone_storyboard_ok = True
    subject_storyboard_ok = True
    variant_ids_ok = True
    detail_variants: list[str] = []
    forbidden_hits: list[str] = []
    forbidden_patterns = {
        phrase: re.compile(rf"(?<![A-Za-z]){re.escape(phrase.replace('_', ' '))}(?![A-Za-z])", re.IGNORECASE)
        for phrase in lock["character_contract"]["forbidden_events"]
    }
    for canonical_row in canonical_clips:
        clip_id = canonical_row["clip"]
        clip = clip_by_id[clip_id]
        variants = clip["prompt_variants"]
        variant_ids_ok &= [row["variant_id"] for row in variants] == ["A", "D", "E"]
        storyboard_picture_id = 4 if canonical_row["has_spear"] else 3
        for variant in variants:
            prompt = variant["video_prompt"]
            report = h3_prompt_contract.validate_prompt(
                prompt, duration_seconds=float(clip["duration_seconds"])
            )
            contract_reports_ok &= report.valid
            detail = variant["detailed_description"]
            detail_variants.append(detail)
            shots = list(h3_prompt_contract.SHOT_RE.finditer(detail))
            four_shot_ok &= len(shots) == 4
            standalone_storyboard_ok &= bool(re.search(
                rf"^<Picture {storyboard_picture_id}> is the chronological four-panel storyboard\.",
                prompt,
                re.MULTILINE,
            ))
            subject_storyboard_ok &= not bool(re.search(
                rf"^<Subject {storyboard_picture_id}>.*storyboard",
                prompt,
                re.MULTILINE | re.IGNORECASE,
            ))
            for number, shot in enumerate(shots, start=1):
                body = shot.group(4)
                current_anchor_ok &= (
                    f"<Picture {storyboard_picture_id}>" in body
                    and bool(re.search(rf"\bpanel\s+{number}\b", body, re.IGNORECASE))
                    and POSITIONS[number - 1] in body.lower()
                )
                if variant["variant_id"] in {"D", "E"} and number < 4:
                    next_anchor_ok &= (
                        f"<Picture {storyboard_picture_id}> panel {number + 1} "
                        f"at the {POSITIONS[number]}" in body
                    )
            for phrase, pattern in forbidden_patterns.items():
                if pattern.search(prompt):
                    forbidden_hits.append(f"{clip_id}/{variant['variant_id']}:{phrase}")
    audit.check("candidate_ids", variant_ids_ok, "모든 clip 후보가 A/D/E 순서")
    audit.check("official_prompt_validation", contract_reports_ok, "42개 prompt 공식 6-section 계약 통과")
    audit.check("four_panel_four_shot", four_shot_ok, "42개 prompt 모두 정확히 4 Shot")
    audit.check("current_storyboard_anchor", current_anchor_ok, "168개 Shot 모두 Picture+현재 panel+절대 위치")
    audit.check("next_storyboard_destination", next_anchor_ok, "D/E Shot 1-3 모두 다음 Picture+panel+절대 도착 위치")
    audit.check("storyboard_is_standalone_picture", standalone_storyboard_ok, "Storyboard를 독립 Picture로 정의")
    audit.check("storyboard_not_subject", subject_storyboard_ok, "Storyboard를 visible Subject로 정의하지 않음")
    audit.check("forbidden_event_absence", not forbidden_hits, f"hits={forbidden_hits}")
    audit.check(
        "candidate_descriptions_unique",
        len(detail_variants) == len(set(detail_variants)) == 42,
        f"unique={len(set(detail_variants))}/42",
    )

    raw_cameras: list[str] = []
    d_transitions: list[str] = []
    e_transitions: list[str] = []
    d_semantic_ok = True
    e_semantic_ok = True
    generic_transition_hits: list[str] = []
    for clip_id, contract in events["clips"].items():
        for variant_id, plan in contract["candidate_plans"].items():
            for number, shot in enumerate(plan["shots"], start=1):
                raw_cameras.append(shot["camera"])
                transition = str(shot.get("transition_to_next") or "")
                if number < 4 and variant_id == "D":
                    d_transitions.append(transition)
                    d_semantic_ok &= bool(re.search(
                        r"dolly|track|truck|arc|crane|pedestal|orbit|pull|dive|drop|descend|rise|creep|hold|stop|sweep",
                        transition,
                        re.IGNORECASE,
                    )) and bool(re.search(
                        r"slow|quick|rapid|stead|brisk|impercept|perceptible|same speed|stop all travel",
                        transition,
                        re.IGNORECASE,
                    )) and f"panel {number + 1}" in transition.lower()
                if number < 4 and variant_id == "E":
                    e_transitions.append(transition)
                    e_semantic_ok &= transition.startswith(("Let ", "Follow ", "Use ", "Rack ")) and (
                        f"panel {number + 1}" in transition.lower()
                    )
                if re.fullmatch(
                    r"(?:move|transition|continue)(?: the camera)? (?:to|toward) (?:the )?(?:next )?panel\.?",
                    transition,
                    re.IGNORECASE,
                ):
                    generic_transition_hits.append(f"{clip_id}/{variant_id}/{number}")
    audit.check(
        "camera_compositions_unique",
        len(raw_cameras) == len(set(raw_cameras)) == 168,
        f"unique={len(set(raw_cameras))}/168",
    )
    audit.check(
        "d_camera_paths_specific",
        d_semantic_ok and len(d_transitions) == len(set(d_transitions)) == 42,
        f"unique={len(set(d_transitions))}/42",
    )
    audit.check(
        "e_action_transitions_specific",
        e_semantic_ok and len(e_transitions) == len(set(e_transitions)) == 42,
        f"unique={len(set(e_transitions))}/42",
    )
    audit.check("generic_transition_absence", not generic_transition_hits, f"hits={generic_transition_hits}")

    reference_policy_ok = True
    spear_policy_ok = True
    project_asset_hash_ok = True
    for canonical_row in canonical_clips:
        clip_id = canonical_row["clip"]
        payload = payloads[clip_id]
        refs = payload["references"]
        roles = [row["role"] for row in refs]
        reference_policy_ok &= set(roles) <= {
            "lua_identity", "abyss_king_identity", "major_prop_spear", "chronological_storyboard"
        }
        has_spear_ref = "major_prop_spear" in roles
        spear_policy_ok &= has_spear_ref == bool(canonical_row["has_spear"])
        spear_policy_ok &= len(refs) == (4 if canonical_row["has_spear"] else 3)
        for ref in refs:
            project_asset = PROJECT_DIR / ref["source_path"]
            if ref["role"] == "lua_identity":
                expected = lock["asset_locks"]["lua_awakened"]["sha256"]
            elif ref["role"] == "abyss_king_identity":
                expected = lock["asset_locks"]["abyss_king"]["sha256"]
            elif ref["role"] == "major_prop_spear":
                expected = lock["asset_locks"]["dragon_spear"]["sha256"]
            else:
                source = EPISODE_DIR / "storyboards_ep00_ade_v1" / canonical_row["storyboard"]
                expected = _sha256(source)
            project_asset_hash_ok &= _sha256(project_asset) == expected
    audit.check("reference_policy", reference_policy_ok, "캐릭터+필요 시 창+스토리보드만 연결")
    audit.check("major_spear_policy", spear_policy_ok, "창 인과 clip 12개에만 Picture 3 창 시트 포함")
    audit.check("project_asset_copy_hashes", project_asset_hash_ok, "project-local Picture가 잠금/스토리보드 원본 해시와 일치")

    bridge_ok = True
    event_rows = [events["clips"][clip_id] for clip_id in expected_ids]
    for current, following in zip(event_rows, event_rows[1:]):
        bridge_ok &= current["bridge_out_id"] == following["bridge_in_id"]
    bridge_ok &= event_rows[-1]["boundary_policy"] == "terminal"
    audit.check("bridge_continuity", bridge_ok, "14개 사건 경계 ID 연속, 마지막 terminal")
    audit.check(
        "shield_contract",
        "same single weakened transparent curved water sheet"
        in events["clips"]["EP00-S03-NC02"]["beats"][0]["description"]
        and "edge-first" in events["clips"]["EP00-S03-NC02"]["beats"][3]["description"]
        and "no water sheet remaining" in events["clips"]["EP00-S03-NC03"]["beats"][0]["description"].lower(),
        "단일 곡면 물막의 연속 압박·가장자리 파열·다음 clip 부재",
    )
    audit.check(
        "ending_contract",
        "full black" in events["clips"]["EP00-S05-NC03"]["beats"][3]["description"].lower()
        and bool(re.search(
            r"before the second (?:internal )?heartbeat completes",
            events["clips"]["EP00-S05-NC03"]["outgoing_bridge"],
            re.IGNORECASE,
        )),
        "두 번째 박동 완료 전 직접 완전 암전",
    )

    contact = _write_contact_manifest(canonical)
    contact_ok = (
        contact["source_count"] == 14
        and contact["contact_sheet_size"] == [1672, 940]
        and all(row["width"] == 1672 and row["height"] == 941 for row in contact["sources"])
    )
    audit.check("contact_sheet_source_hashes", contact_ok, "14개 1672x941 원본 해시와 1672x940 접촉 시트 기록")
    return audit


def _write_reports(audit: Audit) -> None:
    payload = audit.as_dict()
    REPORT_JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rows = [
        "# EP00 H3 R2V Storyboard A/D/E V7 Locked Audit",
        "",
        f"- 결과: {'PASS' if audit.passed else 'FAIL'}",
        f"- 통과: {payload['passed_count']}/{payload['check_count']}",
        "- 큐 등록·영상 생성: 수행하지 않음",
        "",
        "| 상태 | 검사항목 | 근거 |",
        "| --- | --- | --- |",
    ]
    for row in audit.checks:
        rows.append(
            f"| {'PASS' if row['passed'] else 'FAIL'} | `{row['name']}` | {row['detail']} |"
        )
    REPORT_MD_PATH.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-status", default="pending_review")
    args = parser.parse_args()
    audit = run(args.require_status)
    _write_reports(audit)
    print(json.dumps(audit.as_dict(), ensure_ascii=False, indent=2))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
