from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw


WIDTH = 1672
HEIGHT = 941
BACKGROUND = (102, 106, 112)
BORDER = (37, 40, 45)
OUTER_BORDER = 12
DIVIDER = 8
DIVIDERS = (424, 836, 1248)


def is_generated_background(pixel: tuple[int, int, int]) -> bool:
    distance = math.sqrt(sum((pixel[i] - BACKGROUND[i]) ** 2 for i in range(3)))
    return distance <= 22 and max(pixel) - min(pixel) <= 20


def finalize(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGB")
    if image.size != (WIDTH, HEIGHT):
        image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    pixels = image.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if is_generated_background(pixels[x, y]):
                pixels[x, y] = BACKGROUND

    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH - 1, OUTER_BORDER - 1), fill=BORDER)
    draw.rectangle((0, HEIGHT - OUTER_BORDER, WIDTH - 1, HEIGHT - 1), fill=BORDER)
    draw.rectangle((0, 0, OUTER_BORDER - 1, HEIGHT - 1), fill=BORDER)
    draw.rectangle((WIDTH - OUTER_BORDER, 0, WIDTH - 1, HEIGHT - 1), fill=BORDER)
    half = DIVIDER // 2
    for x in DIVIDERS:
        draw.rectangle((x - half, OUTER_BORDER, x + half - 1, HEIGHT - OUTER_BORDER - 1), fill=BORDER)

    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", optimize=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.destination.exists():
        raise FileExistsError(f"destination already exists: {args.destination}")
    finalize(args.source, args.destination)


if __name__ == "__main__":
    main()
