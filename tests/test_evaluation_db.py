from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import evaluation_db


class EvaluationDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / evaluation_db.DEFAULT_DB_PATH

    def tearDown(self):
        self.temp.cleanup()

    def test_current_schema_is_h3_only_and_idempotent(self):
        with evaluation_db.connect(self.db_path) as connection:
            evaluation_db.initialize(connection)
            evaluation_db.initialize(connection)
            version = connection.execute(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            ).fetchone()[0]
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertEqual(str(evaluation_db.SCHEMA_VERSION), version)
        self.assertIn("test_sessions", tables)
        self.assertIn("generation_runs", tables)
        self.assertIn("reviews", tables)
        self.assertNotIn("test_session_batches", tables)
        self.assertNotIn("source_documents", tables)

    def test_existing_database_gets_required_session_columns(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            """CREATE TABLE test_sessions(
                   session_id TEXT PRIMARY KEY, suite_id TEXT, model_id TEXT,
                   workflow_profile_id TEXT, adapter_id TEXT, status TEXT,
                   repetitions INTEGER, notes TEXT, created_at TEXT, updated_at TEXT
               )"""
        )
        connection.execute(
            "CREATE TABLE test_session_cases("
            "session_id TEXT, case_version_id TEXT, ordering INTEGER, "
            "status TEXT, planned_runs INTEGER)"
        )
        connection.commit()
        connection.close()
        with evaluation_db.connect(self.db_path) as connection:
            evaluation_db.initialize(connection)
            session_columns = {
                row["name"] for row in connection.execute(
                    "PRAGMA table_info(test_sessions)"
                )
            }
            case_columns = {
                row["name"] for row in connection.execute(
                    "PRAGMA table_info(test_session_cases)"
                )
            }
        self.assertIn("output_width", session_columns)
        self.assertIn("output_height", session_columns)
        self.assertIn("workflow_settings_json", session_columns)
        self.assertIn("settings_json", case_columns)


if __name__ == "__main__":
    unittest.main()
