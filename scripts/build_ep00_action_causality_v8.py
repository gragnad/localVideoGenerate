from __future__ import annotations

"""Build EP00 V8 from the V2 action-causality screenplay and V2 locked rules."""

import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_project_builder


EPISODE_DIR = ROOT / "projects" / "RaisingaDragonSeason01"
LOCK_PATH = EPISODE_DIR / "EP00_LOCKED_PRODUCTION_RULES_V2.json"
CANONICAL_PATH = EPISODE_DIR / "EP00_CANONICAL_CLIPS_V2.json"
EVENTS_PATH = EPISODE_DIR / "EP00_H3_R2V_ACTION_CAUSALITY_V8_EVENT_CONTRACTS.json"
SPEC_PATH = EPISODE_DIR / "EP00_H3_R2V_ACTION_CAUSALITY_V8_SPEC.json"
PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_ACTION_CAUSALITY_V8"
EVENT_VERSION = "locked_storyboard_shot_plans_v3"
POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")


def clip(
    scene: str,
    name: str,
    source: str,
    duration: float,
    storyboard: str,
    summary: str,
    panels: list[str],
    cameras: list[str],
    motions: list[str],
    *,
    spear: bool = True,
) -> dict[str, Any]:
    return {
        "scene": scene,
        "clip": name,
        "source": source,
        "duration": duration,
        "storyboard": storyboard,
        "summary": summary,
        "panels": panels,
        "cameras": cameras,
        "motions": motions,
        "has_spear": spear,
        "spear_shots": [1, 2, 3, 4] if spear else [],
    }


