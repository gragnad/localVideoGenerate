#!/usr/bin/env python3
from __future__ import annotations

"""Generate the approved EP00 H3 R2V V2 source contracts and build spec.

This file contains only the rebuilt EP00 scenario approved on 2026-08-16.
It deliberately does not read or adapt the rejected EP00 V1 prompt project.
"""

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = ROOT / "projects" / "RaisingaDragonSeason01"
CONTRACTS_PATH = PROJECT_DIR / "EP00_H3_R2V_REBUILD_V2_EVENT_CONTRACTS.json"
SPEC_PATH = PROJECT_DIR / "EP00_H3_R2V_REBUILD_V2_SPEC.json"
PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_REBUILD_V2"


ASSET_CATALOG: dict[str, dict[str, str]] = {
    "lua_awakened": {
        "role": "lua_awakened_original_identity",
        "label": "완전 각성 루아 원본",
        "description": "완전 각성 루아의 최우선 원본 캐릭터 이미지",
        "copy_from": "Lua_Awakened.png",
        "subject_name": "Lua",
        "subject_description": (
            "One young girl with warm brown tied hair, freckles, a weathered beige "
            "sleeveless outfit, rope and shell ornaments, sandals, and asymmetrical "
            "turquoise dragon scales. Keep one person, her child proportions, face, "
            "clothes, scale placement, and fully awakened appearance unchanged"
        ),
        "retention_marker": "fully_preserved",
        "retention_description": (
            "Preserve the same single young Lua, face, age, tied hair, weathered beige "
            "outfit, sandals, ornaments, and asymmetrical turquoise scales"
        ),
    },
    "abyss_king": {
        "role": "abyss_king_original_identity",
        "label": "심해왕 원본",
        "description": "심해왕의 최우선 원본 캐릭터 이미지",
        "copy_from": "ABYSS KING — ANTAGONIST ENTITY.png",
        "subject_name": "AbyssKing",
        "subject_description": (
            "One black-liquid humanoid king with one crown-like liquid head silhouette, "
            "one pair of bright eyes, one connected chest and torso, exactly two long "
            "arms, exactly two hands, and one continuous skirt-like waterfall lower mass. "
            "Its total height is about three times Lua's height. All motion comes from "
            "the connected torso, the same two arms and two hands, and the continuous "
            "lower liquid mass"
        ),
        "retention_marker": "fully_preserved",
        "retention_description": (
            "Preserve one connected three-times-Lua humanoid body, one head, two eyes, "
            "exactly two arms and two hands, and the continuous black-liquid lower mass"
        ),
    },
    "dragon_spear": {
        "role": "physical_spear_original",
        "label": "루아의 물리 창 원본",
        "description": "나무 자루와 검은 돌날로 된 단 하나의 물리 창",
        "copy_from": "spear.png",
        "subject_name": "DragonSpear",
        "subject_description": (
            "One rigid long wooden spear with one black chipped stone head, rope bindings, "
            "and small shell ornaments. It remains a physical hand-held weapon with fixed "
            "length and moves only through Lua's physical grip and whole-body motion"
        ),
        "retention_marker": "fully_preserved",
        "retention_description": (
            "Preserve one fixed-length wooden shaft, one black chipped stone head, rope "
            "bindings, shell ornaments, and continuous physical placement"
        ),
    },
    "heartstone_chamber": {
        "role": "heartstone_chamber_original_environment",
        "label": "해심석 방 원본 공간",
        "description": "원형 수중 궁전과 중앙 제단의 공간 원본",
        "copy_from": "Heartstone_Chamber.png",
        "subject_name": "HeartstoneChamber",
        "subject_description": (
            "The same circular underwater palace chamber with wet dark stone, broken "
            "arches, spaced columns, a central raised dais, and turquoise floor channels. "
            "Preserve one coherent three-dimensional room and its left-to-right battle axis"
        ),
        "retention_marker": "fully_preserved",
        "retention_description": (
            "Preserve the same single chamber, central dais, wet-stone materials, broken "
            "arches, column spacing, turquoise channels, and coherent camera geography"
        ),
    },
    "heartstone": {
        "role": "inactive_heartstone_original_prop",
        "label": "비활성 해심석 원본",
        "description": "중앙 제단 후경에 고정되는 비반응 해심석 원본",
        "copy_from": "Heartstone.png",
        "subject_name": "Heartstone",
        "subject_description": (
            "One heart-shaped cyan crystal on its dark ornate pedestal, fixed in the "
            "central-dais background. It stays inactive: no pulse, flare, vibration, "
            "structural movement, attack, rescue, or response to either fighter"
        ),
        "retention_marker": "fully_preserved",
        "retention_description": (
            "Preserve one fixed heart-shaped crystal and pedestal in the background while "
            "keeping it visibly inactive and uninvolved"
        ),
    },
    "wrist_mark": {
        "role": "dragon_heart_wrist_mark_original",
        "label": "용심 손목 문양 원본",
        "description": "루아 손목의 청백색 심장·물결 문양 원본",
        "copy_from": "Dragon_Heart_Wrist_Mark.png",
        "subject_name": "DragonHeartMark",
        "subject_description": (
            "One blue-white heart-and-current mark attached to the same wrist of Lua. It "
            "may give a brief pulse for danger sensing, shield activation, or Dragon Word, "
            "but never detaches, duplicates, becomes text, or creates an unapproved attack"
        ),
        "retention_marker": "attribute_transfer",
        "retention_description": (
            "Transfer the same single wrist placement, blue-white heart center, curved "
            "current lines, and only the specifically timed pulse state"
        ),
    },
    "current_shield": {
        "role": "single_curved_current_shield_original",
        "label": "불규칙 곡면 물방패 원본",
        "description": "루아와 공격 사이에 세우는 한 장의 불규칙 곡면 물막",
        "copy_from": "Current_Shield_Effect_v2.png",
        "subject_name": "CurrentShield",
        "subject_description": (
            "One irregular curved sheet of transparent turquoise water with a wave-like "
            "rim and droplets. It is one directional barrier between Lua and the attack, "
            "not an oval disc, sphere, solid wall, or multiple shields"
        ),
        "retention_marker": "attribute_transfer",
        "retention_description": (
            "Transfer one irregular curved water sheet, transparent turquoise material, "
            "wave-like edge, pressure deformation, droplets, and authored breakup state"
        ),
    },
    "dragon_language": {
        "role": "dragon_word_water_pattern_original",
        "label": "용언 수면 문양 원본",
        "description": "용언 순간 한 번 펼쳐지는 청백색 수면 문양",
        "copy_from": "Dragon_Language_Effect_v2.png",
        "subject_name": "DragonWordPattern",
        "subject_description": (
            "One blue-white water-surface pattern that expands once around Lua and slows "
            "the Abyss King's arms and torso for one breath. It remains a liquid surface "
            "pattern with no readable language and then thins away"
        ),
        "retention_marker": "attribute_transfer",
        "retention_description": (
            "Transfer one blue-white water-surface pattern, one outward expansion, one-breath "
            "restraint, and the specifically authored thinning and disappearance"
        ),
    },
}


def _shot(start_seconds: float | None, camera: str, beat_ids: list[str]) -> dict[str, Any]:
    row: dict[str, Any] = {"camera": camera, "beat_ids": beat_ids}
    if start_seconds is not None:
        row["start_seconds"] = start_seconds
    return row


