#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "RaisingaDragonSeason01"
SPEC_PATH = PROJECT / "EP00_H3_R2V_REBUILD_V1_SPEC.json"
CONTRACT_PATH = PROJECT / "EP00_H3_INDEPENDENT_SHOT_PLANS_V2.json"


CAMERAS = {
    "A": (
        "A wide establishing shot keeps the cause, travel path and destination readable on one world axis.",
        "A contact-height medium shot cuts closer without crossing that axis.",
        "A result-oriented wide shot lets the spatial change settle before the outgoing anchor.",
        "A restrained closing shot holds the referenced outgoing subject long enough to motivate the cut.",
    ),
    "B": (
        "A three-quarter tracking shot stays with whole-body mechanics and the direction of force.",
        "A closer action shot follows the assigned movement from body load through its visible release or interruption.",
        "An over-shoulder reaction shot changes scale while preserving eyeline and screen direction.",
        "A short opposing-subject close holds the referenced reaction that starts the following cut.",
    ),
    "C": (
        "A reverse-angle reaction shot opens from the receiving side while retaining the established world axis.",
        "A lateral profile shot proves the complete source-to-contact route.",
        "A close-to-wide transition gives the resulting spatial change its full size and direction.",
        "A final motivated close isolates the referenced gesture, gaze or stance used as the edit bridge.",
    ),
}


def _groups(beat_count: int, duration: float, variant: str) -> list[list[int]]:
    if duration >= 11:
        patterns = {
            "A": [[0, 1], [2], [3, 4], [5]],
            "B": [[0], [1, 2], [3], [4, 5]],
            "C": [[0], [1], [2, 3], [4, 5]],
        }
    elif duration <= 6:
        patterns = {
            "A": [[0], [1, 2]],
            "B": [[0, 1], [2]],
            "C": [[0], [1, 2]],
        }
    elif beat_count == 3:
        patterns = {
            "A": [[0], [1], [2]],
            "B": [[0, 1], [2]],
            "C": [[0], [1], [2]],
        }
    else:
        patterns = {
            "A": [[0], [1, 2], [3]],
            "B": [[0, 1], [2], [3]],
            "C": [[0], [1], [2, 3]],
        }
    groups = patterns[variant]
    flattened = [index for group in groups for index in group]
    if flattened != list(range(beat_count)):
        raise ValueError(f"지원하지 않는 beat 구성: duration={duration}, beats={beat_count}")
    return groups


def _starts(duration: float, count: int, variant: str) -> list[float]:
    fractions = {
        2: {"A": (0.60,), "B": (0.57,), "C": (0.54,)},
        3: {"A": (0.29, 0.66), "B": (0.38, 0.70), "C": (0.25, 0.58)},
        4: {"A": (0.22, 0.45, 0.78), "B": (0.18, 0.40, 0.67), "C": (0.20, 0.37, 0.65)},
    }[count][variant]
    return [round(duration * fraction, 1) for fraction in fractions]


def _plans(beats: list[dict], duration: float) -> dict:
    result = {}
    emphases = {
        "A": "cause, travel path, contact and result on a legible spatial axis",
        "B": "whole-body mechanics, force transfer and the opposing subject reaction",
        "C": "reaction-led cutting, impact scale and the referenced outgoing edit bridge",
    }
    for variant in ("A", "B", "C"):
        groups = _groups(len(beats), duration, variant)
        starts = _starts(duration, len(groups), variant)
        shots = []
        for index, group in enumerate(groups):
            camera_rows = CAMERAS[variant]
            camera = camera_rows[min(index, len(camera_rows) - 1)]
            row = {
                "camera": camera,
                "beat_ids": [beats[beat_index]["beat_id"] for beat_index in group],
            }
            if index:
                row["start_seconds"] = starts[index - 1]
            shots.append(row)
        result[variant] = {"emphasis": emphases[variant], "shots": shots}
    return result


def contract(
    *,
    clip_id: str,
    duration: float,
    source_shot_ids: list[str],
    bridge_in_id: str,
    bridge_out_id: str,
    boundary_policy: str,
    incoming_subjects: list[int],
    outgoing_subjects: list[int],
    incoming_bridge: str,
    outgoing_bridge: str,
    shared_event: str,
    beats: list[tuple[str, str]],
) -> tuple[str, dict]:
    beat_rows = [
        {"beat_id": beat_id, "description": description}
        for beat_id, description in beats
    ]
    return clip_id, {
        "source_shot_ids": source_shot_ids,
        "shared_event": shared_event,
        "bridge_in_id": bridge_in_id,
        "bridge_out_id": bridge_out_id,
        "boundary_policy": boundary_policy,
        "incoming_reference_subjects": incoming_subjects,
        "outgoing_reference_subjects": outgoing_subjects,
        "incoming_bridge": incoming_bridge,
        "outgoing_bridge": outgoing_bridge,
        "beats": beat_rows,
        "candidate_plans": _plans(beat_rows, duration),
    }


