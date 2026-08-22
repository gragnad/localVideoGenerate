#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from h3_prompt_project_builder import build_project
from h3_prompt_projects import EVENT_CONTRACT_VERSION


SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "rebuild_v2"
PROJECT_ID = "RaisingaDragonSeason01_EP00_EP01_H3_R2V_STORYBOARD_ADE_V2"
SPEC_PATH = SOURCE_DIR / "EP00_EP01_H3_R2V_STORYBOARD_ADE_V2_SPEC.json"
CONTRACTS_PATH = SOURCE_DIR / "EP00_EP01_H3_R2V_STORYBOARD_ADE_V2_EVENT_CONTRACTS.json"

LINEAGE = [
    "SEASON01_STORY_BIBLE_V2.md",
    "EP00_NARRATIVE_SCREENPLAY_V2.md",
    "EP01_NARRATIVE_SCREENPLAY_V2.md",
    "SEASON01_CHARACTER_PERFORMANCE_SCREEN_GRAMMAR_V2.md",
    "SEASON01_ABILITY_RULE_CARDS_V2.json",
    "SEASON01_KNOWLEDGE_RESOURCE_STATE_MAP_V2.json",
    "SEASON01_H3_DESIGN_ASSET_LOCK_V5.json",
    "SEASON01_ANIMATION_ADAPTATION_BEAT_SHEET_LOCK_V2.json",
    "EP00_EP01_STORYBOARD_BLUEPRINT_V2.md",
    "EP00_EP01_PRODUCTION_CLIP_SEGMENTATION_V2.md",
    "EP00_EP01_STORYBOARD_PRODUCTION_LOCK_V1.json",
    "EP00_EP01_STORYBOARD_APPROVAL_RECORD_20260817.md",
    "EP00_EP01_H3_ADE_CONVERSION_CONTRACT_V2.md",
]


def clip(
    clip_id: str,
    duration: float,
    assets: list[str],
    summary: str,
    beats: list[str],
) -> dict:
    assert len(beats) == 4
    return {
        "clip_id": clip_id,
        "duration": duration,
        "assets": assets,
        "summary": summary,
        "beats": beats,
    }