CLIPS: tuple[dict[str, Any], ...] = (
    clip(
        "EP00-S01", "EP00-S01-NC01", "EP00-S01-SH01", 7.5,
        "EP00-S01-NC01_STORYBOARD_16X9_V5.png",
        "A moving reveal establishes the single circular chamber, Lua, the three-times-taller Abyss King, and the first rotation of his attacking shoulder.",
        [
            "A low rush over the cyan floor channel reveals <Subject 1> Lua screen-left and <Subject 2> AbyssKing screen-right on one floor line at a one-to-three height ratio.",
            "A lateral move beside <Subject 1> Lua shows her two-hand physical spear grip and upward opponent eyeline while <Subject 2> AbyssKing remains full-height in depth.",
            "From behind <Subject 2> AbyssKing's shoulder, <Subject 1> Lua holds ground and raises the physical spear point toward him without looking at the lens.",
            "<Subject 2> AbyssKing's bright eyes remain on <Subject 1> Lua as his right shoulder makes its first forward rotation and both hands remain attached and visible.",
        ],
        [
            "A low wide moving master emphasizes the circular channel, shared floor line, and exact scale.",
            "A lateral medium-long keeps the full King behind Lua's determined spear grip.",
            "A compressed low over-King-shoulder view makes Lua's refusal to retreat readable.",
            "An intimidating three-quarter eye-and-shoulder close view ends on the first attack cue.",
        ],
        ["foreground channel rush and Lua grip", "Lua's raised spear and opponent eyeline", "the King's eye-line dropping into his rotating right shoulder"],
    ),
    clip(
        "EP00-S01", "EP00-S01-NC02", "EP00-S01-SH02", 6.5,
        "EP00-S01-NC02_STORYBOARD_16X9_V7.png",
        "The King's shoulder rotation opens his right arm into a real swing while Lua predicts the path and compresses into an evasive launch.",
        [
            "<Subject 2> AbyssKing continues the same right-shoulder rotation with his whole right arm and <Subject 1> Lua aligned along one diagonal.",
            "The same right elbow opens and the attached hand spreads into a horizontal attack lane aimed at <Subject 1> Lua.",
            "<Subject 1> Lua's eyes track shoulder to elbow to palm as her wrist mark pulses once and she pulls the physical spear close.",
            "<Subject 1> Lua compresses both knees and lowers the spear parallel to her body while <Subject 2> AbyssKing accelerates the right arm into a true sweep.",
        ],
        [
            "A close diagonal holds the rotating shoulder, complete arm, and distant Lua together.",
            "A fast arm-axis tracking view travels from elbow to spreading fingertips.",
            "A sharp Lua three-quarter close-up retains the incoming hand as background threat.",
            "A low side action-wide shows both full-body launch mechanics on the same axis.",
        ],
        ["shoulder rotation traveling down the complete arm", "opening fingers driving focus to Lua's tracking eyes", "Lua's dropping spear and compressed knees against the accelerating sweep"],
    ),
    clip(
        "EP00-S02", "EP00-S02-NC01", "EP00-S02-SH03", 8.5,
        "EP00-S02-NC01_STORYBOARD_16X9_V5.png",
        "The King launches and sweeps his right arm; Lua jumps clear, lands into one combat roll, and retargets his torso.",
        [
            "<Subject 2> AbyssKing fully extends the right arm from his shoulder and begins a horizontal sweep at <Subject 1> Lua's former height as she launches from the floor.",
            "<Subject 1> Lua is airborne outside and above the sweeping forearm with knees tucked and the physical spear parallel to her body; the attached hand misses.",
            "The missed arm drives a broad water-and-dust pressure wake while <Subject 1> Lua lands shoulder-first and begins one continuous combat roll with the spear protected close.",
            "<Subject 1> Lua finishes the roll on one knee, turns sharply toward <Subject 2> AbyssKing's torso, and aligns the spear point while his arm completes the miss behind her.",
        ],
        [
            "A wide side action view preserves the shoulder origin, sweep lane, and Lua's launch.",
            "A dramatic low angle isolates Lua clearing the complete forearm in midair.",
            "A diagonal ground-level track follows landing, pressure wake, and the first half of the roll.",
            "An over-Lua-shoulder low medium-wide resolves the roll and immediate torso retarget.",
        ],
        ["horizontal arm sweep under Lua's airborne body", "Lua's descent and the missed-arm pressure wake", "the rolling spear shaft turning into the torso sightline"],
    ),
    clip(
        "EP00-S02", "EP00-S02-NC02", "EP00-S02-SH04", 9.5,
        "EP00-S02-NC02_STORYBOARD_16X9_V5.png",
        "Lua sprints into a torso strike, the King catches the wooden shaft once, and he lifts the still-gripping Lua off the floor with it.",
        [
            "<Subject 1> Lua explodes from the one-knee landing and sprints three hard steps toward <Subject 2> AbyssKing's torso with the spear pulled back.",
            "<Subject 1> Lua drives the stone spear point into the side of the black-liquid torso; the surface ripples strongly but is not cut or wounded.",
            "<Subject 2> AbyssKing's left hand clamps the wooden shaft at its middle while <Subject 1> Lua keeps both hands on the rear shaft and her feet begin leaving the floor.",
            "<Subject 2> AbyssKing lifts the captured spear overhead with the same left hand; <Subject 1> Lua hangs fully airborne from its rear with both hands and both feet off the floor.",
        ],
        [
            "A low forward track follows all three sprint steps from the finished roll.",
            "An aggressive side medium-wide shows the exact torso contact and surface reaction.",
            "A tight shaft-line view proves the left-hand clamp, Lua's two-hand grip, and rising feet.",
            "A dramatic low wide restores full bodies, lifted spear, airborne Lua, and exact scale.",
        ],
        ["Lua's sprint wake reaching the torso contact", "the torso ripple pulling focus to the left-hand shaft clamp", "the captured shaft rising until Lua's feet clear the floor"],
    ),
    clip(
        "EP00-S02", "EP00-S02-NC03", "EP00-S02-SH05", 9.5,
        "EP00-S02-NC03_STORYBOARD_16X9_V5.png",
        "The King throws and releases Lua with the spear; she reorients, performs one breakfall, retains the spear, and raises one shield against the next palm.",
        [
            "<Subject 2> AbyssKing rotates torso and left shoulder to throw the captured spear and <Subject 1> Lua together sideways, then releases the shaft.",
            "<Subject 1> Lua and the released physical spear travel on one low arc as she pulls it close and rotates her body toward a safe landing; neither King hand touches it.",
            "<Subject 1> Lua lands shoulder-and-side first and completes one breakfall roll while retaining the same spear.",
            "<Subject 1> Lua rises on one knee and forms one transparent irregular curved water sheet with her left hand while retaining the spear; <Subject 2> AbyssKing's new right open palm approaches just before contact.",
        ],
        [
            "A wide rotating view reads the King's torso throw and exact release moment.",
            "A tilted lateral track follows Lua and spear together through the low airborne arc.",
            "A ground-level view follows shoulder contact through one complete breakfall.",
            "A strong frontal three-quarter holds the single new shield and incoming attached palm.",
        ],
        ["the released spear-and-Lua airborne arc", "Lua's body rotation descending into the breakfall", "the roll wake rising into one curved shield before the next palm"],
    ),
    clip(
        "EP00-S03", "EP00-S03-NC01", "EP00-S03-SH06", 10.5,
        "EP00-S03-NC01_STORYBOARD_16X9_V5.png",
        "The incoming right palm bends Lua's shield; she rotates and redirects it, changes position, and faces the King's descending left hand.",
        [
            "<Subject 2> AbyssKing's right open palm hits the center of the one curved water sheet and bends it deeply toward <Subject 1> Lua, who keeps the spear in her right hand.",
            "<Subject 1> Lua side-steps around the floor channel and rotates torso and left arm to tilt the same shield while the palm remains in contact.",
            "The right palm slides off the curved surface in directional droplets as <Subject 1> Lua moves two full steps through the opened lane with her spear.",
            "<Subject 2> AbyssKing retracts the missed right arm without touching the spear and begins dropping the attached left hand from above to block <Subject 1> Lua's new route.",
        ],
        [
            "A side medium-wide makes palm contact, shield curvature, spear, and both bodies readable.",
            "A high oblique action view maps Lua's side-step and shield-angle change.",
            "A low track follows the redirected palm wake and Lua's two-step relocation.",
            "A wide re-establish shows the recovered right arm and descending left-hand threat.",
        ],
        ["shield compression rolling into Lua's side-step", "directional droplets carrying the missed right palm aside", "Lua's two-step travel revealing the descending left hand"],
    ),
    clip(
        "EP00-S03", "EP00-S03-NC02", "EP00-S03-SH07", 10.5,
        "EP00-S03-NC02_STORYBOARD_16X9_V5.png",
        "Lua turns the same shield to the left-hand pressure, slides, pivots on the spear butt, and suffers edge-first shield damage while the right arm winds up.",
        [
            "<Subject 1> Lua turns the same one curved shield toward <Subject 2> AbyssKing's descending left hand while her spear points toward a side escape lane.",
            "The left palm presses the shield upper edge with shoulder and torso weight, sliding <Subject 1> Lua backward across the cyan channel with the spear retained.",
            "<Subject 1> Lua plants the spear butt briefly as a pivot and rotates sideways while keeping the same shield between herself and the left hand; the King never touches the spear.",
            "The shield outer edge tears first into a long droplet spray while its thin center remains connected; <Subject 2> AbyssKing pulls the right arm back for one final strike.",
        ],
        [
            "A diagonal action-wide shows the shield turn and the chosen escape lane.",
            "A low profile makes upper-edge pressure, sliding feet, and bowed sheet unmistakable.",
            "An overhead action view maps the spear-butt pivot and whole-body rotation.",
            "A contact-height close-wide isolates edge-first tearing and the distant right-arm windup.",
        ],
        ["the shield turn meeting the descending left palm", "Lua's backward slide reaching the planted spear-butt pivot", "the pivoting shield rim peeling into droplets before the right-arm windup"],
    ),
    clip(
        "EP00-S03", "EP00-S03-NC03", "EP00-S03-SH08", 9.5,
        "EP00-S03-NC03_STORYBOARD_16X9_V5.png",
        "The King's final right-palm swing tears the weakened shield apart, drives Lua backward without grabbing her spear, and she brakes with its point.",
        [
            "<Subject 2> AbyssKing swings the attached right arm from shoulder and torso toward the already damaged one shield while <Subject 1> Lua braces behind it with the spear cross-body.",
            "The open right palm hits and the water sheet tears from its broken outer edge inward into large droplets without an energy flash.",
            "Residual force drives <Subject 1> Lua backward through droplets toward the central dais as she blocks with spear and scaled forearms; <Subject 2> AbyssKing does not grab the spear.",
            "<Subject 1> Lua jams the spear point diagonally into wet stone to stop her slide, lowers one knee, and raises her head toward the advancing <Subject 2> AbyssKing; no shield remains.",
        ],
        [
            "A dramatic low wide shows the full shoulder-to-palm final swing.",
            "An extreme side impact view isolates edge-to-center water breakup and force direction.",
            "A long lateral track follows Lua's displacement through the droplet field.",
            "A low result-wide shows the diagonal spear brake, skid wake, and changed distance.",
        ],
        ["the right-arm swing compressing the damaged sheet", "the edge-to-center droplet burst driving Lua laterally", "Lua's skid wake converging at the spear-tip brake"],
    ),
    clip(
        "EP00-S04", "EP00-S04-NC01", "EP00-S04-SH09", 8.5,
        "EP00-S04-NC01_STORYBOARD_16X9_V5.png",
        "Lua springs up, evades a rising right-hand sweep and a descending left-hand route closure, then turns into her dragon-word setup.",
        [
            "<Subject 1> Lua uses the spear as a lever to spring from one knee while reading <Subject 2> AbyssKing's advancing right shoulder.",
            "The right hand sweeps upward from low and <Subject 1> Lua throws her full body sideways with the spear vertical to evade the water-pressure path.",
            "The left hand drops to close the route, but <Subject 1> Lua lands and immediately slides low between the two attached hands with the spear flat along her body.",
            "<Subject 1> Lua plants both feet facing <Subject 2> AbyssKing and draws her wrist mark near her chest for one nonverbal breath while he turns both arms toward her.",
        ],
        [
            "A low track follows the spear-lever rise and the King's right-shoulder cue.",
            "A dynamic tilted full-body view shows the upward miss and Lua's lateral flight.",
            "A ground-skimming wide tracks the immediate landing slide between both hands.",
            "A circular medium-wide resolves Lua's turn, wrist placement, and King's two-arm response.",
        ],
        ["the spear-lever rise entering the upward right-hand wake", "Lua's airborne body descending into the low escape slide", "the slide spray curving into Lua's planted dragon-word stance"],
    ),
    clip(
        "EP00-S04", "EP00-S04-NC02", "EP00-S04-SH10", 9.5,
        "EP00-S04-NC02_STORYBOARD_16X9_V5.png",
        "Lua expands one dragon-word water pattern, slows the King's body for one breath, sprints along his arm, and coils into her final thrust.",
        [
            "<Subject 1> Lua releases one brief forceful nonverbal exhale and a blue-white horizontal water-surface geometry expands from her feet across the chamber floor.",
            "The single pattern passes beneath <Subject 2> AbyssKing and visibly slows both arms, torso surface, and suspended droplets for one breath.",
            "<Subject 1> Lua sprints outside the slowed right arm toward the torso centerline with a bright physical water wake and the spear pulled back.",
            "<Subject 1> Lua plants the final foot, coils legs, hips, shoulders and both hands, and aligns the physical spear at <Subject 2> AbyssKing's chest before the thrust.",
        ],
        [
            "A close-to-wide expansion follows the water geometry from Lua across the circular floor.",
            "A huge overhead-oblique shows the complete slowed King inside the effect scale.",
            "A low fast track races beside Lua along the outside of the slowed arm.",
            "An aggressive side medium-wide compresses the planted full-body thrust preparation.",
        ],
        ["the expanding floor geometry reaching the King's slowed body", "suspended droplets opening a lane beside the right arm", "Lua's sprint wake terminating at the deeply planted final foot"],
    ),
    clip(
        "EP00-S04", "EP00-S04-NC03", "EP00-S04-SH11", 10.5,
        "EP00-S04-NC03_STORYBOARD_16X9_V5.png",
        "Lua executes the full thrust; the King catches the shaft once, redirects Lua with the other palm, releases the spear, and leaves her grounded.",
        [
            "<Subject 1> Lua drives rear foot, hips, shoulders and both arms into one straight spear extension toward <Subject 2> AbyssKing's chest with a displaced-water wake.",
            "As the dragon-word effect ends, <Subject 2> AbyssKing's right hand catches the wooden shaft once and stops the stone point short of his chest while <Subject 1> Lua keeps pushing.",
            "The attached left open palm redirects <Subject 1> Lua's scaled forearms and the spear laterally in one forceful push while the right hand releases the shaft.",
            "<Subject 1> Lua lands on one hand and one knee as the intact spear rolls just outside immediate reach; all blue effects are dark and <Subject 2> AbyssKing remains upright.",
        ],
        [
            "An explosive low side wide shows the whole kinetic chain and thrust wake.",
            "A tight shaft-axis view proves the right-hand catch and stopped point.",
            "A wider force-direction view shows the left-palm redirection and right-hand release together.",
            "A low aftermath wide holds Lua's ground contacts, separate spear, and unchanged King.",
        ],
        ["the thrust wake converging at the right-hand shaft catch", "the left-palm lateral redirection carrying Lua and spear across frame", "the released spear rolling away as Lua reaches the one-hand-one-knee landing"],
    ),
    clip(
        "EP00-S05", "EP00-S05-NC01", "EP00-S05-SH12", 7.5,
        "EP00-S05-NC01_STORYBOARD_16X9_V6.png",
        "Lua fails to rise, confirms her wrist and spear are unavailable, and faces the single approaching King.",
        [
            "A floor-level view holds <Subject 1> Lua on one hand and one knee, the intact spear outside reach, and exactly one complete <Subject 2> AbyssKing in the middle background.",
            "<Subject 1> Lua tries to rise with her planted foot and arm but fatigue makes her settle back down as the same complete King moves slightly closer.",
            "<Subject 1> Lua checks the dark inactive wrist and then the spear while exactly one <Subject 2> AbyssKing remains connected and nearer in depth.",
            "<Subject 1> Lua lifts her head toward the same single complete <Subject 2> AbyssKing at middle distance; his open right hand remains attached beside his torso.",
        ],
        [
            "A very low wide restores Lua, spear, one complete King, and their remaining distance.",
            "A low side medium isolates the failed rise while retaining the single King in depth.",
            "An over-Lua-shoulder medium connects dark wrist, unreachable spear, and approaching opponent.",
            "A low side wide resolves Lua's lifted eyeline and the one connected closer King.",
        ],
        ["Lua's attempted rise settling back to the wet floor", "her hand moving from dark wrist toward the unreachable spear", "Lua's lifting eyeline carrying focus to the single approaching King"],
    ),
    clip(
        "EP00-S05", "EP00-S05-NC02", "EP00-S05-SH13", 7.0,
        "EP00-S05-NC02_STORYBOARD_16X9_V5.png",
        "One unseen internal heartbeat stops Lua's breath; she looks inward briefly and then refocuses on the King without any visible new power.",
        [
            "<Subject 1> Lua exhales unevenly in close three-quarter view with her dark wrist at the lower edge and <Subject 2> AbyssKing soft in the background.",
            "One unseen internal heartbeat stops <Subject 1> Lua's breath and widens her eyes slightly while <Subject 2> AbyssKing remains unchanged and no effect appears.",
            "<Subject 1> Lua's gaze moves briefly down toward an internal sensation rather than the wrist, which remains dark; <Subject 2> AbyssKing stays blurred.",
            "<Subject 1> Lua raises her eyes toward <Subject 2> AbyssKing and surprise begins replacing pain without any new color, object, or power.",
        ],
        [
            "A close three-quarter includes breath, dark wrist edge, and the King as scale depth.",
            "A tighter profile captures the single stopped breath with no camera shake.",
            "An intimate high three-quarter follows the short inward-down eyeline.",
            "A close rear three-quarter restores the opponent eyeline and changed emotion.",
        ],
        ["Lua's exhale stopping at the heartbeat", "the tiny downward eye movement toward the internal sensation", "the same eyes lifting back toward the opponent"],
        spear=False,
    ),
    clip(
        "EP00-S05", "EP00-S05-NC03", "EP00-S05-SH14", 6.5,
        "EP00-S05-NC03_STORYBOARD_16X9_V5.png",
        "Lua steadies at the edge of recognition, then the image cuts directly to black before a second internal heartbeat completes.",
        [
            "An extreme close-up holds <Subject 1> Lua's eyes on <Subject 2> AbyssKing, who remains only a recognizable dark shape in depth; she never looks at the lens.",
            "<Subject 1> Lua's ragged breathing settles once and her eye movement becomes steady while <Subject 2> AbyssKing remains unchanged.",
            "<Subject 1> Lua lifts her chin by only a few degrees as recognition begins; no visible new power, object, color, or reaction appears on <Subject 2> AbyssKing.",
            "Before the second internal heartbeat completes, the image cuts directly to full black with no subject, glow, title, identifier, or explanation.",
        ],
        [
            "An extreme eye close-up retains the opponent shape in the same depth axis.",
            "A close three-quarter records the single breath settling without a static duplicate frame.",
            "A low close portrait from the opponent direction reads only the slight chin lift.",
            "A direct full-black frame contains no camera movement, subject rendering, graphic, or residual glow.",
        ],
        ["the opponent-focused eyes settling with one breath", "the final small chin lift completing recognition", "the second heartbeat pre-sound ending in the direct cut to black"],
        spear=False,
    ),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"PNG가 아닙니다: {path}")
    return struct.unpack(">II", header[16:24])


