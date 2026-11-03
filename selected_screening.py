"""Non-destructive selected-candidate playlists and human continuity notes."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import h3_queue
from job_queue import atomic_write_json, now_iso, queue_claim_lock, read_json


def scope(data: dict) -> tuple[dict, str]:
    scene = str(data.get("scene_id") or "").strip()
    if "project_ids" in data:
        incoming = data["project_ids"]
        if not isinstance(incoming, list) or not incoming or not all(isinstance(p, str) for p in incoming):
            raise ValueError("연속 시청할 프로젝트를 선택하세요.")
        projects = sorted(set(p.strip() for p in incoming))
    else:
        projects = [str(data.get("project_id") or "").strip()]
    if ("\0" in scene or len(scene) > 500
            or any(not p or "\0" in p or len(p) > 500 for p in projects)):
        raise ValueError("연속 시청할 프로젝트를 선택하세요.")
    if len(projects) == 1:
        value = {"project_id": projects[0], "scene_id": scene}
        # Preserve the existing single-project state path, without migration or overwrites.
        identity = projects[0] + "\0" + scene
    else:
        value = {"project_ids": projects, "scene_id": scene}
        identity = "multi\0" + json.dumps(value, ensure_ascii=False, sort_keys=True)
    key = hashlib.sha256(identity.encode()).hexdigest()
    return value, key


def state_path(root: Path, key: str) -> Path:
    return root / "runtime/selected_screening" / (key + ".json")


def load_state(root: Path, data: dict) -> dict:
    value, key = scope(data)
    path = state_path(root, key)
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        record = None
    if record is None:
        return {**value, "revision": 0, "order": [], "excluded": [], "issues": {}}
    if (not isinstance(record, dict) or any(record.get(k) != v for k, v in value.items())
            or not isinstance(record.get("revision"), int)
            or not isinstance(record.get("order"), list) or not isinstance(record.get("excluded"), list)
            or not isinstance(record.get("issues"), dict)):
        raise ValueError("연속 시청 기록을 확인할 수 없습니다. 기존 파일을 보존하고 복구하세요.")
    return record


def natural(value: str) -> list:
    return [(1, int(part)) if part.isdigit() else (0, part.casefold()) for part in re.split(r"(\d+)", value)]


def playlist(root: Path, data: dict) -> dict:
    value, _ = scope(data)
    paths = h3_queue.roots(root)
    candidates = [row for row in h3_queue.reconcile(root)
                  if row.get("render_purpose") != "resolution_rerender"
                  and h3_queue._candidate_selected_jobs(row)]
    projects = set(value.get("project_ids") or [value.get("project_id")])
    candidates = [row for row in candidates
                  if h3_queue._candidate_source(paths, row)[0] in projects
                  and (not value["scene_id"] or h3_queue._candidate_source(paths, row)[1] == value["scene_id"])]
    items = []
    seen = set()
    for candidate in candidates:
        for selection in h3_queue._candidate_selected_jobs(candidate):
            job_id = h3_queue._safe_id(selection["job_id"], "영상 ID")
            if job_id in seen:
                continue
            seen.add(job_id)
            request = read_json(paths["jobs"] / job_id / "request.json", {}) or {}
            available = False
            try:
                h3_queue.video_path(root, job_id)
                available = True
            except (ValueError, FileNotFoundError):
                pass
            items.append({"job_id": job_id, "candidate_set_id": candidate["candidate_set_id"],
                          "project_id": candidate.get("source_project_id") or request.get("source_project_id") or "__direct__",
                          "scene_id": candidate.get("source_scene_id") or request.get("source_scene_id") or "",
                          "clip_id": candidate.get("source_clip_id") or request.get("source_clip_id") or "",
                          "candidate_index": request.get("candidate_index"), "available": available,
                          "selected_at": selection.get("selected_at") or candidate.get("updated_at") or ""})
    # No pagination and no deduplication by clip: different versions remain visible.
    items.sort(key=lambda row: (natural(row["clip_id"]), natural(row["scene_id"]), natural(row["project_id"]),
                               natural(str(row["candidate_index"] or "")), row["selected_at"], row["job_id"]))
    return {"items": items, "review": load_state(root, value)}


def save(root: Path, data: dict) -> dict:
    value, key = scope(data)
    order, excluded, issues = data.get("order"), data.get("excluded"), data.get("issues")
    for entries in (order, excluded):
        if not isinstance(entries, list) or len(entries) > 10000 or len(set(map(str, entries))) != len(entries):
            raise ValueError("유효하지 않은 재생 순서입니다.")
        for job_id in entries:
            if not isinstance(job_id, str) or "\n" in job_id or "\0" in job_id:
                raise ValueError("유효하지 않은 영상 ID입니다.")
            h3_queue._safe_id(job_id, "영상 ID")
    if not isinstance(issues, dict) or len(issues) > 10000:
        raise ValueError("유효하지 않은 연결 검수 기록입니다.")
    cleaned = {}
    for pair, note in issues.items():
        ids = pair.split("\n")
        if len(ids) != 2 or ids[0] == ids[1] or not isinstance(note, str) or len(note) > 4000:
            raise ValueError("유효하지 않은 연결 메모입니다.")
        for job_id in ids:
            h3_queue._safe_id(job_id, "영상 ID")
        cleaned[pair] = note
    path = state_path(root, key)
    with queue_claim_lock(path.parent):
        current = load_state(root, value)
        if data.get("revision") != current["revision"]:
            return {"conflict": True, "error": "다른 화면에서 검수 기록이 변경되었습니다. 다시 불러온 뒤 수정하세요."}
        record = {**value, "revision": current["revision"] + 1, "updated_at": now_iso(),
                  "order": order, "excluded": excluded, "issues": cleaned}
        atomic_write_json(path, record)
        return record
