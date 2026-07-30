"""Curated still-image scene prompts for RaisingaDragonSeason01 EP01 Director project."""
from __future__ import annotations

from typing import Any

# Key: (clip_id, segment_id) -> {prompt, negative?, start_state?}
STILL_SPECS: dict[tuple[str, str], dict[str, str]] = {
    # --- SC01-001_01 Storm sea opening ---
    ("SC01-001_01", "SEG01"): {
        "start_state": "Night storm sea with no character visible.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Extreme wide static shot at eye level across a violent storm night ocean. "
            "Churning black waves with white foam, diagonal rain streaks, and a lightning fork "
            "from upper left illuminate towering wave walls. Open central water with no people, "
            "dragons, or creatures visible. Deep blue-black sea palette, cold moonless storm light. "
            "Fixed background: distant lightning-lit horizon, grey storm clouds, spray particles."
        ),
        "negative": (
            "text, subtitles, watermark, characters, dragons, faces, silhouettes, duplicate figures, "
            "live-action, photorealistic, motion blur"
        ),
    },
    ("SC01-001_01", "SEG02"): {
        "start_state": "Wide storm ocean; a tiny blue pulse glows far below the surface.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "High-angle static wide shot looking down into a storm-wave trough. "
            "Black churning water fills the frame; at the deep center a single tiny blue "
            "bioluminescent pulse glows faintly. No creature body visible — only the distant fragile light. "
            "Rain and foam at the surface edges; cold storm lighting from upper left."
        ),
        "negative": (
            "text, subtitles, watermark, visible dragon body, character face, duplicate glows, "
            "live-action, photorealistic, motion blur, camera motion lines"
        ),
    },
    ("SC01-001_01", "SEG03"): {
        "start_state": "High view of storm sea; the blue undersea pulse is slightly brighter beneath a wave trough.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Static high-angle wide composition over storm-dark water. "
            "A wave trough opens at center-bottom; beneath it a slightly brighter blue pulse "
            "shines in the deep water column. Surface foam and rain streaks at top; open dark water "
            "below ready to plunge deeper. No character silhouette visible yet. Teal-black abyss palette."
        ),
        "negative": (
            "text, subtitles, watermark, dragon silhouette, human figure, duplicate lights, "
            "live-action, photorealistic, motion blur"
        ),
    },
    # --- SC01-001_02 Deep sea ruins ---
    ("SC01-001_02", "SEG01"): {
        "start_state": "Deep underwater ruins; a sacred coral pillar is cracking.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Wide static underwater shot in deep sea dragon palace ruins. "
            "Center-left: a cracked ancient coral pillar with bioluminescent blue veins, mid-crack with "
            "small debris drifting. Marine snow particles drift through open central water. "
            "Dark teal abyss and ruined coral architecture recede into background depth. "
            "Cold cyan ambient fill; no characters present."
        ),
        "negative": (
            "text, subtitles, watermark, characters, dragons, faces, live-action, photorealistic, motion blur"
        ),
    },
    ("SC01-001_02", "SEG02"): {
        "start_state": "Deep ruins; Young Mir appears in faint blue glow, battered and half-conscious.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static underwater shot. Young Mir (CHAR_YOUNG_MIR) floats at center in faint blue glow — "
            "small silver-blue hatchling dragon with short curved horns, folded fin-like wings, "
            "water-drop tail crystal, and crown-shaped chest wave mark. Wet scales, half-closed clear blue eyes, "
            "battered exhausted posture. Cracked coral pillar blurred in background left; marine snow drifting. "
            "Exactly one small dragon; fully dragon anatomy, no human features."
        ),
        "negative": (
            "text, subtitles, watermark, duplicate Mir, human child, human clothing, Lua, wings on human, "
            "fused anatomy, live-action, photorealistic, motion blur"
        ),
    },
    ("SC01-001_02", "SEG03"): {
        "start_state": "Young Mir floats battered in the current, eyes half closed, tail crystal dim.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close static shot on Young Mir (CHAR_YOUNG_MIR) suspended in teal water column center frame. "
            "Body angled diagonally as if tumbling but frozen — half-closed blue eyes, weakly flickering "
            "water-drop tail crystal, folded wings against his scaled sides. "
            "Open water behind; marine snow particles. One dragon only; no human anatomy."
        ),
        "negative": (
            "text, subtitles, watermark, duplicate Mir, human face, human hair, clothing on dragon, "
            "Lua merged with Mir, live-action, photorealistic, motion blur"
        ),
    },
    ("SC01-001_02", "SEG04"): {
        "start_state": "Young Mir floats weakly, oriented upward toward a blue light diagonal above.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Low-angle medium static shot looking up past Young Mir (CHAR_YOUNG_MIR) in lower center frame. "
            "Small silver-blue dragon oriented upward, head and snout aimed toward a faint blue diagonal "
            "light beam in upper frame; fins and wings slack from exhaustion. Vulnerable floating posture, "
            "eyes barely open. Deep teal water above; no other characters."
        ),
        "negative": (
            "text, subtitles, watermark, duplicate Mir, human body, wings on human, live-action, "
            "photorealistic, motion blur, completed escape"
        ),
    },
    # --- SC01-001_03 Black Tide pursuit ---
    ("SC01-001_03", "SEG01"): {
        "start_state": "Young Mir weak in deep corridor; Black Tide rises below him.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "High-angle medium-wide static underwater shot. Young Mir (CHAR_YOUNG_MIR) hangs weakly in upper-center "
            "water column — small silver-blue dragon with horns, folded wings, tail crystal. "
            "Two body lengths below in the deep background: the Black Tide (ENTITY_BLACK_TIDE), a separate "
            "supernatural mass of living black water with faint hand-like shadow shapes inside its form. "
            "Teal corridor with diagonal blue ascent light from upper left; faint coral ruin edges at sides. "
            "Mir and Black Tide are distinct entities — not merged."
        ),
        "negative": (
            "text, subtitles, watermark, Black Tide merged into background plate, duplicate Mir, "
            "Mir with black water body, human anatomy, live-action, photorealistic, motion blur"
        ),
    },
    ("SC01-001_03", "SEG02"): {
        "start_state": "Young Mir clings to a faint blue diagonal beam; Black Tide looms below.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static underwater shot angled slightly upward. Young Mir (CHAR_YOUNG_MIR) in upper third "
            "grips a faint blue diagonal light beam with trembling fins — body barely offset from the beam, "
            "exhausted expression. Black Tide (ENTITY_BLACK_TIDE) occupies lower third as a rising black mass "
            "with shadow shapes, one body length below Mir. Clear separation between dragon and tide entity."
        ),
        "negative": (
            "text, subtitles, watermark, merged bodies, Mir absorbed by tide, duplicate characters, "
            "human features on Mir, live-action, photorealistic, motion blur"
        ),
    },
    ("SC01-001_03", "SEG03"): {
        "start_state": "Young Mir's tail crystal emits a bright flash; Black Tide pulls back below.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static underwater shot. Young Mir (CHAR_YOUNG_MIR) at center-left, tail-end water-drop crystal "
            "emitting one bright blue flash; body still on the diagonal beam. Black Tide (ENTITY_BLACK_TIDE) "
            "pulled back in lower-right deep water, shadow shapes contracting away from the blue burst. "
            "Cyan-teal corridor lighting; separate silhouettes."
        ),
        "negative": (
            "text, subtitles, watermark, fused anatomy, tide covering Mir, duplicate Mir, human on dragon, "
            "live-action, photorealistic, motion blur"
        ),
    },
    ("SC01-001_03", "SEG04"): {
        "start_state": "Extreme close on Young Mir's eye reflecting blue light and black shadow.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Extreme close static shot filling frame with Young Mir's (CHAR_YOUNG_MIR) dragon eye — "
            "clear blue iris and trembling vertical pupil. Reflected in the pupil: a shard of blue ascent light "
            "and a curved black shadow shape. Scaled brow ridge visible at frame edges; no full body shown. "
            "Dreamlike sharp focus on eye surface."
        ),
        "negative": (
            "text, subtitles, watermark, human eye, duplicate eyes, full body cramming frame, "
            "live-action, photorealistic, motion blur"
        ),
    },
    # --- SC01-001_04 Memory vision ---
    ("SC01-001_04", "SEG01"): {
        "start_state": "Surreal vision of broken palace gate and sleeping dragon shadows.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Wide static shot with slight dutch tilt through a surreal black abyss. "
            "Broken dragon palace gate and ruined hall columns in midground; enormous sleeping dragon shadows "
            "curled in darkness without readable faces. Floating debris and dust motes in open central space. "
            "Cold blue memory-light, deep black void, desaturated blue-grey palette. No human characters."
        ),
        "negative": (
            "text, subtitles, watermark, readable dragon faces, human children, Lua, live-action, "
            "photorealistic, motion blur"
        ),
    },
    ("SC01-001_04", "SEG02"): {
        "start_state": "Young Mir's eye fills the frame; memory reflections in the pupil.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Extreme close static shot — Young Mir's (CHAR_YOUNG_MIR) dragon eye occupies most of frame. "
            "Pupil wide, trembling; faint ghostly palace shapes reflected on the eye surface. "
            "Scaled skin texture at edges; no mouth or voice visible. Vision-space cold blue lighting."
        ),
        "negative": (
            "text, subtitles, watermark, Korean text, dialogue captions, human eye, duplicate eyes, "
            "live-action, photorealistic, motion blur"
        ),
    },
    ("SC01-001_04", "SEG03"): {
        "start_state": "Close on Young Mir's eye at the instant a disembodied voice speaks.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Extreme close static shot on Young Mir's (CHAR_YOUNG_MIR) dragon eye — pupil contracted in fear, "
            "micro-shudder texture in iris. No visible speaker or mouth anywhere in frame. "
            "Dark void and faint palace reflection in eye surface. Ominous cold blue memory light."
        ),
        "negative": (
            "text, subtitles, watermark, visible mouth, speech bubble, human face, Deep Sea King body, "
            "live-action, photorealistic, motion blur"
        ),
    },
    ("SC01-001_04", "SEG04"): {
        "start_state": "Young Mir trembles in fear as storm light intrudes into the vision.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close static shot on Young Mir (CHAR_YOUNG_MIR) in vision space — small silver-blue dragon "
            "head and upper body at center, eyes wide with fear, wings pressed tight. "
            "Broken palace columns blur behind; harsh white storm light bleeds from upper frame edge into void. "
            "One dragon only; no human anatomy."
        ),
        "negative": (
            "text, subtitles, watermark, duplicate Mir, human child, Lua, live-action, photorealistic, motion blur"
        ),
    },
    # --- SC01-001_05 Surface escape ---
    ("SC01-001_05", "SEG01"): {
        "start_state": "Young Mir strains upward through churning water toward storm-lit surface light.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Low-angle static underwater shot. Young Mir (CHAR_YOUNG_MIR) in lower-center, small body angled "
            "upward toward bright storm-lit surface above — fins spread, tail trailing, strained expression. "
            "Churning teal water and bubble trails; surface light a blurred bright ceiling. One dragon only."
        ),
        "negative": (
            "text, subtitles, watermark, duplicate Mir, human swimmer, wings on human, live-action, "
            "photorealistic, motion blur, Mir already on surface"
        ),
    },
    ("SC01-001_05", "SEG02"): {
        "start_state": "Storm night sea surface; a small blue glow rides in the waves, creature not yet identifiable.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Wide static shot at water surface level — rain, lightning flash upper left, white foam. "
            "Center waves carry a small isolated blue glow without a readable creature shape. "
            "No character faces or bodies identifiable. Coastal storm palette, black-blue sea."
        ),
        "negative": (
            "text, subtitles, watermark, clear dragon silhouette, human figure, duplicate glows, "
            "live-action, photorealistic, motion blur"
        ),
    },
    ("SC01-001_05", "SEG03"): {
        "start_state": "Wide horizon; distant blue glow drifts toward far coastal cliffs.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Extreme wide static horizon shot — storm night sea under dark clouds, faint coastal cliff silhouette "
            "far right. A tiny blue glow isolated in mid-distance waves left-of-center; identity ambiguous. "
            "Ominous quiet after lightning; no characters visible."
        ),
        "negative": (
            "text, subtitles, watermark, identifiable Mir face, human on shore, duplicate glows, "
            "live-action, photorealistic, motion blur"
        ),
    },
    # --- SC01-002_01 Village morning mockery ---
    ("SC01-002_01", "SEG01"): {
        "start_state": "Post-storm village morning on wet breakwater; three children in separate positions.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium-wide static eye-level shot on wet stone breakwater after storm. "
            "Lua (CHAR_LUA) stands center foreground at breakwater end, both hands on her fishing spear "
            "(PROP_LUA_SPEAR) — beige sleeveless tunic, high loose brown bun, white shell pendant, blue left wrist mark. "
            "Village Child 1 (CHAR_VILLAGE_CHILD_1) stands left midground three steps behind Lua — short tousled hair, "
            "dark charcoal sleeveless V-neck tunic, no basket. "
            "Village Child 2 (CHAR_VILLAGE_CHILD_2) stands right midground — high black ponytail with ochre tie, "
            "indigo-blue tunic with cream frill, woven shoulder basket at her right hip. "
            "Clear arm's-length gaps between all three silhouettes. Soft morning light from frame right; distant cave cliff far background."
        ),
        "negative": (
            "text, subtitles, watermark, identical children, swapped hairstyles, Lua with basket or gray tunic, "
            "Child 2 with shell pendant, spear held by children, fused bodies, duplicate faces, live-action, motion blur"
        ),
    },
    ("SC01-002_01", "SEG02"): {
        "start_state": "Lua stands feet apart on breakwater, spear gripped with both hands, eyes on fish shadow in shallow water.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot on wet breakwater. Lua (CHAR_LUA) center foreground, feet apart, fishing spear "
            "(PROP_LUA_SPEAR) raised over her right shoulder with both hands — amber-brown eyes narrowed at a small "
            "fish shadow visible in shallow water at her feet. Overconfident stiff stance. "
            "Village Child 1 (CHAR_VILLAGE_CHILD_1) left background watching; Village Child 2 (CHAR_VILLAGE_CHILD_2) "
            "right background with basket at hip. Three separate children; spear owned by Lua only."
        ),
        "negative": (
            "text, subtitles, watermark, spear in child hands, merged children, trait swap, Lua with ponytail, "
            "Child 1 with bun, live-action, motion blur, splash on face"
        ),
    },
    ("SC01-002_01", "SEG03"): {
        "start_state": "Lua holds spear overhead aimed downward; fish shadow still in water before the strike.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot. Lua (CHAR_LUA) center, spear (PROP_LUA_SPEAR) held high with both hands aimed "
            "down toward shallow water — focused serious expression, fish shadow still visible below. "
            "Village Child 1 (CHAR_VILLAGE_CHILD_1) left midground beginning to point; Village Child 2 (CHAR_VILLAGE_CHILD_2) "
            "right midground watching. No splash yet; dry face. Separate silhouettes."
        ),
        "negative": (
            "text, subtitles, watermark, wet face splash, missed strike completed, spear in wrong hands, "
            "identical children, live-action, motion blur"
        ),
    },
    ("SC01-002_01", "SEG04"): {
        "start_state": "Lua frozen embarrassed with wet face, spear in both hands; Village Child 1 points at empty water.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot toward three children. Lua (CHAR_LUA) center foreground frozen, both hands on "
            "spear (PROP_LUA_SPEAR) tip lowered, water droplets on face, embarrassed startled expression turning toward children. "
            "Village Child 1 (CHAR_VILLAGE_CHILD_1) left midground pointing right hand at empty rippling water, mischievous grin. "
            "Village Child 2 (CHAR_VILLAGE_CHILD_2) right midground, basket at hip, head tilted toward Lua. "
            "All three clearly separate; spear remains Lua's."
        ),
        "negative": (
            "text, subtitles, watermark, Korean subtitles, identical children, spear transfer, fused bodies, "
            "live-action, motion blur"
        ),
    },
    # --- SC01-002_02 Fisherman warning ---
    ("SC01-002_02", "SEG01"): {
        "start_state": "Lua sits in shallow water on breakwater edge, wet, gripping spear; off-screen children laughing.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot at wet breakwater edge. Lua (CHAR_LUA) in left foreground sitting in shallow water, "
            "gripping fishing spear (PROP_LUA_SPEAR) in both hands, wet hair strands on face, forced bravado expression. "
            "Empty midground — no fisherman yet; village shore and overturned boats background. "
            "Morning soft light; Lua alone visible with spear."
        ),
        "negative": (
            "text, subtitles, watermark, Old Fisherman present, spear not in Lua hands, duplicate Lua, "
            "live-action, motion blur"
        ),
    },
    ("SC01-002_02", "SEG02"): {
        "start_state": "Lua stands in shallows gripping spear, speaking with forced confidence.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot. Lua (CHAR_LUA) center in knee-deep shallows, fishing spear (PROP_LUA_SPEAR) vertical "
            "in both hands at chest height — defiant half-smile, wet beige tunic, blue wrist mark visible. "
            "Breakwater stones behind; Old Fisherman not yet in frame. Overcast morning bounce on wet stone."
        ),
        "negative": (
            "text, subtitles, watermark, fisherman in frame, spear dropped, duplicate Lua, live-action, motion blur"
        ),
    },
    ("SC01-002_02", "SEG03"): {
        "start_state": "Old Fisherman stands left midground; Lua straightens in shallows right foreground with spear.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium-wide static shot on breakwater shallows. Old Fisherman (CHAR_OLD_FISHERMAN) left midground — "
            "tall adult, gray beard, navy vest, calm stern face, one hand slightly raised in greeting. "
            "Lua (CHAR_LUA) right foreground waist-deep, spear (PROP_LUA_SPEAR) in both hands, straightened attentive posture, "
            "head turned toward fisherman. Two body lengths between them; clear height difference adult vs child."
        ),
        "negative": (
            "text, subtitles, watermark, Lua with beard, fisherman child-sized, spear in fisherman hands, "
            "trait exchange, fused bodies, live-action, motion blur"
        ),
    },
    ("SC01-002_02", "SEG04"): {
        "start_state": "Old Fisherman speaks sternly; Lua grips spear with hardened expression.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot. Old Fisherman (CHAR_OLD_FISHERMAN) left third, gray beard and vest, "
            "stern teaching expression directed toward Lua. "
            "Lua (CHAR_LUA) right foreground gripping fishing spear (PROP_LUA_SPEAR) with both hands at waist, "
            "jaw set, stubborn eyes — white shell pendant, blue wrist mark. "
            "Wet breakwater underfoot; separate silhouettes."
        ),
        "negative": (
            "text, subtitles, watermark, Korean subtitles, merged faces, child beard, Lua taller than fisherman, "
            "spear transfer, live-action, motion blur"
        ),
    },
    ("SC01-002_02", "SEG05"): {
        "start_state": "Old Fisherman gazes toward distant cliff cave; Lua silent with spear, listening.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium-wide static shot. Old Fisherman (CHAR_OLD_FISHERMAN) left profile gazing toward far cliff cave "
            "entrance visible background right — gray hair and beard, navy vest. "
            "Lua (CHAR_LUA) right foreground facing fisherman, spear (PROP_LUA_SPEAR) lowered in one hand, lips sealed, "
            "conflicted eyes. Cave cliff and calm sea horizon background."
        ),
        "negative": (
            "text, subtitles, watermark, Lua looking away from cave, fisherman missing, duplicate figures, "
            "live-action, motion blur"
        ),
    },
    ("SC01-002_02", "SEG06"): {
        "start_state": "Faint blue flicker in far cave; Lua's eyes widen, spear in hand.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot with depth. Far background right: coastal cliff cave mouth with one faint blue pulse glow. "
            "Lua (CHAR_LUA) right foreground close, eyes wide fixed on cave glow, fishing spear (PROP_LUA_SPEAR) "
            "gripped in both hands — high brown bun, shell pendant. Old Fisherman (CHAR_OLD_FISHERMAN) blurred left "
            "midground edge, turned toward cave. Decision instant frozen on Lua's face."
        ),
        "negative": (
            "text, subtitles, watermark, Lua running, cave glow absent, spear not in Lua hands, trait swap, "
            "live-action, motion blur"
        ),
    },
    # --- SC01-003_01 Cave entry ---
    ("SC01-003_01", "SEG01"): {
        "start_state": "Lua enters wet coastal cave with spear held forward.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Wide shot at cave entrance looking inward — Lua (CHAR_LUA) small in right third along center path, "
            "fishing spear (PROP_LUA_SPEAR) held forward in both hands — cautious wide eyes, beige tunic, high bun. "
            "Shallow seawater ripples across uneven rock center path; deep blue glow in tunnel center ahead. "
            "Damp stone walls with droplets; daylight hint behind camera."
        ),
        "negative": (
            "text, subtitles, watermark, Young Mir visible, spear not in Lua hands, duplicate Lua, "
            "live-action, motion blur"
        ),
    },
    ("SC01-003_01", "SEG02"): {
        "start_state": "Lua stands on wet rock in cave, spear angled toward shadows, afraid but forcing bravery.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Low-angle medium shot from wet rock floor. Lua (CHAR_LUA) center-left on wet rock viewed from below, "
            "spear (PROP_LUA_SPEAR) angled toward dark crevice right background — forced brave expression, tense shoulders. "
            "Reflective shallow water foreground; blue-teal ambient from crevice right."
        ),
        "negative": (
            "text, subtitles, watermark, Mir visible, spear dropped, duplicate Lua, live-action, motion blur"
        ),
    },
    ("SC01-003_01", "SEG03"): {
        "start_state": "Lua in cave calls toward shadows, spear lowered slightly, mouth open mid-call.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Over-the-shoulder shot from behind Lua left shoulder toward cave depth. Lua (CHAR_LUA) left foreground, "
            "back and shoulder toward camera, spear (PROP_LUA_SPEAR) in one hand pointed down, other hand cupped near mouth — "
            "calling expression toward shadows. Blue glow in distant tunnel; wet wall edge left foreground."
        ),
        "negative": (
            "text, subtitles, watermark, Korean text overlay, Mir in frame, spear missing, live-action, motion blur"
        ),
    },
    ("SC01-003_01", "SEG04"): {
        "start_state": "Lua freezes listening after calling; eyes wide toward crevice where a squeak came from.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close shot at crevice mouth. Lua (CHAR_LUA) center-left, body frozen mid-lean toward dark crevice right frame — "
            "eyes wide with curiosity, spear (PROP_LUA_SPEAR) forgotten at her side in one hand. "
            "Blue rim light on face from depth; cave water ripples at feet."
        ),
        "negative": (
            "text, subtitles, watermark, Mir fully revealed, duplicate Lua, live-action, motion blur"
        ),
    },
    # --- SC01-003_02 First sight of Mir ---
    ("SC01-003_02", "SEG01"): {
        "start_state": "Lua peers into crevice; Young Mir visible on wet stone at frame right.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Over-the-shoulder shot from behind Lua as she peers into crevice. Lua (CHAR_LUA) left foreground, "
            "back and shoulder toward camera, spear (PROP_LUA_SPEAR) lowered tip on wet stone — curious cautious face. "
            "Young Mir (CHAR_YOUNG_MIR) visible inside crevice ahead on wet rock — silver-blue scales, short horns, "
            "folded wings, half-open clear blue eyes, tail crystal dim. Separate species silhouettes."
        ),
        "negative": (
            "text, subtitles, watermark, Lua with wings, Mir in human clothes, merged bodies, duplicate figures, "
            "spear in Mir hands, live-action, motion blur"
        ),
    },
    ("SC01-003_02", "SEG02"): {
        "start_state": "Lua exhales shakily staring at Mir; spear resting on stone beside her.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Profile two-shot from lateral cave wall — side silhouettes. Lua (CHAR_LUA) left profile kneeling, "
            "shoulders slack with shaky exhale, wide brown eyes fixed on Mir — spear (PROP_LUA_SPEAR) on wet stone near foot. "
            "Young Mir (CHAR_YOUNG_MIR) right profile on stone, wings folded, vulnerable posture. Clear gap between bodies."
        ),
        "negative": (
            "text, subtitles, watermark, Korean subtitles, trait exchange, Lua scaled, Mir human, live-action, motion blur"
        ),
    },
    ("SC01-003_02", "SEG03"): {
        "start_state": "Lua whispers toward Mir, lips parted on first word, spear on ground.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close two-shot at whisper distance. Lua (CHAR_LUA) left three-quarter view, lips parted whispering, "
            "one hand empty and hovering — spear (PROP_LUA_SPEAR) on ground left-bottom. "
            "Young Mir (CHAR_YOUNG_MIR) right close midground, head tilted, frightened intelligent blue eyes toward Lua. "
            "Separate silhouettes; soft crevice stone background."
        ),
        "negative": (
            "text, subtitles, watermark, dialogue text, merged anatomy, wings on Lua, live-action, motion blur"
        ),
    },
    ("SC01-003_02", "SEG04"): {
        "start_state": "Young Mir opens wide eyes toward Lua; Lua breath held in awe.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Low-angle medium shot at Young Mir's eye level — Mir foreground emphasis. "
            "Young Mir (CHAR_YOUNG_MIR) right foreground larger in frame, large clear blue eyes open wide toward Lua — "
            "small horns, silver-blue scales, folded wings. "
            "Lua (CHAR_LUA) left background smaller, lips slightly parted, awed expression, hands empty. "
            "Cave blue-teal light; two distinct subjects."
        ),
        "negative": (
            "text, subtitles, watermark, identical eyes on both, human Mir, dragon Lua, live-action, motion blur"
        ),
    },
    ("SC01-003_02", "SEG05"): {
        "start_state": "Lua extends open human hand toward Mir; Mir weak on stone, not yet touching.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Close shot on extended hand zone between Lua and Mir. Lua (CHAR_LUA) left lower frame, open human palm "
            "extended low toward Mir — worried gentle face, blue wrist mark visible, no spear in hand. "
            "Young Mir (CHAR_YOUNG_MIR) right upper frame on wet stone leaning back weakly, wings tight, eyes on her hand. "
            "Clear space between palm and dragon snout; no contact yet."
        ),
        "negative": (
            "text, subtitles, watermark, hand merged with dragon, wings on Lua, Mir human child, contact completed, "
            "live-action, motion blur"
        ),
    },
    # --- SC01-003_03 Kneel and reassurance ---
    ("SC01-003_03", "SEG01"): {
        "start_state": "Lua kneels left with spear set down; Mir rests against stone right.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium-wide static two-shot. Lua (CHAR_LUA) left foreground kneeling on wet rock, fishing spear (PROP_LUA_SPEAR) "
            "laid flat on stone beside her — human body fully visible, beige tunic. "
            "Young Mir (CHAR_YOUNG_MIR) right midground resting against damp stone, separate dragon silhouette with folded wings. "
            "Arm's-length empty space between them; cave water ripples foreground."
        ),
        "negative": (
            "text, subtitles, watermark, spear in Mir hands, kneeling dragon, standing merged figures, "
            "live-action, motion blur"
        ),
    },
    ("SC01-003_03", "SEG02"): {
        "start_state": "Lua extends open hand low toward Mir; Mir watches with wide eyes, wings close.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot. Lua (CHAR_LUA) left kneeling, open human hand extended low at Mir's eye level — "
            "relaxed fingers, soft expression. Young Mir (CHAR_YOUNG_MIR) right, small wings pressed to scaled sides, "
            "blue eyes fixed on her fingers. No touch; separate bodies and species."
        ),
        "negative": (
            "text, subtitles, watermark, dragon wings on Lua, human clothing on Mir, fused hands, live-action, motion blur"
        ),
    },
    ("SC01-003_03", "SEG03"): {
        "start_state": "Lua and Mir in medium two-shot; Lua speaks softly with hand extended.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot framing both full silhouettes. Lua (CHAR_LUA) left kneeling, hand extended palm open, "
            "gentle reassuring expression directed at Mir. Young Mir (CHAR_YOUNG_MIR) right on wet stone, "
            "body still, watching her fingers — wings folded. Cave blue ambient; clear separation between them."
        ),
        "negative": (
            "text, subtitles, watermark, Korean captions, merged silhouettes, trait transfer, live-action, motion blur"
        ),
    },
    ("SC01-003_03", "SEG04"): {
        "start_state": "Lua touches her own stomach; Mir still watching from stone without approaching.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot. Lua (CHAR_LUA) left, one hand on her own stomach, other hand lowered — "
            "half-smile explaining expression toward Mir. Young Mir (CHAR_YOUNG_MIR) right on stone, unchanged distance, "
            "eyes on Lua. Empty space between; Lua fully human, Mir fully dragon."
        ),
        "negative": (
            "text, subtitles, watermark, Mir moved closer, Lua dragon traits, live-action, motion blur"
        ),
    },
    # --- SC01-003_04 Contact ---
    ("SC01-003_04", "SEG01"): {
        "start_state": "Mir shifted slightly forward on stone; Lua's steady open hand waits.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close static two-shot on hands zone. Young Mir (CHAR_YOUNG_MIR) right, snout a few centimeters from "
            "Lua's open index finger — body shifted minimally forward on wet stone, wings folded. "
            "Lua (CHAR_LUA) left, human hand steady palm-up, fingers relaxed. No mouth contact yet; separate anatomy clear."
        ),
        "negative": (
            "text, subtitles, watermark, biting contact, blood, fused fingers, dragon arm on Lua, live-action, motion blur"
        ),
    },
    ("SC01-003_04", "SEG02"): {
        "start_state": "Mir's mouth closed weakly on tip of Lua's index finger; Lua flinches.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Close static shot on contact point. Young Mir's (CHAR_YOUNG_MIR) small dragon mouth gently closed on tip of "
            "Lua's (CHAR_LUA) human index finger — clinging not biting; scaled head separate from human hand anatomy. "
            "Lua's face visible upper left, flinching surprise expression. One dragon head, one human hand; no fusion."
        ),
        "negative": (
            "text, subtitles, watermark, severed finger, violent bite, merged mouth-hand, extra limbs, live-action, motion blur"
        ),
    },
    # --- SC01-003_05 Blood and marks ---
    ("SC01-003_05", "SEG01"): {
        "start_state": "One blood drop forms on Lua's fingertip at Mir contact point.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Close static shot. Lua's (CHAR_LUA) human hand center frame, one small blood drop forming on index fingertip — "
            "skin clearly human. Young Mir (CHAR_YOUNG_MIR) lower right, mouth just released, separate scaled snout. "
            "Wet cave stone background blur; no merged tissue."
        ),
        "negative": (
            "text, subtitles, watermark, excessive blood, fused hand and snout, wings on hand, live-action, motion blur"
        ),
    },
    ("SC01-003_05", "SEG02"): {
        "start_state": "Blood drop suspended above broken scale on Mir's shoulder; ripples starting in cave water.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Close static shot. One blood drop suspended mid-air above a broken scale on Young Mir's (CHAR_YOUNG_MIR) "
            "left shoulder — dragon scales silver-blue. Lua's (CHAR_LUA) human hand withdrawn upper left edge, separate. "
            "Cave water ripples concentric at bottom frame; blue mark not yet on wrist."
        ),
        "negative": (
            "text, subtitles, watermark, blood on Lua chest, human scales, merged bodies, live-action, motion blur"
        ),
    },
    ("SC01-003_05", "SEG03"): {
        "start_state": "Blue mark glows on Lua's wrist; Mir's chest mark glows on his scales; bodies separate.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot. Lua (CHAR_LUA) left, blue mark glowing on left wrist only — fully human, no wings. "
            "Young Mir (CHAR_YOUNG_MIR) right, crown-shaped chest wave mark glowing on scales only — fully dragon. "
            "Arm's-length gap; cave water between wet stones. Two distinct species."
        ),
        "negative": (
            "text, subtitles, watermark, chest mark on Lua, wrist mark on Mir, fused glow, trait exchange, "
            "live-action, motion blur"
        ),
    },
    # --- SC01-003_06 Resonance line ---
    ("SC01-003_06", "SEG01"): {
        "start_state": "Thin blue light line connects Lua's wrist mark and Mir's chest mark across open space.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot in cave. Lua (CHAR_LUA) left kneeling, left wrist forward with blue mark; "
            "Young Mir (CHAR_YOUNG_MIR) right on stone with glowing chest mark. "
            "One thin horizontal blue light line spans the gap between marks — silhouettes remain separate, not merged."
        ),
        "negative": (
            "text, subtitles, watermark, bodies fused, single silhouette, wings on Lua, human Mir, live-action, motion blur"
        ),
    },
    ("SC01-003_06", "SEG02"): {
        "start_state": "Resonance line active; Lua human and Mir dragon remain fully separate.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot. Lua (CHAR_LUA) left — human child, beige tunic, high bun, blue wrist glow, no dragon parts. "
            "Young Mir (CHAR_YOUNG_MIR) right — small dragon with horns, wings, tail crystal, chest glow, no human clothes. "
            "Blue connection line between marks; cave background; no deformation."
        ),
        "negative": (
            "text, subtitles, watermark, anatomy transfer, duplicate Lua, duplicate Mir, live-action, motion blur"
        ),
    },
    # --- SC01-003_07 Vision (Mir only) ---
    ("SC01-003_07", "SEG01"): {
        "start_state": "Surreal collapsed dragon palace vision space; no human Lua present.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Wide static shot with slight dutch tilt — surreal vision of collapsed dragon palace. "
            "Broken gate and ruined hall columns; enormous sleeping dragon shadow silhouettes without faces. "
            "Open central void space; floating debris. Desaturated blue-grey memory palette. No human characters."
        ),
        "negative": (
            "text, subtitles, watermark, Lua, human child, readable dragon faces, live-action, motion blur"
        ),
    },
    ("SC01-003_07", "SEG02"): {
        "start_state": "Black roots wrap a fading blue heart-stone at ruined hall center; no Lua.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot on vision hall center. Black root shapes wrapped around a fading blue heart-stone on cracked "
            "palace floor — ruined columns background, sleeping dragon shadows at edges. "
            "Cold blue memory light; no human figures anywhere."
        ),
        "negative": (
            "text, subtitles, watermark, human characters, Lua, Young Mir full body in foreground, live-action, motion blur"
        ),
    },
    ("SC01-003_07", "SEG03"): {
        "start_state": "Nightmare memory abyss with sleeping dragon silhouettes; no physical contact shown.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Wide static shot down black abyss in vision space — sleeping dragon silhouettes curled on ledges without faces, "
            "broken columns receding into void fog. Open drifting central space; desaturated cold blue-black palette. "
            "No Lua, no Young Mir body in frame."
        ),
        "negative": (
            "text, subtitles, watermark, human child, contact scene, readable faces on shadow dragons, live-action, motion blur"
        ),
    },
    # --- SC01-003_08 Return to cave ---
    ("SC01-003_08", "SEG01"): {
        "start_state": "Lua alone in cave gasps staring at blue mark on her wrist.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close shot on glowing wrist mark. Lua (CHAR_LUA) fills center-left frame — human child only, "
            "gasping mouth open, eyes fixed on blue mark glowing on raised left wrist before her face. "
            "Beige tunic, high bun, shell pendant. No dragon anatomy on Lua. Wet cave walls blur background; "
            "Young Mir not visible in this frame."
        ),
        "negative": (
            "text, subtitles, watermark, Lua with wings horns tail, duplicate Lua, live-action, motion blur"
        ),
    },
    ("SC01-003_08", "SEG02"): {
        "start_state": "Mir whimpers on wet stone right; Lua stares at wrist; connection light fading.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium-wide two-shot pulled back — full silhouettes. Lua (CHAR_LUA) left midground kneeling, "
            "wrist mark dimming, stunned eyes downward. "
            "Young Mir (CHAR_YOUNG_MIR) right midground on wet stone whimpering — small dragon, folded wings. "
            "Faint fading blue line between them; arm's-length gap; more cave interior visible."
        ),
        "negative": (
            "text, subtitles, watermark, merged bodies, human Mir, dragon Lua, live-action, motion blur"
        ),
    },
    # --- SC01-003_09 Video-first cinematic anchors ---
    ("SC01-003_09", "SEG01"): {
        "start_state": "Lua kneels beside Mir in the exit-facing composition, breathless and studying her wrist mark.",
        "prompt": (
            "Cinematic keyframe from a premium stylized 3D animated feature, widescreen 16:9. Grounded virtual 35mm lens, "
            "eye-level medium-wide opening with layered cave depth. Lua kneels left midground studying her raised marked wrist; "
            "Young Mir rests separately right midground with wings tucked. Dark wet foreground ledge lower left, blue crevice glow "
            "background left and distant daylight rim far right. Open space supports a clockwise camera path."
        ),
        "negative": (
            "text, subtitles, watermark, flat centered poster, symmetrical lineup, overhead view, reversed light direction, "
            "merged bodies, identity exchange, live-action, motion blur"
        ),
    },
    ("SC01-003_09", "SEG02"): {
        "start_state": "Lua is seen from the mouth-side interior angle, startled toward the entrance; Mir watches from the same patch.",
        "prompt": (
            "Cinematic keyframe from a premium stylized 3D animated feature, widescreen 16:9. Grounded virtual 35mm lens, "
            "eye-level mouth-side interior-facing medium composition. Wet foreground rock edge; Lua kneels frame right in "
            "three-quarter rear profile, head turned toward the off-frame mouth; Young Mir remains frame left. Deep blue alcove "
            "background left and soft daylight rim from behind camera."
        ),
        "negative": (
            "text, subtitles, watermark, flat centered poster, overhead view, bright mouth visible, village person visible, "
            "reversed positions, merged bodies, live-action, motion blur"
        ),
    },
    ("SC01-003_09", "SEG03"): {
        "start_state": "Lua kneels in a three-quarter rear-side view, opening the cloth as Mir reaches her knees.",
        "prompt": (
            "Cinematic keyframe from a premium stylized 3D animated feature, widescreen 16:9. Grounded virtual 35mm lens, "
            "eye-level three-quarter rear-side medium composition. Lua kneels frame right opening loose beige cloth diagonally "
            "across the lower foreground; Young Mir is frame left close to her knees, crawling weakly and not wrapped. Blue "
            "crevice glow left, faint daylight rim far right, layered depth for a cloth-edge camera passage."
        ),
        "negative": (
            "text, subtitles, watermark, flat centered poster, overhead view, high-angle shot, Mir already wrapped, Lua standing, "
            "cloth covering faces, merged bodies, live-action, motion blur"
        ),
    },
    ("SC01-003_09", "SEG04"): {
        "start_state": "Lua stands on the exit axis with wrapped Mir held securely, ready to walk toward daylight.",
        "prompt": (
            "Cinematic keyframe from a premium stylized 3D animated feature, widescreen 16:9. Grounded virtual 35mm lens, "
            "eye-level medium-wide rear tracking start. Lua stands on the right third holding cloth-wrapped Young Mir; only a "
            "small tail crystal peeks out. Dark foreground rocks frame both sides, reflective path leads to bright cave mouth "
            "center-ahead, and cool blue shadow recedes left."
        ),
        "negative": (
            "text, subtitles, watermark, flat centered poster, front-facing Lua, Mir unwrapped, exposed wings, blocked path, "
            "reversed light direction, merged bodies, live-action, motion blur"
        ),
    },
    # --- SC01-004_01 Arrival at house ---
    ("SC01-004_01", "SEG01"): {
        "start_state": "Lua closes house door listening; Mir peeks from cloth at frame right.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static interior shot. Lua (CHAR_LUA) left foreground at wooden door, one hand on latch, ear turned "
            "listening — beige tunic, high bun, shell pendant. Young Mir (CHAR_YOUNG_MIR) right midground peering from "
            "wrapped cloth bundle on floor — one small horn and blue eye visible, dragon only. "
            "Humble coastal house day interior: wooden table, water basin side right, warm window light."
        ),
        "negative": (
            "text, subtitles, watermark, Mir human child, Lua dragon parts, live-action, motion blur"
        ),
    },
    ("SC01-004_01", "SEG02"): {
        "start_state": "Lua stares at Mir with disbelief; Mir peeking from cloth at right.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot in house day interior. Lua (CHAR_LUA) left center, crouched, disbelieving stare toward Mir — "
            "amber eyes wide, blue wrist mark. Young Mir (CHAR_YOUNG_MIR) right in partial cloth wrap on wooden floor, "
            "small dragon face visible. Warm daylight from window frame right; basin background."
        ),
        "negative": (
            "text, subtitles, watermark, Korean captions, merged bodies, trait swap, live-action, motion blur"
        ),
    },
    ("SC01-004_01", "SEG03"): {
        "start_state": "Lua lowers Mir into shallow water basin; Mir half-submerged.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot. Shallow water basin right midground — Young Mir (CHAR_YOUNG_MIR) half-submerged, "
            "silver-blue scales glistening, relaxed eyes at water surface. Lua (CHAR_LUA) left leaning over basin edge, "
            "both human hands on basin rim, amazed expression. House table and shells background left."
        ),
        "negative": (
            "text, subtitles, watermark, Lua in basin, Mir standing human, live-action, motion blur"
        ),
    },
    ("SC01-004_01", "SEG04"): {
        "start_state": "Mir relaxed in basin; Lua kneels beside watching with tired sigh.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot. Young Mir (CHAR_YOUNG_MIR) in basin center-right, body floating calm in shallow water, "
            "crown chest mark visible at waterline. Lua (CHAR_LUA) left kneeling beside basin, chin on one fist, "
            "wistful tired expression looking at Mir. Warm day interior lighting."
        ),
        "negative": (
            "text, subtitles, watermark, Korean text, human Mir, dragon Lua, live-action, motion blur"
        ),
    },
    # --- SC01-004_02 Feeding and shell ---
    ("SC01-004_02", "SEG01"): {
        "start_state": "Lua holds dried fish toward Mir in basin; Mir calm in water.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static interior shot. Lua (CHAR_LUA) left holding dried fish in both human hands extended toward basin — "
            "gentle offering posture. Young Mir (CHAR_YOUNG_MIR) in shallow basin right, calm at water surface, eyes on fish. "
            "Wooden table with scattered shells and fish background; warm daylight."
        ),
        "negative": (
            "text, subtitles, watermark, fish fused to hand, Mir human, live-action, motion blur"
        ),
    },
    ("SC01-004_02", "SEG02"): {
        "start_state": "Lua offers fish; Mir recoils in basin with disgusted expression.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot. Lua (CHAR_LUA) left with dried fish extended, flustered eyebrows. "
            "Young Mir (CHAR_YOUNG_MIR) in basin right recoiled backward — scaled snout wrinkled away from fish, splash ripples. "
            "Separate reactions; comfort shell still on table background center."
        ),
        "negative": (
            "text, subtitles, watermark, Mir eating fish, Korean subtitles, live-action, motion blur"
        ),
    },
    ("SC01-004_02", "SEG03"): {
        "start_state": "Lua holds fish confused; Mir turns body toward pale cream shell on table.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot. Lua (CHAR_LUA) left with fish lowered, puzzled frown. "
            "Young Mir (CHAR_YOUNG_MIR) climbing basin edge toward wooden table center where one pale cream coastal comfort shell "
            "rests among scattered shells — dragon body oriented toward shell, not yet touching. "
            "Interactive prop: shell on table, owned by scene not worn by any character."
        ),
        "negative": (
            "text, subtitles, watermark, shell worn as clothing, Mir licking shell already, live-action, motion blur"
        ),
    },
    ("SC01-004_02", "SEG04"): {
        "start_state": "Mir reaches pale cream shell on table; Lua deadpan beside basin.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot. Young Mir (CHAR_YOUNG_MIR) on table edge center, both small limbs reaching toward "
            "pale cream comfort shell — snout inches from shell, eager expression. Lua (CHAR_LUA) left at basin rim, "
            "deadpan flat expression watching. Warm house interior; shell separate object on table."
        ),
        "negative": (
            "text, subtitles, watermark, shell merged with scales, human Mir, live-action, motion blur"
        ),
    },
    # --- SC01-004_03 Imagined rejection ---
    ("SC01-004_03", "SEG01"): {
        "start_state": "Lua wraps cloth over blue wrist mark; Mir watches from basin.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static interior day shot. Lua (CHAR_LUA) left foreground wrapping cloth over left wrist mark — "
            "worried downward gaze. Young Mir (CHAR_YOUNG_MIR) in basin right background watching her, still water. "
            "Normal warm house lighting; literal interior not yet overlaid."
        ),
        "negative": (
            "text, subtitles, watermark, desaturated overlay, ghost village, live-action, motion blur"
        ),
    },
    ("SC01-004_03", "SEG02"): {
        "start_state": "Desaturated overlay with ghostly village shore at edges; Mir flinches in basin.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot with desaturated fearful overlay. Lua (CHAR_LUA) center-left, cloth on wrist, tense shoulders. "
            "Young Mir (CHAR_YOUNG_MIR) in basin right flinching — wings tight. "
            "Ghostly blurred village shore and baskets at frame edges; no adult faces visible. Cold grey-blue tint over house floor."
        ),
        "negative": (
            "text, subtitles, watermark, readable adult faces, Korean text, normal warm lighting, live-action, motion blur"
        ),
    },
    ("SC01-004_03", "SEG03"): {
        "start_state": "Lua blocks Mir protectively with arms extended; overlay still partially visible.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot. Lua (CHAR_LUA) center foreground arms spread blocking toward basin, fierce protective glare — "
            "human body shielding Young Mir (CHAR_YOUNG_MIR) in basin right behind her arm. "
            "Fading desaturated edge overlay; warm house light returning center."
        ),
        "negative": (
            "text, subtitles, watermark, Lua with dragon wings, Mir in front of Lua, live-action, motion blur"
        ),
    },
    ("SC01-004_03", "SEG04"): {
        "start_state": "Normal house day light; Lua protective over Mir; Mir looks up trustingly.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot. Lua (CHAR_LUA) left standing protective, one arm still extended toward Mir — "
            "soft resolved expression down toward him. Young Mir (CHAR_YOUNG_MIR) in basin right looking up, trusting blue eyes. "
            "Warm daylight restored; no overlay."
        ),
        "negative": (
            "text, subtitles, watermark, overlay remains, trait exchange, live-action, motion blur"
        ),
    },
    # --- SC01-004_04 Promise and droplet ---
    ("SC01-004_04", "SEG01"): {
        "start_state": "Lua clears throat with mock-adult posture; Mir tilts head in basin.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot house interior. Lua (CHAR_LUA) left standing straight with mock-serious adult posture, "
            "one finger raised — high bun, shell pendant. Young Mir (CHAR_YOUNG_MIR) in basin right, head tilted curious, "
            "water surface at chest mark height. Warm day light."
        ),
        "negative": (
            "text, subtitles, watermark, Korean captions, merged figures, live-action, motion blur"
        ),
    },
    ("SC01-004_04", "SEG02"): {
        "start_state": "Lua points at water jar on table; Mir watches from basin.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot. Lua (CHAR_LUA) left pointing right hand at clay water jar on wooden table center — "
            "matter-of-fact expression. Young Mir (CHAR_YOUNG_MIR) in basin right background watching jar direction. "
            "Water jar environment prop on table; not held by Mir."
        ),
        "negative": (
            "text, subtitles, watermark, jar in Mir claws, Lua dragon traits, live-action, motion blur"
        ),
    },
    ("SC01-004_04", "SEG03"): {
        "start_state": "Lua gestures explaining; Mir in basin with tilted head watching.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static two-shot. Lua (CHAR_LUA) left mid-gesture with open palm toward table objects — "
            "explaining expression. Young Mir (CHAR_YOUNG_MIR) in basin right, head tilted, attentive blue eyes. "
            "Table with water jar and shells between them spatially."
        ),
        "negative": (
            "text, subtitles, watermark, dialogue subtitles, trait swap, live-action, motion blur"
        ),
    },
    ("SC01-004_04", "SEG04"): {
        "start_state": "Mir opens small dragon mouth; Lua leans hopeful; no droplet yet.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close static two-shot. Young Mir (CHAR_YOUNG_MIR) in basin center-right, small dragon mouth open empty — "
            "expectant posture. Lua (CHAR_LUA) left leaning forward hopeful, hands on basin rim. "
            "No water droplet visible yet; warm interior."
        ),
        "negative": (
            "text, subtitles, watermark, droplet on forehead already, human mouth on Mir, live-action, motion blur"
        ),
    },
    ("SC01-004_04", "SEG05"): {
        "start_state": "One tiny water droplet floats between Mir's open mouth and Lua's forehead.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close static shot. One tiny water droplet suspended mid-air between Young Mir (CHAR_YOUNG_MIR) "
            "in basin lower right with open dragon mouth and Lua's (CHAR_LUA) forehead upper left — droplet not yet touching skin. "
            "Lua hopeful expression; Mir chest mark and Lua wrist mark beginning faint blue glow. Separate bodies."
        ),
        "negative": (
            "text, subtitles, watermark, droplet already on forehead, fused faces, wings on Lua, live-action, motion blur"
        ),
    },
    # --- SC01-005_01 Night sleep ---
    ("SC01-005_01", "SEG01"): {
        "start_state": "Night house interior; Lua asleep in bed; Mir curled in basin.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium-wide static interior night shot. Lua (CHAR_LUA) asleep in wooden bed left background — beige tunic, "
            "blanket to chin, high bun loose on pillow. Young Mir (CHAR_YOUNG_MIR) curled in shallow water basin right foreground — "
            "small dragon ball shape, fin wings folded. Dim warm interior fill, cool blue moonlight from window far right."
        ),
        "negative": (
            "text, subtitles, watermark, both awake, Mir in bed, Lua in basin, live-action, motion blur"
        ),
    },
    ("SC01-005_01", "SEG02"): {
        "start_state": "Faint synchronized glow from Mir chest mark and Lua wrist under cloth.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static night interior. Lua (CHAR_LUA) sleeping bed left, faint blue glow through cloth at left wrist. "
            "Young Mir (CHAR_YOUNG_MIR) in basin right, matching faint blue glow at chest wave mark — synchronized brightness frozen. "
            "Low warm fill, moonlight window edge."
        ),
        "negative": (
            "text, subtitles, watermark, bright blinding glow, merged sleeping bodies, live-action, motion blur"
        ),
    },
    ("SC01-005_01", "SEG03"): {
        "start_state": "Mir trembles in sleep; Lua's brow furrowed still asleep.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close static night shot split focus. Young Mir (CHAR_YOUNG_MIR) in basin foreground trembling in sleep — "
            "wings twitching. Lua (CHAR_LUA) bed background, eyes closed but brow furrowed in shared disturbance. "
            "Moonlit window edge; quiet house."
        ),
        "negative": (
            "text, subtitles, watermark, both sitting awake, dream overlay visible, live-action, motion blur"
        ),
    },
    # --- SC01-005_02 Nightmare dream ---
    ("SC01-005_02", "SEG01"): {
        "start_state": "Dream palace ruins; Mir small before fading blue heart-stone.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Wide static dream shot. Ruined dragon palace hall — black roots wrapped around fading blue heart-stone center. "
            "Young Mir (CHAR_YOUNG_MIR) small figure foreground center facing heart-stone, back partly toward camera — "
            "silver-blue dragon, horns and tail crystal visible. No human Lua. Cold blue-black nightmare palette."
        ),
        "negative": (
            "text, subtitles, watermark, Lua present, human Mir, live-action, photorealistic, motion blur"
        ),
    },
    ("SC01-005_02", "SEG02"): {
        "start_state": "Enormous prince-dragon shadow silhouette behind small Mir.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static dream shot. Young Mir (CHAR_YOUNG_MIR) small in lower center foreground, head turned slightly upward. "
            "Behind him filling upper frame: enormous prince-dragon shadow silhouette with crown-like horn curve and long body — "
            "no detailed face, silhouette only. Broken hall columns at sides; desaturated blue void."
        ),
        "negative": (
            "text, subtitles, watermark, detailed prince face, human shadow, Lua, live-action, motion blur"
        ),
    },
    ("SC01-005_02", "SEG03"): {
        "start_state": "Mir shudders before prince-dragon shadow; no visible speaker.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static dream shot. Young Mir (CHAR_YOUNG_MIR) center foreground shuddering — wings pulled in, eyes squeezed. "
            "Prince-dragon shadow looms background; no mouth or speaker visible anywhere. "
            "Cracked heart-stone glow dim; cold nightmare light."
        ),
        "negative": (
            "text, subtitles, watermark, visible speaking mouth, Korean text, human Mir, live-action, motion blur"
        ),
    },
    ("SC01-005_02", "SEG04"): {
        "start_state": "Mir trembles violently as dream fractures toward reality light.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close static dream shot. Young Mir (CHAR_YOUNG_MIR) center, violent tremble posture frozen — "
            "eyes wide, mouth open silent. Dream palace cracking with white reality light intruding from upper frame edge; "
            "shadow silhouette fragmenting. One dragon only."
        ),
        "negative": (
            "text, subtitles, watermark, Lua awake in frame, human child, live-action, motion blur"
        ),
    },
    # --- SC01-005_03 Nightmare wake ---
    ("SC01-005_03", "SEG01"): {
        "start_state": "Mir shakes in basin; Lua jolts awake in bed.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static night interior. Young Mir (CHAR_YOUNG_MIR) in basin right foreground shaking — water rippling. "
            "Lua (CHAR_LUA) bed left background sitting up sudden, blanket fallen, startled eyes — human only. "
            "Moonlight window cool blue on basin."
        ),
        "negative": (
            "text, subtitles, watermark, Lua in basin, Mir in bed, live-action, motion blur"
        ),
    },
    ("SC01-005_03", "SEG02"): {
        "start_state": "Lua holds Mir in her arms standing beside basin.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static night shot. Lua (CHAR_LUA) center standing, both human arms cradling Young Mir (CHAR_YOUNG_MIR) against "
            "beige tunic chest — Mir small dragon body fully separate, wings against her arms, reassuring Lua expression down. "
            "Empty basin behind; warm-cool mixed night lighting."
        ),
        "negative": (
            "text, subtitles, watermark, merged embrace anatomy, wings on Lua, human Mir, live-action, motion blur"
        ),
    },
    ("SC01-005_03", "SEG03"): {
        "start_state": "Lua clutches her chest feeling foreign dread; still holding Mir.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close static shot. Lua (CHAR_LUA) center, one arm holding Young Mir (CHAR_YOUNG_MIR) against hip, "
            "other human hand clutched to her own chest — frightened wide eyes staring inward. "
            "Mir's dragon head visible at lower frame, separate body. Night interior shadows."
        ),
        "negative": (
            "text, subtitles, watermark, chest claw on Lua from Mir wrongly, fused torsos, live-action, motion blur"
        ),
    },
    ("SC01-005_03", "SEG04"): {
        "start_state": "Lua holds Mir tighter; Mir licks Lua wrist mark softly glowing.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static night interior. Lua (CHAR_LUA) left holding Young Mir (CHAR_YOUNG_MIR) in both arms — gentle relieved smile. "
            "Mir's small snout touching Lua's left wrist mark with soft blue glow at contact point only. "
            "Window dark sea side background right hint; separate species."
        ),
        "negative": (
            "text, subtitles, watermark, mark on Mir wrist, Lua scaled arm, live-action, motion blur"
        ),
    },
    # --- SC01-005_04 Jellyfish cliffhanger ---
    ("SC01-005_04", "SEG01"): {
        "start_state": "Lua at window; unnaturally still empty night sea outside.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static interior night shot toward window. Lua (CHAR_LUA) right foreground profile approaching window — "
            "beige tunic, high bun, cautious eyes. Through window: dark calm empty sea surface, no creatures, minimal frame edge. "
            "Young Mir (CHAR_YOUNG_MIR) not yet in arms; basin behind left. Cool blue moonlight on sea."
        ),
        "negative": (
            "text, subtitles, watermark, jellyfish in sea background, duplicate sea creatures, live-action, motion blur"
        ),
    },
    ("SC01-005_04", "SEG02"): {
        "start_state": "Black Jellyfish floats above still sea; Lua at window with Mir in arms.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static shot through window composition. Black Jellyfish (ENTITY_BLACK_JELLYFISH) centered outside over dark sea — "
            "semi-transparent dark bell with ink smoke inside, long tentacles below surface; single entity not in background plate duplicate. "
            "Lua (CHAR_LUA) lower right interior holding Young Mir (CHAR_YOUNG_MIR) in arms, both facing window — Mir growling low expression. "
            "Empty sea elsewhere; cool moonlight."
        ),
        "negative": (
            "text, subtitles, watermark, duplicate jellyfish, jellyfish in background plate repetition, "
            "Mir human, Lua wings, live-action, motion blur"
        ),
    },
    ("SC01-005_04", "SEG03"): {
        "start_state": "Lua protective arm around Mir at window, whispering toward jellyfish.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium close static interior window shot. Lua (CHAR_LUA) left-center, one protective arm wrapped around Young Mir "
            "(CHAR_YOUNG_MIR) held at chest — tense lips parted whisper, eyes on sea. Black Jellyfish (ENTITY_BLACK_JELLYFISH) visible "
            "outside upper center through glass, tentacles trailing. Mir separate dragon body under her arm."
        ),
        "negative": (
            "text, subtitles, watermark, Korean subtitles, merged Lua-Mir, jellyfish inside room, live-action, motion blur"
        ),
    },
    ("SC01-005_04", "SEG04"): {
        "start_state": "Marks flash on Mir chest and Lua wrist; jellyfish oriented toward house.",
        "prompt": (
            "High-quality stylized feature-film animation still, 16:9, 1280x704. "
            "Medium static window shot. Lua (CHAR_LUA) right foreground holding Young Mir (CHAR_YOUNG_MIR) — wrist mark bright blue; "
            "Mir chest mark matching glow visible on dragon body. Outside: Black Jellyfish (ENTITY_BLACK_JELLYFISH) bell oriented toward "
            "house window, tentacles spread below dark still sea. Ominous cool palette; no fade overlay."
        ),
        "negative": (
            "text, subtitles, watermark, fade to black bar, duplicate jellyfish, trait exchange, live-action, motion blur"
        ),
    },
}