def _plans(
    duration: float,
    cameras: dict[str, list[str]],
) -> dict[str, dict[str, Any]]:
    if duration <= 7:
        groups = {
            "A": [["b1", "b2"], ["b3", "b4"]],
            "B": [["b1"], ["b2", "b3", "b4"]],
            "C": [["b1"], ["b2"], ["b3", "b4"]],
        }
    elif duration <= 8:
        groups = {
            "A": [["b1"], ["b2"], ["b3", "b4"]],
            "B": [["b1", "b2"], ["b3", "b4"]],
            "C": [["b1"], ["b2", "b3"], ["b4"]],
        }
    elif duration <= 10:
        groups = {
            "A": [["b1"], ["b2"], ["b3", "b4"]],
            "B": [["b1", "b2"], ["b3"], ["b4"]],
            "C": [["b1"], ["b2", "b3"], ["b4"]],
        }
    else:
        groups = {
            "A": [["b1"], ["b2"], ["b3"], ["b4"]],
            "B": [["b1", "b2"], ["b3"], ["b4"]],
            "C": [["b1"], ["b2"], ["b3"], ["b4"]],
        }
    emphases = {
        "A": "wide spatial cause-and-result continuity",
        "B": "whole-body mechanics and readable contact",
        "C": "character perception, pressure, and closing-state evidence",
    }
    result: dict[str, dict[str, Any]] = {}
    for variant_id in ("A", "B", "C"):
        variant_groups = groups[variant_id]
        variant_cameras = cameras[variant_id]
        if len(variant_groups) != len(variant_cameras):
            raise ValueError(f"{variant_id} camera count mismatch")
        shots = []
        for index, (camera, beat_ids) in enumerate(
            zip(variant_cameras, variant_groups, strict=True)
        ):
            start = None if index == 0 else round(duration * index / len(variant_groups), 3)
            shots.append(_shot(start, camera, beat_ids))
        result[variant_id] = {
            "emphasis": emphases[variant_id],
            "shots": shots,
        }
    return result


def _contract(
    *,
    clip_id: str,
    source_shot_id: str,
    shared_event: str,
    bridge_in_id: str,
    bridge_out_id: str,
    boundary_policy: str,
    incoming_bridge: str,
    outgoing_bridge: str,
    incoming_subjects: list[int],
    outgoing_subjects: list[int],
    beats: list[str],
    duration: float,
    cameras: dict[str, list[str]],
) -> dict[str, Any]:
    if len(beats) != 4:
        raise ValueError(f"{clip_id} must have four ordered beats")
    return {
        "shared_event": shared_event,
        "bridge_in_id": bridge_in_id,
        "bridge_out_id": bridge_out_id,
        "boundary_policy": boundary_policy,
        "source_shot_ids": [source_shot_id],
        "incoming_reference_subjects": incoming_subjects,
        "outgoing_reference_subjects": outgoing_subjects,
        "incoming_bridge": incoming_bridge,
        "outgoing_bridge": outgoing_bridge,
        "beats": [
            {"beat_id": f"b{index}", "description": description}
            for index, description in enumerate(beats, start=1)
        ],
        "candidate_plans": _plans(duration, cameras),
    }


def _cameras(
    a: list[str], b: list[str], c: list[str]
) -> dict[str, list[str]]:
    return {"A": a, "B": b, "C": c}