def build_contracts() -> dict:
    rows = [
        contract(
            clip_id="EP00-S01-NC01", duration=7, source_shot_ids=["EP00-S01-SH01"],
            bridge_in_id="episode_open_dark_pulse", bridge_out_id="king_tracks_falling_wake",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 3], outgoing_subjects=[1],
            incoming_bridge="<Subject 2> HeartstoneArena begins in darkness while the first pulse from <Subject 3> Heartstone sends pressure across the floor beneath <Subject 1> AbyssKing.",
            outgoing_bridge="End on a close view of <Subject 1> AbyssKing turning his eyes and crown roots toward the upper-left falling wake; the referenced enemy, not the wake alone, remains the final image.",
            shared_event="Three heartbeats reveal the arena, Heartstone and complete Abyss King before he notices a falling cyan wake.",
            beats=[
                ("first_pulse", "<Subject 3> Heartstone gives one dim heartbeat; suspended grit and water pressure move through <Subject 2> HeartstoneArena while <Subject 1> AbyssKing remains mostly hidden."),
                ("second_pulse", "<Subject 3> Heartstone pulses again and reveals the pedestal, broken arches and the connected root-skirt base of <Subject 1> AbyssKing inside <Subject 2> HeartstoneArena."),
                ("third_pulse", "The third pulse reveals the complete body of <Subject 1> AbyssKing from crown-root head through two arms and six battle roots; he inhales and the columns answer his scale."),
            ],
        ),
        contract(
            clip_id="EP00-S01-NC02", duration=8, source_shot_ids=["EP00-S01-SH02"],
            bridge_in_id="king_tracks_falling_wake", bridge_out_id="lua_turns_toward_exit",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 4], outgoing_subjects=[1],
            incoming_bridge="Open on <Subject 1> Lua descending from upper-left through the wake that <Subject 2> AbyssKing is tracking inside <Subject 4> HeartstoneArena; <Subject 3> DragonSpear stays in both hands and <Subject 5> Heartstone lights the rear-right depth.",
            outgoing_bridge="End on a close view of <Subject 1> Lua lifting her head, then turning her eyes and shoulders toward the arena exit; her referenced face and turn motivate the cut to the enemy's full-body response.",
            shared_event="Lua falls, rotates into a three-point landing, recovers her spear grip and turns toward the exit under the king's gaze.",
            beats=[
                ("fall", "<Subject 1> Lua falls toward wet stone with <Subject 3> DragonSpear secured lengthwise while <Subject 2> AbyssKing remains far ahead in <Subject 4> HeartstoneArena beneath <Subject 5> Heartstone."),
                ("landing", "<Subject 1> Lua rotates hips and shoulders together, then contacts the floor with left palm, right knee and left foot; water and grit burst from the single contact zone while <Subject 3> DragonSpear never leaves her grip."),
                ("recovery", "<Subject 1> Lua absorbs the landing, restores a two-handed hold on <Subject 3> DragonSpear and raises her gaze toward <Subject 2> AbyssKing before checking the exit."),
            ],
        ),
        contract(
            clip_id="EP00-S01-NC03", duration=8, source_shot_ids=["EP00-S01-SH03"],
            bridge_in_id="lua_turns_toward_exit", bridge_out_id="king_left_palm_charged",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 4], outgoing_subjects=[2],
            incoming_bridge="Open on the complete <Subject 2> AbyssKing between the exit and foreground <Subject 1> Lua inside <Subject 4> HeartstoneArena; <Subject 3> DragonSpear is already held low and <Subject 5> Heartstone remains rear-right.",
            outgoing_bridge="End on a close view of <Subject 2> AbyssKing drawing his anatomical left arm behind the torso as black water compresses in the open left palm; the charged referenced hand is the final cause clue.",
            shared_event="The king's connected lower roots block the exit, Lua commits to guard, and the king completes the preparation for a left-palm sweep.",
            beats=[
                ("exit_check", "<Subject 1> Lua takes one step toward the exit with <Subject 3> DragonSpear while the lower body of <Subject 2> AbyssKing remains grounded across <Subject 4> HeartstoneArena under <Subject 5> Heartstone."),
                ("root_block", "Six thick roots physically connected to <Subject 2> AbyssKing slide across the exit and plant against stone before <Subject 1> Lua can pass."),
                ("guard_charge", "<Subject 1> Lua stops, sets both feet and raises <Subject 3> DragonSpear into guard as <Subject 2> AbyssKing braces his roots and begins loading the left arm."),
            ],
        ),
        contract(
            clip_id="EP00-S02-NC01", duration=15, source_shot_ids=["EP00-S02-SH04", "EP00-S02-SH05"],
            bridge_in_id="king_left_palm_charged", bridge_out_id="clear_lane_right_hand_threat",
            boundary_policy="merged_unreferenced_object", incoming_subjects=[1, 2, 4], outgoing_subjects=[1, 2],
            incoming_bridge="Open on <Subject 2> AbyssKing with the charged left palm already drawn back while <Subject 1> Lua guards the lower route in <Subject 4> HeartstoneArena; <Subject 3> DragonSpear, <Subject 5> Heartstone, <Subject 6> FloorCurrent and <Subject 7> DragonHeartMark retain their referenced designs.",
            outgoing_bridge="End after the three fragments have left the active lane: <Subject 1> Lua shifts her full body into a sprint through the opening while the referenced right hand of <Subject 2> AbyssKing begins closing from above.",
            shared_event="The king creates exactly three unreferenced column fragments and, within the same clip, Lua charges her spear, strikes the floor and redirects those exact fragments out of her route.",
            beats=[
                ("sweep", "<Subject 2> AbyssKing braces six roots, rotates torso, shoulder and left arm together, and sweeps the charged left palm across the floor; <Subject 1> Lua lowers <Subject 3> DragonSpear along her body and slides beneath the traveling palm before its five fingertips reach the standing columns."),
                ("three_fragments", "The same connected sweep breaks exactly three columns inside <Subject 4> HeartstoneArena beneath <Subject 5> Heartstone, creating three large fragments with stable left, upper-middle and right shapes."),
                ("approach", "Those exact three unreferenced fragments rotate toward <Subject 1> Lua and close the forward lane without changing count or shape."),
                ("charge", "<Subject 7> DragonHeartMark lights on <Subject 1> Lua's wrist and sends cyan energy through both hands and <Subject 3> DragonSpear into the black stone tip."),
                ("floor_strike", "<Subject 1> Lua lowers her hips and drives <Subject 3> DragonSpear into wet stone; <Subject 6> FloorCurrent expands from the contact point as one horizontal circular pressure ring."),
                ("redirect", "<Subject 6> FloorCurrent sends the same left fragment left, the same upper-middle fragment above the route and the same right fragment right; <Subject 1> Lua recovers <Subject 3> DragonSpear, takes three accelerating steps toward the left wrist of <Subject 2> AbyssKing and enters the cleared lane as his right hand starts closing from above."),
            ],
        ),
        contract(
            clip_id="EP00-S02-NC03", duration=9, source_shot_ids=["EP00-S02-SH06"],
            bridge_in_id="clear_lane_right_hand_threat", bridge_out_id="lua_crosses_twisted_right_hand",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 4], outgoing_subjects=[1, 2],
            incoming_bridge="Open on <Subject 1> Lua sprinting through the cleared lane as the connected right hand of <Subject 2> AbyssKing descends from above inside <Subject 4> HeartstoneArena; <Subject 3> DragonSpear stays in both hands and <Subject 5> Heartstone anchors the rear-right.",
            outgoing_bridge="End with <Subject 1> Lua running across the back of the visibly twisted referenced right hand of <Subject 2> AbyssKing, her body and <Subject 3> DragonSpear aligned toward the forearm.",
            shared_event="Lua runs at the closing right hand, rotates with her spear to strike the wrist, redirects the hand into the floor and crosses its back.",
            beats=[
                ("hand_closes", "The five fingers of <Subject 2> AbyssKing close toward <Subject 1> Lua while the wrist remains visibly connected through the arm to the torso in <Subject 4> HeartstoneArena under <Subject 5> Heartstone."),
                ("body_rotation", "<Subject 1> Lua plants one foot, rotates feet, hips and shoulders as one unit, and carries <Subject 3> DragonSpear through the same circular path rather than spinning the weapon alone."),
                ("wrist_contact", "The blade of <Subject 3> DragonSpear cuts one coral ridge on the back of the right hand of <Subject 2> AbyssKing; the released pressure twists the connected wrist and redirects the open hand into wet stone while <Subject 1> Lua keeps both hands on the shaft."),
                ("cross_hand", "<Subject 1> Lua completes the turn, restores her running grip and crosses the back of the grounded right hand of <Subject 2> AbyssKing toward the forearm."),
            ],
        ),
        contract(
            clip_id="EP00-S02-NC04", duration=8, source_shot_ids=["EP00-S02-SH07"],
            bridge_in_id="lua_crosses_twisted_right_hand", bridge_out_id="lua_hears_roots_below",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 4], outgoing_subjects=[1],
            incoming_bridge="Open on <Subject 1> Lua crossing the twisted right hand of <Subject 2> AbyssKing inside <Subject 4> HeartstoneArena with <Subject 3> DragonSpear held lengthwise, <Subject 5> Heartstone rear-right and <Subject 6> DragonHeartMark fixed to her wrist.",
            outgoing_bridge="End on a close view of <Subject 1> Lua landing on one knee, pressing one foot into the vibrating floor and turning her eyes downward as connected roots scrape beneath her; keep her referenced reaction as the final image.",
            shared_event="The king attacks with both hands, Lua folds through the final lower gap, lands and detects connected roots moving beneath the floor.",
            beats=[
                ("pincer", "The connected left hand of <Subject 2> AbyssKing drops from above while the right palm rises from below around <Subject 1> Lua; <Subject 5> Heartstone lights the depth of <Subject 4> HeartstoneArena."),
                ("gap_escape", "<Subject 6> DragonHeartMark flashes once as <Subject 1> Lua lowers her head, aligns <Subject 3> DragonSpear with her torso, folds knees and shoulders, and performs one compact shoulder-and-side roll through the last gap between the thumbs."),
                ("landing", "The palms of <Subject 2> AbyssKing meet behind <Subject 1> Lua and accelerate her exit; she unfolds and lands beyond them with <Subject 3> DragonSpear still in both hands."),
            ],
        ),
        contract(
            clip_id="EP00-S03-NC01", duration=8, source_shot_ids=["EP00-S03-SH08"],
            bridge_in_id="lua_hears_roots_below", bridge_out_id="lua_inside_six_root_ring",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 4], outgoing_subjects=[1, 2],
            incoming_bridge="Open on the complete <Subject 2> AbyssKing as six thick roots connected to his lower body begin rising around kneeling <Subject 1> Lua inside <Subject 4> HeartstoneArena; <Subject 3> DragonSpear remains in her grip and <Subject 5> Heartstone stays rear-right.",
            outgoing_bridge="End with <Subject 1> Lua standing wide inside the completed six-root ring while the thickest connected root of <Subject 2> AbyssKing remains raised above her open left-hand defense line.",
            shared_event="Exactly six connected battle roots rise and form a readable encirclement while Lua stands and prepares one directional defense axis.",
            beats=[
                ("origins", "Six identifiable roots lift from six points in the same lower body of <Subject 2> AbyssKing while <Subject 1> Lua rises with <Subject 3> DragonSpear inside <Subject 4> HeartstoneArena beneath <Subject 5> Heartstone."),
                ("encirclement", "Three roots of <Subject 2> AbyssKing plant in front of <Subject 1> Lua, two take the flanks, and the thickest remains overhead; thin skirt roots only trail."),
                ("defense_axis", "<Subject 1> Lua takes two steps onto the open patch, sets both feet wide, holds <Subject 3> DragonSpear low and raises her left hand toward the connected roots of <Subject 2> AbyssKing."),
            ],
        ),
        contract(
            clip_id="EP00-S03-NC02", duration=10, source_shot_ids=["EP00-S03-SH09"],
            bridge_in_id="lua_inside_six_root_ring", bridge_out_id="damaged_shield_final_root_ready",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 4], outgoing_subjects=[1, 2, 6],
            incoming_bridge="Open on <Subject 1> Lua inside the six connected roots of <Subject 2> AbyssKing in <Subject 4> HeartstoneArena; <Subject 3> DragonSpear is low, <Subject 5> Heartstone is rear-right, <Subject 6> CurrentShield is not yet formed and <Subject 7> DragonHeartMark begins charging her open left palm.",
            outgoing_bridge="End on stationary <Subject 1> Lua behind the single damaged but intact <Subject 6> CurrentShield while the thickest connected root of <Subject 2> AbyssKing draws back above the shield.",
            shared_event="Lua's first shield attempt is interrupted, she rolls out and stops, then forms one directional shield and absorbs two root strikes.",
            beats=[
                ("failed_charge", "<Subject 7> DragonHeartMark sends light into <Subject 1> Lua's extended palm, but a front-left root of <Subject 2> AbyssKing lashes before <Subject 6> CurrentShield can form; she closes the hand and extinguishes the core."),
                ("roll_stop", "<Subject 1> Lua keeps <Subject 3> DragonSpear close, performs one roll through the right-side gap in <Subject 4> HeartstoneArena beneath <Subject 5> Heartstone, rises outside the ring and plants both feet without continuing to walk."),
                ("shield_forms", "Only after stopping, <Subject 7> DragonHeartMark relights and <Subject 1> Lua opens her left palm to form one upright curved <Subject 6> CurrentShield facing <Subject 2> AbyssKing."),
                ("two_impacts", "A second root of <Subject 2> AbyssKing strikes the lower-left quarter of <Subject 6> CurrentShield and a third strikes the upper-right quarter; two stress zones remain while <Subject 1> Lua holds position."),
            ],
        ),
        contract(
            clip_id="EP00-S03-NC03", duration=10, source_shot_ids=["EP00-S03-SH10"],
            bridge_in_id="damaged_shield_final_root_ready", bridge_out_id="fallen_lua_hand_and_current_approach",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 6], outgoing_subjects=[1, 2, 8],
            incoming_bridge="Open on <Subject 1> Lua braced behind the damaged <Subject 6> CurrentShield as the thickest root and right hand of <Subject 2> AbyssKing align for one strike inside <Subject 4> HeartstoneArena; <Subject 3> DragonSpear, <Subject 5> Heartstone, <Subject 7> DragonHeartMark and <Subject 8> MovingCurrent retain their referenced designs.",
            outgoing_bridge="End with fallen <Subject 1> Lua under the closing referenced right hand of <Subject 2> AbyssKing while the first edge of <Subject 8> MovingCurrent enters beneath that wrist from deep left.",
            shared_event="The final root and right palm collapse the damaged water shield, drive Lua along the attack direction, and a referenced moving current enters beneath the closing wrist.",
            beats=[
                ("root_contact", "The thickest connected root of <Subject 2> AbyssKing strikes the weakened zone of <Subject 6> CurrentShield first while <Subject 1> Lua braces with <Subject 3> DragonSpear under <Subject 5> Heartstone in <Subject 4> HeartstoneArena."),
                ("palm_pressure", "The right palm of <Subject 2> AbyssKing follows along the same force line; <Subject 6> CurrentShield tears into water sheets, droplets and bubbles rather than glass shards as <Subject 7> DragonHeartMark flickers."),
                ("recoil", "<Subject 1> Lua is pushed in the attack direction, skids toward the right column and keeps <Subject 3> DragonSpear in both hands while the collapsed <Subject 6> CurrentShield marks the contact location."),
                ("rescue_clue", "The connected right hand of <Subject 2> AbyssKing casts a closing shadow over <Subject 1> Lua as <Subject 8> MovingCurrent appears from deep left and approaches the underside of the wrist."),
            ],
        ),
        contract(
            clip_id="EP00-S04-NC01", duration=8, source_shot_ids=["EP00-S04-SH11"],
            bridge_in_id="fallen_lua_hand_and_current_approach", bridge_out_id="lua_runs_outer_right_arm",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 6], outgoing_subjects=[1, 2, 6],
            incoming_bridge="Open on fallen <Subject 1> Lua as <Subject 6> MovingCurrent slides under the closing right wrist of <Subject 2> AbyssKing inside <Subject 4> HeartstoneArena; <Subject 3> DragonSpear stays with her and <Subject 5> Heartstone anchors the rear-right.",
            outgoing_bridge="End with <Subject 1> Lua running upright on <Subject 6> MovingCurrent along the outside of the referenced right forearm of <Subject 2> AbyssKing, the lifted hand receding below.",
            shared_event="The moving cyan current lifts the closing right wrist, Lua rises onto it and accelerates along the outside of the king's right arm.",
            beats=[
                ("lift_wrist", "<Subject 6> MovingCurrent increases pressure beneath the right wrist of <Subject 2> AbyssKing and lifts the hand away from <Subject 1> Lua in <Subject 4> HeartstoneArena beneath <Subject 5> Heartstone."),
                ("mount", "<Subject 1> Lua rises from floor to one knee and both feet, keeps <Subject 3> DragonSpear close, and places right then left foot onto the dense center of <Subject 6> MovingCurrent."),
                ("accelerate", "<Subject 6> MovingCurrent bends up the outside of the right forearm of <Subject 2> AbyssKing and carries <Subject 1> Lua into upright running strides."),
            ],
        ),
        contract(
            clip_id="EP00-S04-NC02", duration=9, source_shot_ids=["EP00-S04-SH12"],
            bridge_in_id="lua_runs_outer_right_arm", bridge_out_id="right_arm_begins_twist",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 6], outgoing_subjects=[1, 2],
            incoming_bridge="Open on <Subject 1> Lua running along the outer right arm of <Subject 2> AbyssKing on <Subject 6> MovingCurrent inside <Subject 4> HeartstoneArena; <Subject 3> DragonSpear is reset forward and <Subject 5> Heartstone remains behind-right.",
            outgoing_bridge="End with <Subject 1> Lua reaching the upper right arm as <Subject 2> AbyssKing begins twisting that referenced arm beneath her; hold both connected bodies in the final frame.",
            shared_event="Lua runs up the right arm, evades the opposite left-hand finger attack, cuts the index finger and reaches the upper arm as it begins twisting.",
            beats=[
                ("run", "<Subject 1> Lua alternates upright steps on <Subject 6> MovingCurrent along the right arm of <Subject 2> AbyssKing while <Subject 3> DragonSpear stays aligned with the route through <Subject 4> HeartstoneArena under <Subject 5> Heartstone."),
                ("finger_attack", "The opposite left hand of <Subject 2> AbyssKing spreads all five fingers across the route while remaining visibly connected through wrist, arm and torso."),
                ("evade_cut", "<Subject 1> Lua lowers her torso and passes between the middle and ring fingers; when the index finger returns, she makes one short two-handed cut with <Subject 3> DragonSpear through its coral ridge without leaving <Subject 6> MovingCurrent."),
                ("upper_arm", "<Subject 1> Lua restores forward running on <Subject 6> MovingCurrent and reaches the upper right arm as <Subject 2> AbyssKing starts rotating the shoulder and arm."),
            ],
        ),
        contract(
            clip_id="EP00-S04-NC03", duration=9, source_shot_ids=["EP00-S04-SH13"],
            bridge_in_id="right_arm_begins_twist", bridge_out_id="three_crown_roots_close_route",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 6], outgoing_subjects=[1, 2],
            incoming_bridge="Open on <Subject 1> Lua above the twisting right arm of <Subject 2> AbyssKing while <Subject 6> MovingCurrent still supports her inside <Subject 4> HeartstoneArena; <Subject 3> DragonSpear, <Subject 5> Heartstone and <Subject 7> DragonHeartMark remain referenced.",
            outgoing_bridge="End with <Subject 1> Lua below the referenced right shoulder of <Subject 2> AbyssKing as exactly three connected crown roots enter and close the route ahead.",
            shared_event="Lua absorbs the arm twist with spear and armor, regains the moving current and reaches the shoulder as three crown roots close her route.",
            beats=[
                ("twist", "<Subject 2> AbyssKing twists the right arm beneath <Subject 1> Lua; she lays <Subject 3> DragonSpear across the roll and lets the shaft guide her body rather than pitching away from <Subject 6> MovingCurrent."),
                ("armor", "The pressure lights <Subject 7> DragonHeartMark and activates cyan scale armor over <Subject 1> Lua's forearm, shoulder and ribs while <Subject 5> Heartstone reflects across <Subject 4> HeartstoneArena."),
                ("recover", "<Subject 1> Lua hooks one knee, returns both feet to <Subject 6> MovingCurrent and runs toward the right shoulder of <Subject 2> AbyssKing with <Subject 3> DragonSpear close."),
                ("roots_enter", "Exactly three crown roots connected to the head of <Subject 2> AbyssKing swing into the route ahead of <Subject 1> Lua below the shoulder."),
            ],
        ),
        contract(
            clip_id="EP00-S04-NC04", duration=8, source_shot_ids=["EP00-S04-SH14"],
            bridge_in_id="three_crown_roots_close_route", bridge_out_id="face_to_face_confrontation",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 6], outgoing_subjects=[1, 2],
            incoming_bridge="Open on <Subject 1> Lua below the right shoulder of <Subject 2> AbyssKing as three connected crown roots block <Subject 6> MovingCurrent inside <Subject 4> HeartstoneArena; <Subject 3> DragonSpear and <Subject 5> Heartstone retain their referenced shapes.",
            outgoing_bridge="End on a face-to-face composition containing airborne <Subject 1> Lua and the complete referenced face and torso of <Subject 2> AbyssKing as he straightens to address her.",
            shared_event="Lua deflects and clears three crown roots, uses the right shoulder ridge as a step and launches into open water before the king's face.",
            beats=[
                ("root_break", "<Subject 1> Lua passes under the first connected crown root of <Subject 2> AbyssKing, makes one short cut through the tip of the second with <Subject 3> DragonSpear, and clears the third before it closes while <Subject 6> MovingCurrent carries her forward."),
                ("shoulder_step", "<Subject 1> Lua places one foot on the right shoulder ridge of <Subject 2> AbyssKing in <Subject 4> HeartstoneArena beneath <Subject 5> Heartstone and compresses both legs for launch."),
                ("face_launch", "<Subject 1> Lua pushes off the shoulder, leaves <Subject 6> MovingCurrent behind and enters open water before the face of <Subject 2> AbyssKing with <Subject 3> DragonSpear held for a thrust."),
            ],
        ),
        contract(
            clip_id="EP00-S05-NC01", duration=7, source_shot_ids=["EP00-S05-SH15"],
            bridge_in_id="face_to_face_confrontation", bridge_out_id="lua_charge_begins_after_king_line",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2, 4], outgoing_subjects=[1, 7],
            incoming_bridge="Open on airborne <Subject 1> Lua facing the complete <Subject 2> AbyssKing in <Subject 4> HeartstoneArena; <Subject 3> DragonSpear is held close, <Subject 5> Heartstone remains rear-right, <Subject 6> MovingCurrent trails behind-left and <Subject 7> DragonHeartMark is dim.",
            outgoing_bridge="End on a close view of silent <Subject 1> Lua fixing her thrust grip as <Subject 7> DragonHeartMark begins one controlled cyan charge after the enemy line ends.",
            shared_event="The visible king closes retreat space and speaks; Lua remains silent, fixes her thrust guard and begins charging the wrist mark.",
            beats=[
                ("king_blocks", "<Subject 2> AbyssKing pulls grounded roots inward and spreads exactly two arms to close the retreat space around <Subject 1> Lua while <Subject 5> Heartstone lights <Subject 4> HeartstoneArena and <Subject 6> MovingCurrent trails behind her."),
                ("king_line", "The mouth fissure, throat and chest of <Subject 2> AbyssKing articulate together as <Subject 2> (S1) <d>[Korean]인간은 용을 키울 수 없다.</d> <Subject 1> Lua keeps her lips closed and holds the eyeline."),
                ("lua_guard", "As the line ends, <Subject 1> Lua draws <Subject 3> DragonSpear close with left hand forward and right hand back while <Subject 7> DragonHeartMark begins glowing."),
            ],
        ),
        contract(
            clip_id="EP00-S05-NC02", duration=7, source_shot_ids=["EP00-S05-SH16"],
            bridge_in_id="lua_charge_begins_after_king_line", bridge_out_id="spear_tip_and_king_palms_charge",
            boundary_policy="referenced_cut", incoming_subjects=[1, 7], outgoing_subjects=[1, 2],
            incoming_bridge="Open on <Subject 1> Lua holding the charged guard before silent <Subject 2> AbyssKing inside <Subject 4> HeartstoneArena; <Subject 3> DragonSpear, <Subject 5> Heartstone, <Subject 6> MovingCurrent and <Subject 7> DragonHeartMark remain in their referenced states.",
            outgoing_bridge="End on a two-subject composition: <Subject 1> Lua's spear tip holds compressed cyan light while <Subject 2> AbyssKing brings both referenced palms together before his chest.",
            shared_event="Lua gives her first reply, closes her mouth, moves wrist energy into the spear tip, and the silent king begins gathering black pressure between his palms.",
            beats=[
                ("lua_line", "<Subject 1> Lua holds <Subject 3> DragonSpear on the same axis and <Subject 1> (S1) <d>[Korean]키운 게 아니야.</d> before closing her mouth; <Subject 2> AbyssKing remains silent under <Subject 5> Heartstone in <Subject 4> HeartstoneArena."),
                ("cyan_transfer", "During the silence, light from <Subject 7> DragonHeartMark crosses <Subject 1> Lua's armor and both hands into <Subject 3> DragonSpear while <Subject 6> MovingCurrent pushes hair and cloth forward."),
                ("black_gather", "The mouth of <Subject 2> AbyssKing stays still as exactly two hands move toward each other and begin gathering one black pressure core before the chest; the cyan light at <Subject 3> DragonSpear compresses in opposition."),
            ],
        ),
        contract(
            clip_id="EP00-S05-NC03", duration=8, source_shot_ids=["EP00-S05-SH17"],
            bridge_in_id="spear_tip_and_king_palms_charge", bridge_out_id="lua_inhales_at_maximum_charge",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2], outgoing_subjects=[1, 2],
            incoming_bridge="Open on <Subject 1> Lua at left with <Subject 3> DragonSpear already charged opposite <Subject 2> AbyssKing at right with both palms facing inside <Subject 4> HeartstoneArena; <Subject 5> Heartstone and <Subject 6> DragonHeartMark hold their referenced light.",
            outgoing_bridge="End on a close two-plane composition of <Subject 1> Lua taking one visible inhale behind the maximum spear charge while the referenced hands and eyes of <Subject 2> AbyssKing hold maximum black pressure.",
            shared_event="The spear-tip current and the king's palm core grow simultaneously to maximum charge without firing, and Lua inhales to speak.",
            beats=[
                ("cyan_layers", "<Subject 6> DragonHeartMark keeps a steady glow as transparent current layers wrap the tip of <Subject 3> DragonSpear held by <Subject 1> Lua; <Subject 5> Heartstone lights the rear-right of <Subject 4> HeartstoneArena."),
                ("black_core", "Black ink travels from the six grounded roots of <Subject 2> AbyssKing through torso and exactly two arms into one core between the facing palms."),
                ("maximum_hold", "<Subject 1> Lua and <Subject 2> AbyssKing hold the two fully compressed attacks on the same axis without release; suspended grit gathers between them and <Subject 1> Lua begins one inhale."),
            ],
        ),
        contract(
            clip_id="EP00-S06-NC01", duration=8, source_shot_ids=["EP00-S06-SH18"],
            bridge_in_id="lua_inhales_at_maximum_charge", bridge_out_id="both_sources_hold_precontact_releases",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2], outgoing_subjects=[1, 2],
            incoming_bridge="Open on inhaling <Subject 1> Lua holding the maximum charge around <Subject 3> DragonSpear opposite the fully braced <Subject 2> AbyssKing in <Subject 4> HeartstoneArena beneath <Subject 5> Heartstone.",
            outgoing_bridge="End on the two referenced sources rather than an isolated effect: <Subject 1> Lua holds the completed thrust at left and <Subject 2> AbyssKing holds both extended palms at right while their releases nearly meet between them.",
            shared_event="Lua speaks from the existing charge, thrusts straight once, and both sides release one attack toward near-contact without an extra spin.",
            beats=[
                ("final_line", "<Subject 1> Lua maintains the charged stance around <Subject 3> DragonSpear and <Subject 1> (S1) <d>[Korean]같이 큰 거지.</d> while <Subject 2> AbyssKing stays silent under <Subject 5> Heartstone in <Subject 4> HeartstoneArena."),
                ("dual_release", "After the final word and lip movement end, <Subject 1> Lua extends shoulders and both arms into one straight thrust with <Subject 3> DragonSpear and releases one spiral cyan current; <Subject 2> AbyssKing braces six roots, pushes both palms once and releases one black current."),
                ("precontact", "The two releases advance along the same empty lane and slow immediately before contact while <Subject 1> Lua and <Subject 2> AbyssKing preserve their full recoil-ready postures."),
            ],
        ),
        contract(
            clip_id="EP00-S06-NC02", duration=10, source_shot_ids=["EP00-S06-SH19"],
            bridge_in_id="both_sources_hold_precontact_releases", bridge_out_id="king_chest_receives_cyan_pressure",
            boundary_policy="referenced_cut", incoming_subjects=[1, 2], outgoing_subjects=[2],
            incoming_bridge="Open wide on <Subject 1> Lua and <Subject 2> AbyssKing as the releases from <Subject 3> DragonSpear and the king's two palms resume from near-contact inside <Subject 4> HeartstoneArena beneath <Subject 5> Heartstone.",
            outgoing_bridge="End on a close view of <Subject 2> AbyssKing with both referenced palms forced apart and cyan reflection first reaching the intact chest surface between them; do not end on the pressure plane alone.",
            shared_event="The two releases collide once, form a flat pressure plane, drive opposite recoil through both bodies, and cyan pressure advances a short distance to the king's chest.",
            beats=[
                ("collision", "The cyan release from <Subject 1> Lua's <Subject 3> DragonSpear meets the black release from <Subject 2> AbyssKing once at center inside <Subject 4> HeartstoneArena under <Subject 5> Heartstone."),
                ("pressure_plane", "The collision compresses into one broad flat pressure plane; clear water and bubbles separate vertically while black ink and stone chips separate laterally."),
                ("opposite_recoil", "Pressure pushes <Subject 1> Lua left-rear while both hands keep <Subject 3> DragonSpear aligned; opposite recoil bends the wrists, shoulders and torso of <Subject 2> AbyssKing and stretches six grounded roots."),
                ("short_advance", "The cyan boundary advances only one short step, forces the two palms of <Subject 2> AbyssKing apart and first touches the intact chest surface without yet forming a crack."),
            ],
        ),
        contract(
            clip_id="EP00-S06-NC03", duration=6, source_shot_ids=["EP00-S06-SH20"],
            bridge_in_id="king_chest_receives_cyan_pressure", bridge_out_id="episode_unresolved_result",
            boundary_policy="terminal", incoming_subjects=[1, 2], outgoing_subjects=[1, 2, 4, 5],
            incoming_bridge="Open on <Subject 2> AbyssKing receiving cyan pressure between separated palms while <Subject 1> Lua maintains both hands on <Subject 3> DragonSpear inside <Subject 4> HeartstoneArena with <Subject 5> Heartstone rear-right.",
            outgoing_bridge="End on one stable unresolved full-body frame containing <Subject 1> Lua, <Subject 2> AbyssKing, <Subject 4> HeartstoneArena and the single pulsing <Subject 5> Heartstone; this referenced tableau is the clean editorial transition point.",
            shared_event="Cyan pressure forms one thin chest crack, both bodies recoil, the king's crown and eyes recover, and the Heartstone pulses before an unresolved final tableau.",
            beats=[
                ("chest_crack", "One thin cyan crack forms across the center chest surface of <Subject 2> AbyssKing while <Subject 1> Lua keeps <Subject 3> DragonSpear aligned in <Subject 4> HeartstoneArena under <Subject 5> Heartstone."),
                ("body_recoil", "The force moves <Subject 1> Lua left-rear and the torso of <Subject 2> AbyssKing right-rear while six battle roots and the <Subject 5> Heartstone connection pull taut; neither body falls."),
                ("pulse_tableau", "The crown roots and eyes of <Subject 2> AbyssKing brighten again, then <Subject 5> Heartstone sends one large pulse across <Subject 4> HeartstoneArena and <Subject 1> Lua before motion settles."),
            ],
        ),
    ]
    return {
        "version": "independent_shot_plans_v2",
        "clips": dict(rows),
    }


