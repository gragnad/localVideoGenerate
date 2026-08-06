from __future__ import annotations

"""Model-neutral evaluation database for generated media experiments.

The existing candidate review JSON files remain the durable source documents.
This module imports them into SQLite without modifying or deleting the originals.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 8
DEFAULT_DB_PATH = Path("runtime/evaluation/evaluation.db")
DEFAULT_REVIEW_GLOB = "runtime/candidate_reviews/entries/*.json"

LEGACY_MODEL_ID = "legacy_ltx_2_3_msr_v2"
LEGACY_RUNTIME_ID = "legacy_unknown_runtime"


DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS models (
    model_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    family TEXT NOT NULL,
    display_name TEXT NOT NULL,
    version TEXT,
    modality TEXT NOT NULL DEFAULT 'video',
    checkpoint_sha256 TEXT,
    source_url TEXT,
    license_name TEXT,
    capabilities_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_runtimes (
    runtime_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL REFERENCES models(model_id),
    engine TEXT NOT NULL,
    engine_version TEXT,
    dtype TEXT,
    quantization TEXT,
    device_profile TEXT,
    runtime_config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS benchmark_cases (
    case_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    intent_ko TEXT NOT NULL DEFAULT '',
    intent_json TEXT NOT NULL DEFAULT '{}',
    category TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    source_kind TEXT NOT NULL DEFAULT 'native',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    path TEXT,
    sha256 TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_variants (
    prompt_variant_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES benchmark_cases(case_id),
    model_id TEXT NOT NULL REFERENCES models(model_id),
    adapter_name TEXT,
    adapter_version TEXT,
    global_prompt TEXT NOT NULL DEFAULT '',
    prompt_json TEXT NOT NULL DEFAULT '{}',
    content_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generation_runs (
    run_id TEXT PRIMARY KEY,
    job_id TEXT UNIQUE,
    case_id TEXT NOT NULL REFERENCES benchmark_cases(case_id),
    model_id TEXT NOT NULL REFERENCES models(model_id),
    runtime_id TEXT NOT NULL REFERENCES model_runtimes(runtime_id),
    prompt_variant_id TEXT REFERENCES prompt_variants(prompt_variant_id),
    workflow_kind TEXT,
    workflow_filename TEXT,
    workflow_sha256 TEXT,
    seed_text TEXT,
    seed_mode TEXT,
    width INTEGER,
    height INTEGER,
    fps REAL,
    frame_count INTEGER,
    duration_seconds REAL,
    generation_seconds REAL,
    peak_gpu_memory_bytes INTEGER,
    peak_system_memory_bytes INTEGER,
    status TEXT NOT NULL DEFAULT 'unknown',
    settings_json TEXT NOT NULL DEFAULT '{}',
    output_path TEXT,
    output_sha256 TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS run_assets (
    run_id TEXT NOT NULL REFERENCES generation_runs(run_id) ON DELETE CASCADE,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    role TEXT NOT NULL,
    slot INTEGER,
    ordering INTEGER,
    PRIMARY KEY (run_id, asset_id, role, ordering)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_version_id TEXT PRIMARY KEY,
    review_lineage_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    run_id TEXT NOT NULL REFERENCES generation_runs(run_id),
    reviewer_kind TEXT NOT NULL DEFAULT 'human',
    verdict TEXT NOT NULL,
    positive_note TEXT NOT NULL DEFAULT '',
    overall_note TEXT NOT NULL DEFAULT '',
    created_at TEXT,
    updated_at TEXT,
    source_sha256 TEXT NOT NULL,
    source_path TEXT NOT NULL,
    UNIQUE (review_lineage_id, revision)
);

CREATE TABLE IF NOT EXISTS review_issues (
    review_version_id TEXT NOT NULL REFERENCES reviews(review_version_id) ON DELETE CASCADE,
    issue_id TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    severity TEXT NOT NULL,
    start_seconds REAL,
    end_seconds REAL,
    expected TEXT NOT NULL DEFAULT '',
    observed TEXT NOT NULL DEFAULT '',
    difference_text TEXT NOT NULL DEFAULT '',
    cause_hypothesis TEXT NOT NULL DEFAULT '',
    suggestion TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (review_version_id, issue_id)
);

CREATE TABLE IF NOT EXISTS capability_scores (
    score_id TEXT PRIMARY KEY,
    review_version_id TEXT NOT NULL REFERENCES reviews(review_version_id),
    dimension TEXT NOT NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 5),
    evidence TEXT NOT NULL DEFAULT '',
    UNIQUE (review_version_id, dimension)
);

CREATE TABLE IF NOT EXISTS prompt_policies (
    policy_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL REFERENCES models(model_id),
    dimension TEXT,
    rule_text TEXT NOT NULL,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    confidence TEXT NOT NULL DEFAULT 'experimental',
    evidence_json TEXT NOT NULL DEFAULT '[]',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_policy_scopes (
    policy_id TEXT PRIMARY KEY REFERENCES prompt_policies(policy_id) ON DELETE CASCADE,
    workflow_profile_id TEXT REFERENCES workflow_profiles(workflow_profile_id)
);

CREATE TABLE IF NOT EXISTS source_documents (
    source_sha256 TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    entity_id TEXT,
    import_status TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_runs_case_model ON generation_runs(case_id, model_id);
CREATE INDEX IF NOT EXISTS idx_reviews_run ON reviews(run_id);
CREATE INDEX IF NOT EXISTS idx_issues_category ON review_issues(category, subcategory);
CREATE TABLE IF NOT EXISTS benchmark_suites (
    suite_id TEXT PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL,
    description TEXT NOT NULL DEFAULT "", tier TEXT NOT NULL DEFAULT "diagnostic",
    definition_sha256 TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE (name, version)
);
CREATE TABLE IF NOT EXISTS benchmark_case_versions (
    case_version_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES benchmark_cases(case_id),
    version INTEGER NOT NULL, title TEXT NOT NULL, intent_ko TEXT NOT NULL, category TEXT NOT NULL,
    tier TEXT NOT NULL, contract_json TEXT NOT NULL, definition_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE (case_id, version)
);
CREATE TABLE IF NOT EXISTS suite_cases (
    suite_id TEXT NOT NULL REFERENCES benchmark_suites(suite_id) ON DELETE CASCADE,
    case_version_id TEXT NOT NULL REFERENCES benchmark_case_versions(case_version_id),
    ordering INTEGER NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (suite_id, case_version_id), UNIQUE (suite_id, ordering)
);
CREATE TABLE IF NOT EXISTS workflow_profiles (
    workflow_profile_id TEXT PRIMARY KEY, model_id TEXT NOT NULL REFERENCES models(model_id),
    name TEXT NOT NULL, profile_kind TEXT NOT NULL, workflow_filename TEXT NOT NULL,
    workflow_path TEXT NOT NULL, workflow_sha256 TEXT NOT NULL, workflow_format TEXT NOT NULL,
    defaults_json TEXT NOT NULL DEFAULT "{}", source_url TEXT, notes TEXT NOT NULL DEFAULT "",
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE (model_id, profile_kind, workflow_sha256)
);
CREATE TABLE IF NOT EXISTS workflow_adapters (
    adapter_id TEXT PRIMARY KEY, workflow_profile_id TEXT NOT NULL REFERENCES workflow_profiles(workflow_profile_id),
    adapter_name TEXT NOT NULL, adapter_version TEXT NOT NULL, config_json TEXT NOT NULL DEFAULT "{}",
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE (workflow_profile_id, adapter_name, adapter_version)
);
CREATE TABLE IF NOT EXISTS test_sessions (
    session_id TEXT PRIMARY KEY, suite_id TEXT NOT NULL REFERENCES benchmark_suites(suite_id),
    model_id TEXT NOT NULL REFERENCES models(model_id),
    workflow_profile_id TEXT NOT NULL REFERENCES workflow_profiles(workflow_profile_id),
    adapter_id TEXT REFERENCES workflow_adapters(adapter_id), status TEXT NOT NULL DEFAULT "planned",
    repetitions INTEGER NOT NULL DEFAULT 1, output_width INTEGER, output_height INTEGER,
    notes TEXT NOT NULL DEFAULT "",
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS test_session_cases (
    session_id TEXT NOT NULL REFERENCES test_sessions(session_id) ON DELETE CASCADE,
    case_version_id TEXT NOT NULL REFERENCES benchmark_case_versions(case_version_id),
    ordering INTEGER NOT NULL, status TEXT NOT NULL DEFAULT "planned", planned_runs INTEGER NOT NULL DEFAULT 1,
    settings_json TEXT NOT NULL DEFAULT "{}",
    PRIMARY KEY (session_id, case_version_id)
);
CREATE TABLE IF NOT EXISTS test_session_runs (
    session_id TEXT NOT NULL REFERENCES test_sessions(session_id) ON DELETE CASCADE,
    case_version_id TEXT NOT NULL REFERENCES benchmark_case_versions(case_version_id),
    run_id TEXT NOT NULL REFERENCES generation_runs(run_id), repetition INTEGER NOT NULL,
    PRIMARY KEY (session_id, case_version_id, repetition), UNIQUE (run_id)
);

CREATE TABLE IF NOT EXISTS benchmark_case_prompts (
    case_version_id TEXT NOT NULL REFERENCES benchmark_case_versions(case_version_id),
    language TEXT NOT NULL, prompt_kind TEXT NOT NULL DEFAULT "canonical",
    prompt_text TEXT NOT NULL, prompt_sha256 TEXT NOT NULL,
    PRIMARY KEY (case_version_id, language, prompt_kind)
);
CREATE TABLE IF NOT EXISTS benchmark_case_asset_requirements (
    case_version_id TEXT NOT NULL REFERENCES benchmark_case_versions(case_version_id),
    role TEXT NOT NULL, kind TEXT NOT NULL, minimum_count INTEGER NOT NULL DEFAULT 1,
    description TEXT NOT NULL DEFAULT "", PRIMARY KEY (case_version_id, role)
);
CREATE TABLE IF NOT EXISTS benchmark_case_assets (
    case_version_id TEXT NOT NULL REFERENCES benchmark_case_versions(case_version_id) ON DELETE CASCADE,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id), role TEXT NOT NULL, ordering INTEGER NOT NULL DEFAULT 1,
    linked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (case_version_id, role, ordering),
    UNIQUE (case_version_id, asset_id, role)
);

CREATE TABLE IF NOT EXISTS adapter_preflights (
    preflight_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES test_sessions(session_id) ON DELETE CASCADE,
    adapter_id TEXT NOT NULL REFERENCES workflow_adapters(adapter_id), status TEXT NOT NULL,
    ready_count INTEGER NOT NULL, blocked_count INTEGER NOT NULL, report_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_session_batches (
    session_id TEXT PRIMARY KEY REFERENCES test_sessions(session_id) ON DELETE CASCADE,
    batch_id TEXT NOT NULL UNIQUE,
    queued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_session_lineage (
    child_session_id TEXT PRIMARY KEY REFERENCES test_sessions(session_id) ON DELETE CASCADE,
    parent_session_id TEXT NOT NULL REFERENCES test_sessions(session_id),
    reason TEXT NOT NULL DEFAULT "targeted_retest",
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_policies_model ON prompt_policies(model_id, active);
CREATE INDEX IF NOT EXISTS idx_workflow_profiles_model ON workflow_profiles(model_id, profile_kind);
CREATE INDEX IF NOT EXISTS idx_test_sessions_model ON test_sessions(model_id, created_at);
CREATE INDEX IF NOT EXISTS idx_test_session_batches_batch ON test_session_batches(batch_id);
CREATE INDEX IF NOT EXISTS idx_test_session_lineage_parent ON test_session_lineage(parent_session_id);
"""