CLIP_ROWS: list[dict[str, Any]] = [
    {
        "scene_id": "EP00-S01",
        "clip_id": "EP00-S01-NC01",
        "source_shot_id": "EP00-S01-SH01",
        "duration": 9.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone"],
        "summary": "[reference generation] Lua and the Abyss King face each other on one floor line; the first full-body reveal proves the one-to-three height relationship and displays both full Korean character introductions before the right shoulder begins to move.",
        "style": "Low cold-cyan underwater light reveals wet stone and readable full-body silhouettes without extreme lens distortion.",
        "sound": "Low underwater pressure, distant stone friction, a faint wooden grip creak, shell ornaments, and one heavy liquid shoulder shift.",
        "music": "A restrained sub-bass drone opens, then adds one low pulse when the right shoulder moves.",
        "shared_event": "The first full-body standoff introduces both fighters, proves the Abyss King is about three times Lua's height, displays the full Korean labels, and begins the first right-arm attack.",
        "bridge_in_id": "opening_standoff",
        "bridge_out_id": "king_right_shoulder_starts",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 3, 4],
        "incoming_bridge": "Begin with <Subject 1> Lua on screen-left holding <Subject 3> DragonSpear in both hands and <Subject 2> AbyssKing on screen-right, both grounded on the same floor line inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End with <Subject 1> Lua and <Subject 3> DragonSpear still readable on the left while <Subject 2> AbyssKing's right shoulder first advances on the right inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "Suspended dust parts across <Subject 4> HeartstoneChamber, revealing <Subject 5> Heartstone fixed on the rear central dais with no pulse, movement, or response.",
            "On the same floor line, <Subject 2> AbyssKing is about three times the total height of <Subject 1> Lua, never mountain-sized, with its two hands and continuous lower liquid mass fully readable; <Subject 1> Lua looks up while keeping <Subject 3> DragonSpear off the floor.",
            "Place the visible overlay \"루아 — 완전 각성한 용기사\" beside <Subject 1> Lua and \"심해왕 — 루아가 마주한 마지막 적\" beside <Subject 2> AbyssKing without covering faces, hands, the spear, or the height comparison.",
            "<Subject 2> AbyssKing lowers only its bright eyes toward <Subject 1> Lua, then its right shoulder begins one forward movement while <Subject 5> Heartstone remains inactive in the background.",
        ],
        "cameras": _cameras(
            ["A fixed low wide view establishes the dais and floor line.", "The same undistorted wide frame holds the complete scale comparison.", "A restrained sideward creep preserves both full bodies and isolates the first shoulder motion."],
            ["A floor-height three-quarter wide view uses the columns and shared ground contact to prove real scale.", "A balanced two-shot keeps both labels adjacent to their correct character.", "A medium-wide hold favors complete body mechanics at the right shoulder without losing the smaller fighter."],
            ["A central-dais wide composition begins with the inactive background crystal as a depth marker.", "A long-lens lateral two-shot compresses neither body and preserves the exact one-to-three comparison.", "A final shoulder-level angle keeps the reacting smaller fighter and initiating shoulder within one action axis."],
        ),
    },
    {
        "scene_id": "EP00-S01",
        "clip_id": "EP00-S01-NC02",
        "source_shot_id": "EP00-S01-SH02",
        "duration": 8.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone", "wrist_mark"],
        "summary": "[reference generation] The shortened Korean labels remain for one more clip while the Abyss King extends its right arm and Lua reads shoulder, elbow, and hand before lowering into an early dodge.",
        "style": "A clear side medium-wide view preserves the left-to-right battle axis, wet-stone contact, and restrained cyan reflections.",
        "sound": "Heavy water moving through one arm, a short inhale, cloth and shell movement, one soft wrist pulse, and low palace pressure.",
        "music": "The sub-bass drone gains a tight two-note low-string warning and stays unresolved.",
        "shared_event": "The second introduction shot shortens both labels, shows the right-arm wind-up from shoulder to hand, and makes Lua's wrist pulse and early lowering the cause of her coming dodge.",
        "bridge_in_id": "king_right_shoulder_starts",
        "bridge_out_id": "right_hand_advances_lua_low",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 3, 4],
        "incoming_bridge": "Re-establish <Subject 1> Lua on the left with <Subject 3> DragonSpear and <Subject 2> AbyssKing on the right as its moving right shoulder carries forward inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End as <Subject 2> AbyssKing's open right hand advances toward <Subject 1> Lua, who is already low with <Subject 3> DragonSpear close to her body inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "<Subject 5> Heartstone stays fixed and inactive on the rear dais while the same approximately one-to-three body scale remains readable.",
            "Place \"루아 · 용기사\" beside <Subject 1> Lua and \"심해왕 · 마지막 적\" beside <Subject 2> AbyssKing; these are the final character-description overlays and they do not cover faces, hands, or <Subject 3> DragonSpear.",
            "<Subject 2> AbyssKing leans slightly and extends only its right arm; <Subject 1> Lua's gaze traces the same shoulder, elbow, then open hand, and <Subject 6> DragonHeartMark gives one short blue-white pulse.",
            "Before contact, <Subject 1> Lua draws <Subject 3> DragonSpear close, sets her left foot half a step back, and lowers her center of gravity while the open hand continues toward her.",
        ],
        "cameras": _cameras(
            ["A side medium-wide re-establishes both bodies and the rear dais.", "A clean two-shot holds the shortened overlays beside their matching silhouettes.", "A subtle track links shoulder, elbow, hand, eye line, wrist pulse, and lowered stance."],
            ["An over-the-forearm angle keeps the moving arm's anatomical chain and the smaller fighter in one plane.", "A low profile hold follows the complete anticipatory response and leaves the open hand approaching."],
            ["A rear three-quarter view from the smaller fighter's side preserves the scale and axis.", "A measured push-in prioritizes the eye trace and single wrist pulse while the final overlays remain readable.", "A contact-line medium-wide settles on the lowered dodge-ready state."],
        ),
    },
    {
        "scene_id": "EP00-S02",
        "clip_id": "EP00-S02-NC01",
        "source_shot_id": "EP00-S02-SH03",
        "duration": 10.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone", "wrist_mark"],
        "summary": "[reference generation] Lua's sensed warning becomes a physical low dodge under the approaching right hand; the hand misses, drives a pressure wave along the floor, and Lua lands outside the arm with her spear turned back toward it.",
        "style": "Fast underwater action remains physically legible through shared floor contact, directional silt, and a stable left-to-right axis.",
        "sound": "One low hand sweep, water pressure scraping the floor, a boot push, cloth rush, one short exhale, and drifting grit.",
        "music": "A tight low-string rhythm starts under the foot push and lands on a muted drum when the hand misses.",
        "shared_event": "Lua converts the warning into one complete low dodge beneath the right hand, the missed hand produces a visible floor-level pressure wave, and she lands outside the arm ready to counter.",
        "bridge_in_id": "right_hand_advances_lua_low",
        "bridge_out_id": "lua_low_outside_right_arm",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 3, 4],
        "incoming_bridge": "Begin with <Subject 2> AbyssKing's open right hand already advancing toward low <Subject 1> Lua, who holds <Subject 3> DragonSpear close inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End with <Subject 1> Lua grounded low outside <Subject 2> AbyssKing's right arm, turning <Subject 3> DragonSpear toward that arm inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "<Subject 6> DragonHeartMark leaves only a brief fading warning trace as <Subject 1> Lua fixes her eyes on the gap beneath the incoming right hand; <Subject 5> Heartstone stays inactive in the distant background.",
            "Before the hand reaches her former position, <Subject 1> Lua drives off her right foot, folds her torso low, and slides beneath the outside edge while keeping <Subject 3> DragonSpear parallel to her body and clear of every finger.",
            "<Subject 2> AbyssKing's right hand misses cleanly and sweeps water just above the floor, pushing one broad pressure wave, silt, and tiny stone chips in the same direction; its other hand and connected lower mass retain their positions.",
            "<Subject 1> Lua plants both feet outside the right arm, completes the turn, and brings the physical spear tip toward that arm while <Subject 2> AbyssKing's connected lower body remains grounded.",
        ],
        "cameras": _cameras(
            ["A side wide frames the complete hand path, gap, and destination.", "A short lateral track follows the foot push and whole-body duck without crossing the axis.", "A wider result hold shows the missed hand's pressure direction and the new relative positions."],
            ["A low three-quarter angle aligns the open palm, floor gap, and braced rear foot.", "A body-height tracking view follows the uninterrupted compression and slide.", "A contact-level reverse reveals the miss, pressure wave, and counter-ready landing."],
            ["A tighter reaction view keeps the eye line and fading wrist trace ahead of the attack.", "A floor-skimming camera moves with the low body and parallel spear as the hand passes overhead.", "A still medium-wide lets silt clear around the outside-arm landing and spear turn."],
        ),
    },
    {
        "scene_id": "EP00-S02",
        "clip_id": "EP00-S02-NC02",
        "source_shot_id": "EP00-S02-SH04",
        "duration": 11.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone"],
        "summary": "[reference generation] From the low outside-arm landing, Lua executes one whole-body spear sweep at the wrist and one short thrust toward the inner elbow, but the Abyss King redirects the first path and lowers its left hand to block the second.",
        "style": "Narrow water trails and wet black surface ripples make physical spear contact readable without magical weapon light.",
        "sound": "Boot grip, wooden shaft rotation, two dull wet contacts, small droplets, and the return of one massive hand through water.",
        "music": "Quick low strings articulate the sweep and thrust, ending on a heavy unresolved bass note at the block.",
        "shared_event": "Lua performs the approved two-part physical spear combination, the Abyss King redirects it with normal arm mechanics, and the left hand blocks the second route as the right hand returns.",
        "bridge_in_id": "lua_low_outside_right_arm",
        "bridge_out_id": "left_hand_blocks_spear_right_hand_returns",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 3, 4],
        "incoming_bridge": "Re-establish <Subject 1> Lua low outside <Subject 2> AbyssKing's right arm with <Subject 3> DragonSpear already turned toward it inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End with <Subject 2> AbyssKing's left hand blocking <Subject 3> DragonSpear while its right hand returns toward <Subject 1> Lua inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "<Subject 5> Heartstone remains fixed and inactive behind the action as <Subject 1> Lua plants her left foot, loads her hips, and draws <Subject 3> DragonSpear across her body.",
            "<Subject 1> Lua rotates foot, hips, torso, and shoulders together to sweep the black stone spearhead past the side of <Subject 2> AbyssKing's right wrist, making only one narrow water trail and a broad ripple on the black surface.",
            "Without resetting, <Subject 1> Lua retracts the same rigid spear and drives one short physical thrust toward the inside of the right elbow; <Subject 2> AbyssKing bends that elbow to bleed off the first path.",
            "<Subject 2> AbyssKing lowers its left hand into the thrust route and stops it through direct physical contact while its black surface remains connected and the right hand begins to return toward <Subject 1> Lua.",
        ],
        "cameras": _cameras(
            ["A diagonal medium-wide establishes the foot, both arms, and two attack lanes.", "A controlled side track follows the complete rotational sweep.", "A short forward track follows the retraction into the inner-elbow thrust.", "A stable two-hand result view proves the left-hand block and returning right hand."],
            ["A foot-to-shoulder three-quarter view holds the load and first full-body release in one continuous move.", "A spear-height profile isolates the retraction and second contact route.", "A wider recoil frame shows both hands closing the available space."],
            ["A low reaction angle begins from the ready spear point and the target wrist.", "A wrist-height insert emphasizes the physical ripple rather than damage.", "An over-the-shoulder angle follows the quick inner-elbow correction.", "A final medium-wide holds the blocked spear, both hands, and the trapped attack line."],
        ),
    },
    {
        "scene_id": "EP00-S02",
        "clip_id": "EP00-S02-NC03",
        "source_shot_id": "EP00-S02-SH05",
        "duration": 11.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone", "wrist_mark", "current_shield"],
        "summary": "[reference generation] Lua forms one irregular curved current shield, angles it to deflect the returning right hand, steps through the opening, and drives her physical spear toward the Abyss King's chest as its left hand descends.",
        "style": "Transparent turquoise water deformation, droplets, and black-liquid reflections create spectacle while preserving the contact geometry.",
        "sound": "One wrist pulse, water gathering into one sheet, a deep hand impact, strained water, droplets, a forceful step, and a spear shaft thrust.",
        "music": "Low strings surge with the shield formation and open into a brief brass lift as the attack lane appears.",
        "shared_event": "One wrist pulse forms one curved shield, the returning right hand hits and is deflected by Lua's body-driven angle change, and she advances through the resulting gap with one chest-line spear thrust.",
        "bridge_in_id": "left_hand_blocks_spear_right_hand_returns",
        "bridge_out_id": "spear_near_chest_left_hand_descends",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 3, 4],
        "incoming_bridge": "Begin with <Subject 2> AbyssKing's left hand stopping <Subject 3> DragonSpear as its right hand returns toward <Subject 1> Lua inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End with <Subject 1> Lua's <Subject 3> DragonSpear advanced near <Subject 2> AbyssKing's chest while its left hand descends toward the shaft inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "<Subject 1> Lua opens her free hand and <Subject 6> DragonHeartMark gives one clear pulse; between her and the returning right hand, <Subject 7> CurrentShield gathers as exactly one irregular curved sheet while <Subject 5> Heartstone remains inactive.",
            "<Subject 2> AbyssKing's right palm hits the single water sheet; <Subject 1> Lua turns her hips, shoulders, extended arm, and shield angle together, causing the sheet to bend deeply and redirect the same hand sideways with turquoise droplets and a visible open lane.",
            "Using the opened lane, <Subject 1> Lua keeps control of <Subject 3> DragonSpear, steps forward once, squares her torso, and sends the rigid black stone tip straight toward the chest centerline.",
            "The spear reaches the space just before <Subject 2> AbyssKing's chest without piercing it, and the king's left hand begins one direct descent toward the shaft; <Subject 7> CurrentShield remains deformed at the side as one sheet.",
        ],
        "cameras": _cameras(
            ["A frontal medium-wide establishes both hands, the blocked spear, and the single open shield space.", "A shield-side profile reveals the body-driven angle change and exact deflection direction.", "A centered track moves through the newly opened lane with the forward step.", "A chest-line result frame holds the spear gap and descending left hand."],
            ["A three-quarter body view follows the wrist pulse, one-sheet formation, impact, and full-body shield turn without hiding the feet.", "A lateral track stays with the step and straight physical thrust.", "An offset medium frame proves the chest remains undamaged and the left hand is closing."],
            ["A tight reaction-and-hand view isolates the deliberate pulse and single curved water surface.", "A contact-height insert follows compression, rim turbulence, and sideways hand travel.", "An over-the-spear angle makes the opened lane and one forward step readable.", "A final side two-shot leaves the tip, chest gap, left hand, and deformed shield in one plane."],
        ),
    },
    {
        "scene_id": "EP00-S03",
        "clip_id": "EP00-S03-NC01",
        "source_shot_id": "EP00-S03-SH06",
        "duration": 10.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone", "current_shield"],
        "summary": "[reference generation] The Abyss King presses the side of Lua's spear shaft downward, sends its other arm across her escape line, and confines her between both hands while she keeps the weapon and tries to rotate out.",
        "style": "Close physical pressure is staged through clear palm-to-shaft contact, two-arm spacing, and uninterrupted floor orientation.",
        "sound": "Wood straining under a wet palm, heavy water shifting through two arms, a boot pivot, strained breathing, and residual shield droplets.",
        "music": "The rhythmic strings drop lower and slower as the available space closes.",
        "shared_event": "The left palm redirects the spear rather than grabbing its blade, the right arm closes the escape lane, and Lua retains the weapon but ends confined between both hands with only a weak shield remnant.",
        "bridge_in_id": "spear_near_chest_left_hand_descends",
        "bridge_out_id": "lua_between_hands_weak_shield",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 3, 4],
        "incoming_bridge": "Begin with <Subject 1> Lua's <Subject 3> DragonSpear near <Subject 2> AbyssKing's chest and its left hand already descending inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End with <Subject 1> Lua holding <Subject 3> DragonSpear across her body between <Subject 2> AbyssKing's two hands inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "<Subject 2> AbyssKing places its left palm against the side of <Subject 3> DragonSpear's wooden shaft, not the stone blade, and pushes the thrust route downward; <Subject 5> Heartstone remains inactive behind the contact.",
            "<Subject 1> Lua pulls back with both hands and keeps both feet engaged, but the king's simple palm pressure controls the shaft while the same two arms and continuous lower body remain clearly readable.",
            "<Subject 2> AbyssKing brings only its right arm across the side escape lane while <Subject 1> Lua pivots hips and shoulders, drawing the rigid spear in front of her to attempt one rotation between the arms.",
            "The escape gap closes before she clears it; <Subject 1> Lua remains between the two hands with <Subject 3> DragonSpear held close, and <Subject 6> CurrentShield survives only as one weak, thinning curved remnant at her side.",
        ],
        "cameras": _cameras(
            ["A medium close view establishes chest, descending palm, shaft, and floor direction.", "A side contact view isolates the exact palm-to-wood pressure and downward change.", "A widening overhead-oblique view reveals the other arm crossing the escape lane and settles on the confined result."],
            ["A shaft-height three-quarter track follows the complete press and two-handed resistance.", "A body-height arc follows the pivot but stops before crossing the established axis.", "A frontal result holds both hands, the spear guard, and the one weak shield remnant."],
            ["A tighter hand-and-face view prioritizes the immediate loss of the thrust route.", "A low foot-and-hip angle reveals the attempted rotational escape.", "A shoulder-side result view reveals the second arm occupying the destination and emphasizes the narrow space without changing body scale."],
        ),
    },
    {
        "scene_id": "EP00-S03",
        "clip_id": "EP00-S03-NC02",
        "source_shot_id": "EP00-S03-SH07",
        "duration": 12.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone", "wrist_mark", "current_shield"],
        "summary": "[reference generation] Lua restores the same single curved shield and braces behind it, but continuous right-palm pressure bends the water sheet, slides her feet backward, and tears the shield from its rim into droplets.",
        "style": "Transparent water compression, edge turbulence, foot drag, and massive wet-black hand pressure provide the entire spectacle.",
        "sound": "A strained wrist pulse, rising compressed-water whine, deep palm pressure, boots grinding wet stone, spear wood creak, and a broad liquid tear.",
        "music": "Driving low strings and restrained percussion climb continuously, then cut sharply at the shield tear.",
        "shared_event": "Lua re-forms the one approved shield and braces, the Abyss King's shoulder-driven right palm continuously overwhelms it, her feet slide, and the barrier tears from its rim and disappears.",
        "bridge_in_id": "lua_between_hands_weak_shield",
        "bridge_out_id": "shield_gone_spear_crossguard_hand_advances",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 3, 4],
        "incoming_bridge": "Begin with <Subject 1> Lua confined between <Subject 2> AbyssKing's hands, holding <Subject 3> DragonSpear close inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End with <Subject 1> Lua raising <Subject 3> DragonSpear across her body as <Subject 2> AbyssKing's right hand keeps advancing inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "<Subject 1> Lua spreads both feet, extends her marked arm, and <Subject 6> DragonHeartMark strains brighter as <Subject 7> CurrentShield becomes the same one irregular curved sheet between her and the right palm; <Subject 5> Heartstone stays inactive.",
            "<Subject 2> AbyssKing transfers weight from its connected torso through its right shoulder and arm into one open-palm press; the center of <Subject 7> CurrentShield bows deeply toward <Subject 1> Lua while remaining one water sheet.",
            "The pressure continues without a new strike: the shield rim trembles in waves, turquoise droplets shear off, and <Subject 1> Lua's planted feet slide backward across wet stone while she keeps <Subject 3> DragonSpear in her other hand.",
            "At the final increase, <Subject 7> CurrentShield tears first at the irregular edge and breaks entirely into droplets and thin water fragments, leaving no replacement shield as the same right hand advances and <Subject 1> Lua lifts the spear into a cross-body guard.",
        ],
        "cameras": _cameras(
            ["A low medium-wide establishes the complete brace, one shield, pressing hand, and rear face.", "A shield-edge profile makes center bow and shoulder-to-palm force transmission readable.", "A floor-inclusive side view measures the continuous foot slide and falling droplets.", "A clean result frame holds the empty shield space and cross-body spear guard."],
            ["A three-quarter full-body view follows the marked-arm extension, sheet formation, and one sustained press.", "A lateral camera holds shield curvature and both sliding feet through the escalating load.", "A frontal result view lets the rim tear travel across the single sheet before revealing the advancing palm."],
            ["A close reaction view opens on the strained marked wrist and determined face.", "A contact-height insert reveals transparent compression lines and the palm's unbroken pressure.", "A low boot-level angle turns the backward slide into a clear measure of force.", "A slightly wider final view captures the edge-first tear, droplets, and emergency spear guard."],
        ),
    },
    {
        "scene_id": "EP00-S03",
        "clip_id": "EP00-S03-NC03",
        "source_shot_id": "EP00-S03-SH08",
        "duration": 10.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone"],
        "summary": "[reference generation] With the shield gone, the right hand drives into Lua's cross-body spear and scaled arms, sliding her to the central dais while the Abyss King's continuous lower mass glides once to close the distance.",
        "style": "A side force axis, floor friction, drifting debris, and one connected liquid glide make the strength gap visible.",
        "sound": "One deep hand-to-wood impact, wet stone scraping under two feet, harsh breathing, small chips moving, and a heavy continuous liquid glide.",
        "music": "A broad low percussion hit gives way to descending strings as the distance collapses.",
        "shared_event": "The right hand contacts Lua's horizontal spear and scaled arms, the collision slides her to the dais without breaking the weapon, and the whole connected lower liquid body glides forward once to restore pressure.",
        "bridge_in_id": "shield_gone_spear_crossguard_hand_advances",
        "bridge_out_id": "lua_low_on_spear_king_prepares",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 3, 4],
        "incoming_bridge": "Begin with no shield between <Subject 2> AbyssKing's advancing right hand and <Subject 1> Lua's cross-body <Subject 3> DragonSpear inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End with <Subject 1> Lua low beside the central dais and leaning on <Subject 3> DragonSpear while <Subject 2> AbyssKing prepares again inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "<Subject 2> AbyssKing's right palm makes one direct impact across <Subject 3> DragonSpear and <Subject 1> Lua's turquoise-scaled forearms; <Subject 5> Heartstone remains fixed and inactive behind the dais.",
            "<Subject 1> Lua turns shoulders and hips to bleed off the frontal load, but both feet lose traction and slide along the floor toward the central dais; the rigid spear bends neither, breaks neither, and stays in both hands.",
            "Silt, small stone chips, and one floor-level pressure trail move in the exact direction of her slide while the contact remains a direct hand-to-guard impact.",
            "After <Subject 1> Lua reaches the dais and lowers one knee, <Subject 2> AbyssKing retracts its right hand and glides its one continuous skirt-like lower liquid mass forward once, keeping its upper body, two arms, and lower mass connected.",
        ],
        "cameras": _cameras(
            ["A side wide establishes the contact line and full distance to the dais.", "A matched side track follows the whole-body turn and continuous floor slide.", "A low floor-to-wide result view records friction and debris before revealing the lowered fighter and one connected forward glide."],
            ["A three-quarter medium-wide follows the palm contact and complete defensive body turn.", "A parallel dolly holds both sliding feet, unbroken spear, and dais destination.", "A static result view captures the lowered knee and one connected forward glide."],
            ["A tight contact-height opening emphasizes wood, scaled arms, and the single palm.", "A low rear track follows the backward slide toward the dais.", "A settled medium-wide shows debris arriving, the fighter lowering, and the connected enemy glide."],
        ),
    },
    {
        "scene_id": "EP00-S04",
        "clip_id": "EP00-S04-NC01",
        "source_shot_id": "EP00-S04-SH09",
        "duration": 10.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone", "wrist_mark"],
        "summary": "[reference generation] Lua uses the spear to stand, reads two unstable wrist pulses and the Abyss King's shoulder-to-hand path, then draws the weapon back and chooses one final attack as the next hand motion begins.",
        "style": "A controlled push toward the exhausted face keeps the enemy's attack origin and the physical spear preparation in the same frame.",
        "sound": "Ragged breathing, wood bearing weight, two uneven wrist pulses, one foot planting, and low water moving inside a massive arm.",
        "music": "The action rhythm thins to a single tense low-string line that holds under the decision.",
        "shared_event": "Lua rises with the spear, the same wrist mark pulses twice as a sensing cue, she reads the next hand path, and she draws the spear back for her final established-power attempt.",
        "bridge_in_id": "lua_low_on_spear_king_prepares",
        "bridge_out_id": "king_hand_starts_lua_reads_path",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 3, 4],
        "incoming_bridge": "Begin with <Subject 1> Lua low beside the dais and leaning on <Subject 3> DragonSpear as <Subject 2> AbyssKing prepares its next hand motion inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End as <Subject 2> AbyssKing's next hand starts and <Subject 1> Lua, holding <Subject 3> DragonSpear drawn back, already looks along its path inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "<Subject 1> Lua presses down on <Subject 3> DragonSpear, brings one foot then the other under her, and rises fully despite ragged breath; <Subject 5> Heartstone stays inactive in the rear.",
            "<Subject 6> DragonHeartMark gives exactly two uneven blue-white sensing pulses only, and <Subject 1> Lua's eyes move from <Subject 2> AbyssKing's shoulder toward the predicted hand route.",
            "Understanding the strength gap, <Subject 1> Lua sets both feet, draws the same physical spear behind her with both hands, aligns hips and shoulders, and takes one short deliberate inhale.",
            "<Subject 2> AbyssKing begins the next simple hand attack from its shoulder; before the hand travels far, <Subject 1> Lua has already fixed her gaze outside its path and holds the spear loaded for the final attempt.",
        ],
        "cameras": _cameras(
            ["A medium frame establishes the low body, supporting spear, and distant attack origin.", "A measured push-in follows the complete rise, both pulses, and the predicted path without losing the larger shoulder and hand.", "A restrained pullback leaves the loaded stance and initiating hand in one frame."],
            ["A three-quarter full-body view follows the spear-assisted rise and both feet regaining contact.", "An over-the-shoulder sightline connects the two wrist pulses to shoulder and hand observation.", "A side result view shows the complete spear draw and attack beginning."],
            ["A low exhausted-eye-level angle opens on the effort to stand.", "A close-to-profile move pairs exactly two unstable wrist pulses with the deliberate inhale and full weapon load.", "A final shared-focus frame holds the early eye movement and late hand start."],
        ),
    },
    {
        "scene_id": "EP00-S04",
        "clip_id": "EP00-S04-NC02",
        "source_shot_id": "EP00-S04-SH10",
        "duration": 11.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone", "wrist_mark", "dragon_language"],
        "summary": "[reference generation] Lua steps outside the predicted hand path, utters one brief untranslated Dragon Word, expands one blue-white water-surface pattern, restrains the Abyss King's arms and torso for one breath, and aligns the spear at its chest.",
        "style": "A single blue-white surface-water pattern, slowed droplets, and suppressed ambient motion provide the complete visual peak.",
        "sound": "One missed hand rush, a boot step, one brief low untranslated vocalization, an expanding water resonance, compressed silence, and a spear grip tightening.",
        "music": "The score falls nearly silent before one low choral pressure tone rises under the one-breath restraint.",
        "shared_event": "Lua completes one anticipatory step outside the hand, gives one short low untranslated Dragon Word, one approved water pattern expands, and the resulting one-breath restraint creates time to align the spear.",
        "bridge_in_id": "king_hand_starts_lua_reads_path",
        "bridge_out_id": "king_restrained_lua_spear_aligned",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 3, 4],
        "incoming_bridge": "Begin as <Subject 2> AbyssKing's hand starts along the path already read by <Subject 1> Lua, who holds <Subject 3> DragonSpear loaded inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End with <Subject 2> AbyssKing's arms and torso held slow for one breath while <Subject 1> Lua aligns <Subject 3> DragonSpear at its chest inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "Before contact, <Subject 1> Lua takes one complete step outside the predicted route, lets <Subject 2> AbyssKing's hand pass, turns back toward the chest, and keeps <Subject 3> DragonSpear controlled in both hands; <Subject 5> Heartstone remains inactive.",
            "<Subject 1> Lua draws <Subject 6> DragonHeartMark close to her chest and utters one brief low Dragon Word vocalization; the utterance remains untranslated and <Subject 2> AbyssKing stays silent.",
            "<Subject 7> DragonWordPattern expands once from around <Subject 1> Lua as one blue-white water-surface pattern; nearby droplets slow and <Subject 2> AbyssKing's two arms, torso, and surface ripples stop or markedly slow for only one breath.",
            "At the center of the same fading pattern, <Subject 1> Lua plants both feet and brings <Subject 3> DragonSpear into one straight two-handed alignment at <Subject 2> AbyssKing's chest centerline without striking yet.",
        ],
        "cameras": _cameras(
            ["A diagonal wide establishes the hand route, safe step, and central-dais floor.", "A medium two-shot keeps the turn, marked wrist, and one low utterance readable.", "A widening overhead-oblique view follows the single surface pattern to both restrained arms.", "A centered chest-line frame holds the one-breath opening and aligned physical spear."],
            ["A full-body three-quarter track follows the dodge step, return turn, wrist draw, and utterance as one controlled sequence.", "A side-wide frame reveals one pattern crossing the floor and slowing the complete connected upper body.", "An over-the-spear result angle confirms the aligned tip, restrained hands, and no contact yet."],
            ["A close reaction opening holds the predicted hand passing just outside the body.", "A wrist-and-mouth medium detail gives the brief untranslated sound without visible text.", "A low pattern-level view watches one blue-white water surface expand and droplets slow.", "A quiet final profile isolates the two-foot alignment and one-breath chance."],
        ),
    },
    {
        "scene_id": "EP00-S04",
        "clip_id": "EP00-S04-NC03",
        "source_shot_id": "EP00-S04-SH11",
        "duration": 13.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone", "dragon_language"],
        "summary": "[reference generation] Lua drives her final straight spear thrust, but the Dragon Word pattern thins, one hand catches the shaft, the other strikes her spear and scaled arm sideways, and she falls separated from the dropped weapon while the Abyss King remains standing.",
        "style": "The climax uses a body-driven thrust, a clear stop at the wooden shaft, one lateral pressure impact, and directional water and silt displacement while the enemy chest remains intact.",
        "sound": "A forceful exhale, boot drive, thinning water resonance, one deep shaft catch, a lateral impact, a wooden spear landing, floor slide, and heavy settling water.",
        "music": "The score reaches one restrained low brass peak at the thrust, then collapses into bass and silence after the spear lands.",
        "shared_event": "Lua performs the final whole-body thrust, the one-breath restraint expires, the Abyss King stops the spear with one hand and knocks her away with the other, and the spear drops nearby as all known blue effects go dark.",
        "bridge_in_id": "king_restrained_lua_spear_aligned",
        "bridge_out_id": "lua_down_spear_nearby_known_light_off",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 3, 4],
        "incoming_bridge": "Begin with <Subject 2> AbyssKing restrained for one breath while <Subject 1> Lua holds <Subject 3> DragonSpear aligned at its chest inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End with <Subject 1> Lua down on one hand and one knee, <Subject 3> DragonSpear lying nearby beyond immediate reach, and <Subject 2> AbyssKing still standing inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "<Subject 1> Lua drives from her rear foot through hips, torso, both shoulders, arms, and <Subject 3> DragonSpear in one straight physical thrust while <Subject 5> Heartstone remains fixed and inactive.",
            "Just before the stone point reaches <Subject 2> AbyssKing's chest, <Subject 6> DragonWordPattern thins and fades; the king's fingers resume movement and one hand clamps the side of the wooden shaft, stopping the tip without chest injury.",
            "<Subject 1> Lua continues pushing but gains no distance; <Subject 2> AbyssKing uses its other and only other hand for one lateral impact across the spear and her scaled forearms, producing one directional pressure burst of water and dust while both bodies remain intact.",
            "The single impact separates <Subject 1> Lua from <Subject 3> DragonSpear: the spear falls intact onto the nearby floor beyond immediate reach, she slides and stops on one hand and one knee, all wrist and Dragon Word light is off, and <Subject 2> AbyssKing remains upright and undamaged.",
        ],
        "cameras": _cameras(
            ["A side medium-wide establishes both feet, aligned shaft, restrained hands, and chest gap.", "A parallel track follows the complete rear-foot drive to the stopped tip.", "A contact-height view isolates the thinning pattern, shaft catch, and single lateral counter.", "A wider side result holds the separated body, fallen spear, and standing enemy."],
            ["A low three-quarter full-body track follows the entire loaded thrust and shows the restraint expiring at the tip gap.", "A shaft-level profile makes the catch, continued push, and one opposite-hand impact physically unambiguous.", "A static floor-inclusive result view records the intact spear landing, slide, and final positions."],
            ["A tight determined-face and shoulder opening leads into the rear-foot drive.", "An over-the-spear view compresses the final centimeters without allowing contact injury.", "A palm-and-shaft insert reveals the resumed fingers and one clean lateral force transfer.", "A low defeated-eye-level wide settles on the unlit fighter, nearby spear, and upright silhouette."],
        ),
    },
    {
        "scene_id": "EP00-S05",
        "clip_id": "EP00-S05-NC01",
        "source_shot_id": "EP00-S05-SH12",
        "duration": 9.0,
        "references": ["lua_awakened", "abyss_king", "dragon_spear", "heartstone_chamber", "heartstone", "wrist_mark"],
        "summary": "[reference generation] Lua tries once to rise, fails back to a low position, finds her wrist mark dark and the spear just beyond reach, while the Abyss King's connected lower mass glides slightly closer.",
        "style": "The camera stays at the defeated fighter's height as turquoise droplets settle and the much larger connected silhouette advances without a new attack.",
        "sound": "Irregular breathing, one palm slip on wet stone, a tiny spear roll, settling droplets, and one slow heavy liquid glide.",
        "music": "Almost all music drops out, leaving only a very low sustained tone under the enemy's approach.",
        "shared_event": "The defeat state is re-established, Lua makes one failed attempt to rise, confirms the familiar wrist power stays off and the spear is not immediately reachable, and the Abyss King approaches slightly without attacking.",
        "bridge_in_id": "lua_down_spear_nearby_known_light_off",
        "bridge_out_id": "lua_dark_mark_raises_head",
        "incoming_subjects": [1, 2, 3, 4],
        "outgoing_subjects": [1, 2, 4],
        "incoming_bridge": "Begin with <Subject 1> Lua down on one hand and one knee, <Subject 3> DragonSpear nearby beyond immediate reach, and <Subject 2> AbyssKing standing inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End with <Subject 1> Lua lifting her head away from the dark wrist while <Subject 2> AbyssKing remains larger in the background inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "<Subject 5> Heartstone remains fixed and inactive as settling turquoise droplets and dust reveal <Subject 1> Lua's low one-hand, one-knee posture, the intact <Subject 3> DragonSpear nearby, and <Subject 2> AbyssKing still upright.",
            "<Subject 1> Lua presses her left palm and right knee into wet stone for one attempt to stand, but the supporting arm buckles once and she drops back low without a second attempt.",
            "She looks at <Subject 6> DragonHeartMark; it remains completely dark and inactive, while <Subject 3> DragonSpear gives one tiny floor roll but stays beyond immediate reach.",
            "<Subject 2> AbyssKing glides only slightly closer on its one connected skirt-like lower liquid mass without launching an attack, and <Subject 1> Lua turns her eyes from the dark wrist and begins to raise her head.",
        ],
        "cameras": _cameras(
            ["A low wide re-establishes body, spear, dark wrist, connected lower mass, and rear dais.", "A restrained side track follows the single failed rise and return to the floor.", "A hand-level detail confirms the dark mark and unreachable spear before returning to both figures."],
            ["A defeated-eye-level three-quarter view keeps the height difference as the full attempt to rise fails.", "A close floor plane pairs the dark mark with the small spear roll.", "A widening result shot captures the slight connected glide and head beginning to lift."],
            ["A still low composition prioritizes the aftermath and settling droplets.", "A close reaction view holds the one arm buckle and inspection of the unlit mark.", "A shallow-depth medium view leaves the larger approaching silhouette behind the head lift."],
        ),
    },
    {
        "scene_id": "EP00-S05",
        "clip_id": "EP00-S05-NC02",
        "source_shot_id": "EP00-S05-SH13",
        "duration": 9.0,
        "references": ["lua_awakened", "abyss_king", "wrist_mark", "heartstone_chamber"],
        "summary": "[reference generation] With the familiar wrist mark still dark and the Abyss King blurred behind her, Lua hears one unfamiliar internal heartbeat without visible effect, stops breathing for an instant, and refocuses on the enemy in surprise.",
        "style": "A locked intimate close view uses only breathing, eye movement, shallow depth, and sound while every visible color, object, and light state remains unchanged.",
        "sound": "Ragged exhale, low underwater room pressure, one unfamiliar dense internal heartbeat distinct from the wrist sound, and a very short silence.",
        "music": "No melody; the remaining low tone disappears just before the internal heartbeat and does not resolve afterward.",
        "shared_event": "Lua's familiar mark stays dark, one new internal heartbeat sounds with no visual manifestation, her breath catches and her eyes widen slightly, then she looks back at the Abyss King with surprise before understanding.",
        "bridge_in_id": "lua_dark_mark_raises_head",
        "bridge_out_id": "lua_refocused_on_king",
        "incoming_subjects": [1, 2, 4],
        "outgoing_subjects": [1, 2, 4],
        "incoming_bridge": "Begin close on <Subject 1> Lua lifting her head from the dark wrist while <Subject 2> AbyssKing stays out of focus behind her inside <Subject 4> HeartstoneChamber.",
        "outgoing_bridge": "End with <Subject 1> Lua's eyes newly focused toward <Subject 2> AbyssKing, still a large blurred shape inside <Subject 4> HeartstoneChamber.",
        "beats": [
            "<Subject 1> Lua exhales raggedly in a fixed close composition that includes her face, upper body, and <Subject 3> DragonHeartMark; the attached mark remains dark from beginning to end.",
            "The image and environment remain visually unchanged as one low dense internal heartbeat sounds once, clearly different from the familiar wrist pulse.",
            "<Subject 1> Lua's breath stops for an instant, her eyes open only slightly wider, and her gaze drops briefly as if checking a sensation inside her own body rather than the wrist.",
            "She raises her gaze back toward <Subject 2> AbyssKing with surprise ahead of pain, while the large black form remains blurred and does not react or reveal what the signal is.",
        ],
        "cameras": _cameras(
            ["A locked close medium establishes the face, upper body, dark wrist, and blurred threat.", "A tighter static face-and-wrist crop holds the invisible heartbeat without any visual accent.", "The same lens waits on the breath stop, small eye change, and return of focus."],
            ["A shallow-depth profile close keeps the dark mark and blurred larger form aligned during the exhale and unseen pulse.", "A fixed eye-level close captures the brief downward check without suggesting a source.", "A slight rack of focus only to the eyes records the surprised refocus while the background remains indistinct."],
            ["A still three-quarter close begins on physical exhaustion and an entirely dark mark.", "A sound-led hold refuses any flash, shake, zoom, or object reveal during the single heartbeat.", "A narrow eye close observes the tiny widening, brief downward glance, and final focus toward the unchanged silhouette."],
        ),
    },
    {
        "scene_id": "EP00-S05",
        "clip_id": "EP00-S05-NC03",
        "source_shot_id": "EP00-S05-SH14",
        "duration": 7.0,
        "references": ["lua_awakened", "abyss_king", "heartstone_chamber"],
        "summary": "[reference generation] Lua steadies one breath and slightly lifts her head as her eyes stop shaking; a second unfamiliar heartbeat only begins to gather, then the image cuts directly to complete black before it completes or reveals any power.",
        "style": "A fixed face close-up ends the episode through restrained expression and an abrupt direct cut, with no zoom, spin, flash, new subject, or visible effect.",
        "sound": "One short controlled inhale, very low underwater pressure, the incomplete onset of a second dense internal heartbeat, then immediate total silence.",
        "music": "No non-diegetic melody; silence takes over at the hard cut to black.",
        "shared_event": "Lua steadies her breath and eyes, lifts her head by a fraction, and the onset of a second unfamiliar heartbeat is cut off by complete black before any manifestation, explanation, counterattack, or enemy response.",
        "bridge_in_id": "lua_refocused_on_king",
        "bridge_out_id": "terminal_black",
        "boundary_policy": "terminal",
        "incoming_subjects": [1, 2, 3],
        "outgoing_subjects": [1, 2, 3],
        "incoming_bridge": "Begin on <Subject 1> Lua's refocused eyes with <Subject 2> AbyssKing only a dark partial shape behind her inside <Subject 3> HeartstoneChamber.",
        "outgoing_bridge": "End on <Subject 1> Lua's focused face with <Subject 2> AbyssKing still only a dark partial silhouette inside <Subject 3> HeartstoneChamber, then cut directly to complete black.",
        "beats": [
            "<Subject 1> Lua takes one short inhale and lets her ragged breathing become even while the framing remains fixed and <Subject 2> AbyssKing stays a partial out-of-focus black form.",
            "Her pupils stop shaking and she lifts her head only a fraction, expressing first recognition of an unfamiliar internal sensation without confidence, victory, transformation, or a named realization.",
            "The low onset of a second dense internal heartbeat begins while every visible color, light, eye detail, object, and background state inside <Subject 3> HeartstoneChamber remains unchanged.",
            "Before that second heartbeat completes, cut directly to complete black and total silence; do not show a new power, attack, next exchange, title explanation, or reaction from <Subject 2> AbyssKing.",
        ],
        "cameras": _cameras(
            ["A fixed face close-up holds the refocused eyes and partial background silhouette.", "The same unmoving close-up records the steadied breath, tiny head lift, incomplete heartbeat onset, and direct black cut."],
            ["A locked shallow-depth profile holds the controlled inhale and the eyes becoming still.", "Without changing lens or angle, the frame waits through the fractional lift and cuts before the sound completes."],
            ["A narrow eye close establishes the unchanged face and blurred threat.", "A slightly wider but still fixed face crop allows the one controlled inhale and minimal head movement.", "A final static hold denies every visible manifestation and cuts straight to black on the incomplete onset."],
        ),
    },
]


