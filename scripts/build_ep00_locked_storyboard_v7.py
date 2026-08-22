from __future__ import annotations

"""Build EP00 V7 only from the locked rules and canonical rebuilt screenplay.

This module intentionally does not read or import any EP00 V1-V6 prompt spec,
event contract, generated project, audit, or builder module.  The clip records
below are the versioned machine transcription of the locked screenplay and the
visually reviewed four-panel storyboard assets.
"""

import argparse
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
LOCK_PATH = EPISODE_DIR / "EP00_LOCKED_PRODUCTION_RULES_V1.json"
CANONICAL_DATA_PATH = EPISODE_DIR / "EP00_CANONICAL_CLIPS_V1.json"
SPEC_PATH = EPISODE_DIR / "EP00_H3_R2V_STORYBOARD_ADE_V7_LOCKED_SPEC.json"
EVENTS_PATH = EPISODE_DIR / "EP00_H3_R2V_STORYBOARD_ADE_V7_LOCKED_EVENT_CONTRACTS.json"
PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_STORYBOARD_ADE_V7_LOCKED"
EVENT_VERSION = "locked_storyboard_shot_plans_v3"
POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")


CLIPS: tuple[dict[str, Any], ...] = (
    {
        "scene": "EP00-S01", "clip": "EP00-S01-NC01", "source": "EP00-S01-SH01",
        "duration": 8.5, "storyboard": "EP00-S01-NC01_STORYBOARD_16X9_V3.png",
        "has_spear": True, "spear_shots": [1, 2, 3, 4],
        "summary": "Lua and the Abyss King are revealed on one floor line at a fixed one-to-three height ratio, and his right shoulder begins the first movement.",
        "panels": [
            "<Subject 1> Lua and <Subject 2> AbyssKing stand on one floor line in a low wide reveal; he is about three times her height and her single physical spear stays raised off the floor.",
            "<Subject 1> Lua tightens both hands on the spear and raises her gaze while <Subject 2> AbyssKing remains still and dominant across the open floor.",
            "<Subject 1> Lua resolves to hold position, her asymmetrical scales catching restrained cyan reflections as <Subject 2> AbyssKing lowers only his bright eyes toward her.",
            "<Subject 1> Lua and <Subject 2> AbyssKing remain on the same axis with both of his hands visible; his right shoulder makes its first small forward movement.",
        ],
        "compositions": [
            "A low locked master keeps both full bodies and their shared floor line readable without wide-angle size distortion.",
            "A lateral medium-long view keeps Lua's spear grip, upward eyeline, and the King's complete connected lower mass in frame.",
            "A tight three-quarter Lua portrait keeps the King's bright eyes soft but legible in the deep background.",
            "An over-Lua-shoulder medium-wide restores both hands and isolates the King's right shoulder start.",
        ],
        "d": [
            "Dolly slowly right at ankle height, rise to waist height, and close from the low master into panel 2's lateral medium-long grip view.",
            "Arc slowly clockwise behind Lua at waist height while tightening from medium-long to panel 3's close three-quarter portrait.",
            "Crane slowly upward by one head height and drift behind Lua's left shoulder, widening into panel 4's two-hand shoulder-start view.",
        ],
        "e": [
            "Let the drifting floor haze cross left-to-right beneath the spear and reveal panel 2's tightened grip without changing either stance.",
            "Let Lua's spear shaft rise through the near foreground and clear to reveal panel 3's face and upward eyeline.",
            "Follow Lua's eyeline toward the King's bright eyes, then let his right shoulder enter the foreground edge and reveal panel 4.",
        ],
    },
    {
        "scene": "EP00-S01", "clip": "EP00-S01-NC02", "source": "EP00-S01-SH02",
        "duration": 7.5, "storyboard": "EP00-S01-NC02_STORYBOARD_16X9_V4.png",
        "has_spear": True, "spear_shots": [1, 2, 3, 4],
        "summary": "The Abyss King's right arm opens toward Lua while her eyes read shoulder, elbow, and hand before her body drops into a prepared evasive stance.",
        "panels": [
            "<Subject 2> AbyssKing leans his connected torso slightly forward and begins extending his right arm while <Subject 1> Lua holds the spear close.",
            "<Subject 2> AbyssKing opens the same right hand toward <Subject 1> Lua; his other hand remains separate and his lower mass stays planted.",
            "<Subject 1> Lua's gaze moves from the King's shoulder through elbow to hand, and her wrist mark gives one short pulse while the spear stays physical and dark.",
            "<Subject 1> Lua lowers her center of gravity with one foot back and the spear tight to her body as <Subject 2> AbyssKing's open right hand starts advancing.",
        ],
        "compositions": [
            "An over-Lua-shoulder medium-wide holds the King's shoulder, elbow, hand, and Lua's spear on one readable action line.",
            "A low frontal hand-height view makes the opening palm large but keeps the three-to-one body relationship credible behind it.",
            "A high oblique medium close-up follows Lua's eye path while retaining the King's shoulder-to-hand chain in the background.",
            "A lateral ground-level medium-wide shows Lua's lowered stance and the open hand entering the same lane.",
        ],
        "d": [
            "Truck slowly left at shoulder height, descend to palm height, and close into panel 2's frontal opening-hand view.",
            "Pedestal slowly upward from palm height to Lua's eye level while moving closer into panel 3's oblique eye-path close-up.",
            "Orbit slowly counterclockwise around Lua, descend from eye level to knee height, and widen into panel 4's lateral low stance.",
        ],
        "e": [
            "Let the King's extending forearm traverse the upper frame and uncover panel 2's open-palm frontal composition.",
            "Rack focus from the open fingertips along the elbow and shoulder to Lua's tracking eyes, revealing panel 3.",
            "Let Lua pull the spear shaft down across the foreground, carrying the lens to panel 4's lowered body line.",
        ],
    },
    {
        "scene": "EP00-S02", "clip": "EP00-S02-NC01", "source": "EP00-S02-SH03",
        "duration": 9.5, "storyboard": "EP00-S02-NC01_STORYBOARD_16X9_V3.png",
        "has_spear": True, "spear_shots": [1, 2, 3, 4],
        "summary": "Lua moves before the open right hand reaches her, slips below its lane with the spear parallel to her body, and lands outside the arm as the missed sweep pushes water across the floor.",
        "panels": [
            "<Subject 2> AbyssKing's open right hand enters the lane where <Subject 1> Lua is already low, with her spear held parallel to her body and clear of his fingers.",
            "<Subject 1> Lua drives off her right foot and passes beneath the same hand's outer edge while <Subject 2> AbyssKing continues one reach.",
            "<Subject 2> AbyssKing's hand misses Lua and pushes a broad low pressure wake over the floor as <Subject 1> Lua clears the lane.",
            "<Subject 1> Lua lands low outside the King's right arm and turns the intact spear point toward that arm while <Subject 2> AbyssKing remains three times taller.",
        ],
        "compositions": [
            "A hand-dominant low wide keeps Lua's entire escape lane and the King's connected body visible.",
            "A fast lateral knee-height tracking view profiles Lua's whole-body push under the hand.",
            "A high wide diagonal shows the missed hand path, floor wake, and Lua's cleared position together.",
            "An over-Lua-shoulder low medium view resolves her landing, spear turn, and the King's right-arm exterior.",
        ],
        "d": [
            "Track quickly right at knee height, close by one body length, and settle into panel 2's lateral push-off profile.",
            "Crane quickly upward and backward from knee height to a high wide diagonal, arriving at panel 3's complete missed-lane geometry.",
            "Dive quickly behind Lua's right shoulder while closing from wide to medium, landing at panel 4's low spear-turn view.",
        ],
        "e": [
            "Let Lua's right-foot push throw a thin floor wake past the lens and reveal panel 2's lateral escape profile.",
            "Let the King's missing hand sweep across and clear the near foreground, opening panel 3's high view of the displaced water.",
            "Follow the receding wake to Lua's landing foot, then let her turning spear point lead into panel 4.",
        ],
    },
    {
        "scene": "EP00-S02", "clip": "EP00-S02-NC02", "source": "EP00-S02-SH04",
        "duration": 10.5, "storyboard": "EP00-S02-NC02_STORYBOARD_16X9_V4.png",
        "has_spear": True, "spear_shots": [1, 2, 3, 4],
        "summary": "Lua uses one continuous physical spear combination around the King's right wrist and inner elbow until his left palm stops the wooden shaft.",
        "panels": [
            "<Subject 1> Lua plants her left foot, loads hips and shoulders, and draws the single spear across her torso while <Subject 2> AbyssKing holds his right arm extended.",
            "<Subject 1> Lua completes the rotation and the spear point passes narrowly beside the King's right wrist with only a thin water trail; <Subject 2> AbyssKing remains uncut.",
            "<Subject 1> Lua retracts the same spear and makes one short thrust through the empty inner bend of the King's right elbow as <Subject 2> AbyssKing folds that elbow.",
            "<Subject 2> AbyssKing's left open palm comes down onto the middle wooden shaft and stops it while his right hand begins returning toward <Subject 1> Lua.",
        ],
        "compositions": [
            "A low wide three-quarter view reads Lua's foot plant, hip load, full spear, and the King's three-times-taller stance.",
            "A side medium shot at spear height isolates the near miss beside the right wrist without implying a body hit.",
            "A high oblique action view locates the short spear point precisely inside the right elbow bend.",
            "A tight low reverse contact view makes the left-palm-to-wooden-shaft stop unmistakable and keeps Lua's eyeline on the contact.",
        ],
        "d": [
            "Dolly quickly along the spear from Lua's rear hand toward the point at waist height, tightening into panel 2's wrist-side medium view.",
            "Arc quickly upward over Lua's lead shoulder while widening slightly, arriving at panel 3's high inner-elbow geometry.",
            "Drop quickly from the high oblique to shaft height on the King's left side and close into panel 4's palm-to-wood contact.",
        ],
        "e": [
            "Let the rotating wooden shaft sweep laterally across the lens and clear on panel 2's near-wrist line.",
            "Follow the thin water trail backward along the retracting point, then let the renewed short thrust reveal panel 3's inner elbow.",
            "Let the King's descending left palm fill the upper frame and carry the reveal down to panel 4's exact shaft stop.",
        ],
    },
    {
        "scene": "EP00-S02", "clip": "EP00-S02-NC03", "source": "EP00-S02-SH05",
        "duration": 10.5, "storyboard": "EP00-S02-NC03_STORYBOARD_16X9_V3.png",
        "has_spear": True, "spear_shots": [1, 2, 3, 4],
        "summary": "Lua forms one irregular curved water sheet, angles it to redirect the returning right palm, then steps through the opening with the physical spear as the King's left hand descends.",
        "panels": [
            "<Subject 1> Lua opens her left hand and forms one transparent irregular curved water sheet between herself and the returning right palm of <Subject 2> AbyssKing while retaining the spear.",
            "<Subject 2> AbyssKing's right palm meets the same water sheet and <Subject 1> Lua twists her body and its curved angle together.",
            "The one flexible water sheet bows deeply and redirects the right hand sideways in droplets while <Subject 1> Lua keeps one spear and <Subject 2> AbyssKing keeps exactly two arms.",
            "<Subject 1> Lua steps through the opened lane and aligns the physical spear toward the King's chest as <Subject 2> AbyssKing lowers his left hand toward its shaft.",
        ],
        "compositions": [
            "A tight three-quarter Lua close-up frames her open left hand, one curved water sheet, spear shaft, and the approaching palm.",
            "A wide lateral full-body view shows Lua's body angle controlling the water sheet against the three-times-taller King.",
            "An over-Lua-shoulder medium view reads the bowed membrane, redirected hand, and open lane beyond it.",
            "A high diagonal medium-wide follows Lua through the gap and keeps spear point, chest line, and descending left hand visible.",
        ],
        "d": [
            "Pull quickly backward from hand distance to a full-body lateral width while dropping slightly, arriving at panel 2's shield-angle view.",
            "Arc quickly around Lua's back at shoulder height and close to medium distance, settling into panel 3's bowed-membrane view.",
            "Crane quickly upward and forward along the newly opened lane, widening into panel 4's spear-and-left-hand geometry.",
        ],
        "e": [
            "Let the newly forming curved water edge grow across the near foreground and clear to panel 2's full-body angle.",
            "Follow the right palm's redirected flow sideways through the droplets, revealing panel 3 over Lua's shoulder.",
            "Let the last droplets sweep aside as Lua's step and spear line pull the frame into panel 4's opening.",
        ],
    },
    {
        "scene": "EP00-S03", "clip": "EP00-S03-NC01", "source": "EP00-S03-SH06",
        "duration": 9.5, "storyboard": "EP00-S03-NC01_STORYBOARD_16X9_V4.png",
        "has_spear": True, "spear_shots": [1, 2, 3, 4],
        "summary": "The King's left palm forces the wooden shaft downward while his right arm closes the escape route, leaving Lua trapped between the same two hands with only a weak side remnant of her water sheet.",
        "panels": [
            "<Subject 2> AbyssKing presses his left open palm directly onto the side of the wooden spear shaft, never the stone point, while <Subject 1> Lua keeps both hands on it.",
            "<Subject 1> Lua pulls backward through hands and feet but the same left-palm pressure keeps the shaft down; <Subject 2> AbyssKing remains three times taller.",
            "<Subject 2> AbyssKing brings only his separate right arm across Lua's escape lane as <Subject 1> Lua pivots sideways with the trapped spear.",
            "<Subject 1> Lua is confined between the King's two hands with the spear close to her torso; one very thin transparent water-film remnant survives only at her side while <Subject 2> AbyssKing stays connected.",
        ],
        "compositions": [
            "An extreme low shaft-height contact insert shows the enormous left palm pressing wood and Lua's two hands resisting.",
            "A wide lateral full-body view reveals the complete pull, planted feet, connected King body, and fixed three-to-one scale.",
            "A directly overhead action view maps the right arm crossing the escape lane and Lua's pivot around the spear.",
            "A tight over-Lua-shoulder pressure close-up shows both distinct hands, her opponent-directed gaze, and the weak side water remnant.",
        ],
        "d": [
            "Pull rapidly backward from shaft distance to a full-body lateral width at waist height, arriving at panel 2's whole-body resistance.",
            "Crane rapidly straight upward while rotating clockwise by a quarter turn and widening into panel 3's overhead escape geometry.",
            "Dive rapidly behind Lua's shoulder and close to intimate distance, landing at panel 4 between the two distinct hand planes.",
        ],
        "e": [
            "Let Lua's backward draw slide the wooden shaft across the lens and reveal panel 2's full body strain.",
            "Let the King's separate right forearm cross the foreground in its approved lane-closing motion and uncover panel 3 from above.",
            "Follow Lua's pivoting shoulder under the crossing arm, then let the thin side water remnant catch focus and reveal panel 4.",
        ],
    },
    {
        "scene": "EP00-S03", "clip": "EP00-S03-NC02", "source": "EP00-S03-SH07",
        "duration": 11.5, "storyboard": "EP00-S03-NC02_STORYBOARD_16X9_V4.png",
        "has_spear": True, "spear_shots": [1, 2, 3, 4],
        "summary": "Lua resets the same weakened curved water sheet, but the King's continuous right-palm pressure bows it, drives her backward, and tears its outer edge into droplets until she raises the spear cross-body.",
        "panels": [
            "<Subject 1> Lua resets the same single weakened transparent curved water sheet as <Subject 2> AbyssKing's right open palm begins one continuous forward pressure; she retains the spear.",
            "The same right palm bows the flexible water sheet inward toward <Subject 1> Lua, whose eyes widen and jaw tightens while <Subject 2> AbyssKing stays three times larger.",
            "<Subject 1> Lua slides backward with the spear still in hand as the same water-sheet rim releases small droplets under <Subject 2> AbyssKing's unbroken pressure.",
            "The water sheet separates edge-first completely into droplets; <Subject 2> AbyssKing's right hand advances through the empty space and <Subject 1> Lua raises the intact spear cross-body.",
        ],
        "compositions": [
            "A medium-wide profile holds the single curved membrane, Lua's retained spear, and the King's full three-to-one pressure line.",
            "An intimate side close-up isolates the palm deforming transparent water and Lua's opponent-directed expression.",
            "A high wide oblique tracking view shows Lua's backward floor travel, connected King glide, retained spear, and droplet-shedding rim.",
            "A low contact-height side close view catches the outer-edge dissolution and Lua's immediate cross-body spear position.",
        ],
        "d": [
            "Dolly steadily inward along the palm normal at shoulder height, closing from medium-wide to panel 2's membrane-and-expression close-up.",
            "Crane steadily upward and backward into a high wide oblique while tracking Lua's slide, arriving at panel 3's complete travel path.",
            "Descend steadily along the shedding rim from high wide to hand height and tighten into panel 4's edge-first dissolution.",
        ],
        "e": [
            "Let the bowing water surface fill the foreground, then reveal Lua's strained face through it in panel 2.",
            "Follow the small rim droplets backward across the floor to expose panel 3's continuous slide without resetting pressure.",
            "Let the outer water edge peel past the lens and vanish, uncovering panel 4's empty gap and rising spear shaft.",
        ],
    },
    {
        "scene": "EP00-S03", "clip": "EP00-S03-NC03", "source": "EP00-S03-SH08",
        "duration": 9.5, "storyboard": "EP00-S03-NC03_STORYBOARD_16X9_V4_NO_SHIELD.png",
        "has_spear": True, "spear_shots": [1, 2, 3, 4],
        "summary": "With the water sheet gone, the King's right palm meets Lua's cross-body spear and scaled forearms, sending her sliding to the central floor while the intact spear remains in her hands.",
        "panels": [
            "With no water sheet remaining, <Subject 2> AbyssKing's right open palm reaches the cross-body wooden spear and blue-scaled forearms of <Subject 1> Lua.",
            "<Subject 1> Lua turns her torso to redirect part of the same force while <Subject 2> AbyssKing maintains one right-palm contact and exactly two arms.",
            "<Subject 1> Lua's feet slide across the floor toward the central platform, still holding the intact spear, as small chips and dust move in the same direction and <Subject 2> AbyssKing glides as one connected mass.",
            "<Subject 1> Lua stops low with one knee lowered and the spear braced on the floor while <Subject 2> AbyssKing withdraws the same right hand and closes distance upright.",
        ],
        "compositions": [
            "A side medium-wide shows the exact palm-to-spear-and-scaled-forearm contact direction with no water barrier.",
            "A tight contact-height three-quarter view reads Lua's torso turn, intact wood shaft, and the single continuing palm.",
            "A high lateral wide tracks the complete slide path, both floor contacts, same-direction debris, and connected lower mass.",
            "A low long-lens wide settles on Lua's lowered knee, spear brace, and the three-times-taller King reclaiming distance.",
        ],
        "d": [
            "Track briskly along the force axis at waist height and close from medium-wide to panel 2's torso-turn contact view.",
            "Crane briskly upward while trucking with Lua's slide and widening into panel 3's complete floor path.",
            "Descend briskly to knee height behind the stopping spear and compress distance into panel 4's low settled result.",
        ],
        "e": [
            "Let Lua's turning spear shaft cross the foreground on the approved force line and reveal panel 2's body rotation.",
            "Follow the first floor chip kicked backward by her sliding foot and open into panel 3's full travel path.",
            "Let the last sliding chip pass beneath the lens while the spear tip plants, revealing panel 4's lowered stop.",
        ],
    },
    {
        "scene": "EP00-S04", "clip": "EP00-S04-NC01", "source": "EP00-S04-SH09",
        "duration": 9.5, "storyboard": "EP00-S04-NC01_STORYBOARD_16X9_V3.png",
        "has_spear": True, "spear_shots": [1, 2, 3, 4],
        "summary": "Lua uses the spear to rise, sees the wrist mark pulse twice without stabilizing, reads the King's next hand path, and commits to her final known option.",
        "panels": [
            "<Subject 1> Lua begins low with one knee near the floor and uses the intact spear as a physical brace while <Subject 2> AbyssKing prepares the right shoulder and hand behind her.",
            "<Subject 1> Lua rises to both feet as her wrist mark gives the first weak pulse; <Subject 2> AbyssKing remains upright and three times taller.",
            "The same wrist mark gives a second uneven pulse while <Subject 1> Lua tracks the King's shoulder-to-hand route and draws the spear back; <Subject 2> AbyssKing starts the hand path.",
            "<Subject 1> Lua fixes her gaze on the escape direction and takes one short breath with the spear loaded behind her as <Subject 2> AbyssKing's right hand begins.",
        ],
        "compositions": [
            "A low medium-wide holds Lua's knee, spear brace, and the King's right shoulder in one depth line.",
            "A tight hand-and-face three-quarter view reads the first wrist pulse without losing the King's scale in the background.",
            "A rear lateral full-body view connects the second pulse, Lua's eye path, spear draw, and the starting hand route.",
            "An over-King-hand medium view looks toward Lua's loaded stance and opponent-directed gaze without making her face the camera.",
        ],
        "d": [
            "Pedestal slowly upward with Lua from knee height to chest height and close into panel 2's wrist-and-face view.",
            "Arc slowly behind Lua at chest height while widening to full body, arriving at panel 3's spear draw and hand-route line.",
            "Truck slowly toward the King's starting right hand at shoulder height and tighten into panel 4's over-hand loaded stance.",
        ],
        "e": [
            "Let Lua's rising body pull the spear shaft upward past the lens and reveal panel 2's first wrist pulse.",
            "Use the second wrist pulse only as a brief focus cue, then follow Lua's eye path to reveal panel 3's hand route.",
            "Let the King's approved right-hand start enter the foreground and uncover panel 4's loaded Lua beyond it.",
        ],
    },
    {
        "scene": "EP00-S04", "clip": "EP00-S04-NC02", "source": "EP00-S04-SH10",
        "duration": 10.5, "storyboard": "EP00-S04-NC02_STORYBOARD_16X9_V4.png",
        "has_spear": True, "spear_shots": [4],
        "summary": "Lua completes one step outside the predicted hand path, brings the dark wrist mark near her chest for one brief untranslated vocalization, expands one blue-white floor current, and aligns the spear while the King slows for one breath.",
        "panels": [
            "<Subject 1> Lua completes one step outside <Subject 2> AbyssKing's predicted right-hand lane before contact; the floor remains dark and no current pattern exists yet.",
            "<Subject 1> Lua brings the dark wrist mark near her chest and makes one brief untranslated vocalization without visible writing while <Subject 2> AbyssKing stays silent in the background.",
            "Exactly one thin blue-white water-surface current expands once across the floor around <Subject 1> Lua, and <Subject 2> AbyssKing's two arms and torso visibly slow for one breath.",
            "The same single floor current fades as <Subject 1> Lua aligns the physical spear toward the King's chest across open distance; <Subject 2> AbyssKing remains upright and undamaged.",
        ],
        "compositions": [
            "A very wide lateral full-body view proves Lua's completed step outside the empty hand path and the unchanged floor.",
            "A tight behind-Lua-shoulder portrait isolates her dark wrist near her chest, mouth movement, and silent King in depth.",
            "A directly overhead wide shows exactly one expanding floor current, Lua at its center, and the King's slowed connected body.",
            "A low side medium-long aligns the camera along the physical spear toward the three-times-taller King as the one current fades.",
        ],
        "d": [
            "Dolly quickly behind Lua's right shoulder while rising from hip to chest height and closing into panel 2's wrist-and-mouth portrait.",
            "Crane quickly straight upward from shoulder distance to a directly overhead wide, arriving at panel 3's single-current geometry.",
            "Descend quickly from overhead to spear height on Lua's left side and close to medium-long distance for panel 4's alignment.",
        ],
        "e": [
            "Let Lua's completed sidestep carry her shoulder across the foreground and reveal panel 2's dark wrist near her chest.",
            "Follow the first approved blue-white water line outward from below her hands until it opens panel 3's overhead current.",
            "Follow one fading current line inward to Lua's hands, then let the physical spear shaft extend through frame into panel 4.",
        ],
    },
    {
        "scene": "EP00-S04", "clip": "EP00-S04-NC03", "source": "EP00-S04-SH11",
        "duration": 12.5, "storyboard": "EP00-S04-NC03_STORYBOARD_16X9_V4.png",
        "has_spear": True, "spear_shots": [1, 2, 3, 4],
        "summary": "Lua commits her whole body to one straight physical spear extension, but the King clamps the wooden shaft, redirects it and her scaled forearms laterally, and leaves her stopped on one hand and one knee with the intact spear out of reach.",
        "panels": [
            "<Subject 1> Lua drives from the rear foot into one straight two-handed spear extension across open space while <Subject 2> AbyssKing remains slowed and three times taller; the point stays short of his chest.",
            "As the last floor current vanishes, <Subject 2> AbyssKing's left hand clamps the side of the wooden shaft before its stone point reaches him while <Subject 1> Lua keeps driving.",
            "Keeping the left hand on the shaft, <Subject 2> AbyssKing uses only his right open hand for one lateral redirection across the shaft and Lua's scaled forearms, carrying <Subject 1> Lua off balance.",
            "The intact spear rests just beyond immediate reach; <Subject 1> Lua stops with one hand and one knee on the floor and all blue effects off while <Subject 2> AbyssKing stands unchanged.",
        ],
        "compositions": [
            "A dramatic low side full-body view reads Lua's complete drive line, open tip-to-chest gap, and fixed three-to-one scale.",
            "A tight chest-height contact insert shows one left hand clamping only the wooden shaft with the stone point still clear.",
            "A dynamic overhead three-quarter view separates both King hands and shows the single lateral redirection through shaft and scaled forearms.",
            "A low wide aftermath view holds the one-hand-one-knee posture, intact out-of-reach spear, dark wrist, and upright King.",
        ],
        "d": [
            "Dolly rapidly along the spear axis at chest height and close from full body to panel 2's exact left-hand shaft clamp.",
            "Crane rapidly upward while orbiting clockwise around the two hand planes and widen into panel 3's overhead redirection geometry.",
            "Sweep rapidly down the lateral force line to floor height and pull wide, arriving at panel 4's complete stop tableau.",
        ],
        "e": [
            "Let the advancing wooden shaft run beneath the lens and stop under the King's left hand, revealing panel 2's clamp.",
            "Let the King's approved right open hand traverse the near foreground on the lateral line and uncover panel 3's whole-body redirection.",
            "Follow the intact spear as it leaves Lua's hands and settles across the floor, revealing panel 4's one-hand-one-knee result.",
        ],
    },
    {
        "scene": "EP00-S05", "clip": "EP00-S05-NC01", "source": "EP00-S05-SH12",
        "duration": 8.5, "storyboard": "EP00-S05-NC01_STORYBOARD_16X9_V4.png",
        "has_spear": True, "spear_shots": [1, 2, 3, 4],
        "summary": "Lua tries to rise once from the same one-hand-and-one-knee posture, drops back when the arm buckles, finds the wrist mark dark, and raises her head as the King glides slightly closer.",
        "panels": [
            "<Subject 1> Lua begins with her left palm and right knee on the floor, other foot planted, dark wrist, and intact spear beyond immediate reach while <Subject 2> AbyssKing stands three times taller.",
            "<Subject 1> Lua attempts to rise exactly once by pressing the same palm and planted foot, but the supporting arm buckles before she leaves the low posture; <Subject 2> AbyssKing remains distant.",
            "<Subject 1> Lua settles back into the same left-hand-right-knee posture and looks at the dark wrist mark as the spear makes only a tiny floor roll; <Subject 2> AbyssKing stays upright.",
            "<Subject 1> Lua raises only her head from the same low posture while <Subject 2> AbyssKing glides a small distance closer on one connected lower mass with relaxed hands.",
        ],
        "compositions": [
            "A low wide continuity view holds Lua's exact ground contacts, out-of-reach spear, and the King's oppressive scale.",
            "A tight low side body-mechanics view isolates the one rise attempt, buckling support arm, planted foot, and nearby spear.",
            "A high intimate three-quarter view keeps the restored hand-and-knee posture, dark wrist, and tiny spear roll together.",
            "A very wide over-Lua-shoulder view makes her small head lift and the King's slight connected glide readable across open floor.",
        ],
        "d": [
            "Dolly slowly inward at palm height and close from wide to panel 2's side body-mechanics view without lifting above Lua.",
            "Crane slowly upward by one body height and arc toward her wrist side, arriving at panel 3's high intimate restored posture.",
            "Pull slowly backward over Lua's shoulder while descending slightly and widening into panel 4's open-floor scale view.",
        ],
        "e": [
            "Let Lua's pressing shoulder rise through the foreground and reveal panel 2's single incomplete stand attempt.",
            "Follow her buckling forearm back to the floor, then rack focus to the dark wrist and tiny spear roll in panel 3.",
            "Let Lua's approved head lift guide focus across the open floor to the King's slight glide, revealing panel 4.",
        ],
    },
    {
        "scene": "EP00-S05", "clip": "EP00-S05-NC02", "source": "EP00-S05-SH13",
        "duration": 8.5, "storyboard": "EP00-S05-NC02_STORYBOARD_16X9_V3.png",
        "has_spear": False,
        "summary": "With the wrist mark remaining dark, Lua hears one unfamiliar internal heartbeat, loses one breath, and refocuses on the distant King without any visible change.",
        "panels": [
            "<Subject 1> Lua exhales unevenly in a close view with her dark wrist mark visible while <Subject 2> AbyssKing remains a large soft black shape in the background.",
            "One low internal heartbeat occurs with no visible source or screen disturbance; <Subject 1> Lua's breath stops and her eyes widen slightly while <Subject 2> AbyssKing does not react.",
            "<Subject 1> Lua looks briefly down toward the unfamiliar sensation inside herself rather than at the wrist, which remains dark; <Subject 2> AbyssKing stays out of focus.",
            "<Subject 1> Lua raises her eyes back to <Subject 2> AbyssKing, and surprise overtakes strain while her appearance and the entire room remain unchanged.",
        ],
        "compositions": [
            "A close three-quarter face-and-upper-body view includes the dark wrist and the King as an out-of-focus scale mass.",
            "A tighter fixed profile emphasizes the single stopped breath and tiny eye change without camera shake.",
            "An intimate wrist-side over-shoulder view shows the dark mark while Lua's gaze turns inward and down.",
            "A close rear three-quarter eyeline view refocuses from Lua's eyes to the distant King without changing their positions.",
        ],
        "d": [
            "Dolly imperceptibly inward at eye height and close from close to tighter profile distance, arriving at panel 2's held breath.",
            "Arc very slowly down toward Lua's wrist side while maintaining close distance, settling into panel 3's inward-down gaze.",
            "Rise very slowly back to eye height and drift behind her shoulder without changing distance, arriving at panel 4's restored opponent eyeline.",
        ],
        "e": [
            "Use only Lua's exhale leaving her lips as a shallow focus cue that clears into panel 2's stopped breath.",
            "Follow Lua's approved eye movement downward, not the dark mark itself, to reveal panel 3's inward attention.",
            "Follow the same eyes lifting toward the background and rack focus along that eyeline to reveal panel 4's King.",
        ],
    },
    {
        "scene": "EP00-S05", "clip": "EP00-S05-NC03", "source": "EP00-S05-SH14",
        "duration": 6.5, "storyboard": "EP00-S05-NC03_STORYBOARD_16X9_V3.png",
        "has_spear": False,
        "summary": "Lua steadies one breath and begins to understand the unfamiliar sensation, but the image cuts directly to full black before a second heartbeat completes.",
        "panels": [
            "<Subject 1> Lua holds an eye-level close-up with <Subject 2> AbyssKing reduced to a partial soft black shape behind her; her wrist and appearance remain unchanged.",
            "<Subject 1> Lua's uneven breathing settles for one breath and her eye movement slows while <Subject 2> AbyssKing remains still and unfocused.",
            "<Subject 1> Lua lifts her head only slightly as recognition begins in her expression; a second internal heartbeat starts only as a low pre-sound and <Subject 2> AbyssKing gives no reaction.",
            "Before the second heartbeat completes, the image leaves <Subject 1> Lua and cuts directly to full black with no visible form, color, source, title, or explanation.",
        ],
        "compositions": [
            "A fixed close-up centers Lua's eyes and restrained expression while keeping only a partial soft King shape in depth.",
            "A fixed tighter close-up preserves the same axis and records the single breath settling with no zoom or shake.",
            "An extreme fixed eye close-up preserves the same gaze direction and reads only the slight head lift and recognition.",
            "A direct full-black frame contains no camera movement, subject rendering, graphic, or residual glow.",
        ],
        "d": [
            "Hold eye height and creep forward at the slowest perceptible speed from close to tighter distance, arriving at panel 2 without a pose reset.",
            "Hold the axis and creep forward again by only a few centimeters at the same speed, arriving at panel 3's extreme eye distance.",
            "Stop all travel at extreme close distance and perform only the approved direct cut into panel 4's full black before the pre-sound completes.",
        ],
        "e": [
            "Use Lua's one settling breath as the only focus change and let it reveal panel 2's steadier eyes.",
            "Follow the final tiny upward eye movement within the same fixed frame to reveal panel 3's recognition.",
            "Let the second heartbeat pre-sound begin over the unchanged eye close-up, then use the approved direct cut to reveal panel 4's full black.",
        ],
        "outgoing_subjects": [1],
    },
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"PNG가 아닙니다: {path}")
    return struct.unpack(">II", header[16:24])


