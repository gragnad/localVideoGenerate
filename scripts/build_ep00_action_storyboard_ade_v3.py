from __future__ import annotations

"""Build the separated EP00 action-scene H3 storyboard project.

This generator is the only supported route for the current EP00 action clips.
It reuses the approved V2 identities and storyboards, but replaces the generic
EP00/EP01 camera template with an explicit action timing and physical-causality
contract.
"""

import copy
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_project_builder
import h3_prompt_projects
import build_ep00_ep01_storyboard_ade_v2 as source


PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_ACTION_STORYBOARD_ADE_V3"
SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "rebuild_v2"
SPEC_PATH = SOURCE_DIR / "EP00_H3_R2V_ACTION_STORYBOARD_ADE_V3_SPEC.json"
CONTRACTS_PATH = SOURCE_DIR / "EP00_H3_R2V_ACTION_STORYBOARD_ADE_V3_EVENT_CONTRACTS.json"


def action_meta(
    phase: str,
    speed_profiles: tuple[str, str, str, str],
    motion_links: tuple[str, str, str],
    environmental_proof: str,
) -> dict[str, Any]:
    return {
        "version": h3_prompt_projects.ACTION_SCENE_CONTRACT_VERSION,
        "phase": phase,
        "speed_profiles": list(speed_profiles),
        "motion_links": list(motion_links),
        "environmental_proof": environmental_proof,
    }


