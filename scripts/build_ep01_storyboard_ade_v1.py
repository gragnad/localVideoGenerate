#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from h3_prompt_project_builder import build_project


PROJECT_DIR = ROOT / "projects" / "RaisingaDragonSeason01"
PROJECT_ID = "RaisingaDragonSeason01_EP01_H3_R2V_STORYBOARD_ADE_V1"
SPEC_PATH = PROJECT_DIR / "EP01_H3_R2V_STORYBOARD_ADE_V1_SPEC.json"
CONTRACTS_PATH = PROJECT_DIR / "EP01_H3_R2V_STORYBOARD_ADE_V1_EVENT_CONTRACTS.json"
LINEAGE = [
    "EP01_WEBTOON_VIDEO_SCREENPLAY_V1.md",
    "storyboards_ep01_detailed_v1/EP01_S01_S02_DETAILED_STORYBOARD_PLAN_V1.md",
    "storyboards_ep01_detailed_v1/EP01_S03_S05_DETAILED_STORYBOARD_PLAN_V1.md",
    "storyboards_ep01_detailed_v1/EP01_FULL_DETAILED_STORYBOARD_AUDIT_V1.md",
    "H3_R2V_SCENARIO_AUTHORING_GUIDE.md",
]


def clip(
    clip_id: str,
    duration: float,
    references: list[str | dict],
    incoming: list[int],
    outgoing: list[int],
    summary: str,
    beats: list[str],
    cameras: list[str],
    action_cues: list[str],
) -> dict:
    assert len(beats) == len(cameras) == 4
    assert len(action_cues) == 3
    return {
        "clip_id": clip_id,
        "duration": duration,
        "references": references,
        "incoming": incoming,
        "outgoing": outgoing,
        "summary": summary,
        "beats": beats,
        "cameras": cameras,
        "action_cues": action_cues,
    }