CLIPS = [
    clip("EP00-S01-C01", 9.0, ["lua-complete", "abyss-king", "spear"],
         "Lua reads the Abyss King's occupied channel space but her over-tensed body delays the first move.", [
             "An extreme wide establishes the Heartstone chamber, the three-to-one scale gap between [KING] and [LUA], [SPEAR], three extinguishing channels, and the still-open rear route.",
             "A lower wide shows the side and rear channels darken while [KING] barely moves and [LUA] measures the remaining route instead of attacking.",
             "An over-shoulder medium follows [LUA]'s gaze from [KING]'s shoulder through elbow to the channel-contact hand.",
             "A foot-and-grip close-up shows [LUA] over-tighten around [SPEAR], shifting weight too late and exposing the delayed start.",
         ]),
    clip("EP00-S01-C02", 9.0, ["lua-complete", "abyss-king", "spear"],
         "Lua jumps over the king's arm, is crushed out of the route by pressure, and rises with a revised target.", [
             "A side medium shows [KING]'s right arm level and [LUA] compressing low beside [SPEAR] for one committed jump.",
             "A tracking wide carries [LUA] over the outside of the arm while the scale gap and chamber axis remain readable.",
             "A low impact wide shows pressure collapse [LUA]'s landing, drive her to one knee, and cloud the floor with disturbed water.",
             "A recovery medium shows [LUA] rise without posing and place the tip of [SPEAR] on the channel that has just gone dark.",
         ]),
    clip("EP00-S02-C01", 10.0, ["lua-complete", "abyss-king", "spear"],
         "Lua tests the torso, receives proof that penetration is wrong, and watches the disconnected channel stay dark.", [
             "A measured wide counts three steps from [LUA] and [SPEAR] to [KING]'s torso while the contact hand remains visible.",
             "A low profile tracks [LUA]'s hip-and-shoulder drive into one direct spear thrust with no extra attack.",
             "A contact close-up shows the spear point stop without a wound as concentric surface waves spread across [KING]'s torso.",
             "A channel-side medium holds on the dark route failing to return while [LUA] changes her eyeline from torso to contact hand.",
         ]),
    clip("EP00-S02-C02", 10.0, ["lua-complete", "abyss-king", "spear"],
         "The king takes the spear shaft, throws Lua with it, and makes her revise from body damage to contact separation.", [
             "A shaft-level close-up shows [KING] catch the middle of [SPEAR] while [LUA] still owns the rear grip.",
             "A hand-and-face medium shows [LUA] tighten harder instead of releasing as [KING]'s grip remains minimal.",
             "A full-axis wide shows [LUA] lifted and thrown with [SPEAR], preserving one weapon and one continuous force direction.",
             "A floor-level recovery shot shows [LUA] stop rolling with [SPEAR] still in hand and redirect her gaze to [KING]'s channel-contact hand.",
         ]),
    clip("EP00-S03-C01", 10.0, ["lua-complete", "abyss-king", "spear"],
         "Lua forms an irregular water shield, redirects one hand, and enters the briefly opened channel lane.", [
             "A front three-quarter medium shows [LUA] form one irregular curved water shield while [SPEAR] stays in the other hand.",
             "A low side shot shows the tilted shield redirect [KING]'s right hand rather than stop it head-on.",
             "A channel insert shows the right route light briefly as contact shifts, with no new ability or extra effect.",
             "A wide along the opened lane shows [LUA] enter behind the shield with [SPEAR] aligned to the revealed gap.",
         ]),
    clip("EP00-S03-C02", 10.0, ["lua-complete", "abyss-king", "spear"],
         "The second hand pre-empts Lua, tears the shield, numbs her wrist, and forces her to read both hands together.", [
             "A reverse-axis wide reveals [KING]'s left hand already low on the lane before [LUA] completes entry with [SPEAR].",
             "A tight profile shows directional pain make [LUA] lean away a fraction before the unseen-speed contact.",
             "An impact medium shows the shoulder graze, torn shield edge, and numbed wrist without inventing a deeper wound.",
             "A reset wide keeps both of [KING]'s hands on one readable eyeline as [LUA] lowers [SPEAR] and revises the plan.",
         ]),
    clip("EP00-S04-C01", 11.0, ["lua-complete", "abyss-king", "spear"],
         "Lua maps both hands and channels, stabilizes her breath, and accepts the visible fatigue cost of full scales.", [
             "An overhead wide maps [KING]'s two hands, the circular chamber channels, [LUA], and [SPEAR] on one legible battlefield.",
             "An eye-line close-up shows [LUA]'s Dragon Eye read only the contact outlines, not exact future motion.",
             "A chest-and-shoulder medium shows one controlled Dragon Breath restore her broken rhythm while [KING] holds space.",
             "A full-body profile shows complete scales distribute pressure over [LUA] while cold fatigue and trembling remain visible around [SPEAR].",
         ]),
    clip("EP00-S04-C02", 11.0, ["lua-complete", "abyss-king", "spear"],
         "Lua feints right, vaults off the spear, separates the hands, and spends one low Dragon Word to delay them.", [
             "A chamber wide shows [LUA] make a false right-side entry while [KING]'s hands answer along separate routes.",
             "A ground close-up shows [LUA] plant the butt of [SPEAR] into one floor groove as a physical pivot.",
             "A sweeping profile shows [LUA] vault the opposite way, using [SPEAR] to widen the distance between [KING]'s hands.",
             "A low breath close-up shows one short Dragon Word delay hands and droplets for a single beat, with no added blast.",
         ]),
    clip("EP00-S04-C03", 11.0, ["lua-complete", "abyss-king", "spear"],
         "Lua enters the gap, misreads depth, loses footing and body resources, then spends what remains on contact separation.", [
             "A narrow-lane tracking shot follows [LUA] and [SPEAR] into the gap created between [KING]'s hands.",
             "A subjective depth view shows Dragon Eye range and ordinary human depth disagree by one dangerous step.",
             "A low foot-and-body medium shows [LUA] leave the groove, lose heat and voice, and let complete scales flicker unevenly.",
             "A compressed two-shot shows [LUA] abandon torso damage and commit [SPEAR] and remaining shield residue to separating contact.",
         ]),
    clip("EP00-S05-C01", 10.0, ["lua-complete", "abyss-king", "spear"],
         "Lua recovers shield residue, delays one hand, and wedges the spear into the opposite channel route for a small opening.", [
             "A hand-level close-up shows [LUA] gather only the remaining torn shield flow while still controlling [SPEAR].",
             "A side medium shows that residue push [KING]'s right hand away from recontact by a small measurable distance.",
             "A groove close-up shows [LUA] wedge the shaft of [SPEAR] into the left-hand channel path rather than strike the torso.",
             "A low wide reveals only a slight lift at [KING]'s lower centre as proof that the contact-separation test has partial effect.",
         ]),
    clip("EP00-S05-C02", 10.0, ["lua-complete", "abyss-king", "spear"],
         "The king exchanges hand roles, removes the spear from the groove, closes retreat, and exploits Lua's numb wrist.", [
             "A torso-and-hands medium shows [KING] ignore body defence and begin exchanging the two hand roles around [LUA].",
             "A clear two-hand wide preserves [SPEAR] in [LUA]'s possession while the right hand reaches the wedged shaft and the left closes retreat.",
             "A shaft close-up shows [KING]'s right hand lift [SPEAR] out of the groove without keeping or duplicating the weapon.",
             "A wrist-level reaction shot shows [LUA]'s numb hand register the restored contact too late while she still holds [SPEAR].",
         ]),
    clip("EP00-S05-C03", 9.0, ["lua-complete", "abyss-king", "spear"],
         "Pressure arrives, Lua falls, the spear leaves her reach, and the king restores the channels while she cannot rise.", [
             "A palm-axis medium shows [KING]'s pressure reach [LUA] before she can correct her delayed wrist.",
             "A low impact wide shows [LUA] driven flat to the floor with no new wound or counterattack.",
             "A lateral tracking insert follows [SPEAR] leave [LUA]'s hand and slide intact to the far side of the altar.",
             "A final chamber wide shows [LUA] unable to stand, complete scales still present, [SPEAR] out of reach, and [KING]'s channels restored.",
         ]),
    clip("EP00-S06-C01", 6.5, ["lua-complete", "abyss-king", "spear"],
         "The king occupies the upper space; Lua tests every known response and receives only silence before looking inward.", [
             "A floor-level wide makes [KING]'s open right hand occupy the upper frame above fallen [LUA], with [SPEAR] distant across the altar.",
             "A forearm close-up shows [LUA] try to move the scaled arm and wrist mark without enough strength to rise.",
             "A still medium confirms no external light, mark response, shield, or known ability answers while [KING] remains above her.",
             "A profile close-up follows [LUA]'s gaze leave [KING] and settle toward the inside of her own chest.",
         ]),
    clip("EP00-S06-C02", 6.5, ["lua-complete", "abyss-king", "spear"],
         "Lua perceives one unfamiliar internal heartbeat, looks back at the king, and the second beat becomes blackout.", [
             "An intimate floor close-up holds on fallen [LUA] as one heartbeat unlike her own is perceived without any visible new person or power.",
             "A quiet side profile shows [LUA]'s breath stop for one beat while [KING] remains an out-of-focus occupied presence.",
             "A low reverse wide shows [LUA] lift her eyes back toward [KING], with [SPEAR] still unreachable across the chamber.",
             "A receding extreme wide keeps [LUA] and [KING] in their exact positions as darkness closes from the frame edges just before the second heartbeat.",
         ]),

    clip("EP01-S01-C01", 10.0, ["mir-young"],
         "In the ruined palace exterior, Young Mir evades the black flow by choosing a narrow route.", [
             "An extreme wide establishes the storm above the ruined Dragon Palace exterior and makes [MIR] a small isolated figure among broken arches.",
             "A low tracking medium follows [MIR]'s four feet and long wingless body pass beneath one fallen column.",
             "A rear wide shows the non-creature black flow erase animals and heartbeat lamps behind [MIR] without forming a face or hand.",
             "A compressed side shot shows [MIR] fold the long body and enter a narrow escape path that the larger black mass cannot yet fill.",
         ]),
    clip("EP01-S01-C02", 10.0, ["mir-young"],
         "Mir calls for distant hearts, but black flow cuts the cyan route between signal and answer.", [
             "A crown-mark close-up shows [MIR] ignite one weak cyan call while the ruined exterior remains visible behind.",
             "A long-lens wide reveals several distant sleeping dragon heart-lights answer across the ruins.",
             "An overhead route view shows the cyan channels between [MIR] and the distant lights as one continuous spatial map.",
             "A low wide shows black flow cover the middle of those routes so the light and sound stop before reaching [MIR].",
         ]),
    clip("EP01-S01-C03", 10.0, ["mir-young"],
         "Mir attempts a second weaker signal and confirms that every distant response has gone dark.", [
             "A side medium shows [MIR] brace four feet and prepare a second crown response with visibly reduced strength.",
             "A close-up shows the crown mark relight more weakly and unevenly than before.",
             "An extreme wide shows the remaining distant heart-lights extinguish one by one across the palace ruins.",
             "A front three-quarter close-up shows [MIR] cover the dim mark and read the empty darkness without looking at camera.",
         ]),
    clip("EP01-S01-C04", 10.0, ["mir-young", "abyss-king"],
         "A coercive voice closes the palace option, and Mir chooses the dangerous storm surface.", [
             "A wide frames the ruined crown gate behind [MIR] and the direction of a low unseen voice deeper inside.",
             "A tight body-and-ear reaction shows [MIR] freeze at the pressure of the voice while no speaker body is revealed.",
             "A split-depth profile keeps the crown gate on one side and the violent surface glow on the other as [MIR] compares them.",
             "A decisive side wide shows [MIR] turn the entire long body toward the storm surface and leave the gate behind.",
         ]),
    clip("EP01-S01-C05", 10.0, ["mir-young"],
         "Mir spends the last tail-crystal push and is thrown into the upward current rather than defeating the black flow.", [
             "A tail close-up shows [MIR]'s single fused crystal gather its last weak cyan light.",
             "A profile contact shot shows one short pressure front push only the leading edge of the black flow.",
             "A wide shows recoil throw [MIR]'s small body into the upward current, with no victorious counterattack.",
             "A surface-facing silhouette shows four legs, long S-shaped wingless body, whiskers, horns, dorsal mane, and the single tail crystal enter the storm current.",
         ]),
    clip("EP01-S01-C06", 10.0, ["mir-young"],
         "Mir loses direction in the current, exhausts the remaining light, and sends one final coastal rescue signal.", [
             "A rotating underwater wide shows [MIR] lose orientation inside converging storm currents while anatomy remains stable.",
             "A cracked-scale close-up shows a weak blue pulse leak from the injury rather than a new power.",
             "A subjective blur and body profile show [MIR]'s eyes lose focus and all four limbs slacken.",
             "A coast-facing long shot shows one last short cyan signal leave [MIR] toward the dark cave mouth.",
         ]),
    clip("EP01-S01-C07", 10.0, ["mir-young", "black-jellyfish"],
         "Unconscious Mir reaches the coast; the five-tendril black jellyfish turns toward the remaining signal.", [
             "A wave-level wide carries unconscious [MIR] toward the coastal cave without changing the small body or injuries.",
             "A water-route insert shows the short cyan rescue signal remain in the near-shore current after [MIR] passes.",
             "A distant dark-water long shot reveals exactly one [JELLY], with one bell, five attachments, five tendrils, and five sensory droplets.",
             "A restrained profile shows [JELLY] rotate the whole bell toward the signal while all five tendrils remain distinct and no attack begins.",
         ]),
    clip("EP01-S02-C01", 10.5, ["lua-base", "structure-child", "spear"],
         "The village works in rhythm, but Lua enters one beat late and makes the shared rope slip.", [
             "A post-storm village wide shows adults and [CHILD] push boats and ropes to one wave rhythm while [LUA] stands at the far rope end with [SPEAR] nearby.",
             "A lateral group shot makes the common body rhythm readable before [LUA]'s hand enters one beat late.",
             "A hand-and-rope close-up shows [LUA] catch the line after its tension peak rather than through lack of effort.",
             "A boat-side wide shows the mismatched force make the rope slip and the boat tilt back toward danger.",
         ]),
    clip("EP01-S02-C02", 10.5, ["lua-base", "structure-child"],
         "An adult moves Lua out of danger; her public bravado closes into private shame.", [
             "A low boat-side medium shows the hull tilt again while [LUA] remains inside the unsafe line and [CHILD] watches from the group.",
             "A shoulder-level two-shot shows an adult hand guide [LUA] outside the danger zone without humiliating force.",
             "A public medium shows [LUA] arrange wet clothes and turquoise-edged hair into a practiced confident posture.",
             "A private close-up after the others turn away shows [LUA]'s expression close and shoulders lose their false height.",
         ]),
    clip("EP01-S02-C03", 10.5, ["lua-base", "spear"],
         "Lua over-holds her breath, misses the fish, catches her ankle rope, and falls into the shallows.", [
             "A breakwater-side wide isolates [LUA] as she sets [SPEAR] for one ordinary fishing attempt.",
             "A chest-and-grip close-up shows [LUA] hold breath too early and lock shoulders before the fish reaches range.",
             "A waterline profile shows the delayed spear point miss while the attached rope loops once around her ankle.",
             "A low impact wide shows the taut rope seat [LUA] in shallow water with [SPEAR] intact and no heroic pose.",
         ]),
    clip("EP01-S02-C04", 10.5, ["lua-base", "old-fisherman", "structure-child", "spear"],
         "Children laugh, Lua hides shame as bravado, and the fisherman corrects only her little-finger tension.", [
             "A social wide keeps laughing [CHILD] and village children behind wet [LUA] as she claims she was checking depth beside [SPEAR].",
             "A lonely hand close-up after the laughter recedes shows [LUA] clamp too hard around the spear grip.",
             "A quiet two-shot shows [FISHERMAN] watch the hand rather than pose with or duplicate [SPEAR].",
             "An extreme grip close-up shows [FISHERMAN] loosen only [LUA]'s little-finger pressure, leaving a small visible gap in her hold.",
         ]),
    clip("EP01-S02-C05", 10.5, ["lua-base", "old-fisherman", "spear"],
         "The fisherman connects return safety to the forbidden cave, recognizes black coral, and hides it.", [
             "A hand-level teaching medium shows [FISHERMAN] indicate [LUA]'s corrected grip on [SPEAR] while keeping his own hands weapon-free.",
             "A coastal two-shot places [FISHERMAN]'s warning eyeline toward the storm-damaged forbidden cave and [LUA] listening.",
             "A net insert reveals one black coral fragment among ordinary catch as [FISHERMAN]'s hand stops above it.",
             "A guarded close-up shows [FISHERMAN] recognize an old crown-like resemblance and conceal the fragment from [LUA].",
         ]),
    clip("EP01-S02-C06", 10.5, ["lua-base", "spear"],
         "Lua sees the first cyan signal, pretends not to, and walks away as both signal and grip weaken in opposite directions.", [
             "A puddle macro catches the first cyan rescue reflection with [LUA]'s shoe and [SPEAR] entering frame.",
             "A reaction medium shows [LUA] see the reflection, turn away deliberately, and keep her mouth closed.",
             "A rear walking shot shows several steps increase the distance while [LUA]'s hand tightens again around [SPEAR].",
             "A low reflection view shows the puddle light weaken as [LUA] remains paused near the edge of frame.",
         ]),
    clip("EP01-S02-C07", 10.5, ["lua-base", "spear"],
         "A weaker second signal stops Lua and turns the warning into a choice about abandonment.", [
             "A close puddle view shows the second cyan signal arrive shorter and weaker than the first.",
             "A foot-level insert shows [LUA]'s next step stop while [SPEAR] remains secured in the same hand.",
             "A compressed side profile holds [LUA] between the cave direction and the village warning, with no explanatory apparition.",
             "A restrained face-and-grip close-up shows her self-excusing mouth movement and the spear grip ease by one small degree.",
         ]),
    clip("EP01-S02-C08", 10.5, ["lua-base", "spear"],
         "Lua secures the spear and chooses to answer the signal because no one else will.", [
             "A hand-and-rope close-up shows [LUA] untangle and neatly wrap the line of [SPEAR].",
             "A back three-quarter medium shows [LUA] secure [SPEAR] without changing its length or point.",
             "A cave-facing profile shows [LUA] verify the weak signal direction and make the choice without a heroic pose.",
             "A long shot sends [LUA] alone out of the village frame toward the cave, preserving the established screen direction.",
         ]),
    clip("EP01-S03-C01", 10.5, ["lua-base", "spear"],
         "Lua enters the cave, checks sound and droplets, then realizes the black stain flows toward a small cry.", [
             "A threshold wide follows [LUA] enter a dark cave bend with [SPEAR] forward and exterior light behind.",
             "A shoulder-level tracking medium shows [LUA] check stone sound and falling droplets without looking at camera.",
             "A foot-level close-up reveals a black floor stain only after [LUA]'s step has nearly passed it.",
             "A low directional wide shows the non-creature stain flow deeper toward one unseen small cry, redirecting [LUA]'s eyeline and spear point.",
         ]),
    clip("EP01-S03-C02", 10.5, ["lua-base", "mir-young", "spear"],
         "A partial horn-to-tail reveal becomes injured Mir, and Lua lowers herself after putting the spear down.", [
             "A rock-gap close-up reveals only [MIR]'s horns in darkness while [LUA] and [SPEAR] remain outside the gap.",
             "A lower side view adds [MIR]'s wet long tail and cracked scales without showing more than the approved reveal order.",
             "A forepaw-level medium shows [MIR]'s four-legged body slip while trying to retreat from [LUA].",
             "A cave-floor profile shows [LUA] place [SPEAR] flat behind herself and lower one knee to reduce threat.",
         ]),
    clip("EP01-S03-C03", 10.5, ["lua-base", "mir-young", "spear"],
         "Lua's joke dies when she reads Mir's breath; Mir warns first, and Lua follows the warning direction.", [
             "A cautious two-shot shows kneeling [LUA] make one brief light remark toward injured [MIR], with [SPEAR] still on the floor behind.",
             "A breath close-up shows [LUA]'s expression stop when [MIR]'s rough chest movement becomes readable.",
             "A Mir-level reaction shows [MIR] notice the approaching black water wall first and turn head and whiskers toward it.",
             "An over-shoulder wide shows [LUA] follow [MIR]'s warning eyeline to the black wall instead of staring at the dragon.",
         ]),
    clip("EP01-S03-C04", 10.5, ["lua-base", "mir-young", "spear"],
         "Lua offers an empty hand; Mir bites only to hold on, and Lua stops the reflex to pull away.", [
             "An intimate side medium shows [LUA] extend one empty hand slowly toward [MIR], with [SPEAR] visibly behind her.",
             "A Mir-eye close-up shows [MIR] unable to decide whether the hand belongs to the black threat.",
             "An extreme contact close-up shows [MIR] close the mouth around [LUA]'s finger as the wet forepaws slip again.",
             "A reaction medium shows [LUA] begin to withdraw, then stop the elbow and keep the hand stable when she reads panic rather than attack.",
         ]),
    clip("EP01-S03-C05", 10.5, ["lua-base", "mir-young", "spear"],
         "Lua recognizes Mir's hold, relaxes her hand, and one blood drop starts the first resonance in the required order.", [
             "A contact close-up shows [LUA] read [MIR]'s jaw and forepaws as a desperate hold rather than an attack.",
             "A two-shot shows [LUA] relax the fingers and promise through body language not to release [MIR], with [SPEAR] still behind.",
             "A macro shows exactly one blood drop from [LUA]'s finger touch one cracked scale on [MIR].",
             "An oblique close two-shot shows [MIR]'s chest mark light first and [LUA]'s wrist spiral answer one beat later.",
         ]),
    clip("EP01-S03-C06", 10.5, ["lua-base", "mir-young", "spear"],
         "The first resonance stills the cave, Lua breaks contact in surprise, and Mir's fear remains in her breath.", [
             "A waterline insert shows all cave ripples stop for one beat around the joined hands of [LUA] and [MIR].",
             "A startled medium shows [LUA] pull the hand away and break the new contact without striking [MIR].",
             "A wider cave view shows cyan light and still water release immediately when the bodies separate, with [SPEAR] unmoved.",
             "A breath close-up shows [LUA] inherit [MIR]'s fear as a broken breathing rhythm while [MIR] folds back defensively.",
         ]),
    clip("EP01-S03-C07", 10.0, ["lua-base", "mir-young", "spear"],
         "With the black wall closer, Lua offers her palm again and Mir chooses a second contact that shares danger direction.", [
             "A low wide shows the black water wall reduce the remaining cave distance behind [MIR] and [LUA].",
             "A hand-level medium shows [LUA] open the same palm voluntarily and wait without reaching farther.",
             "A close two-shot shows [MIR] hesitate, then place one forepaw on [LUA]'s marked wrist.",
             "A shared-eyeline medium shows the short second resonance turn both [LUA] and [MIR] toward the same black danger direction, with [SPEAR] still available.",
         ]),
    clip("EP01-S03-C08", 10.0, ["lua-base", "mir-young", "spear"],
         "Lua blocks the low channel alone, loses retreat space, and discovers that Mir will point rather than hide.", [
             "A side wide places [LUA]'s body between the black flow and [MIR] while she lowers the shaft of [SPEAR] across the water path.",
             "A low pressure shot shows water push both [LUA]'s feet and [SPEAR] backward along one clear axis.",
             "An overhead route view shows the shrinking retreat behind [LUA] as she tries to gather [MIR] alone.",
             "A Mir-level medium shows [MIR] refuse to hide against [LUA] and instead turn toward an opposite side passage.",
         ]),
    clip("EP01-S03-C09", 10.0, ["lua-base", "mir-young", "spear"],
         "Mir spends the last tail light to choose a side route, and Lua follows that choice into a two-role escape.", [
             "A tail close-up shows [MIR]'s single fused crystal give one last weak directional flash toward the side passage.",
             "A route medium shows [MIR] hold the body and gaze on that passage rather than the black wall.",
             "A full-body profile shows [LUA] abandon her own planned line, recover [SPEAR], and rotate into [MIR]'s chosen direction.",
             "A rear escape wide shows [LUA] open the path with [SPEAR] while [MIR] watches the black direction behind, both moving through one passage.",
         ]),
    clip("EP01-S04-C01", 10.5, ["lua-base", "mir-young", "old-fisherman"],
         "At the cave mouth, Lua wraps Mir in one ordinary cloth and loosens her hand so he can control his breath.", [
             "A cave-mouth wide places [FISHERMAN]'s silhouette outside and [LUA] inside with [MIR] still visible.",
             "A cloth-level medium shows [LUA] wrap [MIR] in one ordinary beige cloth without changing the dragon or creating a bag.",
             "A close-up shows [MIR]'s rough breathing move the same cloth while [FISHERMAN] calls from outside.",
             "A hand-and-cloth close-up shows [LUA] leave her palm loose on top so [MIR] is covered but not pinned.",
         ]),
    clip("EP01-S04-C02", 10.5, ["lua-base", "mir-young", "old-fisherman"],
         "Lua offers a slow breathing rhythm; Mir follows it while the fisherman and black stain approach together.", [
             "A shoulder-and-hand medium shows [LUA] count her own slow breaths through visible chest and loose palm movement over wrapped [MIR].",
             "A cloth close-up shows [MIR]'s hidden breathing begin to match [LUA]'s slower rhythm.",
             "A cave-axis wide shows [FISHERMAN] take one step inward while [LUA] stays between him and [MIR].",
             "A foot-level close-up shows the black floor stain approach [FISHERMAN]'s boot as [MIR]'s cry finally stops.",
         ]),
    clip("EP01-S04-C03", 10.5, ["lua-base", "mir-young", "old-fisherman"],
         "Lua moves outside before exposure; the fisherman notices blood and tracks but chooses observation instead of unveiling Mir.", [
             "A cloth-level close-up shows [MIR]'s movement decrease but remain visible under the same beige wrap.",
             "A side tracking shot follows [LUA] leave the cave ahead of [FISHERMAN], carrying [MIR] in the same cloth.",
             "A ground insert follows [FISHERMAN]'s gaze to [LUA]'s blood-marked hand and wet footprints rather than the bundle.",
             "A restrained two-shot shows [FISHERMAN] stop at observation distance and decline to force the cloth open.",
         ]),
    clip("EP01-S04-C04", 10.5, ["lua-base", "mir-young", "old-fisherman"],
         "Lua prolongs an explanation while the fisherman reads the hand, moving cloth, and crown reflection in order.", [
             "A village-path medium shows [LUA] begin a long explanation while keeping [FISHERMAN]'s attention on her face.",
             "A gaze-follow close-up moves from [LUA]'s face to the blood on her hand without showing [MIR] directly.",
             "A bundle-level medium shows the same beige cloth move once around [MIR] while [FISHERMAN] remains silent.",
             "A puddle insert shows one crown-shaped reflection beneath them as [LUA]'s increasingly long explanation raises the risk.",
         ]),
    clip("EP01-S04-C05", 10.5, ["lua-base", "mir-young", "old-fisherman"],
         "Mir warns Lua of the stain with two tail taps, and Lua redirects it away from the fisherman.", [
             "A hidden Mir-eye view from the cloth shows [MIR] notice the black stain moving toward [FISHERMAN]'s foot.",
             "An extreme bundle close-up shows [MIR]'s tail tap [LUA]'s marked wrist exactly twice through the cloth.",
             "A reaction close-up shows [LUA] understand the signal and shift one foot toward the water without exposing [MIR].",
             "A low splash shot shows [LUA] kick ordinary water across the stain and bend its route away from [FISHERMAN].",
         ]),
    clip("EP01-S04-C06", 10.5, ["lua-base", "mir-young", "old-fisherman"],
         "The fisherman recognizes shared action, leaves the bundle closed, and grants Lua a temporary choice.", [
             "A three-person medium shows [FISHERMAN] address [LUA] while wrapped [MIR] remains one concealed moving shape.",
             "A hand-level shot shows [FISHERMAN] keep both hands away from the cloth and step out of the path.",
             "A rear long shot follows [LUA] carry [MIR] toward home without answering or turning the moment into a reveal.",
             "A quiet close-up keeps [FISHERMAN] comparing the puddle's crown reflection with the hidden black coral fragment.",
         ]),
    clip("EP01-S04-C07", 10.5, ["lua-base", "mir-young"],
         "Inside the house, Lua preserves the same beige cloth, places Mir in water, and both finally release tension.", [
             "An interior wide shows [LUA] close the house door and lean against it while holding [MIR] in the same beige cloth.",
             "A floor-level medium shows [LUA] unwrap that same cloth without changing its colour and support [MIR] toward the basin.",
             "A basin-side close-up shows [MIR] settle into shallow water while looking between the door and [LUA].",
             "A warm two-shot shows [MIR]'s scales, [LUA]'s shoulders, and both breathing rhythms lower for the first time.",
         ]),
    clip("EP01-S04-C08", 10.5, ["lua-base", "mir-young", "mir-shell"],
         "Mir rejects dried fish, chooses the shell, and Lua respects that choice instead of taking it away.", [
             "A low table medium shows [LUA] slide one dried fish toward [MIR] beside [SHELL].",
             "A Mir-level reaction shows [MIR] push the fish away and turn the head with clear dislike.",
             "A close-up shows [MIR] pull [SHELL] against the chest with both forepaws while [LUA] makes one light remark.",
             "A warm two-shot shows [LUA] observe rather than remove [SHELL], allowing [MIR]'s chosen object to remain in place.",
         ]),
    clip("EP01-S04-C09", 10.5, ["lua-base", "mir-young", "mir-shell"],
         "Lua offers the name Mir twice, and only the second call receives a voluntary response and preserved choice.", [
             "A quiet basin two-shot shows [LUA] ask for a name while [MIR] holds [SHELL] and gives no answer.",
             "A speaker-side close-up shows [LUA] form the first call of the name Mir while [MIR]'s mouth remains closed and head unmoved.",
             "A listener close-up makes [MIR] lift the head only on the second call, with [SHELL] still held.",
             "A relational medium shows [LUA] leave room to change the name later while [MIR] keeps the chosen response rather than being commanded.",
         ]),
    clip("EP01-S04-C10", 10.5, ["lua-base", "mir-young", "mir-shell"],
         "A stopped footstep makes Lua shield Mir; Mir checks the door with one droplet, then turns the released tension into their first laugh.", [
             "An interior wide shows outside footsteps stop at the closed door while [LUA], [MIR], and [SHELL] occupy separate readable positions.",
             "A low profile shows [LUA] move between [MIR] and the door while [MIR] stays beside the basin and [SHELL].",
             "A Mir close-up shows one small water droplet travel toward the door to test it as the footsteps move on.",
             "A warm close two-shot shows the same droplet fall on [LUA]'s forehead and both [LUA] and [MIR] release their first shared laugh.",
         ]),
    clip("EP01-S05-C01", 11.0, ["lua-base", "mir-young", "spear"],
         "At night Lua rewinds a wet spear grip, tightens again, and Mir opens the finger spacing with one forepaw.", [
             "A rainy night interior medium shows [LUA] rewind the wet grip of [SPEAR] beside watching [MIR].",
             "An extreme hand close-up shows [LUA]'s fingers return to the same excessive tension learned earlier.",
             "A relational medium shows [MIR] study the hand rather than the spear point while [LUA] continues wrapping.",
             "A contact close-up shows [MIR] place one forepaw across [LUA]'s hand and open the finger spacing without grabbing the weapon.",
         ]),
    clip("EP01-S05-C02", 11.0, ["lua-base", "mir-young", "spear"],
         "Lua hides surprise with a complaint, recalls the morning failure, and adopts Mir's grip correction.", [
             "A face-and-spear medium shows [LUA] look from [MIR]'s forepaw to the corrected grip in surprise, still inside the same night room.",
             "A close profile shows [LUA] hide anxiety behind one brief complaint while [MIR] keeps watching the hand.",
             "A memory-linked hand insert shows [LUA] deliberately rewrap [SPEAR] with the little-finger gap learned that morning.",
             "A quiet two-shot shows [MIR]'s single tail crystal give a small settling response as [LUA] keeps the corrected grip.",
         ]),
    clip("EP01-S05-C03", 11.0, ["lua-base", "mir-young", "mir-shell"],
         "Separate sleeping positions enter one irregular resonance as the room water begins answering between their two beats.", [
             "An overhead night-room wide keeps sleeping [LUA] and sleeping [MIR] on separate mats with [SHELL] beside Mir.",
             "A wrist-and-chest close-up shows an irregular cyan resonance begin between [LUA]'s mark and [MIR]'s emblem.",
             "A lower lateral wide confirms both remain asleep and physically apart rather than embracing or sharing one bed.",
             "A basin-centred overhead shows the room water answer in the gap between their two mismatched rhythms.",
         ]),
    clip("EP01-S05-C04", 11.0, ["lua-base", "mir-young", "mir-shell"],
         "The shared dream exchanges incomplete abandonment memories without granting either character full knowledge.", [
             "A dream-fragment wide shows [LUA] perceive [MIR]'s ruined palace with distant heart-lights that do not answer.",
             "A second dream-fragment wide shows [MIR] perceive [LUA] alone on the rainy breakwater after the other children leave.",
             "A fractured overlap uses separate reflective shards to keep both memories incomplete, never merging identities or explaining every fact.",
             "A dark overhead returns to sleeping [LUA] and [MIR] in separate positions with [SHELL] beside Mir as only the shared fear intensifies.",
         ]),
    clip("EP01-S05-C05", 11.0, ["lua-base", "mir-young", "mir-shell"],
         "Lua and Mir wake separately, Lua waits with an open palm, and Mir voluntarily takes wrist contact before Lua covers him.", [
             "An overhead wide shows [LUA] and [MIR] wake at the same instant on separate mats, with [SHELL] still beside Mir.",
             "A floor-level two-shot shows both tremble at a distance and resist an immediate automatic embrace.",
             "A hand-level close-up shows [LUA] place one open palm near [MIR] and wait without crossing the remaining space.",
             "An intimate close-up shows [MIR] choose to rest the head on [LUA]'s marked wrist before [LUA] draws the existing dark cloth over Mir.",
         ]),
    clip("EP01-S05-C06", 11.0, ["lua-base", "mir-young", "black-jellyfish", "mir-shell"],
         "One synchronized mark pulse settles the room while the five-tendril jellyfish detects it outside and turns toward the window.", [
             "A mark-level close-up shows [LUA]'s wrist and [MIR]'s chest pulse once at the same rhythm beside [SHELL].",
             "A quiet interior medium shows both breathing patterns settle with no new dialogue or unexplained power.",
             "A rain-channel wide reveals one [JELLY] outside with exactly five attachments, five tendrils, and five sensory droplets responding to the leaked pulse.",
             "An exterior high angle shows [JELLY] rotate toward the lit house window while [LUA] and [MIR] remain visible inside as small silhouettes.",
         ]),
    clip("EP01-S05-C07", 11.0, ["black-jellyfish"],
         "The five-tendril jellyfish tests the window, door gap, and drainage route before extending one sensory tip to the exterior water mark.", [
             "A window-level wide shows one [JELLY] test the wet sill while exactly five tendrils and five sensory droplets remain anatomically connected.",
             "A floor-level profile follows the same [JELLY] turn toward the closed door gap without adding a sixth probe.",
             "An overhead exterior route shot follows [JELLY] move along the drainage channel and record the house corner.",
             "An extreme sensory-tip close-up shows one of the existing five droplet organs approach the wet exterior wood while the other four remain attached behind.",
         ]),
    clip("EP01-S05-C08", 12.0, ["lua-base", "mir-young", "black-jellyfish", "mir-shell"],
         "One jellyfish sensor touches the water mark, leaves a thin black crown trace, and wakes only Mir toward the unseen exterior warning direction.", [
             "A threshold close-up shows one existing sensory droplet of [JELLY] touch the wet wood while all five tendrils remain part of one creature.",
             "An extreme contact macro shows the droplet leave one thin crown-shaped black mark, with no letters, face, hand, or extra symbol.",
             "An interior wide shows [LUA] still asleep while [MIR] wakes beside [SHELL], preserving their exact room positions.",
             "A Mir-focused close-up shows [MIR] alone turn the eyes and head toward the exterior mark direction while [LUA] remains asleep; hold on that warning turn without revealing its cause.",
         ]),
]