def update_spec(spec: dict) -> dict:
    spec = deepcopy(spec)
    clips = {row["clip_id"]: deepcopy(row) for row in spec["clips"]}
    first = clips["EP00-S02-NC01"]
    second = clips.get("EP00-S02-NC02")
    first["duration_seconds"] = 15.0
    if second is not None:
        first["references"] = deepcopy(second["references"])
    first["prompt_base"] = {
        "summary": "[reference generation] The Abyss King creates exactly three column fragments and, in the same clip, Lua charges her spear, strikes the floor and redirects those exact fragments out of her route.",
        "style_opening": ["Cause, fragment identity, floor contact and final cleared route remain readable across motivated cuts."],
        "overall_soundscape": "Compressed black-water release, three column fractures, rotating stone, rising spear resonance, one floor strike, an expanding current ring and three displaced impacts.",
        "non_diegetic_music": "Low percussion follows the sweep, rises through the spear charge and releases on one broad brass impact.",
    }
    first["prompt_variants"] = [
        {"variant_id": "A", "label": "생성부터 편향까지 공간 인과", "rationale": "세 파편의 생성·접근·동일성·편향을 넓은 축에서 증명", "prompt_spec": {}},
        {"variant_id": "B", "label": "전신 역학과 바닥 접촉", "rationale": "심해왕 전신 휩쓸기와 루아 전신 바닥 타격을 접촉 중심으로 연결", "prompt_spec": {}},
        {"variant_id": "C", "label": "루아 반응과 통로 개방", "rationale": "다가오는 파편에 대한 루아 반응에서 시작해 최종 개방 결과와 다음 손 공격을 연결", "prompt_spec": {}},
    ]
    first["continuity_out"] = "동일한 세 파편이 전투선 밖으로 이탈하고 루아가 열린 통로로 달리며 심해왕 오른손이 위에서 닫히기 시작"
    first["scenario_ko"] = "심해왕이 정확히 세 기둥 파편을 만든 뒤, 같은 클립 안에서 루아가 창끝을 충전해 바닥을 찍고 동일한 세 파편을 해류로 편향한다."
    first["review_intent_ko"] = "참조 없는 동일 세 파편이 생성부터 편향·이탈까지 한 클립 안에서 개수와 형태를 유지하는지 검수"

    clips["EP00-S03-NC03"]["references"] = list(dict.fromkeys([
        *clips["EP00-S03-NC03"]["references"],
        "moving_current",
    ]))
    clips["EP00-S03-NC03"]["continuity_out"] = (
        "방패가 물방울로 붕괴하고 루아가 오른쪽 기둥 옆에 쓰러지며 "
        "심해왕 오른손이 덮고 그 손목 아래로 청록 이동광이 진입"
    )

    order = [row["clip_id"] for row in spec["clips"] if row["clip_id"] != "EP00-S02-NC02"]
    updated = []
    for sequence, clip_id in enumerate(order, start=1):
        row = clips[clip_id]
        row["sequence"] = sequence
        updated.append(row)
    spec["clips"] = updated
    spec["event_contracts_file"] = CONTRACT_PATH.name
    spec["description"] = (
        "EP00 영상 제작용 원본 20개 Shot을 19개 R2V Clip으로 작성한다. "
        "참조 없는 동일 기둥 파편의 생성과 편향은 15초 한 Clip으로 병합하며, "
        "각 후보는 2~4개의 독립 Shot 계획과 참조 Subject 기반 종료 브리지를 사용한다. "
        "자동 큐 등록은 하지 않는다."
    )
    return spec


def main() -> int:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    updated_spec = update_spec(spec)
    contracts = build_contracts()
    SPEC_PATH.write_text(
        json.dumps(updated_spec, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    CONTRACT_PATH.write_text(
        json.dumps(contracts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "spec": str(SPEC_PATH),
        "contracts": str(CONTRACT_PATH),
        "clip_count": len(updated_spec["clips"]),
        "contract_count": len(contracts["clips"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
