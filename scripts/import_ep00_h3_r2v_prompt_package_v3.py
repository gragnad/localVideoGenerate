from __future__ import annotations

"""Configure the direct prompt importer for the user-authored 25-clip EP00 V3 package."""

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import import_ep00_h3_r2v_prompt_package as importer  # noqa: E402


ATTACHMENT_DIR = Path(
    "/home/nalstudio/.codex/attachments/8e3bd81d-358a-4111-ae99-a6f13979aa8c"
)
SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_user_prompt_package_v3"
LIBRARY = ROOT / "projects" / "RaisingaDragonSeason01" / "asset_sheets_master_v1"
REVISION_DOCUMENT = Path(
    "/home/nalstudio/.codex/attachments/f97e22f8-ea68-429b-b03d-45e7a41e09b2/EP00_Clip_Revisions_C10_C12_C18_C19_C20.md"
)
REVISION_IDS = ("C10", "C12", "C18", "C19", "C20")
REVISION_CLIP_ASSETS = {
    "C10": ["lua", "spear", "damaged"],
    "C12": ["lua", "damaged"],
    "C18": ["lua", "final"],
    "C19": ["lua", "final"],
    "C20": ["lua", "final"],
}


def revision_prompts() -> dict[str, str]:
    text = REVISION_DOCUMENT.read_text(encoding="utf-8")
    sections = ("subject_definitions", "summary", "detailed_description", "overall_soundscape", "non_diegetic_music")
    prompts: dict[str, str] = {}
    headings = list(re.finditer(r"^## EP00_(C\d{2}) —.*$", text, re.MULTILINE))
    for index, heading in enumerate(headings):
        clip_id = heading.group(1)
        if clip_id not in REVISION_IDS:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else text.index("## Suggested Integration Notes")
        block = text[heading.end():end]
        parts = []
        for section_index, section in enumerate(sections):
            section_match = re.search(rf"^### {section}\s*$", block, re.MULTILINE)
            if not section_match:
                raise ValueError(f"Missing {section} in revision {clip_id}")
            if section_index + 1 < len(sections):
                next_match = re.search(rf"^### {sections[section_index + 1]}\s*$", block, re.MULTILINE)
                if not next_match:
                    raise ValueError(f"Missing {sections[section_index + 1]} in revision {clip_id}")
                body = block[section_match.end():next_match.start()].strip()
            else:
                body = block[section_match.end():].strip()
                body = re.sub(r"\n\n---\s*$", "", body).strip()
            parts.append(f"{section}:\n{body}")
        prompts[clip_id] = "\n\n".join(parts)
    if tuple(prompts) != REVISION_IDS:
        raise ValueError(f"Unexpected revision clips: {tuple(prompts)}")
    return prompts


def configure() -> None:
    importer.PROMPT_DOCUMENT = ATTACHMENT_DIR / "EP00_H3_R2V_Prompt_Document_V3.md"
    importer.EXECUTION_GUIDE = ATTACHMENT_DIR / "EP00_Codex_Project_Execution_Guide_V3.md"
    importer.PROJECT_ID = "RaisingaDragonSeason01_EP00_USER_H3_R2V_PACKAGE_V3"
    importer.SOURCE_DIR = SOURCE_DIR
    importer.LOCK_ID = "EP00_USER_H3_PROMPT_PACKAGE_UNCHANGED_V3"
    importer.PROJECT_TITLE = "Raising a Dragon EP00 · User H3 R2V Package V3"
    importer.PROJECT_DESCRIPTION = (
        "Direct import of twenty-five user-authored V3 camera-driven prompts with exact "
        "picture order, durations, and black-rain background phases."
    )
    importer.IMPORT_SCRIPT = "scripts/import_ep00_h3_r2v_prompt_package_v3.py"
    importer.NEW_BACKGROUND_GENERATION_COUNT = 0
    importer.REUSED_BACKGROUND_COUNT = 3
    # The V3 base import always remains the original twenty-five-clip package.
    # User revisions are added as separate versioned clips by the revision script.
    importer.ADDITIONAL_SOURCE_FILES = []
    importer.PROMPT_OVERRIDES = {}
    importer.PROMPT_SECTION_MARKER = "## 6. Complete H3 R2V Prompts"
    importer.EXPECTED_CLIP_IDS = [f"C{index:02d}" for index in range(1, 26)]
    # The generic importer expects the full prompt in one named group. V3 has
    # metadata between the clip heading and subject_definitions, so normalize
    # only the regex group boundary—not the prompt text itself.
    importer.CLIP_RE = re.compile(
        r"^### (?P<clip_id>C\d{2}) — (?P<title>.+?)\s*$\n"
        r".*?(?P<prompt>^subject_definitions:\s*\n.*?"
        r"^non_diegetic_music:\s*\n.*?)(?=\n\n---(?:\n|\Z))",
        re.MULTILINE | re.DOTALL,
    )
    importer.DURATIONS = dict(zip(
        importer.EXPECTED_CLIP_IDS,
        [7, 6, 5, 6, 5, 8, 5, 6, 5, 6, 6, 6, 6, 6, 6, 6, 5, 7, 7, 5, 4, 4, 6, 6, 6],
        strict=True,
    ))
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
        "C01": ["king", "master"],
        "C02": ["king", "lua", "master"],
        "C03": ["king", "master"],
        "C04": ["king", "master"],
        "C05": ["lua", "master"],
        "C06": ["lua", "damaged", "shield"],
        "C07": ["king", "damaged"],
        "C08": ["lua", "king", "spear", "damaged"],
        "C09": ["king", "spear", "damaged"],
        "C10": ["lua", "king", "spear", "damaged"],
        "C11": ["king", "lua", "damaged"],
        "C12": ["lua", "damaged"],
        "C13": ["lua", "damaged"],
        "C14": ["king", "damaged", "ribbon"],
        "C15": ["king", "lua", "damaged"],
        "C16": ["lua", "damaged"],
        "C17": ["king", "final"],
        "C18": ["lua", "final"],
        "C19": ["lua", "final"],
        "C20": ["lua", "final"],
        "C21": ["lua", "final"],
        "C22": ["lua", "final"],
        "C23": ["lua", "king", "final"],
        "C24": ["lua", "king", "final"],
        "C25": ["lua", "king", "final"],
    }


def main() -> int:
    configure()
    print(json.dumps(importer.build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