ASSET_CATALOG = {
    "lua-base": {
        "role": "lua_base_identity",
        "label": "Lua base identity sheet",
        "copy_from": "designs_hq_v1/h3_identity_sheets/H3_LUA_BASE_IDENTITY_HQ_V2.png",
        "subject_name": "Lua",
        "subject_description": "Lua in her approved base state: one athletic young fisher with warm tan skin, camera-friendly face, blue-grey eyes, asymmetric ink-navy short hair with a sea-teal underlayer, sleeveless layered navy fishing vest, mid-thigh dark work shorts, red-brown sash, black work shoes, and one spiral wrist mark only when the Shot states it is visible. Preserve one person, exact face, body, hair, clothing, and non-camera eyeline.",
        "retention_description": "Preserve Lua's approved base identity, clothing, proportions, hair, and the current wrist-mark state",
    },
    "lua-complete": {
        "role": "lua_complete_identity",
        "label": "Lua complete-scales identity sheet",
        "copy_from": "designs_hq_v1/h3_identity_sheets/H3_LUA_COMPLETE_SCALES_IDENTITY_HQ_V2.png",
        "subject_name": "Lua",
        "subject_description": "Lua in the approved complete-scale state: the same single Lua identity and unchanged fishing clothes, with real overlapping blue dragon plates covering the entire right arm and only the right leg from ankle through exposed thigh. Preserve one person, exact asymmetrical hair, clothing, scale limits, fatigue, injury, and gaze toward the actual threat.",
        "retention_description": "Preserve one Lua in the approved complete-scale state with exact clothing and scale boundaries",
    },
    "mir-young": {
        "role": "young_mir_identity",
        "label": "Young Mir identity sheet",
        "copy_from": "designs_hq_v1/h3_identity_sheets/H3_YOUNG_MIR_IDENTITY_HQ_V2.png",
        "subject_name": "YoungMir",
        "subject_description": "Young Mir: one small East Asian water dragon with exactly four legs, no wings, a long S-shaped blue-scaled body, pale segmented underside, four white whiskers, branching silver horns, navy dorsal fin-mane, one chest emblem, and one single fused cyan tail crystal. Preserve exact anatomy, juvenile scale, injuries, and gaze toward the actual scene cause.",
        "retention_description": "Preserve one juvenile Young Mir with four legs, no wings, four whiskers, exact horns, mane, chest emblem, and one tail crystal",
    },
    "abyss-king": {
        "role": "abyss_king_identity",
        "label": "Abyss King identity sheet",
        "copy_from": "designs_hq_v1/h3_identity_sheets/H3_ABYSS_KING_IDENTITY_HQ_V2.png",
        "subject_name": "AbyssKing",
        "subject_description": "The Abyss King: one towering humanoid abyss entity approximately three times Lua's height, with a stable black liquid-stone body, restrained cyan channel lines, crown-like head silhouette, two continuous arms and hands, and no invented armour, weapon, face, or extra limb. Preserve the three-to-one scale relation and minimal movement.",
        "retention_description": "Preserve one Abyss King with exact body, two hands, channel pattern, crown silhouette, and three-to-one scale relation to Lua",
    },
    "old-fisherman": {
        "role": "old_fisherman_identity",
        "label": "Old Fisherman identity sheet",
        "copy_from": "designs_hq_v1/h3_identity_sheets/H3_OLD_FISHERMAN_IDENTITY_HQ_V1.png",
        "subject_name": "OldFisherman",
        "subject_description": "One approved elderly coastal fisherman with weathered face, compact practical build, grey hair, layered work clothing, and empty hands unless a Shot explicitly gives him an ordinary object. Preserve his distinct identity and never give him Lua's spear, hair, clothing, or wrist mark.",
        "retention_description": "Preserve the approved Old Fisherman identity and keep him distinct from Lua and all generic villagers",
    },
    "structure-child": {
        "role": "structure_child_identity",
        "label": "Village child identity sheet",
        "copy_from": "designs_hq_v1/h3_identity_sheets/H3_STRUCTURE_CHILD_IDENTITY_HQ_V1.png",
        "subject_name": "VillageChild",
        "subject_description": "One approved village child with a distinct face, hair, body, and clothing that do not copy Lua. Preserve one child and use additional generic children only as distant non-identity crowd silhouettes when required by the approved board.",
        "retention_description": "Preserve the approved village-child identity without borrowing Lua's face, hair, costume, spear, or wrist mark",
    },
    "black-jellyfish": {
        "role": "black_jellyfish_identity",
        "label": "Black jellyfish identity sheet",
        "copy_from": "designs_hq_v1/h3_identity_sheets/H3_BLACK_JELLYFISH_IDENTITY_HQ_V2.png",
        "subject_name": "BlackJellyfish",
        "subject_description": "One approved black jellyfish with one glossy dark translucent bell, cyan branching sensory veins, exactly five lower attachments, exactly five long black tendrils, and exactly five droplet-shaped sensory organs, one at each tip. Preserve five throughout every view; never add, split, hide by mutation, or turn a tendril into a hand.",
        "retention_description": "Preserve one black jellyfish with exactly one bell, five attachments, five tendrils, and five sensory droplets",
    },
    "spear": {
        "role": "lua_spear_prop",
        "label": "Lua spear identity sheet",
        "copy_from": "designs_hq_v1/h3_prop_sheets/H3_LUA_SPEAR_PROP_HQ_V3.png",
        "subject_name": "LuaSpear",
        "subject_description": "Lua's one fixed-length weathered wooden spear with the approved dark metal head, downward barb, bindings, grip, scratches, and rear ring. It belongs to Lua unless the Shot explicitly shows it lying out of reach; never duplicate, reverse, resize, or give it to another character.",
        "retention_description": "Preserve one approved Lua spear with exact head, barb direction, shaft, grip, bindings, and ownership",
    },
    "mir-shell": {
        "role": "mir_shell_prop",
        "label": "Mir shell identity sheet",
        "copy_from": "designs_hq_v1/h3_prop_sheets/H3_MIR_SHELL_PROP_HQ_V3.png",
        "subject_name": "MirShell",
        "subject_description": "Mir's one approved pale ivory shell with blue spiral bands, one front opening, one closed rear, the same small scratch, and the same scale relative to Young Mir. Never duplicate, recolour, hatch, or turn it into an egg.",
        "retention_description": "Preserve one approved Mir shell with exact opening, closed rear, blue bands, scratch, scale, and ownership",
    },
}