ACTION_META: dict[str, dict[str, Any]] = {
    "EP00-S01-C01": action_meta(
        "scale_gap_and_route_mapping",
        (
            "Establish the chamber for a brief readable hold; channel lights extinguish in a fast sequential pulse while both silhouettes remain stable.",
            "The King barely shifts; let the route close faster than Lua can finish measuring it, creating speed through lost space rather than body flailing.",
            "Lua's eyes scan shoulder to elbow to hand in one crisp continuous read with no idle portrait hold.",
            "Grip tension snaps tight, the planted foot loads, and the late weight transfer is visible within the final fraction of the Shot.",
        ),
        (
            "the extinguishing channel sequence carries into Lua's route calculation",
            "Lua's eyeline continues from the shrinking route to shoulder, elbow, and hand",
            "the completed eyeline read drops directly into the over-tight grip and late foot load",
        ),
        "Three channel sections go dark in order and the remaining route visibly narrows.",
    ),
    "EP00-S01-C02": action_meta(
        "first_evasion_and_pressure_cost",
        (
            "Hold the crouched anticipation only briefly; the King's arm begins first and Lua releases the loaded legs immediately after it commits.",
            "Execute the jump as one explosive acceleration over the arm, preserving a clean airborne arc rather than slow floating.",
            "Landing contact is abrupt: feet touch, pressure folds the posture, one knee strikes, and displaced water and grit continue past the body.",
            "Recovery is quick but imperfect: roll momentum resolves to one knee, one breath resets the eyes, and the spear retargets without a victory pose.",
        ),
        (
            "the compressed legs release into the same outside-over-arm jump",
            "the descending jump momentum carries without reset into the pressure-collapsed landing",
            "the landing skid and roll finish in the one-knee retarget posture",
        ),
        "A directional pressure wake, disturbed floor water, and grit prove the missed arm's force and Lua's damaged landing.",
    ),
    "EP00-S02-C01": action_meta(
        "first_technique_test",
        (
            "Count three accelerating footfalls with the third step shortest and fastest; do not turn the approach into a slow run cycle.",
            "Drive rear foot, hip, shoulder, hands, and spear in one sharp kinetic chain with the point reaching contact almost instantly.",
            "Stop the spear point abruptly at the black surface; hold the contact evidence just long enough for concentric waves to outrun the stopped weapon.",
            "Let the failed channel response register in one short still beat before Lua's eyeline cuts decisively from torso to the contact hand.",
        ),
        (
            "the third accelerating footfall continues into the full-body spear drive",
            "the thrust velocity ends in a hard point-stop while surface waves keep traveling",
            "the expanding waves lead the eye to the channel that remains dark and Lua's revised target",
        ),
        "Concentric black-surface waves spread beyond the stopped spear while the severed cyan channel stays dark.",
    ),
    "EP00-S02-C02": action_meta(
        "minimal_counter_and_throw",
        (
            "The King's hand closes once at the shaft midpoint with almost no wind-up; spear motion stops before Lua can change grip.",
            "Lua's fingers clamp harder in a brief resistance beat while the King's wrist and shoulder remain unnervingly economical.",
            "Lift and throw happen as one accelerating chain: feet leave the floor, torso rotates, then Lua and spear travel together on one force axis without hovering.",
            "Shoulder contact is abrupt, followed by one continuous roll and a breathless stop; retain the spear and redirect the eyes before the Shot ends.",
        ),
        (
            "the stopped shaft transmits force directly into Lua's tightening rear grip",
            "the maintained grip becomes the lever that lifts and throws Lua with the spear",
            "the airborne force direction continues through shoulder impact, roll, and final retarget",
        ),
        "The shaft bends slightly under opposing force, floor water bursts at shoulder impact, and the roll leaves one readable wet track.",
    ),
    "EP00-S03-C01": action_meta(
        "redirection_test",
        (
            "Form the single curved shield in one compact pull of nearby water; its irregular surface finishes before the palm arrives.",
            "Palm contact compresses the shield first, then Lua rotates hips and shoulder sharply so the force slides sideways instead of stopping.",
            "The palm exits on a fast tangent and directional droplets keep traveling as the right channel relights for only a brief pulse.",
            "Lua takes the opened lane in two quick steps behind the still-connected shield, spear aligned to the gap with no pause to display the pose.",
        ),
        (
            "the completed curved shield receives the already approaching right palm",
            "shield compression rolls into Lua's body rotation and the palm's sideways release",
            "the released droplets and relit channel pull Lua through the newly opened lane",
        ),
        "Shield compression, tangent droplets, and the brief cyan channel pulse prove successful redirection.",
    ),
    "EP00-S03-C02": action_meta(
        "second_hand_preemption",
        (
            "Reveal the low left hand already occupying the lane while Lua's forward momentum is still committed.",
            "Pain warning moves Lua only a fraction before the fingertip crosses the remaining distance with near-instant speed.",
            "Contact is a sharp graze, not a heavy pause: cloth pulls, shoulder turns, shield edge tears, and wrist sensation drops in one chained reaction.",
            "After one short imbalance correction, Lua lowers the spear and maps both hands on the same eyeline without resetting the battlefield.",
        ),
        (
            "Lua's committed lane entry carries into the already waiting left-hand threat",
            "the partial lean becomes the same shoulder graze and shield-edge tear",
            "the torn edge and numb wrist settle into a two-hand tactical read",
        ),
        "A torn water edge, pulled wet cloth, and a broken droplet trail mark the unseen-speed graze direction.",
    ),
    "EP00-S04-C01": action_meta(
        "total_assault_preparation",
        (
            "Map both hands and channel contacts in one fast overhead read; avoid an extended explanatory hold.",
            "Dragon Eye focus tightens quickly from the full map to only the two contact outlines, with no prediction effect added.",
            "One controlled inhale and forceful exhale reset the broken rhythm while the spear tremor visibly decreases but does not vanish.",
            "Show full-body load distribution in a brief readiness beat: scales take pressure, fingers and ankle compensate, cold fatigue remains.",
        ),
        (
            "the overhead spatial map contracts into Lua's two contact-outline eyelines",
            "the completed visual read drives one breath reset rather than a pause for explanation",
            "the breath redistribution travels into feet, scaled limbs, and the spear grip",
        ),
        "Contact outlines, condensed breath, scale flicker, and spear tremor make the resource cost visible before acceleration.",
    ),
    "EP00-S04-C02": action_meta(
        "maximum_density_combination",
        (
            "The false right entry lasts only long enough to commit the King's right hand; Lua cuts direction before either hand can settle.",
            "Plant the spear butt with a hard wet-stone contact and compress the body around it immediately as a spring-loaded pivot.",
            "Release the pivot explosively into the opposite vault; hips clear first, legs whip through, and both King hands separate along readable paths.",
            "Deliver one short low Dragon Word at the vault's exit; hands and droplets decelerate for one beat while Lua continues into the opening.",
        ),
        (
            "the false right sprint transfers without pause into the spear-butt plant",
            "the planted shaft returns stored force into the opposite full-body vault",
            "the vault exit breath triggers the single-beat slowdown while forward momentum remains",
        ),
        "A spear-butt splash, curved vault wake, diverging hand wakes, and briefly suspended droplets prove the combined technique.",
    ),
    "EP00-S04-C03": action_meta(
        "maximum_assault_cost_and_revision",
        (
            "Enter the gap at full sprint while the hands remain separated; maintain the prior vault direction and do not restart from standing.",
            "The subjective depth mismatch flashes briefly as two incompatible distance reads, then resolves too late by exactly one step.",
            "The foot misses the groove abruptly; ankle corrects, body drops, breath fails, and scale light flickers as one cascading resource error.",
            "Before balance fully returns, Lua commits spear and shield residue to contact separation in one desperate forward continuation.",
        ),
        (
            "the vault-exit momentum continues directly into the narrow-lane sprint",
            "the sprint distance becomes the one-step depth error without a temporal pause",
            "the missed groove and failed breath feed the same desperate contact-separation commitment",
        ),
        "A missed groove splash, silent failed exhale, uneven scale light, and dragging spear line prove the combined cost.",
    ),
    "EP00-S05-C01": action_meta(
        "last_contact_separation_test",
        (
            "Gather only existing shield residue in one fast wrist pull while the other hand keeps the spear under control.",
            "The residue strikes the right hand as a compact lateral shove and moves it only a small measurable distance.",
            "Use that fraction of space immediately to jam the spear shaft into the opposite groove before the hand can recontact.",
            "Hold the slight lower-mass lift only long enough to prove partial success; Lua remains under load and does not celebrate.",
        ),
        (
            "the gathered residue releases directly into the right-hand lateral shove",
            "the small displaced distance becomes the opening for the immediate shaft wedge",
            "the wedged shaft transmits force into the slight lift of the King's lower contact edge",
        ),
        "Residue spray, shaft flex, groove water displacement, and a thin lifted black edge prove the partial opening.",
    ),
    "EP00-S05-C02": action_meta(
        "king_role_exchange_counter",
        (
            "The King begins exchanging hand roles with one economical shoulder rotation; his torso never reacts to the opening.",
            "Both hands move simultaneously on separate tasks, keeping the right-to-spear and left-to-retreat geometry readable.",
            "The right hand removes the shaft from the groove in one short lift with no struggle, duplication, or transfer of ownership.",
            "Lua's numb wrist reports the restored contact one beat late; the reaction begins in fingers, then shoulder, then eyes.",
        ),
        (
            "the small shoulder rotation unfolds into two simultaneous hand routes",
            "the right-hand route reaches the wedged shaft as the left-hand route closes retreat",
            "the shaft's sudden release reaches Lua's numb wrist too late for correction",
        ),
        "The groove snaps back with a narrow water surge while the closing left-hand shadow erases Lua's last retreat line.",
    ),
    "EP00-S05-C03": action_meta(
        "defeat_impact_and_aftermath",
        (
            "Pressure reaches Lua almost instantly from the open palm; keep the King economical and make the lost route move faster than she can correct.",
            "Drive Lua flat in one brutal downward displacement followed by a short body rebound and a broad floor-water burst.",
            "The spear exits the numb grip at impact speed and slides intact across the altar, decelerating through water until it stops far away.",
            "After the violent chain, hold the wide aftermath: Lua cannot rise, channels restore in sequence, and the King remains almost motionless.",
        ),
        (
            "the closing pressure line continues directly into Lua's downward floor impact",
            "the impact rebound releases the spear from the numb grip onto its long slide",
            "the spear's deceleration reveals the restored channels and final spatial defeat",
        ),
        "A broad impact splash, brief body rebound, long spear skid wake, and sequential channel restoration prove complete defeat.",
    ),
    "EP00-S06-C01": action_meta(
        "post_defeat_information_collapse",
        (
            "Begin with a quiet but oppressive hold after the impact; the open hand already owns the upper frame.",
            "Lua's scaled arm attempts one incomplete lift, trembles, and drops without a second effort.",
            "Test wrist mark, channel light, shield response, and known power in one compressed sequence of failed micro-reactions, not four separate effects.",
            "The eyes leave the King and move inward slowly enough to read as a new decision while the exterior remains still.",
        ),
        (
            "the aftermath pressure carries into Lua's failed arm lift",
            "the dropped arm becomes the same compressed test of every silent external response",
            "the completed external failure redirects Lua's eyeline toward the chest",
        ),
        "Arm tremor, dead wrist mark, dark channels, and absent shield response prove that every known external route is closed.",
    ),
    "EP00-S06-C02": action_meta(
        "new_force_detection_and_blackout",
        (
            "Hold the fallen close-up in near stillness until one unfamiliar internal heartbeat interrupts the established rhythm.",
            "Breath stops immediately for one beat; only eyes and throat react while no new light, body, weapon, or aura appears.",
            "Lua raises the eyes back to the King with a small decisive acceleration, preserving the distant spear and exact positions.",
            "Let darkness close from the edges at a controlled increasing rate and reach full black immediately before the second heartbeat.",
        ),
        (
            "the first unfamiliar heartbeat interrupts Lua's exhausted breathing",
            "the breath stop resolves into the same upward return of her eyeline",
            "the restored opponent eyeline is overtaken by edge-closing darkness before the second beat",
        ),
        "The only proof is the interrupted breath, changed eyeline, and edge-closing blackout; no visible new power is allowed.",
    ),
}


