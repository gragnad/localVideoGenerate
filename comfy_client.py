from __future__ import annotations

import json
import mimetypes
import time
import uuid
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Any

import requests


class ComfyAPIError(RuntimeError):
    pass


class ComfyClient:
    def __init__(self, base_url: str, request_timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout
        self.session = requests.Session()
        self.client_id = str(uuid.uuid4())

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def health(self) -> dict[str, Any]:
        response = self.session.get(
            self._url("/system_stats"), timeout=self.request_timeout
        )
        response.raise_for_status()
        return response.json()

    def upload_input(
        self,
        *,
        filename: str,
        content: bytes,
        subfolder: str,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        response = self.session.post(
            self._url("/upload/image"),
            files={"image": (filename, content, mime_type)},
            data={
                "type": "input",
                "subfolder": subfolder,
                "overwrite": "true" if overwrite else "false",
            },
            timeout=max(self.request_timeout, 120.0),
        )
        if not response.ok:
            raise ComfyAPIError(
                f"입력 파일 업로드 실패 ({response.status_code}): {response.text[:2000]}"
            )
        payload = response.json()
        for required in ("name", "subfolder", "type"):
            if required not in payload:
                raise ComfyAPIError(f"입력 파일 업로드 응답에 {required} 값이 없습니다: {payload}")
        return payload

    def upload_image(
        self,
        *,
        filename: str,
        content: bytes,
        subfolder: str,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        return self.upload_input(
            filename=filename,
            content=content,
            subfolder=subfolder,
            overwrite=overwrite,
        )

    def queue_prompt(self, workflow: dict[str, Any]) -> dict[str, Any]:
        payload = {"prompt": workflow, "client_id": self.client_id}
        response = self.session.post(
            self._url("/prompt"), json=payload, timeout=self.request_timeout
        )
        if not response.ok:
            raise ComfyAPIError(
                f"워크플로 제출 실패 ({response.status_code}): {response.text[:6000]}"
            )
        result = response.json()
        prompt_id = result.get("prompt_id")
        if not prompt_id:
            raise ComfyAPIError(
                "ComfyUI가 prompt_id를 반환하지 않았습니다:\n"
                + json.dumps(result, ensure_ascii=False, indent=2)[:6000]
            )
        return result

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        response = self.session.get(
            self._url(f"/history/{prompt_id}"), timeout=self.request_timeout
        )
        response.raise_for_status()
        return response.json()

    def get_queue(self) -> dict[str, Any]:
        response = self.session.get(self._url("/queue"), timeout=self.request_timeout)
        response.raise_for_status()
        return response.json()

    def wait_for_completion(
        self,
        prompt_id: str,
        *,
        timeout_seconds: float = 6 * 60 * 60,
        poll_interval: float = 2.0,
        progress_callback: Callable[[float, dict[str, Any] | None], None] | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        last_queue: dict[str, Any] | None = None

        while True:
            elapsed = time.monotonic() - started
            if elapsed > timeout_seconds:
                raise TimeoutError(
                    f"영상 생성 완료를 {timeout_seconds:.0f}초 동안 기다렸지만 끝나지 않았습니다."
                )

            history = self.get_history(prompt_id)
            if prompt_id in history:
                item = history[prompt_id]
                self._raise_on_execution_error(item)
                return history

            try:
                last_queue = self.get_queue()
            except requests.RequestException:
                last_queue = None

            if progress_callback is not None:
                progress_callback(elapsed, last_queue)
            time.sleep(poll_interval)

    @staticmethod
    def _raise_on_execution_error(history_item: dict[str, Any]) -> None:
        status = history_item.get("status") or {}
        messages = status.get("messages") or []
        for message in messages:
            if not isinstance(message, (list, tuple)) or len(message) < 2:
                continue
            if message[0] == "execution_error":
                detail = message[1]
                raise ComfyAPIError(
                    "ComfyUI 실행 중 오류가 발생했습니다:\n"
                    + json.dumps(detail, ensure_ascii=False, indent=2)[:8000]
                )
        if status.get("status_str") == "error":
            raise ComfyAPIError(
                "ComfyUI 실행 상태가 error입니다:\n"
                + json.dumps(status, ensure_ascii=False, indent=2)[:8000]
            )

    @staticmethod
    def extract_media_files(
        history: dict[str, Any],
        prompt_id: str,
        allowed_suffixes: set[str],
    ) -> list[dict[str, str]]:
        item = history.get(prompt_id, {})
        outputs = item.get("outputs", {})
        found: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                filename = value.get("filename")
                subfolder = value.get("subfolder", "")
                file_type = value.get("type", "output")
                if isinstance(filename, str):
                    suffix = PurePosixPath(filename).suffix.lower()
                    if suffix in allowed_suffixes:
                        key = (filename, str(subfolder), str(file_type))
                        if key not in seen:
                            seen.add(key)
                            found.append(
                                {
                                    "filename": filename,
                                    "subfolder": str(subfolder),
                                    "type": str(file_type),
                                }
                            )
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(outputs)
        return found

    @staticmethod
    def extract_output_files(
        history: dict[str, Any],
        prompt_id: str,
    ) -> list[dict[str, str]]:
        return ComfyClient.extract_media_files(
            history,
            prompt_id,
            {".mp4", ".webm", ".mov", ".mkv", ".avi", ".gif"},
        )

    @staticmethod
    def extract_image_files(
        history: dict[str, Any],
        prompt_id: str,
    ) -> list[dict[str, str]]:
        return ComfyClient.extract_media_files(
            history,
            prompt_id,
            {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"},
        )

    def download_file_to_path(
        self,
        file_info: dict[str, str],
        target_path: str,
    ) -> int:
        """ComfyUI output을 메모리에 전부 올리지 않고 로컬 파일로 저장합니다."""
        from pathlib import Path

        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".partial")
        written = 0

        with self.session.get(
            self._url("/view"),
            params={
                "filename": file_info["filename"],
                "subfolder": file_info.get("subfolder", ""),
                "type": file_info.get("type", "output"),
            },
            timeout=max(self.request_timeout, 600.0),
            stream=True,
        ) as response:
            response.raise_for_status()
            with temp.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    written += len(chunk)

        if written <= 0:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
            raise ComfyAPIError("ComfyUI 영상 다운로드 결과가 비어 있습니다.")

        temp.replace(target)
        return written

    def download_file(self, file_info: dict[str, str]) -> bytes:
        response = self.session.get(
            self._url("/view"),
            params={
                "filename": file_info["filename"],
                "subfolder": file_info.get("subfolder", ""),
                "type": file_info.get("type", "output"),
            },
            timeout=max(self.request_timeout, 300.0),
        )
        response.raise_for_status()
        return response.content