SUBJECT_TOKEN_BY_ASSET = {
    "lua-base": "[LUA]",
    "lua-complete": "[LUA]",
    "mir-young": "[MIR]",
    "abyss-king": "[KING]",
    "old-fisherman": "[FISHERMAN]",
    "structure-child": "[CHILD]",
    "black-jellyfish": "[JELLY]",
}

PROP_TOKEN_BY_ASSET = {
    "spear": "[SPEAR]",
    "mir-shell": "[SHELL]",
}


DIALOGUE_BY_CLIP: dict[str, list[dict[str, object]]] = {
    "EP01-S01-C04": [{
        "shot": 2,
        "speaker": "abyss-king",
        "line": "돌아오면 조용해진다.",
        "delivery": "in a low coercive voice from beyond the ruined gate",
        "offscreen": True,
    }],
    "EP01-S02-C04": [{
        "shot": 1,
        "speaker": "lua-base",
        "line": "수심 확인이었어",
        "delivery": "with wet public bravado that hides embarrassment",
    }],
    "EP01-S02-C05": [{
        "shot": 1,
        "speaker": "old-fisherman",
        "line": "돌아올 때도 잡을 수 있게 쥐어라.",
        "delivery": "calmly, as practical safety advice",
    }],
    "EP01-S02-C07": [{
        "shot": 4,
        "speaker": "lua-base",
        "line": "가지 말라면 안 가야 하는데.",
        "delivery": "under her breath as a self-excusing hesitation",
    }],
    "EP01-S02-C08": [{
        "shot": 3,
        "speaker": "lua-base",
        "line": "저렇게 못 부르는 애는 내가 가야지.",
        "delivery": "quietly but with a completed decision",
    }],
    "EP01-S03-C03": [{
        "shot": 1,
        "speaker": "lua-base",
        "line": "도마뱀은 아니지?",
        "delivery": "as one brief cautious joke that immediately fades",
    }],
    "EP01-S03-C05": [{
        "shot": 2,
        "speaker": "lua-base",
        "line": "알았어. 안 놓을게",
        "delivery": "softly as her bitten fingers relax instead of pulling away",
    }],
    "EP01-S04-C06": [{
        "shot": 1,
        "speaker": "old-fisherman",
        "line": "오늘은 혼자 한 일이 아니구나",
        "delivery": "quietly as an observation rather than an accusation",
    }],
    "EP01-S04-C08": [{
        "shot": 3,
        "speaker": "lua-base",
        "line": "입맛도 귀족이네",
        "delivery": "with a light teasing tone while leaving the shell in place",
    }],
    "EP01-S04-C09": [
        {
            "shot": 2,
            "speaker": "lua-base",
            "line": "미르",
            "delivery": "softly",
        },
        {
            "shot": 3,
            "speaker": "lua-base",
            "line": "미르",
            "delivery": "again at the same volume",
        },
        {
            "shot": 4,
            "speaker": "lua-base",
            "line": "싫으면 나중에 바꿔.",
            "delivery": "gently",
        },
    ],
    "EP01-S05-C02": [{
        "shot": 2,
        "speaker": "lua-base",
        "line": "너까지 훈련시키는 거야?",
        "delivery": "with brief defensive humour that hides anxiety",
    }],
}