PHASE_AUDIO = {
    "scale_gap_and_route_mapping": (
        "Deep chamber pressure, three sequential channel dropouts, wet foot tension, spear grip creak, and one restrained arm wake.",
        "Low pulses count the disappearing routes; percussion enters only on Lua's late foot load.",
    ),
    "first_evasion_and_pressure_cost": (
        "A massive arm displacement, Lua's explosive foot release, air-water shear, hard landing splash, floor grit, roll friction, and one broken recovery breath.",
        "Fast low strings accelerate into the jump, cut at floor contact, then return as a shorter tactical pulse.",
    ),
    "first_technique_test": (
        "Three fast wet footfalls, shaft acceleration, a hard muted point-stop, black surface ripples, and the absent cyan channel response.",
        "Tight percussion follows the three steps and stops dead at contact while one low note remains under the failed result.",
    ),
    "minimal_counter_and_throw": (
        "One heavy hand closure on wood, shaft strain, Lua's grip creak, lift pressure, a fast throw wake, shoulder impact, roll friction, and breath loss.",
        "Percussion drops out under the King's minimal grip, then one short low-string sweep follows the throw and ends at impact.",
    ),
    "redirection_test": (
        "Water gathering, shield compression, palm shear, directional droplet spray, two fast steps, and a brief cyan channel return.",
        "Syncopated low percussion follows compression, redirection, and entry without covering the physical water sounds.",
    ),
    "second_hand_preemption": (
        "A near-silent fast hand pass, cloth graze, water-edge tear, numb grip shift, and Lua's sharp corrective breath.",
        "The score briefly drops out before contact, then answers with one clipped low-string accent and an unresolved pulse.",
    ),
    "total_assault_preparation": (
        "Condensed breathing, quiet channel pressure, scale friction, spear tremor, and restrained movements from both attached hands.",
        "A compact accelerating ostinato assembles from breath, grip, and foot load without reaching release yet.",
    ),
    "maximum_density_combination": (
        "Fast foot cuts, spear-butt stone contact, pivot splash, full-body vault shear, diverging hand wakes, one low nonverbal Dragon Word, and suspended droplets.",
        "The fastest EP00 percussion and low strings lock to feint, plant, vault, and one-beat delay, with no long pause between techniques.",
    ),
    "maximum_assault_cost_and_revision": (
        "Lane sprint, displaced water, one disorienting depth pulse, groove miss, ankle skid, failed voiceless breath, scale flicker, and spear drag.",
        "The rapid phrase loses one beat at the depth error, fragments with the resource failures, then drives into the final commitment.",
    ),
    "last_contact_separation_test": (
        "Residual shield pull, compact lateral water shove, wet shaft wedge, groove strain, and a thin black-liquid separation sound.",
        "Short percussion strikes mark gather, shove, wedge, and partial lift while the underlying low string keeps rising.",
    ),
    "king_role_exchange_counter": (
        "Economical shoulder rotation, two broad hand wakes, shaft release from stone, groove water snapback, and Lua's delayed finger response.",
        "The rising phrase is cut apart by two sparse low impacts matching the King's role exchange.",
    ),
    "defeat_impact_and_aftermath": (
        "A compressed pressure hit, broad floor splash, brief body rebound, spear release, long wet-stone skid, and sequential channel restoration.",
        "One brutal low percussion strike and descending strings end the assault; music recedes during the long physical aftermath.",
    ),
    "post_defeat_information_collapse": (
        "Fading chamber pressure, weak scale scrape, failed arm lift, dead wrist mark, no shield response, and Lua's shallow breathing.",
        "Almost no score; one distant low pulse disappears as each known response fails.",
    ),
    "new_force_detection_and_blackout": (
        "Shallow breathing, one unfamiliar internal heartbeat, one beat of breath silence, distant chamber pressure, and the approaching second beat cut off by blackout.",
        "No melody; one unfamiliar sub-bass pulse interrupts silence and a second pulse is withheld by the cut.",
    ),
}