@dataclass
class ImportReport:
    scanned: int = 0
    imported: int = 0
    unchanged: int = 0
    conflicts: int = 0
    failed: int = 0
    messages: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scanned": self.scanned,
            "imported": self.imported,
            "unchanged": self.unchanged,
            "conflicts": self.conflicts,
            "failed": self.failed,
            "messages": list(self.messages),
        }


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(DDL)
    session_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(test_sessions)")
    }
    migrations = []
    if "output_width" not in session_columns:
        migrations.append("ALTER TABLE test_sessions ADD COLUMN output_width INTEGER")
    if "output_height" not in session_columns:
        migrations.append("ALTER TABLE test_sessions ADD COLUMN output_height INTEGER")
    session_case_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(test_session_cases)")
    }
    if "settings_json" not in session_case_columns:
        migrations.append("ALTER TABLE test_session_cases ADD COLUMN settings_json TEXT NOT NULL DEFAULT '{}'")
    for statement in migrations:
        try:
            connection.execute(statement)
        except sqlite3.OperationalError as exc:
            # Multiple UI API subprocesses can initialize the same DB at once.
            # Another process may add the column after our PRAGMA snapshot.
            if "duplicate column name" not in str(exc).lower():
                raise
    connection.execute(
        "INSERT OR REPLACE INTO schema_metadata(key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    connection.commit()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _content_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:24]}"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _legacy_case_id(payload: dict[str, Any]) -> str:
    candidate_set_id = str(payload.get("candidate_set_id") or "").strip()
    if candidate_set_id:
        return f"legacy_case_{candidate_set_id}"
    return _content_id("legacy_case", {
        "intent": (payload.get("generation_snapshot") or {}).get("review_intent_ko", ""),
        "review_id": payload.get("review_id", ""),
    })


def _prompt_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "global_prompt": str(snapshot.get("global_prompt") or ""),
        "segments": list(snapshot.get("segments") or []),
        "relay_segments": list(snapshot.get("relay_segments") or []),
        "prompt_strategy": str(snapshot.get("prompt_strategy") or ""),
    }