def label_subjects(value: str) -> str:
    value = re.sub(r"(?<!<Subject 2> )\bAbyssKing('s)?\b", lambda m: f"<Subject 2> AbyssKing{m.group(1) or ''}", value)
    value = re.sub(r"(?<!<Subject 1> )\bLua('s)?\b", lambda m: f"<Subject 1> Lua{m.group(1) or ''}", value)
    return value


def camera_plan(row: dict[str, Any], variant: str) -> list[dict[str, Any]]:
    starts = [round(float(row["duration"]) * index / 4, 3) for index in (1, 2, 3)]
    plans: list[dict[str, Any]] = []
    d_templates = (
        "Track quickly right at waist height and close by one body length while following {motion}, arriving at panel {panel}.",
        "Arc briskly clockwise at chest height and widen by one body length while following {motion}, arriving at panel {panel}.",
        "Crane rapidly down to knee height and close by half a body length while following {motion}, arriving at panel {panel}.",
    )
    for index, camera in enumerate(row["cameras"], start=1):
        camera = label_subjects(camera)
        if index == 1:
            camera += (
                " Establish <Subject 1> Lua and <Subject 2> AbyssKing on the inherited "
                "action axis, using foreground or depth as required by the reviewed checkpoint."
            )
        if index == 4:
            camera += (
                " Keep <Subject 1> Lua and <Subject 2> AbyssKing visibly readable in the "
                "accumulated exit state unless the reviewed checkpoint is the terminal full-black cut."
            )
        if variant == "A":
            text = f"Directly reproduce this reviewed checkpoint and its accumulated action state. {camera}"
        elif variant == "D":
            text = f"Continue the accumulated action without resetting pose or position. {camera}"
        else:
            text = f"Continue the accumulated action and use only the existing physical motion as the reveal. {camera}"
        plan: dict[str, Any] = {
            "panel_index": index,
            "panel_position": POSITIONS[index - 1],
            "camera": text,
            "beat_ids": [f"P{index}"],
        }
        if index > 1:
            plan["start_seconds"] = starts[index - 2]
        if index < 4 and variant == "D":
            plan["transition_to_next"] = d_templates[index - 1].format(
                motion=label_subjects(row["motions"][index - 1]), panel=index + 1
            )
        if index < 4 and variant == "E":
            plan["transition_to_next"] = (
                f"Follow {label_subjects(row['motions'][index - 1])} across the current frame until it reveals panel {index + 1}'s "
                "new camera position and accumulated physical result."
            )
        plans.append(plan)
    return plans


