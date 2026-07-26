#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from video_sequence import (
    prepare_video_jpeg_sequence,
    public_sequence_summary,
)


parser = argparse.ArgumentParser(
    description="Extract temporally indexed JPEG sequence"
)
parser.add_argument("video")
args = parser.parse_args()

video = Path(args.video).expanduser().resolve()
sequence = prepare_video_jpeg_sequence(
    video,
    max_frames=int(
        os.environ.get(
            "VLLM_REVIEW_VIDEO_MAX_FRAMES",
            "32",
        )
    ),
    max_width=int(
        os.environ.get(
            "VLLM_REVIEW_VIDEO_MAX_WIDTH",
            "768",
        )
    ),
    jpeg_quality=int(
        os.environ.get(
            "VLLM_REVIEW_VIDEO_JPEG_QUALITY",
            "4",
        )
    ),
)

print(
    json.dumps(
        public_sequence_summary(sequence),
        ensure_ascii=False,
        indent=2,
    )
)
