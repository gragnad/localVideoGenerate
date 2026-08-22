from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


WIDTH = 1672
HEIGHT = 941
BACKGROUND = "#666A70"
BORDER = "#25282D"
OUTER_BORDER = 12
DIVIDER = 8
PANEL_BOUNDARIES = (12, 424, 836, 1248, 1660)

PROJECTS = (
    "RaisingaDragonSeason01_EP00_H3_R2V_V2",
    "RaisingaDragonSeason01_EP01_H3_R2V_V2",
)


def build_template() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BORDER)
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        (
            OUTER_BORDER,
            OUTER_BORDER,
            WIDTH - OUTER_BORDER - 1,
            HEIGHT - OUTER_BORDER - 1,
        ),
        fill=BACKGROUND,
    )
    half = DIVIDER // 2
    for x in PANEL_BOUNDARIES[1:-1]:
        draw.rectangle(
            (x - half, OUTER_BORDER, x + half - 1, HEIGHT - OUTER_BORDER - 1),
            fill=BORDER,
        )
    return image


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    image = build_template()
    for project_id in PROJECTS:
        destination = (
            root
            / "prompt_projects"
            / project_id
            / "assets"
            / "reference_sheets_v3"
            / "REFERENCE_SHEET_TEMPLATE_V3.png"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, format="PNG", optimize=False)


if __name__ == "__main__":
    main()