MOUTH_CONTROL_ASSETS = {
    "lua-base",
    "lua-complete",
    "mir-young",
    "abyss-king",
    "old-fisherman",
    "structure-child",
}


def framing(beat: str) -> str:
    lower = beat.lower()
    if "extreme close-up" in lower or "macro" in lower:
        return "extreme close-up"
    if "close-up" in lower or "insert" in lower:
        return "close-up"
    if "overhead" in lower:
        return "overhead composition"
    if "extreme wide" in lower:
        return "extreme wide composition"
    if "wide" in lower or "long shot" in lower:
        return "wide composition"
    if "medium" in lower or "two-shot" in lower:
        return "medium composition"
    return "storyboard composition"


def shot_start_times(duration: float, beats: list[str]) -> list[float]:
    """Allocate four Shot spans by visible information and action load."""
    weights: list[float] = []
    action_words = re.compile(
        r"\b(?:strike|impact|collapse|break|burst|fall|jump|throw|contact|reveal|turn)\b",
        re.IGNORECASE,
    )
    for index, beat in enumerate(beats):
        word_count = len(re.findall(r"[A-Za-z0-9']+", beat))
        weight = 1.0 + min(max(word_count - 14, 0), 20) * 0.012
        if index == 0 and framing(beat) in {
            "wide composition",
            "extreme wide composition",
            "overhead composition",
        }:
            weight += 0.16
        if action_words.search(beat):
            weight += 0.14
        if index == 3:
            weight += 0.10
        weights.append(weight)
    unit = duration / sum(weights)
    elapsed = 0.0
    starts: list[float] = []
    for weight in weights[:-1]:
        elapsed += unit * weight
        starts.append(round(elapsed, 3))
    return starts


