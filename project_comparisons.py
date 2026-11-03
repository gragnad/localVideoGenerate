"""Append-only pairwise preferences, independent from production candidate selection."""
from __future__ import annotations

import json
import re
from pathlib import Path

import h3_queue
from job_queue import atomic_write_json, now_iso, queue_claim_lock, read_json


def record_path(root: Path, comparison_id: str) -> Path:
    if not isinstance(comparison_id, str) or not re.fullmatch(r"comparison_[0-9a-f]{32}", comparison_id):
        raise ValueError("유효하지 않은 비교 이력 ID입니다.")
    base = (root / "runtime/project_comparisons/records").resolve()
    target = base / f"{comparison_id}.json"
    if target.resolve().parent != base:
        raise ValueError("비교 이력 경로가 저장소 밖에 있습니다.")
    return target


def read(path: Path) -> dict | None:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(record, dict) or record.get("schema_version") != 1 or not all(k in record for k in ("comparison_id", "created_at", "left", "right", "winner", "winner_job_id")):
        raise ValueError("비교 이력이 손상되었습니다. 원본을 보존하고 복구가 필요합니다.")
    return record


def snapshot(root: Path, job_id: str) -> dict:
    job_id = h3_queue._safe_id(job_id, "영상 ID")
    paths = h3_queue.roots(root)
    folder = paths["jobs"] / job_id
    if folder.resolve().parent != paths["jobs"].resolve():
        raise ValueError("영상 경로가 저장소 밖에 있습니다.")
    request = read_json(folder / "request.json", None)
    status = read_json(folder / "status.json", {}) or {}
    if not request or status.get("status") != "completed":
        raise ValueError("양쪽 모두 완료된 후보 영상이어야 좋아요를 저장할 수 있습니다.")
    h3_queue.video_path(root, job_id)
    set_id = h3_queue._safe_id(request.get("candidate_set_id", ""), "후보군 ID")
    set_folder = paths["candidate_sets"] / set_id
    if set_folder.resolve().parent != paths["candidate_sets"].resolve():
        raise ValueError("후보군 경로가 저장소 밖에 있습니다.")
    candidate = read_json(set_folder / "candidate_set.json", {}) or {}
    if not candidate or h3_queue._candidate_set_deleted(candidate) or job_id not in candidate.get("candidate_job_ids", []):
        raise ValueError("비교할 후보군을 찾을 수 없습니다.")
    project = request.get("source_project_id") or candidate.get("source_project_id") or "직접 입력"
    return {"job_id": job_id, "candidate_set_id": set_id, "project_id": project,
            "project_name": request.get("source_project_name") or project,
            "scene_id": request.get("source_scene_id") or candidate.get("source_scene_id") or "",
            "clip_id": request.get("source_clip_id") or candidate.get("source_clip_id") or "",
            "candidate_index": request.get("candidate_index"), "seed": request.get("seed_text", request.get("seed")),
            "generation_mode": request.get("generation_mode") or candidate.get("generation_mode") or "r2v"}


def save(root: Path, data: dict) -> dict:
    path = record_path(root, data.get("comparison_id"))
    left = h3_queue._safe_id(data.get("left_job_id", ""), "왼쪽 영상 ID")
    right = h3_queue._safe_id(data.get("right_job_id", ""), "오른쪽 영상 ID")
    winner = data.get("winner")
    if winner not in ("left", "right") or left == right:
        raise ValueError("서로 다른 두 후보와 좋아요를 누른 쪽을 지정하세요.")
    with queue_claim_lock(path.parent):
        previous = read(path)
        if previous:
            if (previous["left"]["job_id"], previous["right"]["job_id"], previous["winner"]) != (left, right, winner):
                return {"conflict": True, "error": "이미 다른 비교에 사용된 이력 ID입니다."}
            return previous  # A retry after a lost response must never add another vote.
        record = {"schema_version": 1, "comparison_id": data["comparison_id"], "created_at": now_iso(),
                  "left": snapshot(root, left), "right": snapshot(root, right), "winner": winner,
                  "winner_job_id": left if winner == "left" else right}
        atomic_write_json(path, record)
        return record


def listing(root: Path, data: dict) -> dict:
    page, size = max(1, int(data.get("page", 1))), max(1, min(100, int(data.get("page_size", 20))))
    left, right = data.get("left_job_id"), data.get("right_job_id")
    if bool(left) != bool(right):
        raise ValueError("비교한 양쪽 영상 ID를 함께 지정하세요.")
    if left:
        left, right = h3_queue._safe_id(left, "영상 ID"), h3_queue._safe_id(right, "영상 ID")
    records = []
    for path in (root / "runtime/project_comparisons/records").glob("comparison_*.json"):
        item = read(path)
        if item and (not left or {item["left"]["job_id"], item["right"]["job_id"]} == {left, right}):
            records.append(item)
    records.sort(key=lambda row: (row["created_at"], row["comparison_id"]), reverse=True)
    pages = max(1, (len(records) + size - 1) // size)
    page = min(page, pages)
    return {"records": records[(page - 1) * size:page * size], "pagination": {"page": page, "total_pages": pages, "total": len(records)}}


def load(root: Path, data: dict) -> dict:
    record = read(record_path(root, data.get("comparison_id")))
    if not record:
        return {"not_found": True, "error": "비교 이력을 찾을 수 없습니다."}
    available = {}
    for side in ("left", "right"):
        try:
            h3_queue.video_path(root, record[side]["job_id"])
            available[side] = True
        except (FileNotFoundError, ValueError):
            available[side] = False
    return {**record, "available": available}