CLIPS = [
    clip("EP01-S01-NC01", 8.5, ["mir-solo"], [1], [1],
         "A storm repeatedly conceals a cyan signal until lightning reveals injured Young Mir moving toward shore.",
         [
             "A violent night-sea extreme wide shows only <Subject 1> YoungMir's tiny cyan light below the surface; no dragon body is readable yet.",
             "A foreground black wave crosses and briefly hides the same cyan signal without forming a creature.",
             "An underwater following view tracks the same signal being forced shoreward beneath lightning-split water.",
             "One lightning flash finally reveals <Subject 1> YoungMir's single injured baby-dragon body inside the cyan signal.",
         ],
         ["storm-sea extreme wide", "compressed wave-level view", "submerged tracking view", "lightning-lit underwater reveal"],
         ["the black foreground wave crossing the signal", "the shoreward pull of the current", "the lightning flash expanding through the water"]),
    clip("EP01-S01-NC02", 9.5, ["mir-solo"], [1], [1],
         "Young Mir catches collapsing ruins, loses the grip, and must find another way out.",
         [
             "A collapsing underwater-ruin wide carries <Subject 1> YoungMir between broken coral columns.",
             "A low side medium shows <Subject 1> YoungMir hook one forepaw over a broken stone edge and arrest the drift.",
             "The current stretches <Subject 1> YoungMir away from the hold while the tail crystal weakens like breath.",
             "An extreme forepaw insert shows the stone cracking and the claws beginning to slip.",
         ],
         ["collapsing-ruin wide", "low side medium", "current-aligned body profile", "forepaw macro insert"],
         ["the current pulling Mir past the broken column", "the tail crystal's fading pulse", "the crack racing beneath Mir's claws"]),
    clip("EP01-S01-NC03", 10.5, ["mir-solo"], [1], [1],
         "The black current closes Mir's route; Mir uses the tail crystal once and escapes by recoil rather than victory.",
         [
             "Over <Subject 1> YoungMir's shoulder, a black non-creature current erases blue motes and closes the route to the surface.",
             "A tight oblique view joins <Subject 1> YoungMir's fearful face and dim tail crystal as the body coils to gather its last force.",
             "The tail crystal ignites once and a short cyan pressure front touches only the leading edge of the black current.",
             "The leading black edge compresses backward while the same recoil throws <Subject 1> YoungMir upward into the escape current.",
         ],
         ["rear shoulder route view", "tight face-and-tail oblique", "low pressure-contact profile", "wide recoil trajectory"],
         ["the black current covering the last blue motes", "Mir's coiling tail and brightening crystal", "the cyan pressure front rebounding from the black edge"]),
    clip("EP01-S01-NC04", 8.5, ["mir-solo"], [1], [1],
         "A memory fragment breaks, unconscious Mir reaches the storm surface, and the cave receives the cyan signal.",
         [
             "A subjective fractured vision places <Subject 1> YoungMir beneath a crown-marked gate and incomplete enormous dragon shadows; no full adult dragon is shown.",
             "The fragment collapses into reality as unconscious <Subject 1> YoungMir is carried upward by the current.",
             "A cyan body-light breaks the storm surface and is immediately swallowed by the next wave.",
             "The same wave runs into an empty coastal cave and <Subject 1> YoungMir's small cyan light blinks once from deep darkness.",
         ],
         ["fractured subjective memory", "submerged upward medium", "storm-surface long lens", "cave-threshold deep wide"],
         ["the memory shard collapsing into bubbles", "the upward current carrying Mir", "the next wave swallowing and carrying the cyan light"]),
    clip("EP01-S02-NC01", 8.5, ["lua", "harpoon"], [1], [1],
         "Lua is isolated below the repairing village and confidently lines up an ordinary fishing-harpoon attempt.",
         [
             "A post-storm village wide shows residents repairing boats while <Subject 1> Lua stands alone below the breakwater.",
             "A high separation composition keeps villagers above and <Subject 1> Lua alone in shallow water below.",
             "A fish-level low view shows <Subject 1> Lua approach with the single ordinary harpoon from <Picture 2>.",
             "A close view of <Subject 1> Lua's eyes and two-hand grip shows false certainty as she prepares the throw; her wrist is plain and unmarked.",
         ],
         ["village-and-breakwater wide", "high separation master", "fish-level approach", "eyes-and-grip close-up"],
         ["the villagers hauling a broken net", "the fish gliding across the shallow lane", "Lua's grip tightening along the harpoon shaft"]),
    clip("EP01-S02-NC02", 9.5, ["lua", "harpoon"], [1], [1],
         "Lua commits to the harpoon thrust, the fish turns, the rope catches her ankle, and the same force drops her into the water.",
         [
             "<Subject 1> Lua plants the lead foot and rotates hips and shoulders to drive the harpoon from <Picture 2> forward.",
             "The fish changes direction just before the harpoon point enters the water and escapes the attack line.",
             "The attached rope wraps once around <Subject 1> Lua's opposite ankle and becomes taut.",
             "The same rope force pulls <Subject 1> Lua off balance into a seated splash while the fish exits and the harpoon remains intact.",
         ],
         ["full-body action profile", "waterline miss insert", "ankle-and-rope close-up", "shallow-water impact wide"],
         ["Lua's rotating shoulders driving the shaft", "the fish cutting across the point", "the rope snapping taut around the ankle"]),
    clip("EP01-S02-NC03", 8.5, ["lua", "harpoon"], [1], [1],
         "The children leave, Lua's embarrassment hardens into resolve, and the old fisherman observes without physically correcting her.",
         [
             "From behind wet <Subject 1> Lua, several village children laugh in the distance while she gives them a guarded side glance.",
             "A wet-hair close three-quarter view keeps <Subject 1> Lua's mouth casually composed but her eyes visibly ashamed; she does not look at camera.",
             "After the children leave, an insert shows <Subject 1> Lua's hand tightening around the ordinary harpoon handle from <Picture 2>.",
             "A distant two-person composition shows the old fisherman and <Subject 1> Lua separately watching the sea; he does not touch her or correct her stance.",
         ],
         ["rear social medium", "close three-quarter reaction", "harpoon-grip insert", "distant observational two-shot"],
         ["the children's laughter moving away", "Lua pushing wet hair aside", "Lua's knuckles tightening around the handle"]),
    clip("EP01-S02-NC04", 8.5, ["lua", "harpoon"], [1], [1],
         "A warning points toward the cave, a cyan reflection answers, and Lua actively chooses to run toward it.",
         [
             "The old fisherman points toward the storm cave while <Subject 1> Lua suppresses a reply and follows his direction.",
             "A puddle close-up catches one distant cyan cave reflection and the edge of <Subject 1> Lua's watching eye.",
             "<Subject 1> Lua checks the adults, frees the ankle rope, wraps it safely, and secures the ordinary harpoon from <Picture 2>.",
             "A long shot sends <Subject 1> Lua running toward the cave while one tiny black stain remains beneath the breakwater.",
         ],
         ["warning two-shot", "puddle reflection macro", "concealed preparation medium", "cave-bound running long shot"],
         ["the fisherman's pointing hand defining the cave direction", "the cyan reflection rippling across the puddle", "Lua pulling the rope tight against her body"]),
    clip("EP01-S03-NC01", 8.5, ["lua", "harpoon"], [1], [1],
         "Lua enters the curved cave, reacts to a pebble behind, then lowers the harpoon toward a tiny cry ahead.",
         [
             "A threshold wide follows <Subject 1> Lua entering with the ordinary harpoon from <Picture 2> aimed into darkness; her wrist remains unmarked.",
             "A side medium follows the curved passage as outside reflection disappears and <Subject 1> Lua's bravado tightens into caution.",
             "A low rear view catches one pebble rolling behind and <Subject 1> Lua pivoting body and harpoon toward it.",
             "An oblique close-up shows <Subject 1> Lua lock eyes on an unseen tiny cry ahead and lower the harpoon point.",
         ],
         ["threshold rear wide", "curved-passage side medium", "pebble-level rear action view", "oblique listening close-up"],
         ["the cave daylight disappearing behind the bend", "the single pebble rolling past Lua's heel", "Lua's pivot ending as the tiny cry arrives ahead"]),
    clip("EP01-S03-NC02", 9.5, ["lua", "mir-duo", "harpoon"], [1, 2], [1, 2],
         "A partial shape becomes injured Young Mir; Mir slips, and Lua deliberately removes the harpoon from their shared space.",
         [
             "Through a narrow rock gap, only portions of <Subject 2> YoungMir's horns, wet tail crystal, and cracked scales are readable while <Subject 1> Lua watches.",
             "<Subject 1> Lua takes one sideways step and a new axis reveals <Subject 2> YoungMir's single complete tiny injured body.",
             "A low side medium shows <Subject 2> YoungMir attempt retreat and slip one wet forepaw while <Subject 1> Lua stays back.",
             "A cave-floor profile shows <Subject 1> Lua place the harpoon from <Picture 3> flat behind herself, kneel, and offer one empty palm to <Subject 2> YoungMir.",
         ],
         ["rock-gap restricted view", "new-axis reveal wide", "Mir-level slip medium", "floor-height de-escalation two-shot"],
         ["Lua's sideways step clearing the rock gap", "Mir's wet forepaw sliding across stone", "the harpoon shaft settling flat behind Lua"]),
    clip("EP01-S03-NC03", 8.5, ["lua", "mir-duo"], [1, 2], [1, 2],
         "Mir holds Lua's finger; Lua begins to recoil, recognizes panic rather than attack, and stops.",
         [
             "Over <Subject 2> YoungMir's shoulder, kneeling <Subject 1> Lua slowly extends one open hand; her wrist remains unmarked.",
             "An extreme contact close-up shows <Subject 2> YoungMir gently close the mouth around <Subject 1> Lua's finger as a hold, not a violent bite.",
             "An oblique reaction medium shows <Subject 1> Lua begin a short reflexive pull while <Subject 2> YoungMir remains attached and frightened.",
             "A recognition close-up shows <Subject 1> Lua stop after seeing <Subject 2> YoungMir's forepaws and jaw cling for safety; Mir remains supported on the floor.",
         ],
         ["Mir-shoulder approach medium", "finger-contact macro", "oblique recoil medium", "intimate recognition close-up"],
         ["Lua's fingertip entering Mir's reach", "Lua's elbow beginning the recoil", "Mir's forepaws tightening without attacking"]),
    clip("EP01-S03-NC04", 8.5, ["lua", "mir-duo", "wrist-mark"], [1, 2], [1, 2],
         "One blood drop causes still water, Mir's chest emblem, then Lua's first wrist mark in that exact order.",
         [
             "A macro shows one blood drop from <Subject 1> Lua's fingertip touch a cracked chest scale on <Subject 2> YoungMir; Lua's wrist is still unmarked.",
             "A ground insert shows shallow cave ripples become completely still immediately after the contact.",
             "A close-up shows <Subject 2> YoungMir's chest emblem ignite cyan first while <Subject 1> Lua's wrist has not yet lit.",
             "An oblique two-shot shows the single wrist mark from <Picture 3> appear on <Subject 1> Lua for the first time, after Mir's light, and both subjects inhale together.",
         ],
         ["blood-contact macro", "glassy-water ground insert", "Mir chest close-up", "resonance relational two-shot"],
         ["the blood drop leaving Lua's fingertip", "the final ripple stopping around their hands", "Mir's chest light casting cyan onto Lua's previously bare wrist"]),
    clip("EP01-S03-NC05", 9.5, ["lua", "mir-duo", "harpoon", "heartstone"], [1], [1, 2],
         "Fragments reveal ruins and the obscured Heartstone; back in the cave, Mir crawls to Lua and Lua carries Mir out with the harpoon recovered.",
         [
             "Within <Subject 1> Lua's subjective vision, a fractured tilted glimpse shows collapsed dragon ruins and incomplete enormous sleeping-dragon silhouettes.",
             "A second compressed vision shows the Heartstone from <Picture 4> weakening behind an abstract black crown-shaped shadow with no anatomy.",
             "Reality returns as <Subject 1> Lua turns toward an unseen adult call and <Subject 2> YoungMir makes exactly one exhausted crawl toward her.",
             "A rear long shot shows <Subject 1> Lua carry <Subject 2> YoungMir fully supported in cloth through the side passage with the harpoon from <Picture 3> securely recovered; Mir's eye looks back.",
         ],
         ["fractured subjective ruin view", "compressed symbolic Heartstone insert", "grounded cave decision medium", "side-passage departure long shot"],
         ["the ruin fragment shattering into the Heartstone vision", "the adult call snapping Lua's view back to the cave", "Mir's single crawl causing Lua to unfold the cloth"]),
    clip("EP01-S04-NC01", 8.5, ["lua", "mir-duo"], [1, 2], [1, 2],
         "Lua closes the house, listens, unwraps Mir, and carries the fully supported baby toward the basin.",
         [
             "An interior wide shows <Subject 1> Lua enter carrying cloth-wrapped <Subject 2> YoungMir and close the door.",
             "A low door-side medium shows <Subject 1> Lua brace against the closed door and listen while safely cradling <Subject 2> YoungMir.",
             "A table-height close-up shows <Subject 1> Lua loosen the cloth and <Subject 2> YoungMir cautiously reveal only the head.",
             "A clear three-quarter medium shows <Subject 1> Lua support <Subject 2> YoungMir under chest and rear body while moving toward the basin.",
         ],
         ["interior entrance wide", "low door-side tension medium", "cloth-level reveal close-up", "supported-carry three-quarter medium"],
         ["the door closing behind Lua", "the outside footsteps fading", "the cloth fold dropping to reveal Mir's head"]),
    clip("EP01-S04-NC02", 8.5, ["lua", "mir-duo"], [1, 2], [1, 2],
         "Water relaxes Mir; dried fish fails, and Mir chooses a shell while Lua's tension turns to amusement.",
         [
             "At basin side, <Subject 1> Lua lowers <Subject 2> YoungMir into shallow water while supporting chest and rear body.",
             "A waterline close-up shows <Subject 2> YoungMir's claws and shoulders relax as water wraps the scales.",
             "Across the low table, <Subject 1> Lua offers one dried fish and <Subject 2> YoungMir recoils and turns away in clear disgust.",
             "A warm table-height medium shows <Subject 2> YoungMir hug one pale shell while <Subject 1> Lua watches with restrained amusement.",
         ],
         ["basin-side support medium", "waterline relaxation close-up", "food-offer table two-shot", "warm shell-choice medium"],
         ["Lua's hands lowering Mir through the waterline", "Mir turning completely away from the dried fish", "Mir's forepaws pulling the single shell to the chest"]),
    clip("EP01-S04-NC03", 8.5, ["lua", "mir-duo", "harpoon"], [1, 2], [1, 2],
         "Footsteps stop; Lua takes the harpoon and remains between the door and Mir even after danger passes.",
         [
             "From beside <Subject 2> YoungMir, a medium-wide shows both subjects react when footsteps stop outside the closed door.",
             "A clean profile wide places door, shielding <Subject 1> Lua, and tiny <Subject 2> YoungMir in order as Lua takes the harpoon from <Picture 3>.",
             "A door-latch close-up keeps <Subject 1> Lua's alert profile and harpoon while footsteps pass away; <Subject 2> YoungMir stays behind her.",
             "A low view beside <Subject 2> YoungMir shows <Subject 1> Lua remain planted between Mir and the door, confirming protection.",
         ],
         ["Mir-side alert medium-wide", "profile blocking wide", "door-latch threat close-up", "protected Mir-level medium"],
         ["both heads snapping toward the stopped footsteps", "Lua crossing the room and lifting the harpoon", "the departing footsteps leaving the latch motionless"]),
    clip("EP01-S04-NC04", 8.5, ["lua", "mir-duo"], [1, 2], [1, 2],
         "Mir lifts one droplet, it lands on Lua, then their two marks pulse together as the sea becomes too still.",
         [
             "An oblique basin medium shows <Subject 2> YoungMir and <Subject 1> Lua concentrate on the water with both marks dark.",
             "A low macro shows exactly one droplet floating between <Subject 2> YoungMir and <Subject 1> Lua as both track it.",
             "A side reaction close-up shows the same droplet on <Subject 1> Lua's forehead while <Subject 2> YoungMir remains dry and proud; neither looks at camera.",
             "A window-side profile two-shot shows <Subject 2> YoungMir's chest and <Subject 1> Lua's wrist pulse once together as they look at each other and the sea remains unnaturally flat.",
         ],
         ["oblique basin concentration medium", "single-droplet macro", "side comic reaction close-up", "window-side uncanny profile two-shot"],
         ["the water surface dimpling beneath Mir's focus", "the single droplet drifting toward Lua", "the droplet striking Lua's forehead before both marks answer"]),
    clip("EP01-S05-NC01", 8.5, ["lua", "mir-duo"], [1, 2], [1, 2],
         "Separate sleeping rhythms become one through the linked marks and transition into the shared dream.",
         [
             "A high night-room extreme wide separates sleeping <Subject 1> Lua on the mat and sleeping <Subject 2> YoungMir in the basin.",
             "A low lateral composition shows the two subjects breathe at visibly different phases.",
             "One unified depth composition places <Subject 1> Lua's wrist mark in foreground and <Subject 2> YoungMir's chest emblem in the basin background as faint pulses alternate.",
             "A floor-level wide shows the two faint pulses and breathing align while restrained cyan dream haze forms in the shared room.",
         ],
         ["high corner sleep wide", "low lateral rhythm view", "single-frame depth-linked mark close-up", "floor-level dream-transition wide"],
         ["Lua's exhale contrasting with Mir's inhale", "the alternating faint mark pulses crossing the room", "the two pulses meeting on the same beat"]),
    clip("EP01-S05-NC02", 9.5, ["mir-solo", "heartstone"], [1], [1],
         "In the nightmare, an abstract shadow blocks Mir, a faceless prince shadow appears, and darkness makes unchanged baby Mir feel smaller.",
         [
             "A vast dream-chamber wide shows <Subject 1> YoungMir approach the weakening Heartstone from <Picture 2>.",
             "A low rear view shows an abstract black crown-shaped shadow with no anatomy spread across Mir's path to the Heartstone.",
             "An oblique wide shows only an incomplete faceless prince-dragon shadow on mist behind <Subject 1> YoungMir, never a solid adult dragon.",
             "From near the dim Heartstone, a compressed view makes unchanged baby <Subject 1> YoungMir appear smaller only through expanding negative space.",
         ],
         ["oppressive dream-chamber wide", "low rear blocked-path view", "oblique identity-shadow wide", "Heartstone-side isolation compression"],
         ["Mir's steps carrying him toward the weakening blue light", "the black void spreading across the path", "the incomplete prince shadow lengthening behind Mir"]),
    clip("EP01-S05-NC03", 8.5, ["lua", "mir-duo"], [1, 2], [1, 2],
         "Mir thrashes, Lua wakes and lifts the whole body correctly, then experiences Mir's fear through resonance.",
         [
             "A basin close-up shows sleeping <Subject 2> YoungMir thrash and splash shallow water in the nightmare.",
             "A low medium toward the mat shows <Subject 1> Lua jolt awake and immediately locate <Subject 2> YoungMir.",
             "An oblique rescue medium shows <Subject 1> Lua lift <Subject 2> YoungMir with both hands under chest and rear body.",
             "An intimate close-up shows <Subject 1> Lua safely cradle <Subject 2> YoungMir and clutch her own chest as his fear crosses the glowing wrist mark.",
         ],
         ["basin nightmare close-up", "wake-up low medium", "supported-lift oblique medium", "transferred-fear intimate close-up"],
         ["Mir's splash reaching the floor beside the mat", "Lua's gaze locking onto the basin", "water dripping from Mir as Lua draws him to her chest"]),
    clip("EP01-S05-NC04", 8.5, ["lua", "mir-duo", "black-jelly-3"], [1, 2], [1, 2, 3],
         "Lua recognizes Mir's fear, their breathing calms, the wave sound vanishes, and the black jellyfish is revealed outside.",
         [
             "A three-quarter close-up shows <Subject 1> Lua look down at <Subject 2> YoungMir and understand the fear is his, not hers.",
             "A wrist-level macro shows <Subject 2> YoungMir rest the head against <Subject 1> Lua's single wrist mark as their breathing calms.",
             "A house-side wide shows both subjects turn together toward the window when the wave sound disappears.",
             "Over their partial silhouettes, a long-lens window view reveals exactly one distant <Subject 3> BlackJellyfish floating on motionless moonlit water.",
         ],
         ["compassionate three-quarter close-up", "single-mark soothing macro", "simultaneous window-turn wide", "over-shoulder jellyfish reveal long lens"],
         ["Mir settling his head against Lua's wrist", "the last audible wave dying outside", "both eyelines converging through the window"]),
    clip("EP01-S05-NC05", 9.5, ["lua", "mir-duo", "black-jelly-3"], [3], [3],
         "The black jellyfish aims at the house; Lua tightens her hold, and one tentacle marks and freezes the exterior wall.",
         [
             "A sea-surface medium shows exactly one <Subject 3> BlackJellyfish as internal ink gathers toward the distant coastal house.",
             "An underwater tracking view shows the same <Subject 3> BlackJellyfish align its long thin tentacles toward the single house.",
             "An interior oblique medium shows <Subject 2> YoungMir warn while <Subject 1> Lua tightens both arms around him and watches the threat.",
             "An exterior wall macro shows one tentacle tip from <Subject 3> BlackJellyfish touch the wood and spread one black stain with a thin frost rim into blackout.",
         ],
         ["surface creature-intent medium", "underwater route tracking view", "interior protective reaction medium", "wall-contact extreme macro"],
         ["the ink mass shifting inside the transparent bell", "the tentacles fanning into one houseward axis", "Mir's warning causing Lua's arms to tighten"]),
]