def camera_instruction(variant_id: str, framing_name: str) -> str:
    if variant_id == "A":
        return (
            f"Use the approved {framing_name} as the baseline camera treatment. "
            "Keep the camera static, with stabilization only; preserve viewpoint, subject "
            "placement, scale, eyelines, action axis, and the described action."
        )
    if "close-up" in framing_name:
        smooth_move = "push slowly toward the active point of contact"
        reactive_move = "make one brief fast push timed to the visible contact or state change"
    elif "wide" in framing_name or "overhead" in framing_name:
        smooth_move = "truck slowly along the established action axis"
        reactive_move = "make one quick controlled pan or track with the dominant visible motion"
    elif "medium" in framing_name:
        smooth_move = "make a slow short arc around the active eyeline without crossing the action axis"
        reactive_move = "make one quick reactive reframe with the approved eyeline or body movement"
    else:
        smooth_move = "push slowly along the established action axis"
        reactive_move = "make one quick reactive reframe with the dominant visible motion"
    if variant_id == "D":
        return (
            f"Use controlled spatial camera movement within this Shot: {smooth_move}. "
            "Keep the approved subject placement and screen direction readable, and end before "
            "any later planned composition or state appears."
        )
    return (
        f"Use action-responsive camera movement within this Shot: {reactive_move}, then settle. "
        "Use only motion already described in this Shot; do not invent action or reveal a later "
        "planned composition."
    )