def _ensure_legacy_profile(connection: sqlite3.Connection) -> None:
    connection.execute(
        """INSERT OR IGNORE INTO models(
               model_id, provider, family, display_name, version, capabilities_json
           ) VALUES (?, ?, ?, ?, ?, ?)""",
        (
            LEGACY_MODEL_ID,
            "Lightricks",
            "LTX-Video",
            "LTX 2.3 MSR V2 (legacy import)",
            "2.3",
            _canonical_json({"metadata_completeness": "legacy_partial"}),
        ),
    )
    connection.execute(
        """INSERT OR IGNORE INTO model_runtimes(
               runtime_id, model_id, engine, runtime_config_json
           ) VALUES (?, ?, ?, ?)""",
        (
            LEGACY_RUNTIME_ID,
            LEGACY_MODEL_ID,
            "unknown",
            _canonical_json({"metadata_completeness": "legacy_unknown"}),
        ),
    )


def _validate_review(payload: dict[str, Any]) -> tuple[str, int, str]:
    review_id = str(payload.get("review_id") or "").strip()
    if not review_id:
        raise ValueError("review_id is missing")
    try:
        revision = int(payload.get("revision") or 1)
    except (TypeError, ValueError) as exc:
        raise ValueError("revision is invalid") from exc
    if revision < 1:
        raise ValueError("revision must be at least 1")
    job_id = str(payload.get("job_id") or "").strip()
    if not job_id:
        raise ValueError("job_id is missing")
    issues = payload.get("issues") or []
    if not isinstance(issues, list):
        raise ValueError("issues must be a list")
    return review_id, revision, job_id


