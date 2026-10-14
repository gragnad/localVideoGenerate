#!/usr/bin/env python3
from __future__ import annotations

"""Hide current non-episode H3 candidates and move their output files safely.

The candidate metadata and job records remain in place. Output directories move
under a dated temporary archive, while compatibility symlinks preserve existing
video evidence paths and job playback. A manifest and pre-change candidate JSON
copies make the operation auditable and reversible.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from job_queue import atomic_write_json, now_iso, queue_claim_lock, read_json


EPISODE_ID = re.compile(r"EP0[0-3]", re.IGNORECASE)
TERMINAL = {"completed", "failed", "cancelled"}
ARCHIVE_REASON = "non_episode_asset_candidate_cleanup_20260916"


def _candidate_source_text(payload: dict[str, Any]) -> str:
    return " ".join(
        str(payload.get(key) or "")
        for key in ("source_project_id", "source_scene_id", "source_clip_id")
    )


def _selected_job_ids(payload: dict[str, Any]) -> list[str]:
    selected = payload.get("selected_jobs")
    if isinstance(selected, list):
        return [
            str(row.get("job_id") if isinstance(row, dict) else row).strip()
            for row in selected
            if str(row.get("job_id") if isinstance(row, dict) else row).strip()
        ]
    legacy = str(payload.get("selected_job_id") or "").strip()
    return [legacy] if legacy else []


def _candidate_is_target(payload: dict[str, Any]) -> bool:
    if not payload or payload.get("deleted") or payload.get("deleted_at"):
        return False
    if str(payload.get("status") or "") == "deleted":
        return False
    if payload.get("render_purpose") == "resolution_rerender":
        return False
    if payload.get("hidden_from_candidate_page"):
        return False
    return EPISODE_ID.search(_candidate_source_text(payload)) is None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _output_inventory(directory: Path) -> list[dict[str, Any]]:
    if not directory.is_dir():
        return []
    return [
        {
            "relative_path": str(path.relative_to(directory)),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    ]


def _target_candidates(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    candidate_root = root / "runtime/h3/candidate_sets"
    rows: list[tuple[Path, dict[str, Any]]] = []
    if not candidate_root.is_dir():
        return rows
    for directory in sorted(candidate_root.iterdir()):
        if not directory.is_dir():
            continue
        path = directory / "candidate_set.json"
        payload = read_json(path, {}) or {}
        if _candidate_is_target(payload):
            rows.append((path, payload))
    return rows


def _preflight(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    job_root = root / "runtime/h3/jobs"
    output_root = root / "runtime/h3/outputs"
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for candidate_path, payload in _target_candidates(root):
        set_id = str(payload.get("candidate_set_id") or candidate_path.parent.name)
        job_ids = [str(value) for value in payload.get("candidate_job_ids") or []]
        statuses = {
            job_id: str(
                (read_json(job_root / job_id / "status.json", {}) or {}).get("status")
                or "missing"
            )
            for job_id in job_ids
        }
        unfinished = [
            job_id for job_id, status in statuses.items() if status not in TERMINAL
        ]
        selected = _selected_job_ids(payload)
        output_path = output_root / set_id
        if unfinished:
            errors.append(f"{set_id}: unfinished jobs: {', '.join(unfinished)}")
        if selected:
            errors.append(f"{set_id}: selected jobs: {', '.join(selected)}")
        if not output_path.is_dir() or output_path.is_symlink():
            errors.append(f"{set_id}: movable output directory not found: {output_path}")
        rows.append({
            "candidate_set_id": set_id,
            "candidate_path": str(candidate_path),
            "source_project_id": payload.get("source_project_id"),
            "source_scene_id": payload.get("source_scene_id"),
            "source_clip_id": payload.get("source_clip_id"),
            "created_at": payload.get("created_at"),
            "candidate_job_ids": job_ids,
            "job_statuses": statuses,
            "original_output_path": str(output_path),
            "output_size_bytes": sum(
                path.stat().st_size
                for path in output_path.rglob("*")
                if path.is_file()
            ) if output_path.is_dir() else 0,
        })
    return rows, errors


def _default_archive_root(root: Path) -> Path:
    base = root / "runtime/h3/temporary"
    stem = "non_episode_asset_candidate_outputs_20260916"
    candidate = base / stem
    index = 2
    while candidate.exists():
        candidate = base / f"{stem}_v{index}"
        index += 1
    return candidate


def archive(root: Path, archive_root: Path | None, *, apply: bool) -> dict[str, Any]:
    root = root.resolve()
    archive_root = (archive_root or _default_archive_root(root)).resolve()
    rows, errors = _preflight(root)
    summary = {
        "mode": "apply" if apply else "dry_run",
        "root": str(root),
        "archive_root": str(archive_root),
        "selection_rule": (
            "current non-deleted, non-rerender candidate sets whose project, "
            "scene and clip identifiers contain none of EP00, EP01, EP02 or EP03"
        ),
        "candidate_set_count": len(rows),
        "job_count": sum(len(row["candidate_job_ids"]) for row in rows),
        "output_size_bytes": sum(row["output_size_bytes"] for row in rows),
        "preflight_errors": errors,
    }
    if not apply:
        return summary
    if errors:
        raise RuntimeError("Archive preflight failed:\n" + "\n".join(errors))
    if not rows:
        raise RuntimeError("No current non-episode candidate sets were found.")
    if archive_root.exists():
        raise FileExistsError(f"Archive path already exists: {archive_root}")

    candidate_root = root / "runtime/h3/candidate_sets"
    output_root = root / "runtime/h3/outputs"
    outputs_archive = archive_root / "outputs"
    metadata_archive = archive_root / "candidate_metadata_before"
    outputs_archive.mkdir(parents=True)
    metadata_archive.mkdir(parents=True)
    stamp = now_iso()
    manifest: dict[str, Any] = {
        **summary,
        "status": "staging",
        "created_at": stamp,
        "reason": ARCHIVE_REASON,
        "compatibility": (
            "Each original output directory is replaced by a relative symlink "
            "so existing manifests and dictionary evidence paths remain valid."
        ),
        "entries": [],
    }
    manifest_path = archive_root / "manifest.json"
    atomic_write_json(manifest_path, manifest)
    processed: list[dict[str, Any]] = []

    try:
        with queue_claim_lock(root / "runtime/h3/jobs"), queue_claim_lock(candidate_root):
            for row in rows:
                set_id = row["candidate_set_id"]
                candidate_path = Path(row["candidate_path"])
                payload = read_json(candidate_path, {}) or {}
                if not _candidate_is_target(payload):
                    raise RuntimeError(f"Candidate changed after preflight: {set_id}")
                source = output_root / set_id
                target = outputs_archive / set_id
                inventory = _output_inventory(source)
                if target.exists() or source.is_symlink() or not source.is_dir():
                    raise RuntimeError(f"Output path changed after preflight: {source}")

                backup = metadata_archive / f"{set_id}.json"
                shutil.copy2(candidate_path, backup)
                source.rename(target)
                relative_target = os.path.relpath(target, start=source.parent)
                source.symlink_to(relative_target, target_is_directory=True)

                payload.update(
                    hidden_from_candidate_page=True,
                    hidden_from_candidate_page_at=stamp,
                    hidden_from_candidate_page_reason=ARCHIVE_REASON,
                    temporary_output_archive={
                        "archive_root": str(archive_root),
                        "output_path": str(target),
                        "compatibility_symlink": str(source),
                    },
                    updated_at=stamp,
                )
                atomic_write_json(candidate_path, payload)
                entry = {
                    **row,
                    "archived_output_path": str(target),
                    "compatibility_symlink": str(source),
                    "candidate_metadata_backup": str(backup),
                    "output_files": inventory,
                }
                processed.append(entry)
                manifest["entries"] = processed
                atomic_write_json(manifest_path, manifest)
    except Exception:
        for entry in reversed(processed):
            source = Path(entry["original_output_path"])
            target = Path(entry["archived_output_path"])
            backup = Path(entry["candidate_metadata_backup"])
            if source.is_symlink():
                source.unlink()
            if target.is_dir() and not source.exists():
                target.rename(source)
            if backup.is_file():
                shutil.copy2(backup, Path(entry["candidate_path"]))
        manifest.update(status="rolled_back", rolled_back_at=now_iso())
        atomic_write_json(manifest_path, manifest)
        raise

    manifest.update(
        status="complete",
        completed_at=now_iso(),
        archived_candidate_set_count=len(processed),
        archived_job_count=sum(len(row["candidate_job_ids"]) for row in processed),
        archived_file_count=sum(len(row["output_files"]) for row in processed),
        archived_bytes=sum(
            file_row["size_bytes"]
            for row in processed
            for file_row in row["output_files"]
        ),
    )
    atomic_write_json(manifest_path, manifest)
    return {
        key: manifest[key]
        for key in (
            "status", "archive_root", "archived_candidate_set_count",
            "archived_job_count", "archived_file_count", "archived_bytes",
        )
    }


def restore(root: Path, archive_root: Path) -> dict[str, Any]:
    root = root.resolve()
    archive_root = archive_root.resolve()
    manifest_path = archive_root / "manifest.json"
    manifest = read_json(manifest_path, {}) or {}
    if manifest.get("status") != "complete":
        raise RuntimeError("Only a complete archive can be restored.")
    entries = list(manifest.get("entries") or [])
    candidate_root = root / "runtime/h3/candidate_sets"
    restored = 0
    with queue_claim_lock(root / "runtime/h3/jobs"), queue_claim_lock(candidate_root):
        for entry in reversed(entries):
            source = Path(entry["original_output_path"])
            target = Path(entry["archived_output_path"])
            backup = Path(entry["candidate_metadata_backup"])
            if not source.is_symlink():
                raise RuntimeError(f"Compatibility symlink is missing: {source}")
            if not target.is_dir() or not backup.is_file():
                raise RuntimeError(f"Archive entry is incomplete: {entry['candidate_set_id']}")
            source.unlink()
            target.rename(source)
            shutil.copy2(backup, Path(entry["candidate_path"]))
            restored += 1
    manifest.update(status="restored", restored_at=now_iso())
    atomic_write_json(manifest_path, manifest)
    return {"status": "restored", "restored_candidate_set_count": restored}


def verify(root: Path, archive_root: Path) -> dict[str, Any]:
    root = root.resolve()
    archive_root = archive_root.resolve()
    manifest = read_json(archive_root / "manifest.json", {}) or {}
    if manifest.get("status") != "complete":
        raise RuntimeError("Only a complete archive can be verified.")
    entries = list(manifest.get("entries") or [])
    errors: list[str] = []
    checked_files = 0
    checked_bytes = 0
    checked_jobs = 0
    for entry in entries:
        set_id = str(entry.get("candidate_set_id") or "")
        candidate_path = Path(str(entry.get("candidate_path") or ""))
        payload = read_json(candidate_path, {}) or {}
        source = Path(str(entry.get("original_output_path") or ""))
        target = Path(str(entry.get("archived_output_path") or ""))
        if payload.get("hidden_from_candidate_page") is not True:
            errors.append(f"{set_id}: candidate-page hidden flag missing")
        recorded_archive = dict(payload.get("temporary_output_archive") or {})
        if recorded_archive.get("archive_root") != str(archive_root):
            errors.append(f"{set_id}: candidate archive root mismatch")
        if not source.is_symlink():
            errors.append(f"{set_id}: compatibility symlink missing")
        elif source.resolve() != target.resolve():
            errors.append(f"{set_id}: compatibility symlink target mismatch")
        if not target.is_dir():
            errors.append(f"{set_id}: archived output directory missing")
            continue
        checked_jobs += len(entry.get("candidate_job_ids") or [])
        for file_row in entry.get("output_files") or []:
            path = target / str(file_row.get("relative_path") or "")
            if not path.is_file():
                errors.append(f"{set_id}: archived file missing: {path.name}")
                continue
            size = path.stat().st_size
            expected_size = int(file_row.get("size_bytes") or -1)
            if size != expected_size:
                errors.append(f"{set_id}: size mismatch: {path.name}")
                continue
            if _sha256(path) != str(file_row.get("sha256") or ""):
                errors.append(f"{set_id}: sha256 mismatch: {path.name}")
                continue
            checked_files += 1
            checked_bytes += size
    expected_sets = int(manifest.get("archived_candidate_set_count") or -1)
    expected_jobs = int(manifest.get("archived_job_count") or -1)
    expected_files = int(manifest.get("archived_file_count") or -1)
    expected_bytes = int(manifest.get("archived_bytes") or -1)
    if len(entries) != expected_sets:
        errors.append("manifest candidate-set count mismatch")
    if checked_jobs != expected_jobs:
        errors.append("manifest job count mismatch")
    if checked_files != expected_files:
        errors.append("manifest file count mismatch")
    if checked_bytes != expected_bytes:
        errors.append("manifest byte count mismatch")
    return {
        "status": "pass" if not errors else "fail",
        "archive_root": str(archive_root),
        "candidate_set_count": len(entries),
        "job_count": checked_jobs,
        "verified_file_count": checked_files,
        "verified_bytes": checked_bytes,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--archive-root", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restore", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if sum(bool(value) for value in (args.apply, args.restore, args.verify)) > 1:
        parser.error("--apply, --restore and --verify are mutually exclusive")
    if args.restore:
        result = restore(args.root, args.restore)
    elif args.verify:
        result = verify(args.root, args.verify)
    else:
        result = archive(args.root, args.archive_root, apply=args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
