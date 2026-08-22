from __future__ import annotations

"""Configure the direct prompt importer for the user-authored EP00 V2 package."""

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import import_ep00_h3_r2v_prompt_package as importer  # noqa: E402


ATTACHMENT_DIR = Path(
    "/home/nalstudio/.codex/attachments/b3c93179-9ed8-436d-877f-4578cb48967c"
)
SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_user_prompt_package_v2"
LIBRARY = ROOT / "projects" / "RaisingaDragonSeason01" / "asset_sheets_master_v1"


def configure() -> None:
    importer.PROMPT_DOCUMENT = ATTACHMENT_DIR / "EP00_H3_R2V_Prompt_Document_V2.md"
    importer.EXECUTION_GUIDE = ATTACHMENT_DIR / "EP00_Codex_Project_Execution_Guide_V2.md"
    importer.PROJECT_ID = "RaisingaDragonSeason01_EP00_USER_H3_R2V_PACKAGE_V2"
    importer.SOURCE_DIR = SOURCE_DIR
    importer.LOCK_ID = "EP00_USER_H3_PROMPT_PACKAGE_UNCHANGED_V2"
    importer.PROJECT_TITLE = "Raising a Dragon EP00 · User H3 R2V Package V2"
    importer.PROJECT_DESCRIPTION = (
        "Direct import of thirteen user-authored V2 prompts with V2 guide asset order, "
        "clip durations, and black-rain continuity backgrounds."
    )
    importer.IMPORT_SCRIPT = "scripts/import_ep00_h3_r2v_prompt_package_v2.py"
    importer.NEW_BACKGROUND_GENERATION_COUNT = 2
    importer.REUSED_BACKGROUND_COUNT = 1
    importer.PROMPT_SECTION_MARKER = "# 13. Complete H3 R2V Prompts"
    importer.CLIP_RE = re.compile(
        r"^## (?P<clip_id>C\d{2}) — (?P<title>.+?)\s*$\n\n"
        r"(?P<prompt>subject_definitions:\n.*?^non_diegetic_music:\n.*?)(?=\n\n---(?:\n|\Z))",
        re.MULTILINE | re.DOTALL,
    )
    importer.DURATIONS = {
        "C01": 7.0,
        "C02": 6.0,
        "C03": 6.0,
        "C04": 10.0,
        "C05": 7.0,
        "C06": 8.0,
        "C07": 10.0,
        "C08": 8.0,
        "C09": 7.0,
        "C10": 10.0,
        "C11": 10.0,
        "C12": 7.0,
        "C13": 6.0,
    }
    importer.ASSETS = {
        "lua": LIBRARY / "01_characters/H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2.png",
        "king": LIBRARY / "02_enemies/H3_ABYSS_KING_IDENTITY_HQ_V2.png",
        "spear": LIBRARY / "03_props/H3_LUA_SPEAR_PROP_HQ_V3.png",
        "shield": LIBRARY / "05_effects/EP00/Current_Shield_IRREGULAR_CURVED_REFERENCE_SHEET_V4.png",
        "ribbon": LIBRARY / "05_effects/EP00/Moving_Current_Ribbon_REFERENCE_SHEET_V3.png",
        "master": SOURCE_DIR / "generated_backgrounds/BG_EP00_S01_ABYSS_ALTAR_MASTER.png",
        "damaged": SOURCE_DIR / "generated_backgrounds/BG_EP00_S01_ABYSS_ALTAR_DAMAGED.png",
        "final": SOURCE_DIR / "generated_backgrounds/BG_EP00_S01_ABYSS_ALTAR_FINAL_DAMAGE.png",
    }
    importer.CLIP_ASSETS = {
        "C01": ["lua", "king", "spear", "master"],
        "C02": ["lua", "king", "spear", "master"],
        "C03": ["lua", "king", "spear", "master"],
        "C04": ["lua", "king", "spear", "master", "shield"],
        "C05": ["lua", "king", "spear", "damaged"],
        "C06": ["lua", "king", "spear", "damaged"],
        "C07": ["lua", "king", "damaged"],
        "C08": ["lua", "king", "damaged", "ribbon"],
        "C09": ["lua", "king", "damaged"],
        "C10": ["lua", "king", "damaged"],
        "C11": ["lua", "king", "damaged"],
        "C12": ["lua", "king", "final"],
        "C13": ["lua", "king", "final"],
    }


def main() -> int:
    configure()
    print(json.dumps(importer.build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
