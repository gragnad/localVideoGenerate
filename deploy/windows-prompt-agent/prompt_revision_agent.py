from __future__ import annotations

"""Authenticated Windows HTTP wrapper for structured Codex prompt authoring."""

import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


AGENT_VERSION = "3"
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,160}$")
MAX_BODY_BYTES = 2 * 1024 * 1024


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt_variants": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "variant_id": {"type": "string", "minLength": 1},
                    "label": {"type": "string", "minLength": 1},
                    "rationale": {"type": "string", "minLength": 1},
                    "video_prompt": {"type": "string", "minLength": 1},
                },
                "required": ["variant_id", "label", "rationale", "video_prompt"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["prompt_variants"],
    "additionalProperties": False,
}


class AgentState:
    def __init__(self, state_dir: Path, token: str, codex_command: str, timeout: int):
        self.state_dir = state_dir
        self.token = token
        self.codex_command = codex_command
        self.timeout = timeout
        self.busy = False
        self.started_at = time.time()
        self.last_activity = time.monotonic()
        self.hibernate_armed = False
        self.hibernate_after = 0
        self.lock = threading.Lock()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        (self.state_dir / "results").mkdir(parents=True, exist_ok=True)

    def cache_path(self, request_id: str) -> Path:
        return self.state_dir / "results" / f"{request_id}.json"

    def arm_hibernate(self, seconds: Any) -> None:
        try:
            seconds = int(seconds)
        except (TypeError, ValueError):
            return
        if 60 <= seconds <= 3600:
            self.hibernate_after = seconds
            self.hibernate_armed = True
            self.last_activity = time.monotonic()


def _read_token(path: Path) -> str:
    token = path.read_text(encoding="utf-8").strip()
    if len(token) < 32:
        raise ValueError("Bearer token must contain at least 32 characters")
    return token


def _prompt(payload: dict[str, Any]) -> str:
    expected = payload.get("expected_variant_ids") or []
    feedback = str(payload.get("feedback") or "").strip()
    context = payload.get("clip_context") or {}
    previous_error = str(payload.get("previous_error") or "").strip()
    return f"""You are authoring three brand-new complete MiniMax H3 R2V prompts.
Return only JSON matching the supplied output schema. Do not inspect files, run commands, or use tools.

Required variant IDs in exact order: {json.dumps(expected, ensure_ascii=False)}
User direction:
{feedback}

Fresh-authoring contract:
- Do not revise, imitate, or quote an earlier prompt. No source prompts are provided.
- Use only the scenario, causal states, dialogue requirements, and Picture facts in Clip context.
- Produce exactly three independently staged, standalone full prompts. They must differ in camera evidence, action path, and time allocation, not just synonyms.
- Use exactly these six sections in order: subject_definitions, summary, retention_analysis, detailed_description, overall_soundscape, non_diegetic_music.
- Start summary with `[reference generation] ` and keep rendering/style detail out of summary.
- After zero to two concrete lighting/material sentences, detailed_description must begin `[Shot 1]`.
- Never emit `ACTION / VFX`, `CAMERA PLAN`, `CAMERA:`, `ACTION:`, LOCK blocks, independent-mode blocks, negative prompts, or background-color isolation instructions.
- In every Shot, put `<Subject N>` before that subject's name. Repeat the tag after each Shot change.
- Before every `<d>[Korean]...</d>`, identify the visible speaker as `<Subject N> (Sx)`.
- When dialogue and visible action coincide, write both in the same Shot as concurrent performance.
- One action Shot is one continuous camera setup that clearly shows preparation, whole-body execution, contact/evasion/defense, and a visible result. It may contain several fast causally linked movements.
- Do not overcut: at most 2 Shots through 6 seconds, 3 through 10 seconds, and 4 through 15 seconds.
- Do not say `the previous clip`. Restate the incoming visible state. End on the visible cause clue or persistent state required by the next clip.
- Each label and rationale must state its genuinely different directing approach.
- Do not wrap JSON in Markdown.

Clip context:
{json.dumps(context, ensure_ascii=False, indent=2)}

Previous validation or transport error to correct, if any:
{previous_error or 'None'}
"""


def _codex_prefix(command: str) -> list[str]:
    resolved = shutil.which(command) or command
    if os.name == "nt" and Path(resolved).suffix.lower() in {".cmd", ".bat"}:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", resolved]
    return [resolved]


