"""Register a completed local audio file and its JSON description. Never generates music."""
import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import music_library


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True, help="Completed WAV/MP3/FLAC/OGG/M4A")
    parser.add_argument("--metadata", type=Path, required=True, help="UTF-8 JSON; see docs/MUSIC_LIBRARY.md")
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("VIDEO_ENGINE_ROOT", PROJECT_ROOT)), help="Engine root (defaults to this repository)")
    args = parser.parse_args()
    try:
        raw = json.loads(args.metadata.read_text(encoding="utf-8"))
        result = music_library.register(args.root.expanduser().resolve(), args.audio, raw)
    except Exception as error:
        parser.exit(1, f"음악 등록 실패: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
