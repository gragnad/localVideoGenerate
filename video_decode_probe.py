#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import sys
from pathlib import Path


path = Path(sys.argv[1])
result = {
    "path": str(path),
    "exists": path.is_file(),
    "size_bytes": path.stat().st_size if path.is_file() else 0,
    "pyav": {},
    "opencv_path": {},
    "opencv_bytes": {},
}

if not path.is_file():
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(2)

try:
    import av

    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        frame = next(container.decode(video=0), None)
        result["pyav"] = {
            "ok": frame is not None,
            "codec": getattr(
                stream.codec_context,
                "name",
                None,
            ),
            "width": getattr(stream, "width", None),
            "height": getattr(stream, "height", None),
            "average_rate": (
                str(stream.average_rate)
                if stream.average_rate
                else None
            ),
        }
except Exception as exc:
    result["pyav"] = {
        "ok": False,
        "error": f"{type(exc).__name__}: {exc}",
    }

try:
    import cv2

    cap = cv2.VideoCapture(str(path))
    result["opencv_path"] = {
        "ok": bool(cap.isOpened()),
        "frame_count": int(
            cap.get(cv2.CAP_PROP_FRAME_COUNT)
        ),
        "fps": float(cap.get(cv2.CAP_PROP_FPS)),
    }
    cap.release()
except Exception as exc:
    result["opencv_path"] = {
        "ok": False,
        "error": f"{type(exc).__name__}: {exc}",
    }

try:
    import cv2
    import cv2.videoio_registry as vr

    data = path.read_bytes()
    backend = None
    for candidate in vr.getStreamBufferedBackends():
        if not vr.hasBackend(candidate):
            continue
        backend = candidate
        break

    cap = cv2.VideoCapture(io.BytesIO(data), backend, [])
    result["opencv_bytes"] = {
        "ok": bool(cap.isOpened()),
        "selected_backend": backend,
        "frame_count": int(
            cap.get(cv2.CAP_PROP_FRAME_COUNT)
        ),
        "fps": float(cap.get(cv2.CAP_PROP_FPS)),
    }
    cap.release()
except Exception as exc:
    result["opencv_bytes"] = {
        "ok": False,
        "error": f"{type(exc).__name__}: {exc}",
    }

print(json.dumps(result, ensure_ascii=False, indent=2))

if not result["pyav"].get("ok"):
    raise SystemExit(1)