def dialogue_clause(
    clip_id: str,
    row_assets: list[str],
    subject_ids: dict[str, int],
    dialogue: dict[str, object],
) -> str:
    speaker_asset = str(dialogue["speaker"])
    if speaker_asset not in subject_ids:
        raise ValueError(f"{clip_id}: dialogue speaker asset is not referenced: {speaker_asset}")
    speaker_id = subject_ids[speaker_asset]
    line = str(dialogue["line"]).strip()
    delivery = str(dialogue["delivery"]).strip()
    if dialogue.get("offscreen"):
        speaker_action = (
            f"<Subject {speaker_id}> (S1), offscreen and unseen, {delivery}"
        )
    else:
        speaker_action = f"<Subject {speaker_id}> (S1), {delivery}"
    parts = [f"{speaker_action}: <d>[Korean] {line}</d>"]
    listeners = [
        asset for asset in row_assets
        if asset in MOUTH_CONTROL_ASSETS and asset != speaker_asset
    ]
    if listeners:
        listener_names = " and ".join(
            f"<Subject {subject_ids[asset]}>"
            for asset in listeners
        )
        if len(listeners) == 1:
            parts.append(
                f"Listener {listener_names}: mouth closed."
            )
        else:
            parts.append(
                f"Listeners {listener_names}: mouths closed."
            )
    return " ".join(parts)