def framing(beat: str) -> str:
    return source.framing(beat)


def label_action_text(value: str) -> str:
    value = re.sub(
        r"\b(?:The|the) King's\b",
        "<Subject 2> AbyssKing's",
        value,
    )
    value = re.sub(
        r"\b(?:The|the) King\b",
        "<Subject 2> AbyssKing",
        value,
    )
    value = re.sub(
        r"\bboth King hands\b",
        "both <Subject 2> AbyssKing hands",
        value,
    )
    return re.sub(
        r"\bLua('s)?\b",
        lambda match: "<Subject 1> Lua" + (match.group(1) or ""),
        value,
    )


def action_camera(variant_id: str, beat: str, phase: str, shot_index: int) -> str:
    view = framing(beat)
    lower = beat.lower()
    if phase in {"post_defeat_information_collapse", "new_force_detection_and_blackout"}:
        energetic = False
    else:
        energetic = True
    if variant_id == "A":
        camera = (
            f"Use the approved {view} with an anchored camera while full-speed motion completes. "
            "Preserve axis and scale; do not freeze, float, or reproduce a reference image."
        )
    elif variant_id == "D":
        if "close-up" in view:
            move = "push decisively along the current force or eyeline to its physical evidence"
        elif "wide" in view or "overhead" in view:
            move = "track along the current axis with parallax, matching acceleration to the spatial result"
        else:
            move = "arc by less than one body length around the current contact while preserving the 180-degree relation"
        if not energetic:
            move = "drift once toward the current sensory evidence without breaking the stillness"
        camera = (
            f"Within this Shot, {move}. Do not preview a later composition, reset space, or slow the body action."
        )
    else:
        if re.search(r"impact|contact|hit|graze|tear|stop|drive|throw|fall|collapse|pressure", lower):
            move = "let contact trigger one sharp reframe and brief controlled impact shake, keeping the result centered"
        elif re.search(r"gaze|eye|read|breath|heartbeat|wrist|grip", lower):
            move = "snap attention with the existing eye, breath, hand, or grip change to its result"
        else:
            move = "pan sharply with the existing body, hand, spear, or water motion through its result"
        if not energetic:
            move = "react only to breath, eyeline, heartbeat, or darkness with one restrained reframe"
        camera = (
            f"Within this Shot, {move}. No new attack, later composition, or reference-sheet cut."
        )
    return camera