def asset_catalog(lock: dict[str, Any]) -> dict[str, Any]:
    assets = lock["asset_locks"]
    return {
        "lua": {
            "role": "lua_identity",
            "label": "Lua identity sheet",
            "copy_from": assets["lua_awakened"]["path"],
            "subject_id": 1,
            "subject_name": "Lua",
            "subject_description": "One fully awakened young spear fighter with tied brown hair, freckles, weathered beige clothing, shell ornaments, sandals, and asymmetrical turquoise dragon scales. Preserve one person and the same identity.",
            "retention_marker": "fully_preserved",
            "retention_description": "Preserve the same Lua identity, body, clothing, scales, and expression continuity",
        },
        "king": {
            "role": "abyss_king_identity",
            "label": "Abyss King identity sheet",
            "copy_from": assets["abyss_king"]["path"],
            "subject_id": 2,
            "subject_name": "AbyssKing",
            "subject_description": "One connected black-liquid humanoid about three times Lua's height, with one crown-like head, one pair of bright eyes, one torso, exactly two arms, exactly two hands, and one continuous skirt-like lower mass.",
            "retention_marker": "fully_preserved",
            "retention_description": "Preserve one connected three-times-Lua body with exactly two arms and hands",
        },
        "spear": {
            "role": "major_prop_spear",
            "label": "Physical spear identity sheet",
            "copy_from": assets["dragon_spear"]["path"],
            "standalone_picture_name": "the single physical spear",
            "standalone_picture_description": "One fixed-length wooden shaft with one black chipped stone point, rope bindings and shell ornaments. It never glows or moves autonomously.",
            "retention_marker": "fully_preserved",
            "retention_description": "Preserve the one intact fixed-length physical spear in cited Shots",
        },
    }