def _run_codex(state: AgentState, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("prompt_revision_request_id") or "")
    if not REQUEST_ID_RE.fullmatch(request_id):
        raise ValueError("Invalid prompt_revision_request_id")
    expected = payload.get("expected_variant_ids")
    context = payload.get("clip_context")
    if not isinstance(expected, list) or len(expected) != 3:
        raise ValueError("expected_variant_ids must contain exactly three IDs")
    if not isinstance(context, dict) or not context:
        raise ValueError("clip_context must contain the source scenario contract")

    cached_path = state.cache_path(request_id)
    previous_error = str(payload.get("previous_error") or "").strip()
    if cached_path.is_file() and not previous_error:
        cached = json.loads(cached_path.read_text(encoding="utf-8"))
        if isinstance(cached, dict):
            cached["cached"] = True
            return cached
    elif cached_path.is_file():
        cached_path.unlink()

    with tempfile.TemporaryDirectory(prefix="h3-prompt-", dir=state.state_dir) as temp:
        temp_dir = Path(temp)
        schema_path = temp_dir / "schema.json"
        output_path = temp_dir / "output.json"
        schema_path.write_text(
            json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        command = _codex_prefix(state.codex_command) + [
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--output-schema",
            str(schema_path),
            "-o",
            str(output_path),
            "-",
        ]
        completed = subprocess.run(
            command,
            input=_prompt(payload),
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=state.state_dir,
            timeout=state.timeout,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "Codex failed").strip()
            raise RuntimeError(detail[-4000:])
        result = json.loads(output_path.read_text(encoding="utf-8"))

    variants = result.get("prompt_variants") if isinstance(result, dict) else None
    if not isinstance(variants, list) or len(variants) != 3:
        raise ValueError("Codex response must contain exactly three prompt_variants")
    if [row.get("variant_id") for row in variants if isinstance(row, dict)] != expected:
        raise ValueError("Codex response variant IDs do not match expected_variant_ids")
    response = {
        "schema_version": 1,
        "prompt_revision_request_id": request_id,
        "prompt_variants": variants,
        "agent_version": AGENT_VERSION,
        "cached": False,
    }
    temporary = cached_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(cached_path)
    return response


class Handler(BaseHTTPRequestHandler):
    server_version = "H3PromptAgent/3"

    @property
    def state(self) -> AgentState:
        return self.server.agent_state  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {self.address_string()} {format % args}")

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        supplied = self.headers.get("authorization", "")
        expected = f"Bearer {self.state.token}"
        return hmac.compare_digest(supplied, expected)

    def do_GET(self) -> None:
        if self.path != "/healthz":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        self._send(
            HTTPStatus.OK,
            {
                "status": "ok",
                "agent_version": AGENT_VERSION,
                "busy": self.state.busy,
                "started_at_epoch": self.state.started_at,
                "hibernate_armed": self.state.hibernate_armed,
            },
        )

    def do_POST(self) -> None:
        if self.path not in {
            "/v1/h3/prompt-revisions",
            "/v1/power/hibernate",
        }:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid_body_size"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if self.path == "/v1/power/hibernate":
            if payload.get("confirm") != "hibernate":
                self._send(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "confirm must equal hibernate"},
                )
                return
            with self.state.lock:
                if self.state.busy:
                    self._send(HTTPStatus.CONFLICT, {"error": "agent_busy"})
                    return
                self.state.hibernate_armed = False
            self._send(
                HTTPStatus.ACCEPTED,
                {
                    "status": "hibernate_scheduled",
                    "agent_version": AGENT_VERSION,
                    "scheduled_in_seconds": 2,
                },
            )
            self.wfile.flush()
            threading.Thread(target=_hibernate_after_response, daemon=True).start()
            return

        with self.state.lock:
            if self.state.busy:
                self._send(HTTPStatus.CONFLICT, {"error": "agent_busy"})
                return
            self.state.busy = True
        try:
            lease = payload.get("power_lease") or {}
            if isinstance(lease, dict):
                self.state.arm_hibernate(lease.get("hibernate_after_idle_seconds"))
            response = _run_codex(self.state, payload)
            self.state.last_activity = time.monotonic()
            self._send(HTTPStatus.OK, response)
        except subprocess.TimeoutExpired:
            self._send(HTTPStatus.GATEWAY_TIMEOUT, {"error": "codex_timeout"})
        except Exception as exc:
            self._send(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"{type(exc).__name__}: {str(exc)[:4000]}"},
            )
        finally:
            with self.state.lock:
                self.state.busy = False
                self.state.last_activity = time.monotonic()


def _power_monitor(state: AgentState) -> None:
    while True:
        time.sleep(5)
        with state.lock:
            should_hibernate = (
                state.hibernate_armed
                and not state.busy
                and state.hibernate_after > 0
                and time.monotonic() - state.last_activity >= state.hibernate_after
            )
            if should_hibernate:
                state.hibernate_armed = False
        if should_hibernate:
            print("Managed wake lease expired; requesting Windows hibernation", flush=True)
            subprocess.run(["shutdown.exe", "/h"], check=False)


def _hibernate_after_response() -> None:
    time.sleep(2)
    subprocess.run(["shutdown.exe", "/h"], check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default=os.environ.get("H3_PROMPT_AGENT_BIND", "100.78.202.37"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("H3_PROMPT_AGENT_PORT", "8765")))
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--codex-command", default=os.environ.get("H3_PROMPT_AGENT_CODEX", "codex"))
    parser.add_argument("--codex-timeout", type=int, default=1800)
    args = parser.parse_args()
    try:
        token = _read_token(args.token_file.resolve())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not shutil.which(args.codex_command):
        print(f"Codex command was not found: {args.codex_command}", file=sys.stderr)
        return 2

    state = AgentState(args.state_dir.resolve(), token, args.codex_command, args.codex_timeout)
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    server.agent_state = state  # type: ignore[attr-defined]
    threading.Thread(target=_power_monitor, args=(state,), daemon=True).start()
    print(f"H3 prompt agent listening on http://{args.bind}:{args.port}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