def _reindex_contracts(
    clips: list[dict[str, Any]], contracts: dict[str, Any]
) -> None:
    for sequence, clip in enumerate(clips, start=1):
        clip_id = str(clip["clip_id"])
        clip["sequence"] = sequence
        clip["continuity_in"] = f"EP00_ACTION_V3_STATE_{sequence - 1:02d}"
        clip["continuity_out"] = f"EP00_ACTION_V3_STATE_{sequence:02d}"
        contract = contracts[clip_id]
        contract["bridge_in_id"] = clip["continuity_in"]
        contract["bridge_out_id"] = clip["continuity_out"]
        contract["boundary_policy"] = (
            "terminal" if sequence == len(clips) else "referenced_cut"
        )


def build_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    combined_spec, combined_contracts = source.build_payloads()
    spec = copy.deepcopy(combined_spec)
    contracts_payload = copy.deepcopy(combined_contracts)
    clips = [
        clip for clip in spec["clips"]
        if str(clip.get("clip_id") or "").startswith("EP00-")
    ]
    contracts = {
        clip_id: contract
        for clip_id, contract in contracts_payload["clips"].items()
        if clip_id.startswith("EP00-")
    }
    if set(ACTION_META) != {str(clip["clip_id"]) for clip in clips}:
        raise ValueError("EP00 action metadata does not cover the canonical 14 clips exactly.")

    catalog = spec["asset_catalog"]
    for asset_key in ("lua-complete", "abyss-king"):
        catalog[asset_key]["subject_description"] += (
            " Use identity and anatomy only; never reproduce the source sheet layout or background."
        )
    catalog["spear"]["subject_description"] += (
        " Use weapon geometry only; never reproduce the source sheet layout or background."
    )
    catalog["spear"]["retention_marker"] = "partially_preserved"
    catalog["spear"]["retention_description"] = (
        "Preserve only the single spear's geometry, material, scale, orientation, and ownership; ignore the source sheet layout and background"
    )

    _reindex_contracts(clips, contracts)
    for clip in clips:
        clip_id = str(clip["clip_id"])
        meta = ACTION_META[clip_id]
        phase = str(meta["phase"])
        contract = contracts[clip_id]
        storyboard_key = "storyboard-" + clip_id.lower()
        storyboard = catalog[storyboard_key]
        storyboard["retention_marker"] = "partially_preserved"
        storyboard["retention_description"] = (
            "Use only the four chronological viewpoints, placements, action states, and order; never reproduce the 2x2 sheet, borders, labels, or simultaneous layout"
        )
        storyboard["standalone_picture_description"] = (
            "This is one planning-only 2x2 storyboard for four chronological full-screen Shots. "
            "Read it once from top-left to top-right to bottom-left to bottom-right. Use only each Shot's viewpoint, subject placement, scale, eyeline, action axis, and accumulated physical state. "
            "Never render the sheet, grid, borders, labels, blank reference background, or more than one chronological composition at a time."
        )
        storyboard["storyboard_beats"] = [
            str(row["description"]) for row in contract["beats"]
        ]

        speed_profiles = list(meta["speed_profiles"])
        motion_links = list(meta["motion_links"])
        for variant_id in ("A", "D", "E"):
            shots = contract["candidate_plans"][variant_id]["shots"]
            contract["candidate_plans"][variant_id]["emphasis"] = {
                "A": "approved action checkpoints with explicit speed, contact, recoil, and aftermath",
                "D": "shot-local spatial camera movement matched to physical acceleration and current evidence",
                "E": "action-reactive camera impulse driven by existing body, weapon, water, and impact motion",
            }[variant_id]
            for index, shot in enumerate(shots):
                beat = str(contract["beats"][index]["description"])
                inherited = (
                    ""
                    if index == 0
                    else " Continue inherited momentum without a pose or position reset."
                )
                shot["camera"] = (
                    f"Action timing: {label_action_text(speed_profiles[index])}{inherited} "
                    + action_camera(variant_id, beat, phase, index)
                )

        soundscape, music = PHASE_AUDIO[phase]
        clip["scene_type"] = h3_prompt_projects.ACTION_SCENE_TYPE
        clip["prompt_profile"] = h3_prompt_projects.ACTION_PROMPT_PROFILE
        clip["prompt_generator"] = h3_prompt_projects.ACTION_PROMPT_GENERATOR
        clip["action_scene_contract"] = copy.deepcopy(meta)
        clip["status"] = "action_prompt_internal_validation_pass"
        clip["semantic_review"] = "pending_user_action_prompt_review"
        clip["authoring_notes"] = (
            "This clip is fail-closed to the dedicated action-scene generator. "
            "A/D/E share identical action timing, physical cause, contact, result, and end state; only the camera response differs. "
            "No queue or video generation is authorized by this build."
        )
        clip["prompt_base"] = {
            "summary": str(clip["prompt_base"]["summary"]),
            "style_opening": [
                "2D cel action uses grounded anatomy, brief anticipation, instant execution, clear contact, recoil, and aftermath; Lua chains fast corrections while the Abyss King erases routes with minimal attached-hand motion",
                "Each Shot stays full-screen in the 16:9 Heartstone Chamber; never show planning layouts, montages, storyboard borders, turnarounds, prop sheets, a white reference-sheet background, labels, or text; "
                f"environmental proof for this clip is {meta['environmental_proof']}",
            ],
            "overall_soundscape": soundscape,
            "non_diegetic_music": music,
        }

    spec.update({
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · Dedicated Action Storyboard A/D/E V3",
        "description": "Separated EP00 action project. Four explicit speed profiles and three inherited motion links are mandatory in every clip; generic narrative prompt generation is rejected.",
        "source_policy": "rebuild_v2_approved_ep00_storyboards_with_dedicated_action_scene_generator_only",
        "build_script": "scripts/build_ep00_action_storyboard_ade_v3.py",
        "event_contracts_file": CONTRACTS_PATH.name,
        "prompt_profile": h3_prompt_projects.ACTION_PROMPT_PROFILE,
        "prompt_generator": h3_prompt_projects.ACTION_PROMPT_GENERATOR,
        "generation_blocked": False,
        "replacement_project_ids": [],
        "clips": clips,
        "review_decision": "new_separated_action_prompts_pending_user_review_no_queue_no_video",
    })
    contracts_payload["clips"] = contracts
    contracts_payload["project_id"] = PROJECT_ID
    return spec, contracts_payload


def main() -> int:
    spec, contracts = build_payloads()
    SPEC_PATH.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    CONTRACTS_PATH.write_text(
        json.dumps(contracts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    result = h3_prompt_project_builder.build_project(ROOT, SPEC_PATH)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