def build_payloads() -> tuple[dict, dict]:
    catalog = dict(ASSET_CATALOG)
    clips_payload = []
    contracts = {}
    sequence_total = len(CLIPS)

    for sequence, row in enumerate(CLIPS, start=1):
        clip_id = row["clip_id"]
        scene_id = clip_id.rsplit("-", 1)[0]
        subject_assets = [
            key for key in row["assets"]
            if key in SUBJECT_TOKEN_BY_ASSET or key in PROP_TOKEN_BY_ASSET
        ]
        subject_ids = {key: index for index, key in enumerate(subject_assets, start=1)}
        references = list(subject_assets)

        storyboard_key = "storyboard-" + clip_id.lower()
        episode_dir = "ep00" if clip_id.startswith("EP00-") else "ep01"
        catalog[storyboard_key] = {
            "role": "chronological_storyboard",
            "label": f"{clip_id} approved four-panel storyboard",
            "copy_from": f"storyboards_v2/{episode_dir}/{clip_id.replace('-', '_')}_STORYBOARD_V2.png",
            "reference_kind": "storyboard",
            "storyboard_panel_count": 4,
            "storyboard_reading_order": "top-left, top-right, bottom-left, bottom-right",
            "storyboard_beats": list(row["beats"]),
            "standalone_picture_name": "the approved chronological four-panel storyboard",
            "standalone_picture_description": "This single 2x2 storyboard is the planning reference for Shot 1 through Shot 4. Read it once in this shot order: top-left, top-right, bottom-left, bottom-right. It defines each Shot's viewpoint, subject placement, relative scale, eyelines, action axis, chronological progression, and ending state. Its layout, borders, simultaneous arrangement, labels, and text are planning metadata only and must never appear in the output video.",
            "retention_shots": [1, 2, 3, 4],
            "retention_description": "Follow the four planned viewpoints, subject placements, chronological order, causal progression, and ending states without reproducing the storyboard sheet",
        }
        references.append(storyboard_key)
        storyboard_picture_id = len(references)

        replacements: dict[str, str] = {}
        for asset_key, subject_id in subject_ids.items():
            token = SUBJECT_TOKEN_BY_ASSET.get(asset_key) or PROP_TOKEN_BY_ASSET[asset_key]
            replacements[token] = (
                f"<Subject {subject_id}> {ASSET_CATALOG[asset_key]['subject_name']}"
            )

        def render_text(value: str) -> str:
            for token, replacement in replacements.items():
                value = value.replace(token, replacement)
            if re.search(r"\[[A-Z]+\]", value):
                raise ValueError(f"{clip_id}: unresolved token in {value}")
            return value

        beats = [render_text(value) for value in row["beats"]]
        dialogue_rows = DIALOGUE_BY_CLIP.get(clip_id, [])
        for dialogue in dialogue_rows:
            shot_number = int(dialogue["shot"])
            if shot_number < 1 or shot_number > 4:
                raise ValueError(f"{clip_id}: dialogue Shot is outside 1-4: {shot_number}")
            beats[shot_number - 1] += " " + dialogue_clause(
                clip_id,
                row["assets"],
                subject_ids,
                dialogue,
            )
        required_dialogue = [str(dialogue["line"]).strip() for dialogue in dialogue_rows]
        catalog[storyboard_key]["storyboard_beats"] = beats
        summary = render_text(row["summary"])
        beat_rows = [
            {"beat_id": f"P{index}", "description": value}
            for index, value in enumerate(beats, start=1)
        ]
        start_times = shot_start_times(row["duration"], beats)
        plans = {}
        for variant_id in ("A", "D", "E"):
            shots = []
            for index, beat in enumerate(beats):
                current_framing = framing(beat)
                camera = camera_instruction(variant_id, current_framing)
                shot = {
                    "panel_index": index + 1,
                    "panel_position": ("top-left", "top-right", "bottom-left", "bottom-right")[index],
                    "camera": camera,
                    "beat_ids": [f"P{index + 1}"],
                }
                if index:
                    shot["start_seconds"] = start_times[index - 1]
                shots.append(shot)
            plans[variant_id] = {
                "emphasis": {
                    "A": "baseline framing and cuts with stable camera treatment",
                    "D": "smooth spatial and directional camera movement contained within each Shot",
                    "E": "reactive kinetic camera movement motivated only by approved action, eyeline, and environment motion",
                }[variant_id],
                "shots": shots,
            }

        def subjects_in(text: str) -> list[int]:
            found = [int(value) for value in re.findall(r"<Subject (\d+)>", text)]
            return list(dict.fromkeys(found))

        incoming = subjects_in(beats[0]) or [1]
        outgoing = subjects_in(beats[-1]) or [1]
        incoming_names = " and ".join(f"<Subject {value}>" for value in incoming)
        outgoing_names = " and ".join(f"<Subject {value}>" for value in outgoing)
        if clip_id == "EP01-S01-C01":
            incoming_bridge = (
                "Begin after a hard temporal reset from the underwater chamber blackout into an earlier storm night in the deep sea with <Subject 1> YoungMir; do not carry the chamber location, injury, scale state, props, or knowledge into this scene."
            )
        else:
            incoming_bridge = (
                f"Continue the exact approved incoming state for {incoming_names}; begin only the next visible action in the first planned storyboard state and preserve pose, scale, location, screen direction, fatigue, injury, knowledge, prop ownership, light, and contact until the described action changes them."
            )
        if sequence == sequence_total:
            outgoing_bridge = (
                f"End with {outgoing_names} in the final planned storyboard state, preserving the exterior mark direction and Young Mir's warning eyeline; hold this unresolved warning and do not reveal or continue the next event."
            )
        else:
            outgoing_bridge = (
                f"End with {outgoing_names} in the final planned storyboard state and hold location, screen direction, pose, scale, gaze, fatigue, injury, knowledge, prop ownership, light, effect, and contact unchanged through the cut."
            )

        state_in = f"ADE_V2_STATE_{sequence - 1:03d}"
        state_out = f"ADE_V2_STATE_{sequence:03d}"
        contracts[clip_id] = {
            "shared_event": summary,
            "bridge_in_id": state_in,
            "bridge_out_id": state_out,
            "boundary_policy": "terminal" if sequence == sequence_total else "referenced_cut",
            "source_shot_ids": [clip_id],
            "incoming_reference_subjects": incoming,
            "outgoing_reference_subjects": outgoing,
            "incoming_bridge": incoming_bridge,
            "outgoing_bridge": outgoing_bridge,
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
            "source_shot_id": clip_id,
            "status": "approved_storyboard_visual_prompt",
            "duration_seconds": row["duration"],
            "references": references,
            "prompt_base": {
                "summary": summary,
                "style_opening": [
                    "High-detail hand-drawn 2D cel animation uses grounded anatomy, clear silhouettes, restrained cyan resonance light, deep ink-black threat shapes, realistic wet materials, and dark maritime fantasy cinematography",
                    "Preserve the approved 16:9 single-frame composition, character identity, action axis, cause-to-effect motion, chronological order, and ending state without imitating any existing franchise",
                ],
                "overall_soundscape": (
                    "Use only scene-supported ambience and physical sound. Render each tagged "
                    "Korean line exactly once in order, with natural synchronized lip movement "
                    "only on its marked speaker. All other subjects keep closed mouths; no "
                    "additional intelligible words are heard."
                    if required_dialogue else
                    "Use only ambience and physical sounds directly supported by the visible "
                    "environment, movement, contact, material interaction, breathing, or creature "
                    "motion. No intelligible dialogue is authorized; speaking-like actions remain "
                    "indistinct, and no new words or lip-synced lines are invented."
                ),
                "non_diegetic_music": "An original restrained score uses sparse low strings, soft wood percussion, and long pauses. Its dynamics follow visible movement and recede during listening reactions; do not imitate existing music or motifs.",
            },
            "prompt_variants": [
                {"variant_id": "A", "label": "후보 A", "rationale": "기본 구도와 컷 순서를 안정된 카메라로 직접 보존", "prompt_spec": {}},
                {"variant_id": "D", "label": "후보 D", "rationale": "각 Shot 안에서만 부드러운 공간·방향 카메라 움직임 적용", "prompt_spec": {}},
                {"variant_id": "E", "label": "후보 E", "rationale": "승인 행동·시선·환경 움직임에 반응하는 역동 카메라 적용", "prompt_spec": {}},
            ],
            "canonical_source_lineage": LINEAGE,
            "locked_rule_id": "EP00_EP01_STORYBOARD_PRODUCTION_LOCK_V1",
            "continuity_in": state_in,
            "continuity_out": state_out,
            "required_dialogue": required_dialogue,
            "storyboard_review_contract": {
                "picture_id": storyboard_picture_id,
                "panel_positions": ["top-left", "top-right", "bottom-left", "bottom-right"],
                "panel_to_shot": "one_to_one",
                "visual_asset_status": "user_approved_and_agent_reviewed",
            },
            "authoring_notes": "Canonical Korean dialogue is restored only where exact wording is locked. Tagged speakers receive synchronized lip movement; all listeners keep closed mouths. Unspecified speech remains indistinct and no new dialogue is invented. The approved target duration already applies the half-second correction once per Clip. Queue and video generation remain forbidden.",
            "visual_review": "user_approved_storyboard_and_agent_verified_production_lock",
            "semantic_review": "causality_camera_dialogue_speaker_listener_and_continuity_passed",
        })

    spec = {
        "schema_version": 2,
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00–EP01 · Storyboard A/D/E V2",
        "description": "The approved rebuild-v2 EP00 and EP01 production storyboards converted into 56 H3 Full Reference clips and 168 A/D/E prompts with canonical EP01 Korean dialogue. A is the stable baseline, D adds smooth spatial camera movement, and E adds action-responsive kinetic camera movement without changing story order, dialogue, or ending state.",
        "source_policy": "rebuild_v2_approved_storyboards_only_no_historical_prompt_lineage",
        "canonical_source_lineage": LINEAGE,
        "locked_rule_id": "EP00_EP01_STORYBOARD_PRODUCTION_LOCK_V1",
        "build_script": "scripts/build_ep00_ep01_storyboard_ade_v2.py",
        "event_contracts_file": CONTRACTS_PATH.name,
        "asset_catalog": catalog,
        "clips": clips_payload,
        "review_decision": "user_authorized_canonical_ep01_dialogue_prompt_revision_no_queue_no_video",
    }
    contracts_payload = {
        "version": EVENT_CONTRACT_VERSION,
        "canonical_source_lineage": LINEAGE,
        "clips": contracts,
    }
    return spec, contracts_payload


def main() -> int:
    raise RuntimeError(
        "EP00·EP01 통합 생성기는 신규 제작에 사용할 수 없습니다. "
        "EP00 액션은 scripts/build_ep00_action_storyboard_ade_v3.py, "
        "EP01 일반 연출은 scripts/build_ep01_storyboard_ade_v3.py를 사용하세요."
    )


if __name__ == "__main__":
    raise SystemExit(main())
