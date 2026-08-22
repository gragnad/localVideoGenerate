from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REBUILD = ROOT / "projects" / "RaisingaDragonSeason01" / "rebuild_v2"
SPEAR = REBUILD / "designs_hq_v1" / "h3_prop_sheets" / "H3_LUA_SPEAR_PROP_HQ_V3.png"
SHELL = REBUILD / "designs_hq_v1" / "h3_prop_sheets" / "H3_MIR_SHELL_PROP_HQ_V3.png"
OUTPUT = REBUILD / "designs_hq_v1" / "review" / "H3_MAJOR_PROPS_LATEST_ONLY_CONTACT_SHEET_HQ_V3.png"


def main() -> None:
    canvas = Image.new("RGB", (1672, 471), (242, 240, 237))
    for index, path in enumerate((SPEAR, SHELL)):
        with Image.open(path) as source:
            tile = source.convert("RGB").resize((836, 471), Image.Resampling.LANCZOS)
        canvas.paste(tile, (index * 836, 0))
    canvas.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