def _import_one(
    connection: sqlite3.Connection,
    path: Path,
    payload: dict[str, Any],
    source_sha256: str,
) -> str:
    review_id, revision, job_id = _validate_review(payload)
    review_version_id = f"{review_id}@{revision}"
    existing = connection.execute(
        "SELECT source_sha256 FROM reviews WHERE review_lineage_id = ? AND revision = ?",
        (review_id, revision),
    ).fetchone()
    if existing:
        return "unchanged" if existing["source_sha256"] == source_sha256 else "conflict"

    snapshot = dict(payload.get("generation_snapshot") or {})
    case_id = _legacy_case_id(payload)
    intent_ko = str(snapshot.get("review_intent_ko") or "")
    prompt_payload = _prompt_payload(snapshot)
    prompt_variant_id = _content_id("prompt", {
        "case_id": case_id,
        "model_id": LEGACY_MODEL_ID,
        **prompt_payload,
    })
    run_id = f"legacy_run_{job_id}"
    resolution = dict(snapshot.get("resolution") or {})

    connection.execute(
        """INSERT OR IGNORE INTO benchmark_cases(
               case_id, title, intent_ko, intent_json, source_kind
           ) VALUES (?, ?, ?, ?, 'legacy_candidate_set')""",
        (
            case_id,
            str(payload.get("candidate_set_id") or job_id),
            intent_ko,
            _canonical_json({"candidate_set_id": payload.get("candidate_set_id")}),
        ),
    )
    connection.execute(
        """INSERT OR IGNORE INTO prompt_variants(
               prompt_variant_id, case_id, model_id, adapter_name, adapter_version,
               global_prompt, prompt_json, content_sha256
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            prompt_variant_id,
            case_id,
            LEGACY_MODEL_ID,
            str(snapshot.get("prompt_strategy") or "legacy_unknown"),
            None,
            str(snapshot.get("global_prompt") or ""),
            _canonical_json(prompt_payload),
            prompt_variant_id.removeprefix("prompt_"),
        ),
    )
    settings = {
        "snapshot_schema": "candidate_review_v1",
        "segments": list(snapshot.get("segments") or []),
        "relay_segments": list(snapshot.get("relay_segments") or []),
        "unavailable_fields": [
            "checkpoint_sha256",
            "engine_version",
            "dtype",
            "quantization",
            "sampler",
            "scheduler",
            "steps",
            "guidance",
            "generation_seconds",
            "peak_gpu_memory_bytes",
            "peak_system_memory_bytes",
        ],
    }
    connection.execute(
        """INSERT OR IGNORE INTO generation_runs(
               run_id, job_id, case_id, model_id, runtime_id, prompt_variant_id,
               workflow_kind, workflow_filename, workflow_sha256, seed_text,
               seed_mode, width, height, fps, settings_json
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            job_id,
            case_id,
            LEGACY_MODEL_ID,
            LEGACY_RUNTIME_ID,
            prompt_variant_id,
            str(snapshot.get("workflow_kind") or ""),
            str(snapshot.get("workflow_filename") or ""),
            str(snapshot.get("workflow_sha256") or ""),
            None if snapshot.get("seed") is None else str(snapshot.get("seed")),
            str(snapshot.get("seed_mode") or ""),
            resolution.get("width"),
            resolution.get("height"),
            snapshot.get("fps"),
            _canonical_json(settings),
        ),
    )
    connection.execute(
        """INSERT INTO reviews(
               review_version_id, review_lineage_id, revision, run_id, verdict,
               positive_note, overall_note, created_at, updated_at,
               source_sha256, source_path
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            review_version_id,
            review_id,
            revision,
            run_id,
            str(payload.get("verdict") or "unrated"),
            str(payload.get("positive_note") or ""),
            str(payload.get("overall_note") or ""),
            str(payload.get("created_at") or ""),
            str(payload.get("updated_at") or ""),
            source_sha256,
            str(path),
        ),
    )
    for index, raw_issue in enumerate(payload.get("issues") or [], 1):
        issue = dict(raw_issue or {})
        issue_id = str(issue.get("issue_id") or f"issue_{index:02d}")
        connection.execute(
            """INSERT INTO review_issues(
                   review_version_id, issue_id, category, subcategory, severity,
                   start_seconds, end_seconds, expected, observed, difference_text,
                   cause_hypothesis, suggestion
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                review_version_id,
                issue_id,
                str(issue.get("category") or "other"),
                str(issue.get("subcategory") or "unspecified"),
                str(issue.get("severity") or "major"),
                issue.get("start_seconds"),
                issue.get("end_seconds"),
                str(issue.get("expected") or ""),
                str(issue.get("observed") or ""),
                str(issue.get("difference") or ""),
                str(issue.get("cause_hypothesis") or ""),
                str(issue.get("suggestion") or ""),
            ),
        )
    connection.execute(
        """INSERT INTO source_documents(
               source_sha256, source_path, source_kind, entity_id, import_status
           ) VALUES (?, ?, 'candidate_review_json', ?, 'imported')""",
        (source_sha256, str(path), review_version_id),
    )
    return "imported"


