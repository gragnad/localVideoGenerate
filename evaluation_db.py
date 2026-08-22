from __future__ import annotations

"""Model-neutral evaluation database for H3 generation experiments."""

import sqlite3
from pathlib import Path


SCHEMA_VERSION = 10
DEFAULT_DB_PATH = Path("runtime/evaluation/evaluation.db")
BUSY_TIMEOUT_MS = 30_000


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
    workflow_settings_json TEXT NOT NULL DEFAULT "{}", notes TEXT NOT NULL DEFAULT "",
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

CREATE TABLE IF NOT EXISTS test_session_lineage (
    child_session_id TEXT PRIMARY KEY REFERENCES test_sessions(session_id) ON DELETE CASCADE,
    parent_session_id TEXT NOT NULL REFERENCES test_sessions(session_id),
    reason TEXT NOT NULL DEFAULT "targeted_retest",
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_policies_model ON prompt_policies(model_id, active);
CREATE INDEX IF NOT EXISTS idx_workflow_profiles_model ON workflow_profiles(model_id, profile_kind);
CREATE INDEX IF NOT EXISTS idx_test_sessions_model ON test_sessions(model_id, created_at);
CREATE INDEX IF NOT EXISTS idx_test_session_lineage_parent ON test_session_lineage(parent_session_id);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000)
    connection.row_factory = sqlite3.Row
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
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
    if "workflow_settings_json" not in session_columns:
        migrations.append(
            "ALTER TABLE test_sessions ADD COLUMN workflow_settings_json "
            "TEXT NOT NULL DEFAULT '{}'"
        )
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
        """INSERT INTO schema_metadata(key, value) VALUES ('schema_version', ?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value
           WHERE schema_metadata.value<>excluded.value""",
        (str(SCHEMA_VERSION),),
    )
    connection.commit()