def subject_text(ids: list[int]) -> str:
    return " and ".join(f"<Subject {value}>" for value in ids)


def labeled(value: str, references: list[str | dict]) -> str:
    text = value
    if "lua" in references:
        text = text.replace("Lua", "<Subject 1> Lua")
    if "mir-duo" in references:
        text = text.replace("Mir", "<Subject 2> YoungMir")
    elif "mir-solo" in references:
        text = text.replace("Mir", "<Subject 1> YoungMir")
    return text


def build_payloads() -> tuple[dict, dict]:
    asset_catalog: dict[str, dict] = {
        "lua": {
            "role": "lua_identity",
            "label": "Lua identity sheet",
            "copy_from": "Lua.png",
            "subject_id": 1,
            "subject_name": "Lua",
            "subject_description": "One small brown-skinned fishing-village girl with a messy brown bun, large amber-brown eyes, freckles, a worn beige-gray sleeveless tunic and shorts, sandals, shell necklace, and the exact single wrist mark state stated by each Shot. Preserve one person, face, age, body proportions, clothing, and gaze toward the actual scene cause rather than the camera.",
            "retention_description": "Preserve the same single Lua identity and clip-specific wrist-mark state in every cited Shot",
        },
        "mir-solo": {
            "role": "young_mir_identity",
            "label": "Young Mir identity sheet",
            "copy_from": "YoungMir.png",
            "subject_id": 1,
            "subject_name": "YoungMir",
            "subject_description": "One tiny injured pearly ice-blue baby dragon with two dark curved horns, huge blue eyes, translucent fin ears and wings, four limbs, one blue teardrop tail crystal, and one chest emblem. Preserve baby scale and never create an adult body unless a Shot explicitly requests only a non-physical shadow.",
            "retention_description": "Preserve one tiny Young Mir body with exact horns, fins, wings, tail crystal, chest emblem, and baby scale",
        },
        "mir-duo": {
            "role": "young_mir_identity",
            "label": "Young Mir identity sheet",
            "copy_from": "YoungMir.png",
            "subject_id": 2,
            "subject_name": "YoungMir",
            "subject_description": "One tiny injured pearly ice-blue baby dragon with two dark curved horns, huge blue eyes, translucent fin ears and wings, four limbs, one blue teardrop tail crystal, and one chest emblem. Preserve baby scale and never turn Mir into a human child or adult dragon.",
            "retention_description": "Preserve one tiny Young Mir body with exact anatomy, chest emblem, and baby scale",
        },
        "black-jelly-3": {
            "role": "black_jellyfish_identity",
            "label": "Black jellyfish identity sheet",
            "copy_from": "BLACK JELLYFISH .png",
            "subject_id": 3,
            "subject_name": "BlackJellyfish",
            "subject_description": "One transparent smoky-gray jellyfish bell containing one dense black ink mass with many long thin black tentacles. Preserve one creature and never merge it with the earlier non-creature black current.",
            "retention_description": "Preserve one black jellyfish with one transparent bell, internal ink, and continuous thin tentacles",
        },
        "harpoon": {
            "role": "major_prop_harpoon",
            "label": "Ordinary fishing harpoon identity sheet",
            "copy_from": "spear.png",
            "standalone_picture_name": "the single ordinary fishing harpoon",
            "standalone_picture_description": "Use one fixed-length weathered wooden pole with one dark chipped stone point, rope bindings, and small shell charms. It moves only through Lua's physical grip and remains intact.",
            "retention_shots": [1, 2, 3, 4],
            "retention_description": "Preserve one intact ordinary fishing harpoon only in the Shots that state it is visible",
        },
        "heartstone": {
            "role": "major_prop_heartstone",
            "label": "Heartstone identity reference",
            "copy_from": "Heartstone.png",
            "standalone_picture_name": "the heart-shaped blue Heartstone",
            "standalone_picture_description": "Preserve one heart-shaped translucent blue crystal in its dark wave-carved base; only the stated light intensity may change.",
            "retention_shots": [1, 2, 3, 4],
            "retention_description": "Preserve the same single Heartstone form and vary only its stated brightness",
        },
        "wrist-mark": {
            "role": "major_detail_wrist_mark",
            "label": "Dragon Heart wrist mark reference",
            "copy_from": "Dragon_Heart_Wrist_Mark.png",
            "standalone_picture_name": "Lua's single Dragon Heart wrist mark",
            "standalone_picture_description": "Use this exact blue spiral-crown mark once on Lua's wrist. It does not exist before the Shot that explicitly creates it and must never multiply or extend up the arm.",
            "retention_shots": [4],
            "retention_description": "Create the exact single mark only in Shot 4 after Mir's chest emblem lights",
        },
    }
    for row in CLIPS:
        key = "storyboard-" + row["clip_id"].lower()
        asset_catalog[key] = {
            "role": "chronological_storyboard",
            "label": f'{row["clip_id"]} reviewed four-panel storyboard',
            "copy_from": f'storyboards_ep01_detailed_v1/{row["clip_id"]}_STORYBOARD_16X9_V1.png',
            "reference_kind": "storyboard",
            "storyboard_panel_count": 4,
            "storyboard_reading_order": "top-left, top-right, bottom-left, bottom-right",
            "storyboard_beats": row["beats"],
            "standalone_picture_name": "the chronological four-panel storyboard",
            "standalone_picture_description": "Read the 2x2 grid as ordered video checkpoints: top-left, top-right, bottom-left, bottom-right. Preserve each panel's actual composition, blocking, gaze, emotion, prop state, and causal continuity, but never render the grid or duplicate the scene in the output video.",
            "retention_shots": [1, 2, 3, 4],
            "retention_description": "Preserve all four storyboard checkpoints in one-to-one Shot order",
        }

    clips_payload = []
    contracts = {}
    for sequence, row in enumerate(CLIPS, start=1):
        clip_id = row["clip_id"]
        scene_id = clip_id.rsplit("-", 1)[0]
        storyboard_key = "storyboard-" + clip_id.lower()
        references = [*row["references"], storyboard_key]
        storyboard_picture_id = len(references)
        step = row["duration"] / 4
        beat_rows = [
            {"beat_id": f"P{index}", "description": value}
            for index, value in enumerate(row["beats"], start=1)
        ]
        plans = {}
        for variant_id in ("A", "D", "E"):
            shots = []
            for index in range(4):
                camera = labeled(row["cameras"][index], row["references"])
                if variant_id == "A":
                    camera_text = (
                        f"Directly reproduce the reviewed storyboard checkpoint with its {camera}. "
                        "Do not invent travel, a new pose, a new prop, a new effect, or an event beyond this checkpoint."
                    )
                elif variant_id == "D":
                    camera_text = (
                        f"Maintain the accumulated physical state in a {camera}; keep the action axis, scale, gaze, contact, prop, and effect continuity readable."
                    )
                else:
                    camera_text = (
                        f"Maintain the accumulated physical state in a {camera}; use only approved in-scene motion to reveal the next state without resetting any pose."
                    )
                shot = {
                    "panel_index": index + 1,
                    "panel_position": ("top-left", "top-right", "bottom-left", "bottom-right")[index],
                    "camera": camera_text,
                    "beat_ids": [f"P{index + 1}"],
                }
                if index:
                    shot["start_seconds"] = round(step * index, 3)
                if index < 3 and variant_id == "D":
                    next_camera = labeled(row["cameras"][index + 1], row["references"])
                    paths = (
                        f"Dolly 0.8 metres right along the established screen axis, adjust lens height by half a body, and settle from the {camera} into the {next_camera} without a cut or pose reset.",
                        f"Arc 25 degrees clockwise around the active subject at chest height, tighten one lens size, and settle from the {camera} into the {next_camera} while preserving screen direction.",
                        f"Drift 0.7 metres behind the active eyeline and crane 0.5 metres toward its destination, arriving from the {camera} in the {next_camera} before the action changes.",
                    )
                    shot["transition_to_next"] = paths[index]
                elif index < 3 and variant_id == "E":
                    next_camera = labeled(row["cameras"][index + 1], row["references"])
                    cue = labeled(row["action_cues"][index], row["references"])
                    shot["transition_to_next"] = (
                        f"Use {cue} as the only moving foreground or eyeline cue; pan with that exact motion and let it clear the frame to reveal the {next_camera}, without adding another action."
                    )
                shots.append(shot)
            plans[variant_id] = {
                "emphasis": {
                    "A": "direct reproduction of all four reviewed storyboard checkpoints",
                    "D": "continuous camera travel that arrives at the next reviewed checkpoint inside the current Shot",
                    "E": "action-motivated reveal using only the approved motion already present in the storyboard",
                }[variant_id],
                "shots": shots,
            }

        incoming_text = subject_text(row["incoming"])
        outgoing_text = subject_text(row["outgoing"])
        bridge_in = f"Continue the exact accumulated state with {incoming_text}; begin only the first event visible in {clip_id} and do not reset pose, scale, prop, light, or contact."
        bridge_out = f"End with {outgoing_text} in the exact panel-4 accumulated state so the next clip can continue without a pose, scale, gaze, prop, light, effect, or contact reset."
        contracts[clip_id] = {
            "shared_event": row["summary"],
            "bridge_in_id": f"EP01_STATE_{sequence - 1:02d}",
            "bridge_out_id": f"EP01_STATE_{sequence:02d}",
            "boundary_policy": "terminal" if sequence == len(CLIPS) else "referenced_cut",
            "source_shot_ids": [f"{scene_id}-STORYBOARD-{clip_id.rsplit('-', 1)[1]}"],
            "incoming_reference_subjects": row["incoming"],
            "outgoing_reference_subjects": row["outgoing"],
            "incoming_bridge": bridge_in,
            "outgoing_bridge": bridge_out,
            "storyboard_required": True,
            "storyboard_picture_id": storyboard_picture_id,
            "storyboard_panel_count": 4,
            "beats": beat_rows,
            "candidate_plans": plans,
        }
        clips_payload.append({
            "scene_id": scene_id,
            "clip_id": clip_id,
            "sequence": sequence,
            "source_shot_id": f"{scene_id}-STORYBOARD-{clip_id.rsplit('-', 1)[1]}",
            "status": "verified_storyboard",
            "duration_seconds": row["duration"],
            "references": references,
            "prompt_base": {
                "summary": row["summary"],
                "style_opening": [
                    "A polished cinematic 3D animated fantasy episode uses physically grounded water, restrained cyan Dragon Heart light, and clear emotional staging",
                    "Preserve the reviewed storyboard's 16:9 composition, action axis, character scale, gaze, prop continuity, and cause-to-effect motion",
                ],
                "overall_soundscape": "Natural surf, water, wet stone or wood contact, cloth, breathing, footsteps, and creature movement only as required by the visible event; no intelligible dialogue or lip sync in this deferred-dialogue version.",
                "non_diegetic_music": "Restrained cinematic pulse follows the emotional causality, leaves comedy light, and recedes under the final threat.",
            },
            "prompt_variants": [
                {"variant_id": "A", "label": "후보 A", "rationale": f"{clip_id} 검수 스토리보드의 네 체크포인트를 발명 없이 직접 재현", "prompt_spec": {}},
                {"variant_id": "D", "label": "후보 D", "rationale": f"{clip_id}의 실제 카메라 경로가 다음 체크포인트 구도에 현재 Shot 안에서 도착", "prompt_spec": {}},
                {"variant_id": "E", "label": "후보 E", "rationale": f"{clip_id} 내부의 승인된 행동·시선·소품 움직임만으로 다음 체크포인트를 공개", "prompt_spec": {}},
            ],
            "canonical_source_lineage": LINEAGE,
            "continuity_in": f"EP01_STATE_{sequence - 1:02d}",
            "continuity_out": f"EP01_STATE_{sequence:02d}",
            "storyboard_review_contract": {
                "picture_id": storyboard_picture_id,
                "panel_positions": ["top-left", "top-right", "bottom-left", "bottom-right"],
                "panel_to_shot": "one_to_one",
                "visual_asset_status": "agent_visually_reviewed",
            },
            "authoring_notes": "Dialogue and lip-sync rules are intentionally deferred. The basic duration correction is applied once per clip as a half-second step, never once per storyboard panel.",
            "visual_review": "agent_passed_full_storyboard_sheet_review",
            "semantic_review": "storyboard_first_causality_and_continuity_passed",
        })

    spec = {
        "schema_version": 2,
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP01 · Storyboard-First A/D/E V1",
        "description": "New EP01 H3 R2V prompt project built only after reviewing 22 detailed four-panel storyboards. Each panel maps one-to-one to four Shots; A is direct reproduction, D is continuous camera travel, and E is an action-motivated reveal.",
        "source_policy": "storyboard_first_no_prior_prompt_project_lineage",
        "canonical_source_lineage": LINEAGE,
        "build_script": "scripts/build_ep01_storyboard_ade_v1.py",
        "event_contracts_file": CONTRACTS_PATH.name,
        "asset_catalog": asset_catalog,
        "clips": clips_payload,
        "review_decision": "build_prompts_only_no_queue_no_video_generation_dialogue_deferred",
    }
    contract_payload = {
        "version": "locked_storyboard_shot_plans_v3",
        "canonical_source_lineage": LINEAGE,
        "clips": contracts,
    }
    return spec, contract_payload


def main() -> int:
    spec, contracts = build_payloads()
    SPEC_PATH.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CONTRACTS_PATH.write_text(json.dumps(contracts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = build_project(ROOT, SPEC_PATH)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
