#!/usr/bin/env python3
"""Generate the clean-slate EP01 MSR project from video intent first.

The target video, blocking and camera path are authored first.  Each anchor-image
prompt is then compiled from that video's opening state plus a shared spatial
bible.  This project does not import or mutate the V1 prompt project.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from msr_sequence_v2 import PROMPT_STRATEGY, WORKFLOW, compile_global_prompt
from scripts.ep01_v2_video_prompts import DIALOGUE_OVERRIDES, VIDEO_BEATS_BY_CLIP

PROJECT_ID = "RaisingaDragonSeason01_EP01_MSR_VIDEO_FIRST_V2"
PROJECT_TITLE = "용 키우기 EP01 — 영상 우선 MSR V2"
SOURCE = "RaisingaDragonSeason01/Raising a Dragon.md"
STYLE = (
    "Premium stylized 3D ocean-fantasy feature animation, tactile coastal materials, "
    "expressive cinematic acting, coherent geography and widescreen 16:9 composition."
)
NEGATIVE = (
    "storyboard, collage, split screen, multiple moments, motion trail, duplicated character, "
    "merged identities, extra limbs, floating prop, oversized dragon, human baby, human child "
    "inside bowl, person inside basket, changed room layout, changed cave texture, text, subtitle, watermark"
)
MIR_SCALE = (
    "Young Mir is a DRAGON hatchling, never a human baby or child. His nose-to-tail-base body length "
    "is approximately Lua's torso length; his complete curled dragon body fits inside the shallow water bowl."
)

CHARACTERS = {
    "lua": ("Lua.png", "Lua, the small sun-browned human coastal girl in the reference sheet, with messy light-brown hair, large brown eyes, worn beige sleeveless tunic, rope belt and shell ornaments; human anatomy only."),
    "mir": ("YoungMir.png", f"{MIR_SCALE} Preserve his blue-silver scales, short dark horns, fin-like wings, bright blue eyes, tail-tip crystal and crown-wave chest mark."),
    "child1": ("villageChild01.png", "Village Child 1, the reference boy with short hair and empty hands; preserve his exact human face, age and clothes."),
    "child2": ("village_child_2.png", "Village Child 2, the reference girl with tied hair and her own woven shoulder basket; preserve her exact human face, age and clothes."),
    "fisherman": ("old_fisherman.png", "The Old Fisherman from the reference sheet, an elderly human coastal man with weathered face and practical fishing clothes."),
    "black_tide": ("BLACK TIDE — SUPERNATURAL .png", "The Black Tide, one living mass of black seawater with unstable hand-, mouth- and face-like ridges; no stable human body."),
    "jellyfish": ("BLACK JELLYFISH .png", "The Black Jellyfish, one translucent black deep-sea jellyfish filled with ink-like smoke and long trailing tentacles; non-human anatomy."),
}
PROPS = {
    "spear": ("spear.png", "Lua's single rigid fishing spear: rough wooden shaft, dark stone point and cord binding; always owned and physically supported by Lua."),
}

SPACES = {
    "storm_ocean": "A storm-lashed night ocean with the coast far screen-right, giant black waves, diagonal rain and deep open water below.",
    "palace_ruins": "One immense ruined deep-sea dragon palace of weathered pale coral stone, broken columns, blue shafts of light and drifting marine dust.",
    "memory_palace": "A coherent submerged memory-space with one broken palace gate, distant sleeping dragon silhouettes, black roots at the perimeter and a blue heart-light on the central axis.",
    "breakwater": "One fixed post-storm village breakwater: shallow sea along the screen-right edge, raised wet stone path through center, damaged village and nets screen-left, distant cliff cave on the far-right horizon.",
    "cave_clean": "BG_COASTAL_CAVE_CLEAN: one narrow coastal cave of smooth dark wave-polished basalt, sparse broad rock planes, shallow water along the center floor, entrance behind-left and one blue-lit crevice deeper on the right wall. Keep this exact texture, topology and entrance-to-crevice axis in every cave frame.",
    "vision_corridor": "A distinct supernatural vision corridor inside the ruined dragon palace; this is intentionally separate from the coastal cave.",
    "lua_house_day": "One fixed small coastal house in daylight: door on the left wall, wooden bed back-left, shallow water bowl on the floor center-right, low table directly behind the bowl with one palm-sized spiral shell, covered window on the back wall, nets and water container fixed at far right.",
    "lua_house_night": "The exact same Lua house geometry as daytime, now at night: door left, bed back-left, bowl floor center-right, low table and shell behind it, covered window back wall and water container far right. Only lighting changes.",
    "night_coast": "The silent night coast outside Lua's house, with the house fixed on the far-left shore and open black sea extending screen-right.",
}


STATIC_FRAMING = {
    1:"24 mm extreme-wide; high horizon, empty storm sea dominant, one clearly readable cobalt-blue signal low-center.",
    2:"28 mm underwater wide; wounded Mir small in lower third, cracked pillar and palace scale readable.",
    3:"50 mm side profile; Mir's complete body isolated against a diagonal current channel.",
    4:"35 mm vertical wide; Mir high-center, one Black Tide far below, clear water gap.",
    5:"50 mm medium side; Mir and Black Tide in separate upper and lower layers.",
    6:"40 mm centered symmetry; small Mir at center, broken gate and blue heart behind, roots confined to outer edges.",
    7:"28 mm coastal wide; incoming wave and Mir silhouette readable before shore rocks.",
    8:"50 mm low three-quarter medium-wide; Lua, complete spear and fish are separate shapes.",
    9:"50 mm medium side; Lua's unbalanced body, sandal, stone edge and spear tip visible.",
    10:"50 mm medium side on same stone edge; seated Lua and supporting hand fully visible.",
    11:"65 mm medium two-shot; Child 1 left, Child 2 right, open eyeline to empty frame-right.",
    12:"65 mm waist-up reverse shot; Lua right, open eyeline to empty frame-left, spear low.",
    13:"50 mm grounded two-shot; Lua and fisherman separated, cave on shared far-right sightline.",
    14:"35 mm rear three-quarter wide; Lua foreground, continuous stone route to distant cave.",
    15:"35 mm cave wide; entrance behind-left, Lua left-center, water center, blue crevice far-right.",
    16:"50 mm low two-shot; kneeling Lua left, complete small Mir right, open stone gap.",
    17:"70 mm medium-close side; Lua left, Mir right, open hand centered, visible air gap.",
    18:"85 mm tight side close-up; one Lua fingertip and Mir's small dragon mouth are focal contact.",
    19:"28 mm centered corridor wide; gate, sleeping silhouettes, roots and blue heart in separate layers.",
    20:"65 mm low side two-shot; Lua left, Mir right, both glowing marks unobstructed.",
    21:"50 mm full-body rear-side; Lua carries one compact cloth bundle toward behind-left exit.",
    22:"50 mm threshold side; Lua and intact bundle between dark cave and bright coast.",
    23:"35 mm interior wide facing left door; Lua enters left, empty bowl right, shell on table.",
    24:"50 mm medium on bowl axis; Lua left, small Mir above empty bowl right.",
    25:"60 mm medium two-shot; Lua left with one dry fish, Mir in bowl, shell behind.",
    26:"50 mm low interior; bowl foreground, Mir center, one shell on table, Lua farther back.",
    27:"55 mm medium two-shot; closed door left, Lua center as barrier, Mir and bowl right.",
    28:"50 mm wide door-to-bowl view; closed door left, Lua seated center, Mir beside bowl right, all physically separate.",
    29:"85 mm tight side close-up; Mir mouth, one droplet and Lua forehead aligned with gaps.",
    30:"85 mm detail two-shot; forehead bead, Lua wrist mark and Mir chest mark are three bright readable focal points.",
    31:"35 mm room wide; Lua on bed back-left, Mir in bowl center-right, full room geometry.",
    32:"40 mm centered memory view; small Mir before heart, one flat horned cast shadow attached to his feet on the floor and wall.",
    33:"60 mm low side medium; Lua's two hands support Mir's complete dragon body above bowl.",
    34:"70 mm intimate medium close-up; Lua and one small dragon with both marks visible.",
    35:"40 mm room wide; bowl right foreground, Lua at back window, bed left background.",
    36:"28 mm exterior wide; warm house far-left, one Black Jellyfish frame-right, open gap."
}
STATIC_STATE_OVERRIDES = {
    5:"One exhausted small dragon curls around its bright tail crystal in the upper half. One Black Tide occupies the lower half. A clean blue-water band separates them.",
    6:"Small Mir floats alone at center before a broken empty gate. A small blue heart-light glows on the central axis and thin black roots stay at the far perimeter. The background contains no face, head, statue or additional dragon.",
    7:"One incoming wave visibly contains Mir's complete small blue-silver silhouette and bright tail crystal. Wet black shore rocks wait ahead; Mir is not hidden.",
    9:"Lua pitches forward beyond her planted foot after a missed thrust. Her front sandal releases from the wet edge and the spear tip is in shallow water. Her body has not reached the water.",
    11:"Child 1 stands frame-left and Child 2 frame-right. Both faces and bodies turn toward an unseen point beyond the screen-right edge. No third person is visible.",
    12:"Soaked Lua stands alone frame-right. Her face and torso turn toward an unseen point beyond the screen-left edge. She holds the complete spear low. No child is visible.",
    17:"Lua crouches left and small Mir lies right. Lua presents one open palm at center. A visible air gap remains between every fingertip and Mir's mouth.",
    18:"Lua's single extended index fingertip is visibly inserted one centimeter between Mir's gently closed small dragon jaws. Mir holds only the fingertip; there is clear physical contact, while the rest of Lua's hand remains outside his mouth.",
    20:"Lua kneels left with glowing wrist mark visible. Small Mir lies right with crown-wave chest mark visible. Their bodies do not overlap.",
    21:"Lua carries one compact beige cloth bundle against her chest with both arms. Mir's body, wings, legs and tail are fully enclosed; only his small horned blue-silver dragon head is visible.",
    22:"Lua stands at the cave threshold holding the same compact beige cloth bundle. Mir remains fully enclosed except for his small horned dragon head. No cloth lies on the ground.",
    23:"Lua enters through the left door carrying one cloth-wrapped Mir bundle. The shallow bowl is empty at center-right. One palm-sized spiral shell is already on the low table behind it.",
    24:"Lua supports the complete small dragon directly above the empty bowl. Mir's curled body is smaller than the rim and has not touched water. The shell remains on the table.",
    25:"Small Mir's complete curled dragon body rests inside the bowl. Lua holds exactly one dry fish outside it. The shell remains on the table.",
    26:"Small Mir stands between bowl and table, facing exactly one palm-sized spiral shell already at the table edge. Lua is behind with empty hands.",
    27:"Lua sits between the closed left door and small Mir. Mir remains beside the bowl holding the same shell. Their bodies do not overlap.",
    28:"Lua sits on the floor at center with her ordinary human body directly blocking the straight sightline from the closed left door to small Mir beside the bowl. Mir holds the same shell. The room contains no magical effect.",
    29:"Small Mir remains fully inside the bowl. Exactly one clear water droplet is suspended halfway between his mouth and Lua's forehead; it touches neither face. Both marks are dim.",
    30:"One clearly readable crystal water bead rests at the center of Lua's forehead. No droplet remains in the air. Lua turns her glowing wrist mark toward the viewer and Mir turns his glowing chest mark toward the viewer while remaining inside the bowl.",
    31:"Lua sleeps alone on the bed back-left. One small quadrupedal dragon hatchling is curled completely inside the bowl center-right. The bowl contains no human figure.",
    32:"Small Mir stands alone before the blue heart. One flat translucent crown-horned cast shadow begins exactly at Mir's feet and continues across the floor onto the wall; it has no eyes, texture, volume or separate body.",
    33:"Lua's two hands support one complete small quadrupedal dragon above the bowl. Mir's head, four limbs, fin-like wings and crystal-tipped tail are distinct.",
    34:"Lua sits cradling one small quadrupedal dragon. Mir's dragon face, wings and tail remain visible. Lua's wrist mark and Mir's chest mark are unobstructed.",
    36:"One translucent Black Jellyfish floats over the sea at frame-right facing the single warm house at frame-left. No other creature or building is present."
}
IMAGE_SUBJECTS = {
    "Lua.png":"Lua, one small sun-browned human coastal girl with messy light-brown hair, large brown eyes, worn beige sleeveless tunic, rope belt and shell ornaments.",
    "YoungMir.png":"Young Mir, one small blue-silver quadrupedal dragon hatchling with short dark horns, fin-like wings, four clawed legs, bright blue eyes, crystal-tipped tail and crown-wave chest mark.",
    "villageChild01.png":"Village Child 1, one short-haired human coastal boy with empty hands and reference clothing.",
    "village_child_2.png":"Village Child 2, one tied-hair human coastal girl with her own woven basket and reference clothing.",
    "old_fisherman.png":"The Old Fisherman, one elderly human coastal man with weathered face and practical fishing clothes.",
    "BLACK TIDE — SUPERNATURAL .png":"The Black Tide, one continuous mass of black seawater with unstable face-like ridges and no stable body.",
    "BLACK JELLYFISH .png":"The Black Jellyfish, one translucent black deep-sea jellyfish filled with ink-like smoke and long tentacles.",
    "spear.png":"Lua's single rigid fishing spear with rough wooden shaft, dark stone point and cord binding."
}

REGEN_REVISIONS = {1: 3, 6: 3, 18: 3, 28: 3, 30: 3, 32: 3}
NEGATIVE_OVERRIDES = {
    1: "invisible blue signal, dragon visible above water",
    6: "giant face, giant head, dragon portrait, crowned creature, statue, foreground figure",
    18: "pointing gesture, fingertip outside mouth, open gap between finger and mouth",
    28: "force field, magic shield, energy wall, glowing barrier, transparent wall",
    30: "missing forehead bead, hidden wrist, hidden chest mark, unlit symbols",
    32: "second dragon, giant dragon body, volumetric creature, detached shadow, glowing eyes in shadow",
}



def ref(slot: int, key: str, *, prop: bool = False) -> dict[str, Any]:
    filename, description = (PROPS if prop else CHARACTERS)[key]
    return {
        "reference_id": slot,
        "slot": slot,
        "role": f"prop_{slot}" if prop else f"character_{slot}",
        "source_path": f"RaisingaDragonSeason01/{filename}",
        "description": description,
    }


def beat(seconds: float, prompt: str) -> dict[str, Any]:
    return {"seconds": seconds, "prompt": prompt.strip()}


def shot(
    frame: int,
    scene: str,
    slug: str,
    title: str,
    seconds: int,
    space: str,
    refs: list[dict[str, Any]],
    camera: str,
    opening: str,
    beats: list[dict[str, Any]],
    state_in: str,
    state_out: str,
    *,
    dialogue_ko: str = "",
    continuity_from: str | None = None,
) -> dict[str, Any]:
    clip_id = f"{scene}_{slug}"
    return {
        "frame": frame,
        "frame_id": f"EP01_{frame:02d}",
        "scene_id": scene,
        "clip_id": clip_id,
        "title": title,
        "seconds": seconds,
        "space_id": space,
        "refs": refs,
        "camera": camera,
        "opening": opening,
        "beats": beats,
        "state_in": state_in,
        "state_out": state_out,
        "dialogue_ko": dialogue_ko,
        "continuity_from": continuity_from,
    }


SHOTS: list[dict[str, Any]] = [
    shot(1, "SC01-001", "V01", "폭풍 아래 푸른 신호", 12, "storm_ocean", [],
         "Extreme wide locked coastward composition; slow descent toward the wave trough.",
         "No character is visible; a tiny blue point sits deep beneath a distant wave trough.",
         [beat(6, "Storm waves, rain and lightning dominate the empty frame."), beat(6, "The tiny blue point pulses once and moves beneath the waves toward the coast.")],
         "empty storm sea", "blue signal travelling coastward"),
    shot(2, "SC01-001", "V02", "용궁 붕괴와 발견", 10, "palace_ruins", [ref(1, "mir")],
         "Immense underwater wide; one restrained forward drift through settling dust.",
         "A cracked coral pillar leans above wounded Young Mir, who lies small and readable on the palace floor.",
         [beat(10, "The pillar collapses behind Mir in one heavy event. Dust spreads, revealing his wounded face and dim tail crystal.")],
         "pillar unstable, Mir motionless", "pillar settled, Mir discovered"),
    shot(3, "SC01-001", "V03", "해류에 떠밀리는 미르", 8, "palace_ruins", [ref(1, "mir")],
         "Side tracking shot along one diagonal current channel.",
         "Young Mir is already suspended sideways in the current with palace ruins receding behind him.",
         [beat(8, "The current carries Mir continuously away from the ruins. He weakly lifts his head and his tail crystal flickers once.")],
         "Mir suspended near ruins", "Mir farther from ruins"),
    shot(4, "SC01-001", "V04", "검은 물결의 추격", 12, "palace_ruins", [ref(1, "mir"), ref(2, "black_tide")],
         "Vertical pursuit axis; camera tracks upward beside Mir.",
         "Mir swims weakly upward in a blue shaft while one Black Tide mass rises far below with clear water between them.",
         [beat(12, "Mir climbs continuously while the Black Tide closes part of the gap and forms brief unstable ridges. End before contact.")],
         "wide separation", "near contact"),
    shot(5, "SC01-001", "V05", "꼬리 결정의 방어", 8, "palace_ruins", [ref(1, "mir"), ref(2, "black_tide")],
         "Medium underwater side angle; one short upward lift after the pulse.",
         "Exhausted Mir curls around his bright tail crystal above the near Black Tide; both remain separate.",
         [beat(8, "The crystal releases one blue pulse that presses the black water down. Mir uses the reopened gap to rise toward brighter water.")],
         "near contact", "gap reopened, Mir escaping"),
    shot(6, "SC01-001", "V06", "기억하지 마라", 12, "memory_palace", [ref(1, "mir"), ref(2, "black_tide")],
         "Slow centered push toward Mir; memory remains one coherent space.",
         "Mir floats at center, broken gate behind him and black roots framing the blue open center.",
         [beat(6, "The unseen voice says in Korean, \"기억하지 마라.\" Mir contracts in fear."), beat(6, "The roots advance as the voice says, \"그러면 아프지 않다.\" Storm light tears open behind Mir.")],
         "memory open", "memory torn by storm light", dialogue_ko="기억하지 마라. / 그러면 아프지 않다."),
    shot(7, "SC01-001", "V07", "해안으로 밀려온 빛", 10, "storm_ocean", [ref(1, "mir")],
         "Distant coastal wide; camera holds the shoreward travel direction.",
         "A wave already carries Mir's small blue-silver dragon silhouette toward wet black shore rocks.",
         [beat(10, "The same wave carries Mir behind the shore rocks while his glow dims to darkness.")],
         "Mir inside incoming wave", "Mir hidden behind shore rocks"),

    shot(8, "SC01-002", "V01", "물고기를 겨누는 루아", 4, "breakwater", [ref(1, "lua"), ref(3, "spear", prop=True)],
         "Low three-quarter side view facing the sea-right edge; subtle push along the spear line.",
         "Lua holds a low aiming stance on secure wet stone; the complete spear and a separate fish below the water are readable with a clean gap.",
         [beat(4, "The fish moves sideways. Lua follows it with one small low spear adjustment and holds her breath immediately before the thrust.")],
         "low aim", "held breath before thrust"),
    shot(9, "SC01-002", "V02", "젖은 가장자리의 낙상", 5, "breakwater", [ref(1, "lua"), ref(3, "spear", prop=True)],
         "Medium side view; energetic push and downward side tracking with the fall.",
         "Lua is already beyond her front foot after the missed thrust, spear tip in shallow water and front sandal releasing from the edge.",
         [beat(5, "Her forward momentum carries her into one accidental fall. Knees and hip hit shallow water with one compact weighted splash while the spear stays in her hands.")],
         "off-balance after miss", "settled in shallow water"),
    shot(10, "SC01-002", "V03", "물에서 일어나는 루아", 5, "breakwater", [ref(1, "lua"), ref(3, "spear", prop=True)],
         "Same side axis; only a small upward camera correction.",
         "Lua is already seated in the shallow water beside the same stone edge, soaked and still holding the spear.",
         [beat(5, "Lua braces one free hand on the stone, rises once to stable footing and forces an embarrassed dignified expression.")],
         "settled after fall", "standing soaked", continuity_from="SC01-002_V02"),
    shot(11, "SC01-002", "V04", "두 아이의 놀림", 12, "breakwater", [ref(1, "child1"), ref(2, "child2")],
         "Camera looks toward the sea-right side of the master axis; one restrained slow push.",
         "Child 1 stands frame-left and Child 2 frame-right; both look toward empty frame-right where Lua stands in the reverse shot.",
         [beat(6, "Only Child 1 points and says in Korean, \"또 놓쳤다!\" Child 2 listens with closed lips."), beat(6, "Only Child 2 says, \"루아 누나는 바다랑 안 맞아!\" Child 1 stays silent.")],
         "children watching frame-right", "children laughing frame-right", dialogue_ko="또 놓쳤다! / 루아 누나는 바다랑 안 맞아!"),
    shot(12, "SC01-002", "V05", "루아의 허세", 18, "breakwater", [ref(1, "lua"), ref(3, "spear", prop=True)],
         "Reverse angle on the same axis, camera looking toward sea-left; one gentle waist-up to chest-up push.",
         "Soaked Lua stands alone frame-right and looks toward empty frame-left where the children stand in the reverse shot; spear remains low.",
         [beat(6, "Lua says, \"안 맞긴 뭐가 안 맞아!\""), beat(6, "She keeps both hands low and says, \"방금 건 일부러 빠진 거야.\""), beat(6, "After one beat she adds, \"수심 확인.\"")],
         "Lua facing frame-left", "Lua holding embarrassed pride", dialogue_ko="안 맞긴 뭐가 안 맞아! / 방금 건 일부러 빠진 거야. / 수심 확인."),
    shot(13, "SC01-002", "V06", "늙은 어부의 경고", 15, "breakwater", [ref(1, "lua"), ref(2, "fisherman"), ref(3, "spear", prop=True)],
         "Stable two-shot on the established breakwater axis; final slow pan along the fisherman's gaze to the cave.",
         "Lua and the Old Fisherman already share one grounded two-shot, with the cave readable on their far-right sightline.",
         [beat(5, "The fisherman says, \"루아야.\" Lua answers, \"네!\""), beat(5, "He says, \"바다는 고집으로 되는 게 아니다.\""), beat(5, "He looks to the cave and warns, \"오늘은 동굴 쪽 가지 마라. 폭풍 뒤에는 뭐가 밀려올지 몰라.\"")],
         "two-shot before warning", "shared gaze toward cave", dialogue_ko="루아야. / 네! / 바다는 고집으로 되는 게 아니다. / 오늘은 동굴 쪽 가지 마라. 폭풍 뒤에는 뭐가 밀려올지 몰라."),
    shot(14, "SC01-002", "V07", "푸른 동굴을 향해", 12, "breakwater", [ref(1, "lua"), ref(3, "spear", prop=True)],
         "Profile start followed by one smooth low rear three-quarter tracking move on the raised stone path.",
         "Lua stands alone with the cave at the end of a visible continuous dry stone route; spear secured low at her side.",
         [beat(6, "A blue reflection crosses wet stone to Lua's face as she thinks, \"가라면 가지 말아야 하는데.\""), beat(6, "A second pulse cues her decision. She thinks, \"저렇게 빛나면 가야지.\" and runs only on the visible stone route.")],
         "Lua deciding on dry path", "Lua running toward cave", dialogue_ko="가라면 가지 말아야 하는데. / 저렇게 빛나면 가야지."),

    shot(15, "SC01-003", "V01", "동굴 진입", 10, "cave_clean", [ref(1, "lua"), ref(3, "spear", prop=True)],
         "Wide rear three-quarter camera on the fixed entrance-to-crevice axis; slow walking-speed track.",
         "Lua stands just inside the behind-left entrance, spear tip touching the center water strip and blue crevice far ahead-right.",
         [beat(10, "Lua advances along the visible smooth-rock path, tests the water and stops when the blue reflection strengthens.")],
         "at cave entrance", "stopped before blue crevice"),
    shot(16, "SC01-003", "V02", "작은 용과의 첫 대면", 15, "cave_clean", [ref(1, "lua"), ref(2, "mir"), ref(3, "spear", prop=True)],
         "Low two-shot on the same entrance-to-crevice axis; one restrained push across the open wet-stone gap.",
         "Lua kneels left with spear resting behind her; small dragon Mir lies right at the established blue crevice, separated by open stone.",
         [beat(7, "Mir shifts as one complete small dragon body. Lua says, \"방금 귀여웠는데? 너… 도마뱀은 아니지?\""), beat(8, "Mir opens his eyes and meets Lua's gaze. Lua says, \"말도 안 돼.\"")],
         "Mir partly weak at crevice", "first sustained eye contact", dialogue_ko="방금 귀여웠는데? / 너… 도마뱀은 아니지? / 말도 안 돼."),
    shot(17, "SC01-003", "V03", "도움을 내미는 손", 8, "cave_clean", [ref(1, "lua"), ref(2, "mir")],
         "Same low side axis and distance as frame 16; gentle push following Lua's open hand.",
         "Lua crouches left and Mir lies right; a clean gap remains as Lua's one open hand starts near her own knee.",
         [beat(8, "Lua extends one open hand and stops before contact, saying, \"야, 괜찮아. 안 잡아먹어. 나도 오늘 아침 못 먹었거든.\"")],
         "open hand near Lua", "open hand offered before contact", dialogue_ko="야, 괜찮아. 안 잡아먹어. 나도 오늘 아침 못 먹었거든.", continuity_from="SC01-003_V02"),
    shot(18, "SC01-003", "V04", "살려달라는 이빨", 6, "cave_clean", [ref(1, "lua"), ref(2, "mir")],
         "Close side view preserving the exact left-Lua/right-Mir axis and smooth cave texture.",
         "Mir's small dragon mouth is already gently closed around one visible Lua fingertip; Mir remains on the stone and Lua supports her wrist.",
         [beat(6, "Lua flinches and cries, \"악!\" Mir clings weakly for support; Lua steadies rather than pulling away.")],
         "gentle fingertip contact established", "Lua understands the plea", dialogue_ko="악!", continuity_from="SC01-003_V03"),
    shot(19, "SC01-003", "V05", "용심 공명 환영", 15, "vision_corridor", [ref(1, "mir")],
         "One forward camera flight along the central vision corridor.",
         "A blue pulse enters the broken gate; the central path leads past sleeping dragons and black roots toward the blue heart.",
         [beat(5, "The pulse illuminates the gate."), beat(5, "The camera passes sleeping dragon silhouettes while roots tighten outside the central path."), beat(5, "The heart contracts and releases one wave back toward reality.")],
         "vision opens", "vision returns to reality"),
    shot(20, "SC01-003", "V06", "내가 본 거야", 14, "cave_clean", [ref(1, "lua"), ref(2, "mir")],
         "Return to the same cave side axis used in frames 17–18; one slow push toward Lua.",
         "Lua kneels left after the flash, wrist mark lowered and visible; small Mir lies right at the same crevice with chest mark visible.",
         [beat(7, "Lua asks, \"방금… 내가 본 거야?\" Mir chirps weakly."), beat(7, "Lua looks from both marks to Mir and asks, \"너 대체 뭐야?\"")],
         "post-vision separation", "two marks pulse once", dialogue_ko="방금… 내가 본 거야? / 너 대체 뭐야?"),
    shot(21, "SC01-003", "V07", "감싼 미르와 출구 이동", 8, "cave_clean", [ref(1, "lua"), ref(2, "mir")],
         "Rear-side tracking toward the behind-left exit, reversing the frame-15 travel direction.",
         "Lua is already standing with small dragon Mir securely wrapped in one continuous outer cloth against her chest; the same smooth-rock path leads to the exit.",
         [beat(8, "Lua adjusts the same wrap once, says, \"하. 나 진짜 사고 쳤다.\" and walks toward the exit without changing Mir's wrapped state.")],
         "Mir wrapped before movement", "Lua reaches cave threshold with Mir wrapped", dialogue_ko="하. 나 진짜 사고 쳤다."),
    shot(22, "SC01-003", "V08", "출구에서 멈춘 루아", 7, "cave_clean", [ref(1, "lua"), ref(2, "mir")],
         "Threshold side angle; small lateral move preserves the cave/coast boundary.",
         "Lua has stopped at the same cave threshold, still holding Mir in the exact same cloth wrap; smooth cave behind, bright coast ahead.",
         [beat(7, "A villager calls, \"루아! 거기 있냐?\" Lua tightens her arm, turns slightly to shield the still-wrapped Mir and listens.")],
         "same wrap at threshold", "protective guarded hold unchanged", dialogue_ko="루아! 거기 있냐?", continuity_from="SC01-003_V07"),

    shot(23, "SC01-004", "V01", "비밀스러운 집 입장", 8, "lua_house_day", [ref(1, "lua"), ref(2, "mir")],
         "Medium-wide from inside the room facing the fixed left-side door; slight lateral reveal toward bowl and table.",
         "Lua enters through the left door holding Mir in the same cave cloth wrap. Bowl center-right and the palm-sized shell already on the low table are visible.",
         [beat(8, "Lua closes the door, listens and says, \"진짜네. 꿈이면 지금쯤 깨야 하는데.\" Mir's dragon face peeks from the unchanged wrap.")],
         "wrapped Mir enters house", "door closed, wrap unchanged", dialogue_ko="진짜네. 꿈이면 지금쯤 깨야 하는데."),
    shot(24, "SC01-004", "V02", "물그릇의 첫 휴식", 8, "lua_house_day", [ref(1, "lua"), ref(2, "mir")],
         "Low side view along the door-to-bowl path; bowl and table remain fixed center-right.",
         "Lua supports small dragon Mir immediately above the shallow bowl; his whole curled body visibly fits inside it. Shell remains on the low table behind.",
         [beat(8, "Lua lowers Mir once into the bowl. He relaxes and she says, \"너 물에서 자는 거야? 좋겠다. 난 그러면 죽는데.\"")],
         "Mir above bowl", "Mir settled fully inside bowl", dialogue_ko="너 물에서 자는 거야? 좋겠다. 난 그러면 죽는데."),
    shot(25, "SC01-004", "V03", "마른 생선의 거절", 7, "lua_house_day", [ref(1, "lua"), ref(2, "mir")],
         "Stable medium two-shot on the same bowl axis.",
         "Small dragon Mir sits fully inside the bowl right; Lua kneels left holding one dry fish across a clear gap. Shell remains on the table.",
         [beat(7, "Lua offers the fish. Mir recoils once. Lua asks, \"아니, 바다에서 왔잖아. 생선 안 먹어?\"")],
         "fish offered", "fish rejected, Mir still in bowl", dialogue_ko="아니, 바다에서 왔잖아. 생선 안 먹어?", continuity_from="SC01-004_V02"),
    shot(26, "SC01-004", "V04", "탁자 조개의 선택", 8, "lua_house_day", [ref(1, "lua"), ref(2, "mir")],
         "Low tracking view from bowl to the fixed low table behind it.",
         "Small Mir stands beside the bowl facing the same palm-sized shell already visible on the low table; Lua remains behind with empty hands.",
         [beat(8, "Mir crawls the short path to the low table, reaches the established shell and hugs the one shell. Lua says, \"입맛도 귀족이네.\"")],
         "shell on table before movement", "Mir holding same shell", dialogue_ko="입맛도 귀족이네."),
    shot(27, "SC01-004", "V05", "숨길 결심", 9, "lua_house_day", [ref(1, "lua"), ref(2, "mir")],
         "Quiet medium two-shot from bowl toward the fixed left door.",
         "Mir sits beside the bowl holding the same small shell; Lua sits between Mir and the closed left door, wrist mark low and visible.",
         [beat(9, "Muffled imagined adult voices say, \"불길하다! 바다에 돌려보내!\" Lua looks to the door, then back to Mir and decides to protect him.")],
         "quiet two-shot with shell", "Lua committed to shielding Mir", dialogue_ko="불길하다! 바다에 돌려보내!"),
    shot(28, "SC01-004", "V06", "문 앞의 보호", 12, "lua_house_day", [ref(1, "lua"), ref(2, "mir")],
         "Same door–Lua–Mir axis; one gentle push across the conversational gap.",
         "Lua physically occupies the line between the closed door left and small Mir beside the bowl right; shell remains with Mir.",
         [beat(6, "Lua says, \"안 돼. 그러니까… 당분간 여기 있어.\""), beat(6, "She adds, \"근데 밥값은 해야 돼. 물 좀 데워준다든가?\" Mir tilts his head.")],
         "Lua shielding door", "protective agreement", dialogue_ko="안 돼. 그러니까… 당분간 여기 있어. / 근데 밥값은 해야 돼. 물 좀 데워준다든가?"),
    shot(29, "SC01-004", "V07", "공중의 작은 물방울", 7, "lua_house_day", [ref(1, "lua"), ref(2, "mir")],
         "Close side view on the fixed bowl axis; camera holds the clear path between faces.",
         "Small Mir remains fully inside the bowl; one clear droplet is already suspended halfway between his mouth and Lua's forehead. No contact yet.",
         [beat(7, "The single droplet travels slowly toward Lua while both remain still. End immediately before contact.")],
         "droplet midair", "droplet immediately before forehead contact"),
    shot(30, "SC01-004", "V08", "물방울 착지와 공명", 10, "lua_house_day", [ref(1, "lua"), ref(2, "mir")],
         "Same side axis, scale and bowl position as frame 29; slow final push to the two marks.",
         "One tiny bead is already on Lua's forehead after contact; small Mir remains fully inside the same bowl. Both marks are visible and dim.",
         [beat(5, "Lua says, \"그래. 가능성은 있다.\" Mir chirps proudly."), beat(5, "Their two marks brighten in one shared pulse and both become still.")],
         "droplet landed", "two marks pulsing", dialogue_ko="그래. 가능성은 있다.", continuity_from="SC01-004_V07"),

    shot(31, "SC01-005", "V01", "같은 꿈의 시작", 15, "lua_house_night", [ref(1, "lua"), ref(2, "mir")],
         "Quiet wide using the exact daytime room geometry; almost imperceptible push.",
         "Lua sleeps on the back-left bed; small dragon Mir sleeps curled completely inside the center-right bowl. Their marks are visible across the room.",
         [beat(8, "Their marks begin one slow synchronized pulse. Mir trembles and Lua mirrors his fear in sleep."), beat(7, "Blue light spreads through the unchanged room until its edges dissolve into the palace dream.")],
         "same house at night", "room dissolving into shared dream"),
    shot(32, "SC01-005", "V02", "버려진 새끼 용", 14, "memory_palace", [ref(1, "mir")],
         "Slow centered approach toward Mir and the heart stone.",
         "Small dragon Mir stands before the blue heart; one enormous crown-horned future shadow rises directly from his feet, not a second dragon.",
         [beat(7, "The voice says, \"너는 왕자가 아니다.\""), beat(7, "The voice says, \"버려진 새끼 용이다.\" The connected shadow contracts and blue light cracks open behind Mir.")],
         "future shadow connected", "dream breaking", dialogue_ko="너는 왕자가 아니다. / 버려진 새끼 용이다."),
    shot(33, "SC01-005", "V03", "잠에서 깬 루아", 8, "lua_house_night", [ref(1, "lua"), ref(2, "mir")],
         "Low side view preserving bed back-left and bowl center-right; restrained upward correction with the lift.",
         "Lua kneels beside the bowl with both empty hands under trembling small dragon Mir; his complete body is still identifiable as a dragon.",
         [beat(8, "Lua lifts Mir once into her arms and says, \"뭐야… 야. 괜찮아. 나 여기 있어.\"")],
         "Mir in bowl, Lua supporting", "Mir securely held", dialogue_ko="뭐야… 야. 괜찮아. 나 여기 있어."),
    shot(34, "SC01-005", "V04", "너도 무서운 거구나", 10, "lua_house_night", [ref(1, "lua"), ref(2, "mir")],
         "Intimate medium shot in the same room; one slow push to the marks.",
         "Lua is already seated holding the small dragon securely; Mir's dragon face is beside Lua's wrist mark and his chest mark remains visible.",
         [beat(10, "Lua says, \"이거… 내 무서움이 아니야. 너도 무서운 거구나.\" Mir touches his nose to her wrist and both lights soften.")],
         "stable embrace", "shared fear calmed", dialogue_ko="이거… 내 무서움이 아니야. 너도 무서운 거구나.", continuity_from="SC01-005_V03"),
    shot(35, "SC01-005", "V05", "고요해진 창밖", 9, "lua_house_night", [ref(1, "lua"), ref(2, "mir")],
         "Side track from bowl toward the fixed back-wall window.",
         "Lua stands between the bowl and covered window; small dragon Mir remains on the floor beside the bowl behind her.",
         [beat(9, "Sea sound vanishes. Mir growls once. Lua walks to the window, lifts the cloth edge and sees cold sea light.")],
         "Lua notices silence", "Lua looking outside"),
    shot(36, "SC01-005", "V06", "집을 향하는 검은 해파리", 12, "night_coast", [ref(1, "jellyfish")],
         "Exterior wide with one restrained parallel drift along the established sea-to-house direction.",
         "The Black Jellyfish floats alone above the screen-right sea; Lua's warm house is fixed far-left as its destination.",
         [beat(6, "Ink-like smoke rotates inside the jellyfish as it turns toward the house."), beat(6, "It begins one slow glide leftward. Lua asks off-screen, \"저게… 널 찾으러 온 거야?\"")],
         "jellyfish turns toward house", "jellyfish approaching house", dialogue_ko="저게… 널 찾으러 온 거야?"),
]


shot_ids = {item["clip_id"] for item in SHOTS}
prompt_ids = set(VIDEO_BEATS_BY_CLIP)
if shot_ids != prompt_ids:
    missing = sorted(shot_ids - prompt_ids)
    extra = sorted(prompt_ids - shot_ids)
    raise RuntimeError(f"Detailed video prompt coverage mismatch: missing={missing}, extra={extra}")
for item in SHOTS:
    detailed_beats = VIDEO_BEATS_BY_CLIP[item["clip_id"]]
    detailed_seconds = sum(float(row["seconds"]) for row in detailed_beats)
    if abs(detailed_seconds - float(item["seconds"])) > 1e-6:
        raise RuntimeError(
            f"{item['clip_id']} detailed prompt duration mismatch: {detailed_seconds} != {item['seconds']}"
        )
    item["beats"] = detailed_beats
    if item["clip_id"] in DIALOGUE_OVERRIDES:
        item["dialogue_ko"] = DIALOGUE_OVERRIDES[item["clip_id"]]


def anchor_prompt(item: dict[str, Any]) -> str:
    filenames = [Path(row["source_path"]).name for row in item["refs"]]
    subjects = " ".join(IMAGE_SUBJECTS[name] for name in filenames if name in IMAGE_SUBJECTS)
    if not subjects:
        subjects = "No character, creature or recognizable body is visible."
    has_mir = "YoungMir.png" in filenames
    has_lua = "Lua.png" in filenames
    if has_mir and item["space_id"] in {"lua_house_day", "lua_house_night"}:
        scale_lock = "Young Mir's complete curled dragon body fits inside the shallow water bowl."
    elif has_mir and has_lua:
        scale_lock = "Young Mir's nose-to-tail-base body length equals Lua's torso length."
    elif has_mir:
        scale_lock = "Young Mir is approximately 45 cm from nose to tail base and remains much smaller than an adult human."
    else:
        scale_lock = "Keep every subject at the physically credible scale established by the location."
    frozen_state = STATIC_STATE_OVERRIDES.get(item["frame"], item["opening"])
    return (
        "Single cinematic still image from a premium stylized 3D ocean-fantasy animated feature, widescreen 16:9. "
        f"LOCATION LAYOUT: {SPACES[item['space_id']]} "
        f"STATIC FRAMING: {STATIC_FRAMING[item['frame']]} "
        f"VISIBLE SUBJECTS: {subjects} "
        f"EXACT FROZEN STATE: {frozen_state} "
        f"SCALE LOCK: {scale_lock} "
        "Depict one coherent frozen instant only. Keep anatomy, object count, contact state, screen position, "
        "depth separation, prop ownership and location topology unambiguous."
    )


def payload(item: dict[str, Any], previous: str | None, following: str | None) -> dict[str, Any]:
    relay = [{"order": i, **row} for i, row in enumerate(item["beats"], 1)]
    video_prompt = " ".join(row["prompt"] for row in item["beats"])
    image_revision = REGEN_REVISIONS.get(item["frame"], 2)
    anchor_id = f"ANC_{item['clip_id']}_VIDEO_FIRST_V2_IMAGE_R{image_revision}"
    anchor = {
        "background_id": anchor_id,
        "description": item["opening"],
        "source_path": None,
        "status": "missing",
        "review_status": "pending",
    }
    return {
        "schema_version": 4,
        "workflow": WORKFLOW,
        "prompt_strategy": PROMPT_STRATEGY,
        "director_prompt_inheritance": False,
        "project_id": PROJECT_ID,
        "scene_id": item["scene_id"],
        "clip_id": item["clip_id"],
        "frame_id": item["frame_id"],
        "sequence": item["frame"],
        "scenario_source": SOURCE,
        "fps": 24,
        "resolution": {"width": 1280, "height": 704},
        "maximum_duration_seconds": 20,
        "requested_seconds": item["seconds"],
        "world_prompt": STYLE,
        "global_prompt": compile_global_prompt(STYLE, item["refs"]),
        "reference_mode": "anchor_as_reference" if not item["refs"] else "subject_references",
        "references": item["refs"],
        "previous_clip": previous,
        "next_clip": following,
        "continuity_mode": "new_anchor",
        "continuity_from_clip": item["continuity_from"],
        "video_design": {
            "authored_first": True,
            "prompt_version": 2,
            "detail_basis": "SC01-002 candidate reviews plus scene-by-scene EP01 scenario reconstruction",
            "space_id": item["space_id"],
            "space_bible": SPACES[item["space_id"]],
            "camera": item["camera"],
            "opening_state": item["opening"],
            "state_in": item["state_in"],
            "state_out": item["state_out"],
            "dialogue_ko": item["dialogue_ko"],
            "compiled_video_prompt": video_prompt,
        },
        "relay_segments": relay,
        "anchor": dict(anchor),
        "background": dict(anchor),
        "background_generation": {
            "required": True,
            "derived_from": "video_design.opening_state",
            "image_prompt_version": image_revision,
            "space_id": item["space_id"],
            "frame_id": item["frame_id"],
            "suggested_filename": f"{item['frame_id']}_{item['clip_id']}_R{image_revision}.png",
            "aspect_ratio": "16:9",
            "recommended_resolution": {"width": 1280, "height": 704},
            "prompt": anchor_prompt(item),
            "negative_prompt": ", ".join(part for part in (NEGATIVE, NEGATIVE_OVERRIDES.get(item["frame"], "")) if part),
            "continuity_contract": {
                "state_in": item["state_in"],
                "state_out": item["state_out"],
                "continuity_from_clip": item["continuity_from"],
            },
        },
        "review_intent_ko": f"{item['title']} — 영상 시작 상태와 {item['space_id']} 공간 연속성 검증",
        "review": {
            "status": "reviewed",
            "warnings": [],
            "unresolved_questions": [],
            "notes": [
                "Video prompt authored before anchor-image prompt.",
                "Anchor prompt compiled from video opening state and shared space bible.",
                "SC01-002 review findings are constraints, not inherited scene prompts.",
            ],
        },
    }


def render_markdown(data: dict[str, Any], title: str) -> str:
    return (
        f"# {data['frame_id']} · {data['clip_id']} — {title}\n\n"
        "## Target video first\n\n"
        f"{data['video_design']['compiled_video_prompt']}\n\n"
        "## Derived anchor image prompt\n\n"
        f"{data['background_generation']['prompt']}\n\n"
        "## Machine Payload\n\n```json\n"
        + json.dumps(data, ensure_ascii=False, indent=2)
        + "\n```\n"
    )


def main() -> None:
    project = ROOT / "prompt_projects" / PROJECT_ID
    project.mkdir(parents=True, exist_ok=True)
    for stale in project.rglob("EP01_*_SC*.md"):
        stale.unlink()
    catalog: dict[str, Any] = {}
    scene_seconds: dict[str, int] = {}
    for index, item in enumerate(SHOTS):
        previous = SHOTS[index - 1]["clip_id"] if index else None
        following = SHOTS[index + 1]["clip_id"] if index + 1 < len(SHOTS) else None
        data = payload(item, previous, following)
        scene_dir = project / item["scene_id"]
        scene_dir.mkdir(parents=True, exist_ok=True)
        (scene_dir / f"{item['clip_id']}.md").write_text(
            render_markdown(data, item["title"]), encoding="utf-8"
        )
        anchor_id = data["anchor"]["background_id"]
        catalog[anchor_id] = {
            **data["background_generation"],
            "background_id": anchor_id,
            "description": data["anchor"]["description"],
            "continuity_mode": data["continuity_mode"],
            "continuity_from_clip": data["continuity_from_clip"],
        }
        scene_seconds[item["scene_id"]] = scene_seconds.get(item["scene_id"], 0) + item["seconds"]
    manifest = {
        "schema_version": 4,
        "project_id": PROJECT_ID,
        "title": PROJECT_TITLE,
        "description": "Clean-slate EP01 project authored video-first with anchor prompts derived from target shots.",
        "scenario_source": SOURCE,
        "workflow": WORKFLOW,
        "prompt_strategy": PROMPT_STRATEGY,
        "video_first": True,
        "video_prompt_revision": {
            "version": 2,
            "coverage": "36/36 clips",
            "organization": "scene-by-scene",
            "basis": "75 SC01-002 candidate reviews and EP01 scenario source",
        },
        "image_prompt_revision": {
            "default_version": 2,
            "selective_regeneration_version": 3,
            "selective_regeneration_frames": sorted(REGEN_REVISIONS),
            "basis": "visual audit of 36 generated V2 R2 anchors",
            "old_images_preserved": True,
        },
        "clip_count": len(SHOTS),
        "total_requested_seconds": sum(item["seconds"] for item in SHOTS),
        "scene_requested_seconds": scene_seconds,
        "status_summary": {"awaiting_background": len(SHOTS), "reviewed": 0, "invalid": 0},
        "policy": {
            "fps": 24,
            "max_clip_seconds": 20,
            "max_primary_characters": 2,
            "reference_slots": {"1": "character_1", "2": "character_2", "3": "prop_3", "4": "prop_4"},
            "prompt_order": ["target_video", "opening_state", "anchor_image"],
            "language": "English visual/action prompts; Korean dialogue only",
        },
        "review_basis": {
            "source": "SC01-002 candidate reviews",
            "review_count": 75,
            "rules": [
                "Keep successful stable dialogue and visible-path locomotion patterns.",
                "Split difficult physical state transitions only where the target video requires it.",
                "Use the result to improve video-to-anchor compilation, not to replace video intent with character poses.",
            ],
        },
    }
    (project / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (project / "background_catalog.json").write_text(
        json.dumps({"schema_version": 3, "project_id": PROJECT_ID, "backgrounds": catalog}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    links = project / "background_links.json"
    if not links.exists():
        links.write_text(json.dumps({"schema_version": 1, "project_id": PROJECT_ID, "links": {}}, indent=2) + "\n", encoding="utf-8")
    plan = [
        "# EP01 영상 우선 MSR V2",
        "",
        "영상 프롬프트를 먼저 확정하고 이미지 앵커는 영상 시작 상태에서 파생합니다.",
        "",
        "| 순서 | 프레임 | 클립 | 공간 | 길이 | 제목 | 상태 입력 → 출력 |",
        "|---:|---|---|---|---:|---|---|",
    ]
    for item in SHOTS:
        plan.append(
            f"| {item['frame']} | `{item['frame_id']}` | `{item['clip_id']}` | `{item['space_id']}` | "
            f"{item['seconds']}초 | {item['title']} | {item['state_in']} → {item['state_out']} |"
        )
    (project / "EP01_VIDEO_FIRST_PLAN.txt").write_text("\n".join(plan) + "\n", encoding="utf-8")
    print(json.dumps({
        "project_id": PROJECT_ID,
        "clips": len(SHOTS),
        "seconds": manifest["total_requested_seconds"],
        "scene_seconds": scene_seconds,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