def _build_contracts() -> dict[str, Any]:
    clips: dict[str, Any] = {}
    for row in CLIP_ROWS:
        clips[row["clip_id"]] = _contract(
            clip_id=row["clip_id"],
            source_shot_id=row["source_shot_id"],
            shared_event=row["shared_event"],
            bridge_in_id=row["bridge_in_id"],
            bridge_out_id=row["bridge_out_id"],
            boundary_policy=row.get("boundary_policy", "referenced_cut"),
            incoming_bridge=row["incoming_bridge"],
            outgoing_bridge=row["outgoing_bridge"],
            incoming_subjects=row["incoming_subjects"],
            outgoing_subjects=row["outgoing_subjects"],
            beats=row["beats"],
            duration=row["duration"],
            cameras=row["cameras"],
        )
    return {"version": "independent_shot_plans_v2", "clips": clips}


def _build_spec() -> dict[str, Any]:
    clips = []
    for sequence, row in enumerate(CLIP_ROWS, start=1):
        clips.append({
            "scene_id": row["scene_id"],
            "clip_id": row["clip_id"],
            "sequence": sequence,
            "duration_seconds": row["duration"],
            "references": row["references"],
            "prompt_base": {
                "summary": row["summary"],
                "style_opening": [row["style"]],
                "overall_soundscape": row["sound"],
                "non_diegetic_music": row["music"],
            },
            "prompt_variants": [
                {
                    "variant_id": variant_id,
                    "label": label,
                    "rationale": rationale,
                    "prompt_spec": {},
                }
                for variant_id, label, rationale in (
                    ("A", "공간 인과", f"{row['clip_id']} 사건의 준비·실행·접촉·결과를 넓은 공간 축과 종료 상태로 증명"),
                    ("B", "신체 역학", f"{row['clip_id']} 사건의 동일 beat를 전신 움직임과 물리 접촉 중심으로 구성"),
                    ("C", "인지와 압력", f"{row['clip_id']} 사건의 동일 beat를 루아의 판단, 압력 변화와 다음 상태 단서 중심으로 구성"),
                )
            ],
            "scenario_ko": f"승인된 {row['source_shot_id']} 한 Shot의 사건만 사용한다.",
            "review_intent_ko": "A/B/C가 같은 사건 beat를 같은 순서로 한 번씩 사용하고 카메라 강조점만 다른지 검수한다.",
            "authoring_notes": [
                "기존 EP00 V1 사건과 뿌리 공격을 사용하지 않는다.",
                "심해왕은 두 팔과 두 손만 사용하고 루아의 약 3배 높이를 유지한다.",
                "큐 등록과 영상 생성은 이 프로젝트 생성 범위에 포함하지 않는다.",
            ],
        })
    return {
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon Season 01 · EP00 H3 R2V Rebuild V2",
        "description": (
            "캐릭터 원본 이미지 분석 뒤 새로 승인된 140초 EP00 영상 제작 시나리오의 "
            "14개 Shot을 14개 H3 R2V Clip과 동일 사건 A/B/C 후보로 작성한다. "
            "기존 EP00 사건, 뿌리 공격, 추가 신체와 미확정 새 힘 표현은 사용하지 않으며 "
            "자동 큐 등록과 영상 생성은 하지 않는다."
        ),
        "event_contracts_file": CONTRACTS_PATH.name,
        "asset_catalog": ASSET_CATALOG,
        "clips": clips,
    }


def main() -> int:
    contracts = _build_contracts()
    spec = _build_spec()
    CONTRACTS_PATH.write_text(
        json.dumps(contracts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    SPEC_PATH.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    total = sum(float(row["duration"]) for row in CLIP_ROWS)
    print(json.dumps({
        "project_id": PROJECT_ID,
        "contracts": str(CONTRACTS_PATH),
        "spec": str(SPEC_PATH),
        "clip_count": len(CLIP_ROWS),
        "duration_seconds": total,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
