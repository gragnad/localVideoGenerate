from __future__ import annotations

"""Fail-closed audit for the approved EP00/EP01 storyboard A/D/E prompt project."""

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


REBUILD = ROOT / "projects" / "RaisingaDragonSeason01" / "rebuild_v2"
PROJECT_ID = "RaisingaDragonSeason01_EP00_EP01_H3_R2V_STORYBOARD_ADE_V2"
PROJECT_DIR = ROOT / "prompt_projects" / PROJECT_ID
LOCK_PATH = REBUILD / "EP00_EP01_STORYBOARD_PRODUCTION_LOCK_V1.json"
SPEC_PATH = REBUILD / "EP00_EP01_H3_R2V_STORYBOARD_ADE_V2_SPEC.json"
EVENTS_PATH = REBUILD / "EP00_EP01_H3_R2V_STORYBOARD_ADE_V2_EVENT_CONTRACTS.json"
APPROVAL_PATH = REBUILD / "EP00_EP01_STORYBOARD_APPROVAL_RECORD_20260817.md"
ORDINALS = ("first", "second", "third", "fourth")
GRID_TERMS_RE = re.compile(
    r"\b(?:2x2|grid|quadrant|top-left|top-right|bottom-left|bottom-right|panel)\b",
    re.IGNORECASE,
)
EXPECTED_DIALOGUE = {
    "EP01-S01-C04": ["돌아오면 조용해진다."],
    "EP01-S02-C04": ["수심 확인이었어"],
    "EP01-S02-C05": ["돌아올 때도 잡을 수 있게 쥐어라."],
    "EP01-S02-C07": ["가지 말라면 안 가야 하는데."],
    "EP01-S02-C08": ["저렇게 못 부르는 애는 내가 가야지."],
    "EP01-S03-C03": ["도마뱀은 아니지?"],
    "EP01-S03-C05": ["알았어. 안 놓을게"],
    "EP01-S04-C06": ["오늘은 혼자 한 일이 아니구나"],
    "EP01-S04-C08": ["입맛도 귀족이네"],
    "EP01-S04-C09": ["미르", "미르", "싫으면 나중에 바꿔."],
    "EP01-S05-C02": ["너까지 훈련시키는 거야?"],
}
DIALOGUE_CLIPS_WITH_LISTENERS = set(EXPECTED_DIALOGUE) - {
    "EP01-S02-C07",
    "EP01-S02-C08",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"PNG header is invalid: {path}")
    return struct.unpack(">II", header[16:24])


class Audit:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, passed: bool, detail: str) -> None:
        self.checks.append({"name": name, "passed": bool(passed), "detail": detail})

    @property
    def passed(self) -> bool:
        return all(row["passed"] for row in self.checks)

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "project_id": PROJECT_ID,
            "passed": self.passed,
            "check_count": len(self.checks),
            "passed_count": sum(1 for row in self.checks if row["passed"]),
            "failed_count": sum(1 for row in self.checks if not row["passed"]),
            "checks": self.checks,
        }