def storyboard_asset(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "chronological_storyboard",
        "label": "Reviewed four-panel action storyboard",
        "copy_from": f"storyboards_ep00_action_v2/{row['storyboard']}",
        "reference_kind": "storyboard",
        "storyboard_panel_count": 4,
        "storyboard_reading_order": "top-left, top-right, bottom-left, bottom-right",
        "storyboard_beats": row["panels"],
        "standalone_picture_name": "the chronological four-panel storyboard",
        "standalone_picture_description": "Read the 2x2 grid as four ordered action checkpoints. Preserve composition, blocking, eyelines, environment identity, prop and effect state, and causal continuity, but never render the grid or any production label.",
        "retention_marker": "fully_preserved",
        "retention_description": "Preserve the four reviewed action checkpoints and their one-to-one Shot order",
        "retention_shots": [1, 2, 3, 4],
    }


def build_payloads(lock: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    sources = [
        "EP00_LOCKED_PRODUCTION_RULES_V2.json",
        *lock["canonical_sources"].values(),
        "EP00_CANONICAL_CLIPS_V2.json",
    ]
    assets = asset_catalog(lock)
    spec_clips: list[dict[str, Any]] = []
    contracts: dict[str, Any] = {}
    bridges = [f"EP00_V8_ACTION_STATE_{index:02d}" for index in range(15)]
    for sequence, row in enumerate(CLIPS, start=1):
        key = f"storyboard_{sequence:02d}"
        assets[key] = storyboard_asset(row)
        storyboard_picture_id = 4 if row["has_spear"] else 3
        references: list[Any] = ["lua", "king"]
        if row["has_spear"]:
            references.append({"asset_key": "spear", "retention_shots": row["spear_shots"]})
        references.append(key)
        incoming = (
            "Begin with <Subject 1> Lua and <Subject 2> AbyssKing on the inherited action axis; "
            f"carry this exact physical state: {row['panels'][0]}"
        )
        outgoing = (
            "End only after <Subject 1> Lua's recognition begins and the image cuts directly to full black before the second internal heartbeat completes; <Subject 2> AbyssKing receives no visible reaction."
            if sequence == len(CLIPS)
            else f"End on the accumulated physical state: {row['panels'][3]}"
        )
        contract = {
            "shared_event": row["summary"],
            "bridge_in_id": bridges[sequence - 1],
            "bridge_out_id": bridges[sequence],
            "boundary_policy": "terminal" if sequence == len(CLIPS) else "referenced_cut",
            "source_shot_ids": [row["source"]],
            "incoming_reference_subjects": [1, 2],
            "outgoing_reference_subjects": [1, 2],
            "incoming_bridge": incoming,
            "outgoing_bridge": outgoing,
            "storyboard_required": True,
            "storyboard_picture_id": storyboard_picture_id,
            "storyboard_panel_count": 4,
            "beats": [
                {"beat_id": f"P{index}", "description": label_subjects(panel)}
                for index, panel in enumerate(row["panels"], start=1)
            ],
            "candidate_plans": {
                variant: {
                    "emphasis": {
                        "A": "direct reviewed action checkpoint reproduction",
                        "D": "continuous camera travel following the same physical action into the next checkpoint",
                        "E": "existing action and effect motion revealing the next accumulated checkpoint",
                    }[variant],
                    "shots": camera_plan(row, variant),
                }
                for variant in ("A", "D", "E")
            },
        }
        contracts[row["clip"]] = contract
        spec_clips.append({
            "scene_id": row["scene"],
            "clip_id": row["clip"],
            "sequence": sequence,
            "source_shot_id": row["source"],
            "status": "pending_review",
            "duration_seconds": row["duration"],
            "references": references,
            "prompt_base": {
                "summary": row["summary"],
                "style_opening": [
                    "The same circular underwater Heartstone Chamber persists: central round dais, concentric cyan water channels, dragon-statue columns, and upper black hanging strands",
                    "Use fast readable whole-body choreography, physically sourced water pressure, directional droplets and surface reactions; never display production identifiers or written text",
                ],
                "overall_soundscape": "Underwater pressure, rapid displaced water, wet floor contact, physical spear movement, Lua's breath, and only effect sounds caused by the shown action.",
                "non_diegetic_music": "Fast low strings and percussion follow each cause, contact, displacement and reversal, then fall near silent after defeat.",
            },
            "prompt_variants": [
                {"variant_id": variant, "label": f"후보 {variant}", "rationale": {
                    "A": "검수된 네 행동 상태를 가장 직접적으로 재현",
                    "D": "현재 행동을 따라 다음 카메라 도착점까지 연속 이동",
                    "E": "현재 물리 동작과 이펙트가 다음 행동 상태를 공개",
                }[variant], "prompt_spec": {}}
                for variant in ("A", "D", "E")
            ],
            "canonical_source_lineage": sources,
            "locked_rule_id": lock["lock_id"],
            "continuity_in": bridges[sequence - 1],
            "continuity_out": bridges[sequence],
            "storyboard_review_contract": {
                "picture_id": storyboard_picture_id,
                "panel_positions": list(POSITIONS),
                "panel_to_shot": "one_to_one",
                "environment": "Heartstone_Chamber",
                "action_state_changes": 4,
                "visual_asset_status": "agent_visually_reviewed",
            },
            "visual_review": "pending_full_contact_sheet_review",
            "semantic_review": "pending_full_project_audit",
        })
    canonical = {
        "schema_version": 2,
        "canonical_id": "raising_a_dragon_s01_ep00_action_causality_clips_v2",
        "locked_rule_id": lock["lock_id"],
        "screenplay": "EP00_VISUAL_PRODUCTION_SCREENPLAY_REBUILD_V2.md",
        "total_duration_seconds": sum(float(row["duration"]) for row in CLIPS),
        "clips": list(CLIPS),
    }
    events = {
        "version": EVENT_VERSION,
        "locked_rule_id": lock["lock_id"],
        "canonical_source_lineage": sources,
        "clips": contracts,
    }
    spec = {
        "schema_version": 2,
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · Action Causality V8",
        "description": "Rebuilt from screenplay causality with dynamic four-state action clips, one persistent chamber, and no production IDs inside prompts.",
        "source_policy": "v2_screenplay_and_locked_action_causality_only_no_v1_v7_prompt_lineage",
        "canonical_source_lineage": sources,
        "locked_rule_id": lock["lock_id"],
        "build_script": "scripts/build_ep00_action_causality_v8.py",
        "asset_catalog": assets,
        "event_contracts_file": EVENTS_PATH.name,
        "clips": spec_clips,
    }
    return canonical, events, spec


def preflight(lock: dict[str, Any]) -> None:
    expected = lock["clip_contract"]
    if len(CLIPS) != expected["clip_count"]:
        raise ValueError("V2 잠금 계약과 Clip 수가 다릅니다.")
    total = sum(float(row["duration"]) for row in CLIPS)
    if total != float(expected["total_duration_seconds"]):
        raise ValueError(f"V2 잠금 시간과 다릅니다: {total}")
    if any(len(row["panels"]) != 4 or len(row["cameras"]) != 4 or len(row["motions"]) != 3 for row in CLIPS):
        raise ValueError("각 Clip은 4개 행동 상태, 4개 카메라, 3개 연결 동작이 필요합니다.")
    for asset in lock["asset_locks"].values():
        path = EPISODE_DIR / asset["path"]
        if sha256(path) != asset["sha256"]:
            raise ValueError(f"잠금 자산 해시가 다릅니다: {path}")
    workflow = Path(lock["workflow_lock"]["path"])
    if sha256(workflow) != lock["workflow_lock"]["sha256"]:
        raise ValueError("H3 workflow 해시가 다릅니다.")
    for row in CLIPS:
        path = EPISODE_DIR / "storyboards_ep00_action_v2" / row["storyboard"]
        if png_size(path) != (1672, 941):
            raise ValueError(f"16:9 스토리보드 크기가 아닙니다: {path}")


def main() -> int:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    preflight(lock)
    canonical, events, spec = build_payloads(lock)
    CANONICAL_PATH.write_text(json.dumps(canonical, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    EVENTS_PATH.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SPEC_PATH.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = h3_prompt_project_builder.build_project(ROOT, SPEC_PATH)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