def _times(duration: float) -> list[float]:
    return [round(duration * index / 4, 3) for index in (1, 2, 3)]


def _label_composition(value: str) -> str:
    """Ensure official Subject labels precede any character alias in camera prose."""
    value = re.sub(
        r"(?<!<Subject 2> )\bAbyssKing('s)?\b",
        lambda match: f"<Subject 2> AbyssKing{match.group(1) or ''}",
        value,
    )
    value = re.sub(
        r"(?<!<Subject 2> Abyss)\bKing('s)?\b",
        lambda match: f"<Subject 2> AbyssKing{match.group(1) or ''}",
        value,
    )
    value = re.sub(
        r"(?<!<Subject 1> )\bLua('s)?\b",
        lambda match: f"<Subject 1> Lua{match.group(1) or ''}",
        value,
    )
    return value


def _camera_plan(clip: dict[str, Any], variant: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    starts = _times(float(clip["duration"]))
    for index, composition in enumerate(clip["compositions"], start=1):
        composition = _label_composition(composition)
        if variant == "A":
            camera = (
                f"Directly reproduce the storyboard checkpoint composition. {composition} "
                "Do not invent travel beyond the depicted checkpoint."
            )
        elif variant == "D":
            camera = f"Maintain the accumulated action state. {composition}"
        else:
            camera = (
                f"Maintain the accumulated action state and use only the approved "
                f"in-scene motion for the reveal. {composition}"
            )
        row: dict[str, Any] = {
            "panel_index": index,
            "panel_position": POSITIONS[index - 1],
            "camera": camera,
            "beat_ids": [f"P{index}"],
        }
        if index > 1:
            row["start_seconds"] = starts[index - 2]
        if index < 4 and variant in {"D", "E"}:
            row["transition_to_next"] = clip[variant.lower()][index - 1]
        rows.append(row)
    return rows


def _asset_catalog(lock: dict[str, Any]) -> dict[str, Any]:
    assets = lock["asset_locks"]
    return {
        "lua": {
            "role": "lua_identity",
            "label": "Lua identity sheet",
            "copy_from": assets["lua_awakened"]["path"],
            "subject_id": 1,
            "subject_name": "Lua",
            "subject_description": (
                "One young spear fighter with warm brown tied hair, freckles, a weathered beige sleeveless outfit, "
                "rope and shell ornaments, sandals, and asymmetrical turquoise dragon scales. Preserve one person, "
                "the same face, proportions, clothing, scale placement, and fully awakened appearance."
            ),
            "retention_marker": "fully_preserved",
            "retention_description": "Preserve the same single Lua identity and fully awakened appearance in every cited Shot",
        },
        "king": {
            "role": "abyss_king_identity",
            "label": "Abyss King identity sheet",
            "copy_from": assets["abyss_king"]["path"],
            "subject_id": 2,
            "subject_name": "AbyssKing",
            "subject_description": (
                "One connected black-liquid humanoid king about three times Lua's height, with one crown-like head, "
                "one pair of bright eyes, one torso, exactly two long arms, exactly two hands, and one continuous "
                "skirt-like lower mass. Preserve the connected anatomy and fixed scale."
            ),
            "retention_marker": "fully_preserved",
            "retention_description": "Preserve one connected three-times-Lua body with exactly two arms and two hands",
        },
        "spear": {
            "role": "major_prop_spear",
            "label": "Dragon spear identity sheet",
            "copy_from": assets["dragon_spear"]["path"],
            "standalone_picture_name": "the single physical dragon spear",
            "standalone_picture_description": (
                "Use one fixed-length wooden shaft with one black chipped stone point, rope bindings, and small shell "
                "ornaments. It moves only through Lua's physical grip and remains intact."
            ),
            "retention_marker": "fully_preserved",
            "retention_description": "Preserve one intact fixed-length physical spear only in the cited Shots",
        },
    }


def _storyboard_entry(clip: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "chronological_storyboard",
        "label": f"{clip['clip']} reviewed four-panel storyboard",
        "copy_from": f"storyboards_ep00_ade_v1/{clip['storyboard']}",
        "reference_kind": "storyboard",
        "storyboard_panel_count": 4,
        "storyboard_reading_order": "top-left, top-right, bottom-left, bottom-right",
        "storyboard_beats": list(clip["panels"]),
        "standalone_picture_name": "the chronological four-panel storyboard",
        "standalone_picture_description": (
            "Read the 2x2 grid as four ordered checkpoints: top-left, top-right, bottom-left, then bottom-right. "
            "Preserve each panel's composition, blocking, eyelines, emotion, prop state, and causal exit-to-entry "
            "continuity, but never render the grid or duplicate the scene."
        ),
        "retention_marker": "fully_preserved",
        "retention_description": "Preserve all four panel checkpoints and their one-to-one Shot order",
        "retention_shots": [1, 2, 3, 4],
    }


def _build_payloads(lock: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    canonical_sources = [
        "EP00_LOCKED_PRODUCTION_RULES_V1.json",
        *lock["canonical_sources"].values(),
        "EP00_CANONICAL_CLIPS_V1.json",
    ]
    asset_catalog = _asset_catalog(lock)
    clips: list[dict[str, Any]] = []
    contracts: dict[str, Any] = {}
    canonical_rows: list[dict[str, Any]] = []
    bridge_ids = [f"EP00_LOCKED_STATE_{index:02d}" for index in range(15)]
    for sequence, clip in enumerate(CLIPS, start=1):
        panel_descriptions = [_label_composition(value) for value in clip["panels"]]
        storyboard_key = f"storyboard_{clip['clip'].lower()}"
        asset_catalog[storyboard_key] = _storyboard_entry(clip)
        has_spear = bool(clip["has_spear"])
        references: list[Any] = ["lua", "king"]
        if has_spear:
            references.append({"asset_key": "spear", "retention_shots": clip["spear_shots"]})
        references.append(storyboard_key)
        storyboard_picture_id = 4 if has_spear else 3
        variants = [
            {
                "variant_id": variant,
                "label": f"후보 {variant}",
                "rationale": {
                    "A": f"{clip['clip']}의 검수된 네 체크포인트를 발명 없이 직접 재현",
                    "D": f"{clip['clip']} 고유 카메라 경로가 다음 체크포인트 도착을 현재 Shot 안에서 시작",
                    "E": f"{clip['clip']}의 승인된 인물·창·물·시선 움직임만으로 다음 체크포인트를 공개",
                }[variant],
                "prompt_spec": {},
            }
            for variant in ("A", "D", "E")
        ]
        incoming = (
            f"Continue the exact prior state with <Subject 1> Lua and <Subject 2> AbyssKing on the same action axis; "
            f"begin only the first event shown for {clip['clip']}."
        )
        if sequence == len(CLIPS):
            outgoing = (
                "End only after <Subject 1> Lua's recognition begins and the image cuts directly to full black "
                "before the second internal heartbeat completes."
            )
        else:
            outgoing = (
                f"End with <Subject 1> Lua and <Subject 2> AbyssKing in the exact panel-4 accumulated state so "
                f"the next clip begins without a pose, contact, prop, effect, or scale reset."
            )
        outgoing_subjects = clip.get("outgoing_subjects", [1, 2])
        contract = {
            "shared_event": clip["summary"],
            "bridge_in_id": bridge_ids[sequence - 1],
            "bridge_out_id": bridge_ids[sequence],
            "boundary_policy": "terminal" if sequence == len(CLIPS) else "referenced_cut",
            "source_shot_ids": [clip["source"]],
            "incoming_reference_subjects": [1, 2],
            "outgoing_reference_subjects": outgoing_subjects,
            "incoming_bridge": incoming,
            "outgoing_bridge": outgoing,
            "storyboard_required": True,
            "storyboard_picture_id": storyboard_picture_id,
            "storyboard_panel_count": 4,
            "beats": [
                {"beat_id": f"P{index}", "description": description}
                for index, description in enumerate(panel_descriptions, start=1)
            ],
            "candidate_plans": {
                variant: {
                    "emphasis": {
                        "A": "direct reviewed checkpoint reproduction",
                        "D": "clip-specific continuous camera travel into the next checkpoint",
                        "E": "clip-specific action-motivated reveal into the next checkpoint",
                    }[variant],
                    "shots": _camera_plan(clip, variant),
                }
                for variant in ("A", "D", "E")
            },
        }
        contracts[clip["clip"]] = contract
        clip_row = {
            "scene_id": clip["scene"],
            "clip_id": clip["clip"],
            "sequence": sequence,
            "source_shot_id": clip["source"],
            "status": "pending_review",
            "duration_seconds": clip["duration"],
            "references": references,
            "prompt_base": {
                "summary": clip["summary"],
                "style_opening": [
                    "A vast wet abyssal stone throne hall uses restrained cyan crystal reflections and deep black water shadows",
                    "Keep the left-to-right action axis, one-to-three character scale, and physically continuous motion readable",
                ],
                "overall_soundscape": (
                    "Low underwater pressure, controlled black-liquid movement, wet floor friction, Lua's breath, "
                    "and only the physical water or spear sounds required by the shown event."
                ),
                "non_diegetic_music": (
                    "A fast restrained low-string pulse follows the action causality and recedes toward near silence "
                    "in the final scene."
                ),
            },
            "prompt_variants": variants,
            "canonical_source_lineage": canonical_sources,
            "locked_rule_id": lock["lock_id"],
            "continuity_in": bridge_ids[sequence - 1],
            "continuity_out": bridge_ids[sequence],
            "storyboard_review_contract": {
                "picture_id": storyboard_picture_id,
                "panel_positions": list(POSITIONS),
                "panel_to_shot": "one_to_one",
                "visual_asset_status": "agent_visually_reviewed",
            },
            "visual_review": "agent_visually_reviewed",
            "semantic_review": "pending_full_project_audit",
        }
        clips.append(clip_row)
        canonical_rows.append(json.loads(json.dumps(clip, ensure_ascii=False)))
    canonical = {
        "schema_version": 1,
        "canonical_id": "raising_a_dragon_s01_ep00_canonical_clips_v1",
        "locked_rule_id": lock["lock_id"],
        "source_lineage": canonical_sources[:-1],
        "clips": canonical_rows,
    }
    events = {
        "version": EVENT_VERSION,
        "locked_rule_id": lock["lock_id"],
        "canonical_source_lineage": canonical_sources,
        "clips": contracts,
    }
    spec = {
        "schema_version": 2,
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon S01 EP00 · Locked Storyboard A/D/E V7",
        "description": (
            "Canonical EP00 build with independent storyboard Pictures, four panel-to-Shot anchors, "
            "major spear references, and clip-specific A/D/E camera continuity."
        ),
        "source_policy": "locked_canonical_sources_only_no_v1_v6_prompt_lineage",
        "canonical_source_lineage": canonical_sources,
        "locked_rule_id": lock["lock_id"],
        "build_script": "scripts/build_ep00_locked_storyboard_v7.py",
        "asset_catalog": asset_catalog,
        "event_contracts_file": EVENTS_PATH.name,
        "clips": clips,
    }
    return canonical, events, spec


def _preflight(lock: dict[str, Any]) -> None:
    clip_contract = lock["clip_contract"]
    if len(CLIPS) != int(clip_contract["clip_count"]):
        raise ValueError("잠금 계약과 정본 clip 수가 다릅니다.")
    if sum(float(clip["duration"]) for clip in CLIPS) != float(
        clip_contract["total_duration_seconds"]
    ):
        raise ValueError("잠금 계약과 정본 총 길이가 다릅니다.")
    if any(len(clip["panels"]) != 4 for clip in CLIPS):
        raise ValueError("모든 정본 clip에는 4개 패널 사건이 필요합니다.")
    for asset in lock["asset_locks"].values():
        path = EPISODE_DIR / asset["path"]
        if _sha256(path) != asset["sha256"]:
            raise ValueError(f"잠금 자산 해시가 다릅니다: {path}")
    workflow = Path(lock["workflow_lock"]["path"])
    if _sha256(workflow) != lock["workflow_lock"]["sha256"]:
        raise ValueError("잠금 H3 workflow 해시가 다릅니다.")
    workflow_payload = json.loads(workflow.read_text(encoding="utf-8"))
    node_names: list[str] = []
    if isinstance(workflow_payload, dict):
        for node in workflow_payload.values():
            if not isinstance(node, dict):
                continue
            node_names.extend(
                str(value).lower()
                for value in (node.get("class_type"), node.get("type"))
                if value
            )
            meta = node.get("_meta") or {}
            if isinstance(meta, dict) and meta.get("title"):
                node_names.append(str(meta["title"]).lower())
    for fragment in lock["workflow_lock"]["forbidden_node_name_fragments"]:
        if any(fragment.lower() in name for name in node_names):
            raise ValueError(f"금지 workflow 노드 조각이 있습니다: {fragment}")
    for clip in CLIPS:
        path = EPISODE_DIR / "storyboards_ep00_ade_v1" / clip["storyboard"]
        if _png_size(path) != (1672, 941):
            raise ValueError(f"스토리보드가 1672x941 16:9가 아닙니다: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-only", action="store_true")
    args = parser.parse_args()
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    _preflight(lock)
    canonical, events, spec = _build_payloads(lock)
    CANONICAL_DATA_PATH.write_text(
        json.dumps(canonical, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    EVENTS_PATH.write_text(
        json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    SPEC_PATH.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.emit_only:
        print(json.dumps({"canonical": str(CANONICAL_DATA_PATH), "events": str(EVENTS_PATH), "spec": str(SPEC_PATH)}, ensure_ascii=False))
        return 0
    result = h3_prompt_project_builder.build_project(ROOT, SPEC_PATH)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