def import_candidate_reviews(
    connection: sqlite3.Connection,
    paths: Iterable[Path],
) -> ImportReport:
    """Import review snapshots transactionally, preserving every source file."""
    initialize(connection)
    _ensure_legacy_profile(connection)
    report = ImportReport()
    for path in sorted(Path(item) for item in paths):
        report.scanned += 1
        try:
            source_sha256 = _file_sha256(path)
            known = connection.execute(
                "SELECT import_status FROM source_documents WHERE source_sha256 = ?",
                (source_sha256,),
            ).fetchone()
            if known and known["import_status"] == "imported":
                report.unchanged += 1
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            with connection:
                outcome = _import_one(connection, path, payload, source_sha256)
            if outcome == "imported":
                report.imported += 1
            elif outcome == "conflict":
                report.conflicts += 1
                report.messages.append(f"conflict: {path}")
            else:
                report.unchanged += 1
        except (OSError, json.JSONDecodeError, ValueError, sqlite3.Error) as exc:
            report.failed += 1
            report.messages.append(f"failed: {path}: {exc}")
    connection.commit()
    return report


def import_from_root(root: Path, db_path: Path | None = None) -> ImportReport:
    target = db_path or (root / DEFAULT_DB_PATH)
    paths = (root / "runtime/candidate_reviews/entries").glob("*.json")
    with connect(target) as connection:
        return import_candidate_reviews(connection, paths)