def run() -> Audit:
    audit = Audit()
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    events = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    manifest = json.loads((PROJECT_DIR / "manifest.json").read_text(encoding="utf-8"))
    approval = APPROVAL_PATH.read_text(encoding="utf-8")
    overview = h3_prompt_projects.project_clips(ROOT, PROJECT_ID)
    clips = overview["clips"]
    clips_by_id = {row["clip_id"]: row for row in clips}

    asset_rows = [*lock["ep00_assets"], *lock["ep01_assets"]]
    expected_ids = [row["clip_id"] for row in asset_rows]
    actual_ids = [row["clip_id"] for row in sorted(clips, key=lambda row: row["sequence"])]
    audit.check(
        "approved_scope_and_order",
        len(asset_rows) == 56
        and len(lock["ep00_assets"]) == 14
        and len(lock["ep01_assets"]) == 42
        and actual_ids == expected_ids,
        f"EP00={len(lock['ep00_assets'])}, EP01={len(lock['ep01_assets'])}, project={len(clips)}",
    )

    storyboard_ok = True
    storyboard_copy_ok = True
    for row in asset_rows:
        source = REBUILD / row["path"]
        storyboard_ok &= (
            source.is_file()
            and png_size(source) == (int(row["width"]), int(row["height"]))
            and int(row["panels"]) == 4
            and sha256(source) == row["sha256"]
        )
        clip = clips_by_id[row["clip_id"]]
        storyboard_refs = [ref for ref in clip["references"] if ref["reference_kind"] == "storyboard"]
        storyboard_copy_ok &= (
            len(storyboard_refs) == 1
            and storyboard_refs[0]["picture_index"] == len(clip["references"])
            and sha256(PROJECT_DIR / storyboard_refs[0]["source_path"]) == row["sha256"]
        )
    audit.check("storyboard_lock_integrity", storyboard_ok, "56/56 PNG size, panel count and SHA-256 match production lock")
    audit.check("storyboard_project_copy_integrity", storyboard_copy_ok, "Each clip uses its locked storyboard as the final Picture reference")

    expected_role_hashes = {
        row["role"]: sha256(REBUILD / row["copy_from"])
        for row in spec["asset_catalog"].values()
        if row.get("reference_kind") != "storyboard"
    }
    active_reference_hashes_ok = True
    for clip in clips:
        for reference in clip["references"]:
            if reference["reference_kind"] == "storyboard":
                continue
            active_reference_hashes_ok &= (
                reference["role"] in expected_role_hashes
                and sha256(PROJECT_DIR / reference["source_path"])
                == expected_role_hashes[reference["role"]]
            )
    audit.check(
        "active_reference_hashes",
        active_reference_hashes_ok,
        "Every copied character and major-prop Picture matches the active source asset hash",
    )

    prompt_count = sum(len(row["prompt_variants"]) for row in clips)
    total = sum(float(row["duration_seconds"]) for row in clips)
    ep00_total = sum(float(row["duration_seconds"]) for row in clips if row["clip_id"].startswith("EP00-"))
    ep01_total = sum(float(row["duration_seconds"]) for row in clips if row["clip_id"].startswith("EP01-"))
    audit.check(
        "counts_and_duration",
        len(clips) == 56 and prompt_count == 168 and total == 574.0 and ep00_total == 133.0 and ep01_total == 441.0,
        f"clips={len(clips)}, prompts={prompt_count}, total={total:g}s, EP00={ep00_total:g}s, EP01={ep01_total:g}s",
    )
    audit.check("all_clips_ready", all(row["ready"] for row in clips), f"ready={sum(1 for row in clips if row['ready'])}/56")
    audit.check(
        "no_queue_or_video_side_effect",
        all(manifest.get(key) is False for key in (
            "queue_authorized",
            "video_generation_authorized",
            "queue_registration_performed",
            "video_generation_performed",
        )),
        "Queue registration and video generation remain unauthorized and unperformed",
    )
    audit.check(
        "explicit_user_approval_record",
        "스토리 보드 작성을 이어준 다음 프롬포트 작성까지 진행" in approval
        and "총 56장의 제작 스토리보드를 H3 A/D/E 프롬프트 변환 입력으로 승인" in approval,
        APPROVAL_PATH.name,
    )

    contract_ok = True
    variants_ok = True
    four_shot_ok = True
    anchor_ok = True
    grid_free_shots_ok = True
    camera_semantics_ok = True
    refs_ok = True
    official_warnings: list[str] = []
    unresolved: list[str] = []
    production_id_hits: list[str] = []
    grammar_hits: list[str] = []
    descriptions: list[str] = []
    dialogue_contract_ok = True
    dialogue_speaker_listener_ok = True
    dialogue_tag_count = 0
    for clip in clips:
        clip_id = clip["clip_id"]
        expected_dialogue = EXPECTED_DIALOGUE.get(clip_id, [])
        dialogue_contract_ok &= clip.get("required_dialogue", []) == expected_dialogue
        variants = clip["prompt_variants"]
        variants_ok &= [row["variant_id"] for row in variants] == ["A", "D", "E"]
        refs_ok &= 1 <= len(clip["references"]) <= 9
        storyboard_ref = next(ref for ref in clip["references"] if ref["reference_kind"] == "storyboard")
        picture_id = storyboard_ref["picture_index"]
        for variant in variants:
            prompt = variant["video_prompt"]
            detail = variant["detailed_description"]
            descriptions.append(detail)
            dialogue_rows = h3_prompt_contract.DIALOGUE_RE.findall(prompt)
            actual_dialogue = [line.strip() for _language, line in dialogue_rows]
            dialogue_tag_count += len(dialogue_rows)
            dialogue_contract_ok &= actual_dialogue == expected_dialogue
            dialogue_contract_ok &= all(
                language.strip() == "Korean" for language, _line in dialogue_rows
            )
            report = h3_prompt_contract.validate_prompt(prompt, duration_seconds=float(clip["duration_seconds"]))
            contract_ok &= report.valid
            official_warnings.extend(
                f"{clip_id}/{variant['variant_id']}:{issue.code}"
                for issue in report.warnings
            )
            shots = list(h3_prompt_contract.SHOT_RE.finditer(detail))
            four_shot_ok &= len(shots) == 4
            for number, shot in enumerate(shots, start=1):
                body = shot.group(4)
                anchor_ok &= (
                    f"<Picture {picture_id}>" in body
                    and f"{ORDINALS[number - 1]} planned composition" in body.lower()
                )
                grid_free_shots_ok &= not bool(GRID_TERMS_RE.search(body))
                marker = {
                    "A": "baseline camera treatment",
                    "D": "controlled spatial camera movement within this shot",
                    "E": "action-responsive camera movement within this shot",
                }[variant["variant_id"]]
                camera_semantics_ok &= marker in body.lower()
                if h3_prompt_contract.DIALOGUE_RE.search(body):
                    dialogue_speaker_listener_ok &= bool(
                        h3_prompt_contract.SPEAKER_RE.search(body)
                    )
                    if clip_id in DIALOGUE_CLIPS_WITH_LISTENERS:
                        dialogue_speaker_listener_ok &= "closed and react" in body.lower()
            if re.search(r"\[[A-Z][A-Z0-9_-]*\]", prompt):
                unresolved.append(f"{clip_id}/{variant['variant_id']}")
            if re.search(
                r"\b(?:EP|SC)\d{2}(?:-[A-Z0-9]+)*\b|\b(?:Scene|Clip)\s+\d+\b|\bClip\b",
                prompt,
                re.IGNORECASE,
            ):
                production_id_hits.append(f"{clip_id}/{variant['variant_id']}")
            if any(fragment in prompt for fragment in (
                "approved approved storyboard composition",
                "the single the single",
                "one the single spear",
                "single the single spear",
                "same the single shell",
            )):
                grammar_hits.append(f"{clip_id}/{variant['variant_id']}")
        raw_path = ROOT / "prompt_projects" / clip["markdown_path"]
        payload = h3_prompt_projects.extract_payload(raw_path.read_text(encoding="utf-8"))
        beat_text = json.dumps(
            next(ref for ref in payload["references"] if ref["reference_kind"] == "storyboard").get("storyboard_beats"),
            ensure_ascii=False,
        )
        if re.search(r"\[[A-Z][A-Z0-9_-]*\]", beat_text):
            unresolved.append(f"{clip_id}/storyboard_beats")
    audit.check("official_h3_contract", contract_ok, "168/168 prompts pass the official six-section and timing contract")
    audit.check("official_h3_warnings", not official_warnings, f"hits={official_warnings}")
    audit.check("candidate_contract", variants_ok, "56/56 clips contain exactly A, D and E")
    audit.check("four_compositions_four_shots", four_shot_ok, "168/168 prompts use four planned storyboard compositions as four ordered Shots")
    audit.check("storyboard_composition_anchors", anchor_ok, "672/672 Shots name the storyboard Picture and their ordered planned composition")
    audit.check("no_grid_terms_inside_shots", grid_free_shots_ok, "2x2, grid, quadrant and panel-position terms occur only in the Picture definition")
    audit.check("candidate_camera_semantics", camera_semantics_ok, "A=baseline, D=smooth spatial movement, E=action-responsive movement in all 672 Shots")
    canonical_dialogue = re.findall(
        r"“([^”]+)”",
        (REBUILD / "EP01_NARRATIVE_SCREENPLAY_V2.md").read_text(encoding="utf-8"),
    )
    expected_canonical_dialogue = [
        line
        for lines in EXPECTED_DIALOGUE.values()
        for line in lines
        if line != "미르"
    ]
    audit.check(
        "canonical_ep01_dialogue_coverage",
        expected_canonical_dialogue == canonical_dialogue,
        f"canonical={len(canonical_dialogue)}, mapped={len(expected_canonical_dialogue)}",
    )
    audit.check(
        "required_dialogue_exact_match",
        dialogue_contract_ok and dialogue_tag_count == 39,
        f"11 dialogue Clips, 13 events × A/D/E, tags={dialogue_tag_count}",
    )
    audit.check(
        "dialogue_speaker_and_listener_control",
        dialogue_speaker_listener_ok,
        "Every line has an explicit speaker; visible listeners keep closed mouths and react nonverbally",
    )
    audit.check("reference_limit", refs_ok, "All clips use 1-9 references")
    audit.check("no_unresolved_tokens", not unresolved, f"hits={unresolved}")
    audit.check("no_production_ids_inside_prompt", not production_id_hits, f"hits={production_id_hits}")
    audit.check("no_known_replacement_grammar_errors", not grammar_hits, f"hits={grammar_hits}")
    audit.check("candidate_descriptions_unique", len(descriptions) == len(set(descriptions)) == 168, f"unique={len(set(descriptions))}/168")

    event_rows = events["clips"]
    bridge_ok = True
    storyboard_event_ok = True
    for index, clip_id in enumerate(expected_ids):
        event = event_rows[clip_id]
        storyboard_event_ok &= (
            event["storyboard_required"] is True
            and event["storyboard_panel_count"] == 4
            and [row["beat_id"] for row in event["beats"]] == ["P1", "P2", "P3", "P4"]
        )
        if index:
            previous = event_rows[expected_ids[index - 1]]
            bridge_ok &= previous["bridge_out_id"] == event["bridge_in_id"]
    bridge_ok &= event_rows[expected_ids[-1]]["boundary_policy"] == "terminal"
    audit.check("event_storyboard_contract", storyboard_event_ok, "56/56 event contracts lock four ordered storyboard beats")
    audit.check("bridge_chain", bridge_ok, "All 55 internal boundaries chain exactly; the final clip holds a terminal warning state")

    spec_ids = [row["clip_id"] for row in sorted(spec["clips"], key=lambda row: row["sequence"])]
    audit.check(
        "spec_manifest_lineage",
        spec["project_id"] == PROJECT_ID
        and manifest["project_id"] == PROJECT_ID
        and spec_ids == expected_ids
        and manifest.get("prompt_contract_version") == h3_prompt_contract.CONTRACT_VERSION
        and manifest.get("candidate_semantics") == h3_prompt_projects.EVENT_CONTRACT_VERSION
        and manifest.get("locked_rule_id") == spec.get("locked_rule_id"),
        "Spec, event contracts, prompt Markdown and manifest share one project lineage",
    )
    return audit


def main() -> int:
    audit = run()
    print(json.dumps(audit.payload(), ensure_ascii=False, indent=2))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
