#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from msr_sequence_v2 import PROMPT_STRATEGY, WORKFLOW, compile_global_prompt

PROJECT_ID = "RaisingaDragonSeason01_EP01_MSR_CONTINUITY_V1"
PROJECT_TITLE = "용 키우기 EP01 — MSR 연속 생성 V1"
SOURCE = "RaisingaDragonSeason01/Raising a Dragon.md"
STYLE = (
    "Premium stylized 3D ocean-fantasy animation with tactile coastal materials, "
    "expressive feature-film acting, coherent spatial continuity and cinematic 16:9 composition."
)
DREAM_STYLE = (
    "Premium stylized 3D ocean-fantasy animation with a dark submerged-memory atmosphere, "
    "coherent spatial continuity and cinematic 16:9 composition."
)
NEGATIVE = (
    "split screen, comic panels, collage, duplicated character, merged identities, extra limbs, "
    "swapped clothing, floating prop, text, subtitle, watermark, flat poster pose"
)

CHARACTERS = {
    "lua": ("Lua.png", "Lua, a small human coastal girl with sun-browned skin, messy light-brown hair, large brown eyes, a short worn sleeveless beige tunic, rope belt and shell ornaments; human anatomy only."),
    "mir": ("YoungMir.png", "Young Mir is a DRAGON hatchling, never a human baby or child: a small blue-silver sea dragon with short dark horns, fin-like wings, bright blue eyes, a teardrop crystal at the tail tip and a faint crown-wave chest mark. His nose-to-tail-base body length is approximately Lua's torso length and he fits completely inside the shallow water bowl; preserve dragon anatomy and this scale."),
    "child1": ("villageChild01.png", "Village Child 1, the coastal village boy shown in the reference sheet; preserve his exact face, short hair, clothing, age and human anatomy, visually distinct from every other village child."),
    "child2": ("village_child_2.png", "Village Child 2, the coastal village girl shown in the reference sheet with tied hair and her woven shoulder basket; preserve her exact face, hair, clothing, age and human anatomy, visually distinct from every other village child."),
    "fisherman": ("old_fisherman.png", "The Old Fisherman shown in the reference sheet, an elderly coastal man with weathered features and practical fishing clothes; preserve his exact face, hair, age, clothing and calm grounded posture."),
    "black_tide": ("BLACK TIDE — SUPERNATURAL .png", "The Black Tide, a living supernatural mass of black seawater and smoke-like shadow that briefly forms hand-, mouth- and face-like silhouettes; never give it a stable human body."),
    "jellyfish": ("BLACK JELLYFISH .png", "The Black Jellyfish, a large translucent black deep-sea creature filled with ink-like smoke and long trailing tentacles; preserve its non-human jellyfish anatomy."),
}
PROPS = {
    "spear": ("spear.png", "Lua's fixed fishing spear: a rough wooden shaft with a dark stone spearhead and simple cord binding; it remains one rigid object owned and held by Lua."),
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


CLIPS: list[dict[str, Any]] = [
    {
        "scene_id": "SC01-001", "clip_id": "SC01-001_M01", "title": "폭풍 아래 푸른 신호", "seconds": 18,
        "source": "EP01 S#1 — 폭풍 밤바다, 파도 아래 처음 보이는 푸른빛", "mode": "new_anchor", "refs": [ref(1, "mir")],
        "anchor": "A storm-lashed night ocean seen in one immense coherent wide composition, giant black waves, forked lightning, diagonal rain, and a tiny blue glow barely visible beneath a distant wave trough. Young Mir is not yet clearly visible. Leave depth and open water for the glow to travel toward the coast.",
        "relay": [beat(9, "The storm ocean dominates the frame. Waves, rain and lightning create all motion while no character is visible."), beat(9, "A tiny blue glow begins pulsing far below the waves and is carried toward the coast, suggesting a living presence without revealing it clearly.")],
    },
    {
        "scene_id": "SC01-001", "clip_id": "SC01-001_M02", "title": "무너진 용궁의 어린 미르", "seconds": 18,
        "source": "EP01 S#1 — 심해 용궁 잔해에서 상처 입은 미르 발견", "mode": "new_anchor", "refs": [ref(1, "mir")],
        "anchor": "A ruined deep-sea palace corridor with a cracked ancient coral pillar, drifting marine dust and cold blue darkness. Young Mir is small within the immense ruins, wounded and nearly unconscious inside a weak blue glow. One coherent underwater moment with clear scale and no other creature.",
        "relay": [beat(6, "An ancient coral pillar cracks and collapses through the ruined palace while marine dust spreads like snow."), beat(6, "Young Mir becomes visible inside the weak blue glow, wounded, eyes half closed and unable to control his body."), beat(6, "The current rolls Young Mir away from the fallen pillar; his tail crystal flickers once as he tries to wake.")],
    },
    {
        "scene_id": "SC01-001", "clip_id": "SC01-001_M03", "title": "검은 물결의 추격", "seconds": 20,
        "source": "EP01 S#1 — 미르를 아래에서 추격하는 검은 물결", "mode": "continuity_frame", "from": "SC01-001_M02", "refs": [ref(1, "mir"), ref(2, "black_tide")],
        "anchor": "A vertical deep-sea pursuit corridor above the ruined palace. Young Mir struggles upward along a diagonal blue shaft of light while the Black Tide rises below as living black water and unstable shadow shapes. Keep both entities clearly separated in depth and preserve an open ascent path.",
        "relay": [beat(7, "Young Mir notices the Black Tide climbing from below and weakly forces himself upward through the blue light."), beat(7, "The Black Tide stretches into unstable hand- and mouth-like silhouettes but never gains a fixed body; it closes distance as Mir loses strength."), beat(6, "Young Mir's tail crystal flashes like a final shield. The pulse pushes back the nearest shadow long enough for him to rise toward the surface.")],
    },
    {
        "scene_id": "SC01-001", "clip_id": "SC01-001_M04", "title": "기억하지 마라", "seconds": 12,
        "source": "EP01 S#1 — 미르의 흔들리는 기억과 심해왕의 목소리", "mode": "new_anchor", "refs": [ref(1, "mir"), ref(2, "black_tide")], "world": DREAM_STYLE,
        "anchor": "A submerged memory-space made from fragments of a broken dragon palace gate, sleeping colossal dragon silhouettes and black root-like darkness. Young Mir floats small and frightened at the center while the Black Tide remains an abstract pressure around the edges, not a humanoid figure.",
        "relay": [beat(6, "Broken palace doors and sleeping giant dragon silhouettes flash through Young Mir's unstable memory. A deep unseen voice says in Korean, \"기억하지 마라.\""), beat(6, "The memory darkens around Mir as the unseen voice says in Korean, \"그러면 아프지 않다.\" Mir recoils and the vision tears apart into storm light.")],
    },
    {
        "scene_id": "SC01-001", "clip_id": "SC01-001_M05", "title": "해안으로 밀려온 빛", "seconds": 12,
        "source": "EP01 S#1 — 폭풍 수면과 해안으로 떠밀리는 푸른빛", "mode": "new_anchor", "refs": [ref(1, "mir")],
        "anchor": "A distant storm coast at night with violent surf, wet black rocks and a small blue glow carried inside a wave toward shore. Young Mir is mostly obscured by water but his blue-silver silhouette can be faintly recognized. One coherent coastal wide image.",
        "relay": [beat(6, "Young Mir breaks through the storm surface inside a wave, barely conscious as the blue light dims."), beat(6, "The current carries the small blue-silver body toward the dark coast until the glow disappears behind the shore rocks.")],
    },
    {
        "scene_id": "SC01-002", "clip_id": "SC01-002_M01", "title": "한 번의 찌르기와 빗나감", "seconds": 5,
        "source": "EP01 S#2 — 루아가 물고기를 겨누고 작살을 한 번 찌르지만 놓침", "mode": "new_anchor", "anchor_id": "ANC_SC01-002_M01_V3", "refs": [ref(1, "lua"), ref(3, "spear", prop=True)],
        "review_ko": "젖은 방파제 가장자리에서 루아가 낮은 준비 자세로 물고기를 겨눈다. 작살 끝은 수면 바로 위에 있고 두 손과 팔꿈치는 어깨보다 아래에 있다. 머리·몸통·꼬리가 명확한 작은 물고기는 작살 진행축에서 옆으로 떨어져 있으며 둘 사이에는 깨끗한 물 공간이 보인다. 루아가 낮은 자세에서 짧고 직접적인 찌르기를 정확히 한 번 수행하면 물고기가 옆으로 피하고 작살 끝이 물에 들어가 작은 물보라가 생긴다. 카메라는 작살선을 따라 짧게 접근한 뒤 물보라와 앞으로 쏠리는 루아를 아래로 따라간다. 대사는 없다.",
        "anchor": "A dynamic low three-quarter side composition on a post-storm wet stone breakwater. Lua is fully visible at the shallow edge in a compact low aiming stance, with both elbows and both hands below shoulder level. Her fixed spear forms a strong diagonal from her low hands to a dark stone point hovering just above the water below her waist. A single small natural fish is clearly readable underwater with a distinct head, body and tail, swimming laterally several body lengths to the side of the spear point. A broad clean gap of open water visibly separates the fish from the spear. Lua's front sandal rests at the slick boundary, and her feet, spear point, fish and water contact area remain readable in the same frame. Damaged nets and small boats stay secondary in the distant background.",
        "relay": [beat(5, "Begin in the supplied dynamic low three-quarter side composition with Lua, both feet, the complete spear, the separate fish and the shallow water visible together. During one brief aiming beat, the camera makes one subtle forward push along the existing diagonal spear line. The spear point stays low near the surface as Lua makes exactly one short forward-and-down stabbing thrust from her low hands. The fish immediately darts farther sideways across the clear water gap; the spear point enters the vacated water and makes one small splash. The camera gives one short restrained downward follow toward that splash as the missed thrust pulls Lua's shoulders slightly beyond her front foot. End on the first loss of balance. The moment plays silently.")],
    },
    {
        "scene_id": "SC01-002", "clip_id": "SC01-002_M01B", "title": "젖은 가장자리의 낙상", "seconds": 5,
        "source": "EP01 S#2 — 빗나간 찌르기의 힘으로 루아가 미끄러져 얕은 물에 빠짐", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(3, "spear", prop=True)],
        "review_ko": "루아는 이미 작살을 찌른 직후 상체와 어깨가 앞발보다 앞으로 나간 불안정한 자세로 시작한다. 작살 끝은 얕은 물에 있고 앞 샌들은 젖은 돌 가장자리에 반쯤 걸쳐 있다. 앞으로 전달되는 체중 때문에 앞발이 한 번 미끄러지고 놀란 숨이 짧게 새어 나온다. 카메라는 중간 측면 구도에서 루아의 상체로 빠르게 접근한 뒤, 짧은 시네마틱 슬로모션으로 앞으로 무너지는 몸을 가까운 측면에서 아래로 추적한다. 무릎과 엉덩이가 얕은 물에 닿는 순간에는 정상 속도의 무게감 있는 물보라가 발생한다. 같은 작살은 처음부터 끝까지 루아의 두 손과 함께 움직인다.",
        "anchor": "A post-storm coastal village morning on the same wet stone breakwater. Lua is frozen immediately after a missed low spear thrust in a full-body side view: her shoulders and chest are already beyond her front foot, the spear tip is already in the shallow water, her front sandal is half over the slick stone edge and her rear leg is stretched behind her. This is a visibly unstable forward-falling pose, with open shallow water directly below her and no other person visible.",
        "relay": [beat(5, "Begin from the supplied off-balance pose with the spear point already resting in the shallow water and both of Lua's hands physically supporting the same shaft. Her existing forward momentum flows through her shoulders and hips. The front sandal releases from the slick stone lip, surprise flashes across her face and a brief startled breath escapes. The camera performs one energetic continuous move: a fast push from the medium side view toward Lua's upper body as her foot slips, followed by a close downward side-tracking sweep with her falling body. A brief cinematic slow-motion emphasis reveals her shifting weight and startled expression during the descent. Her knees and hip then meet the shallow water at full impact speed with one weighty compact splash, while the spear travels with her hands throughout the fall.")],
    },
    {
        "scene_id": "SC01-002", "clip_id": "SC01-002_M01C", "title": "물에서 일어나는 루아", "seconds": 5,
        "source": "EP01 S#2 — 얕은 물에 빠진 루아가 태연한 척 다시 일어남", "mode": "continuity_frame", "from": "SC01-002_M01B", "refs": [ref(1, "lua"), ref(3, "spear", prop=True)],
        "review_ko": "직전 낙상 뒤 루아가 얕은 물에 무릎과 엉덩이를 담근 상태에서 시작한다. 루아는 같은 작살을 놓지 않고 한 손으로 가까운 돌을 짚은 뒤 한쪽 무릎을 세워 몸을 일으킨다. 젖은 머리카락이 얼굴에 붙고 당황했지만 아무 일도 아니라는 표정을 지으려 한다. 새로운 찌르기나 두 번째 낙상은 없다. 대사는 없다.",
        "anchor": "Use the selected stable end frame from SC01-002_M01B after the completed fall. Lua is seated or kneeling in the shallow water beside the same wet stone edge, visibly soaked, still owning the same spear, with one nearby solid stone available for her supporting hand. Preserve the same morning light, side orientation and breakwater geography.",
        "relay": [beat(5, "Continue directly after the completed fall with Lua already settled in the shallow water. She keeps ownership of the same spear, places one free hand firmly on the nearby stone, draws one knee underneath her and pushes herself back to stable footing in one continuous recovery. Wet hair hangs across her face; after standing, she lowers the spear and forces an embarrassed expression of dignity. The camera makes only a small upward correction to keep her body framed. No dialogue.")],
    },
    {
        "scene_id": "SC01-002", "clip_id": "SC01-002_M02", "title": "두 아이의 놀림", "seconds": 12,
        "source": "EP01 S#2 — 마을아이 1과 2가 함께 등장해 화면 밖 루아를 놀림", "mode": "new_anchor", "refs": [ref(1, "child1"), ref(2, "child2")],
        "review_ko": "아침의 젖은 방파제에서 마을아이 1은 화면 왼쪽, 마을아이 2는 화면 오른쪽에 서고 주변 공간은 비어 있다. 마을아이 1이 물을 가리키며 한 번 웃고 한국어로 \"또 놓쳤다!\"라고 말한다. 마을아이 1이 입을 닫은 뒤 마을아이 2가 한국어로 \"루아 누나는 바다랑 안 맞아!\"라고 말한다. 두 아이는 처음부터 끝까지 같은 위치와 외형을 유지하며, 카메라는 두 사람을 향해 천천히 다가간다.",
        "anchor": "A post-storm wet village breakwater in morning light. Exactly two village children occupy a clean medium two-shot: Village Child 1 stands frame-left with short hair and empty hands; Village Child 2 stands frame-right with tied hair and her woven shoulder basket attached only to her own hip. Both bodies angle toward the empty frame-right edge. Open wet stone and sea fill that sightline, while the foreground and background remain empty.",
        "relay": [beat(6, "Begin from the supplied anchor and keep exactly the same two children in a stable medium two-shot. Village Child 1 remains frame-left with empty hands; Village Child 2 remains frame-right with her own woven shoulder basket. Both look toward the empty frame-right edge. Village Child 1 points toward the water, gives one contained laugh and says exactly once in natural Korean, \"또 놓쳤다!\" Only Village Child 1 speaks and moves his mouth; Village Child 2 listens with closed lips. The camera makes one restrained slow push-in without changing their positions or the empty surrounding space."), beat(6, "Continue the same take and preserve the same two distinct faces, hair, clothes and basket ownership. Village Child 1 closes his mouth and lowers his hand. Village Child 2 leans forward slightly, keeps her eyes toward the empty frame-right edge and says exactly once in natural Korean, \"루아 누나는 바다랑 안 맞아!\" Only Village Child 2 speaks and moves her mouth; Village Child 1 stays silent. The two children share one brief laugh as the camera settles, and the composition remains a clean two-shot from beginning to end. No repeated line, Chinese speech, invented words or other voice.")],
    },
    {
        "scene_id": "SC01-002", "clip_id": "SC01-002_M03", "title": "루아의 허세", "seconds": 18,
        "source": "EP01 S#2 — 루아 단독 역방향 컷, 두 아이에게 반박하고 수심 확인이라고 변명", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(3, "spear", prop=True)],
        "review_ko": "젖은 루아가 방파제에 혼자 서서 작살을 낮게 들고 화면 왼쪽의 빈 공간을 바라본다. 루아가 한국어로 \"안 맞긴 뭐가 안 맞아!\"라고 말하고, 카메라는 허리 위 중간 구도에서 가슴 위 중간 클로즈업까지 눈에 보이게 천천히 가까워진다. 루아는 손을 머리 쪽으로 올리지 않고 작살을 안정적으로 낮게 유지한 채 어깨를 펴고 턱을 들며 \"방금 건 일부러 빠진 거야.\"라고 말한다. 잠깐 침묵한 뒤 얕은 물을 보았다가 다시 왼쪽을 바라보며 \"수심 확인.\"이라고 말한다. 전체 영상에는 루아 한 명만 등장한다.",
        "anchor": "A post-storm wet breakwater in the same morning light and horizon height. Wet Lua stands alone in a clean medium composition, holding her fixed fishing spear low and angling her body toward frame-left. Empty wet stone and open sea fill the entire frame-left sightline and background.",
        "relay": [beat(6, "Begin from the supplied anchor in a stable waist-up medium shot of wet Lua alone, her eyes directed toward the empty frame-left edge. Lua keeps the rigid spear safely low, lifts only her chin and says exactly once in natural Korean, \"안 맞긴 뭐가 안 맞아!\" Only Lua speaks and moves her mouth. The camera begins one clearly visible but gentle continuous push from waist-up framing toward chest-up framing while the wet stone and sea remain empty around her."), beat(6, "Continue the same unbroken solo shot and the same gentle push-in. Both of Lua's hands remain below chest level and never approach her hair or face; the hand holding the spear keeps it physically supported and motionless at her side. Lua straightens her shoulders, raises her chin a little farther, forces a proud half-smile and says exactly once in natural Korean, \"방금 건 일부러 빠진 거야.\" The same fixed wooden spear with dark stone tip stays low and solid throughout. The surrounding breakwater remains empty and quiet."), beat(6, "Let the camera complete its move and settle into a chest-up medium-close solo shot after one clear silent beat. Lua glances briefly toward the shallow water using only her eyes, returns her gaze to the empty frame-left edge and adds dryly in natural Korean, \"수심 확인.\" Only Lua speaks. Hold on her deadpan attempt to preserve dignity, with closed lips after the final line. Her hands and spear remain low and physically supported, and the composition remains one character against empty wet stone and sea, with no extra dialogue, repeated line, Chinese speech or invented voice.")],
    },
    {
        "scene_id": "SC01-002", "clip_id": "SC01-002_M04", "title": "늙은 어부의 경고", "seconds": 15,
        "source": "EP01 S#2 — SC01-002_02 씬 3·4·5, 루아와 늙은 어부", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(2, "fisherman"), ref(3, "spear", prop=True)],
        "review_ko": "젖은 방파제에서 루아와 늙은 어부가 같은 축의 중간 전신 구도에 함께 선다. 늙은 어부가 다가와 \"루아야.\"라고 부르고 루아가 \"네!\"라고 답한다. 어부가 \"바다는 고집으로 되는 게 아니다.\"라고 말하면 루아는 말없이 상처받은 반응을 보인다. 어부가 먼 동굴을 바라보며 \"오늘은 동굴 쪽 가지 마라. 폭풍 뒤에는 뭐가 밀려올지 몰라.\"라고 경고하고, 카메라는 그의 시선을 따라 천천히 동굴을 보여준다.",
        "anchor": "A grounded two-person composition on the wet coastal breakwater. Lua stands with her fishing spear while the Old Fisherman has approached and calmly faces her. The cliff cave is visible far along their shared sightline. No village children are visible.",
        "relay": [beat(5, "Start in a stable medium-wide two-shot that keeps both Lua and the Old Fisherman visible on the same wet breakwater axis. The fisherman takes his final two slow steps, stops beside Lua without blocking her and says exactly once in natural Korean, \"루아야.\" Lua immediately straightens, keeps her spear pointed safely down and answers exactly once, \"네!\" The camera remains locked; only the current speaker moves their mouth and the other stays silent."), beat(5, "Maintain the same two-shot, distance and eyeline with no cut or isolated talking head. The Old Fisherman studies Lua calmly and says exactly once in natural Korean, \"바다는 고집으로 되는 게 아니다.\" Only he speaks. Lua remains silent with closed lips; her defensive posture softens by a few centimeters, her eyes lower and the familiar warning briefly hurts her. Keep both reactions visible and the spear solid in Lua's hands."), beat(5, "After a short quiet beat, the Old Fisherman turns his head toward the distant cliff. The camera performs the clip's only move: a slow motivated pan and slight lateral slide along his gaze until the cave mouth becomes visible in the background while both characters remain in the foreground. He alone warns in natural Korean, \"오늘은 동굴 쪽 가지 마라. 폭풍 뒤에는 뭐가 밀려올지 몰라.\" Lua says nothing, keeps her lips closed and follows his gaze. End in a settled composition linking them to the cave; no extra speech or abrupt camera move.")],
    },
    {
        "scene_id": "SC01-002", "clip_id": "SC01-002_M05", "title": "푸른 동굴을 향해", "seconds": 12,
        "source": "EP01 S#2 — 루아 단독, 동굴 빛을 보고 몰래 달려감", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(3, "spear", prop=True)],
        "review_ko": "루아가 동굴까지 육지로 이어진 돌길 앞에 혼자 서 있다. 동굴에서 나온 첫 번째 푸른빛이 젖은 돌을 따라 루아의 얼굴과 눈에 닿는다. 루아는 입을 움직이지 않는 한국어 내면 독백으로 \"가라면 가지 말아야 하는데.\"라고 생각한다. 더 강한 두 번째 푸른빛을 본 뒤 \"저렇게 빛나면 가야지.\"라고 생각하고 작살을 몸 옆에 고정한 채 동굴을 향해 달린다. 카메라는 낮은 후방 3/4 구도로 따라가며, 루아의 모든 발걸음은 물이 아닌 단단한 돌길을 딛는다.",
        "anchor": "Lua alone at the edge of the coastal village with the distant cliff cave visible beyond wet rocks. A continuous raised stone footpath connects her position to the cave entirely over land, with no water crossing. A faint blue pulse comes from the cave mouth. Lua holds her fishing spear and has a clear route along solid stone.",
        "relay": [beat(6, "Begin from the supplied anchor in a stable medium-wide profile composition with Lua alone in the foreground and the distant cave mouth readable at the end of one continuous raised stone footpath. Storm-damaged fishing nets hang softly out of focus at one edge of frame. Keep the camera still as the cave emits one faint blue pulse; let the reflected light travel across wet stones before reaching Lua's face and catching in her eyes. Lua stops, turns only her eyes toward the cave, then cautiously checks behind her without moving her feet. She keeps the fixed spear low and thinks exactly once in an internal Korean voice-over, \"가라면 가지 말아야 하는데.\" Her lips remain closed because this is thought, not spoken dialogue."), beat(6, "A stronger second blue pulse gives Lua a clear visual decision cue. Begin with a brief closer reaction as curiosity replaces hesitation; Lua suppresses a grin and thinks exactly once in the same internal Korean voice-over, \"저렇게 빛나면 가야지.\" Her lips stay closed. She tightens one hand around the same rigid spear, pivots toward the cave and breaks into a purposeful run along the raised stone footpath. On her pivot, the camera transitions into the clip's single motivated move: a smooth low rear three-quarter tracking shot that follows at a steady distance, keeping Lua, the solid path and the glowing cave on the same travel axis. Every running step lands visibly on solid stone; she never enters or crosses water. The spear remains secured along her side, never swings wildly, duplicates or merges with her body. End with Lua running toward the cave entrance as the blue glow grows larger ahead, not yet inside it and without an abrupt cut.")],
    },
    {
        "scene_id": "SC01-003", "clip_id": "SC01-003_M01", "title": "해안 동굴 진입", "seconds": 18,
        "source": "EP01 S#3 — 루아 단독으로 젖은 동굴 안에 진입", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(3, "spear", prop=True)],
        "anchor": "A dark wet coastal cave with shallow seawater, dripping rock, a narrow entrance behind Lua and a faint blue glow deeper inside. Lua enters alone with her fishing spear held forward. Preserve an unobstructed path from the entrance toward the glow; no dragon is visible yet.",
        "relay": [beat(6, "Lua steps into the cave alone, carefully testing the shallow water with her spear while the blue glow pulses deeper inside."), beat(6, "Trying to sound brave, Lua calls naturally in Korean, \"나와라. 내가 마을에서 제일 무서운 사람은 아니지만.\""), beat(6, "Lua continues naturally in Korean, \"상당히 귀찮은 사람이다.\" A tiny squeak answers from the rocks and she freezes.")],
    },
    {
        "scene_id": "SC01-003", "clip_id": "SC01-003_M02", "title": "작은 용 발견", "seconds": 20,
        "source": "EP01 S#3 — 루아와 어린 미르의 첫 대면", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(2, "mir"), ref(3, "spear", prop=True)],
        "anchor": "Inside the same wet cave, Lua kneels at a respectful distance from a rock crevice while wounded Young Mir is partly visible in weak blue light. Lua's spear is lowered away from Mir. Keep Lua fully human and Mir fully dragon, with clear physical separation and an open approach path.",
        "relay": [beat(7, "Lua hears the soft squeak and says naturally in Korean, \"방금 귀여웠는데?\" She lowers the spear and peers into the crevice."), beat(7, "Young Mir's horns, wet blue-silver tail and half-open eyes become visible. Lua whispers, \"너… 도마뱀은 아니지?\""), beat(6, "Young Mir opens his large clear eyes and looks directly at Lua. Lua stops breathing for a moment and says, \"말도 안 돼.\"")],
    },
    {
        "scene_id": "SC01-003", "clip_id": "SC01-003_M03", "title": "살려달라는 이빨", "seconds": 18,
        "source": "EP01 S#3 — 루아가 손을 내밀고 미르가 약하게 물어 매달림", "mode": "continuity_frame", "from": "SC01-003_M02", "refs": [ref(1, "lua"), ref(2, "mir")],
        "anchor": "Use a stable continuation frame from the first meeting: Lua crouched low with an open hand offered near the ground, Young Mir weak and unable to retreat on wet stone. Maintain the same cave axis, distance, anatomy separation and blue lighting.",
        "relay": [beat(6, "Lua notices Young Mir cannot stand. Her curiosity turns to concern and she says gently in Korean, \"야, 야. 괜찮아. 안 잡아먹어.\""), beat(6, "Lua lowers her hand and jokes softly, \"나도 오늘 아침 못 먹었거든.\" Young Mir watches her fingers and gathers his remaining strength."), beat(6, "Young Mir suddenly bites Lua's finger weakly. Lua cries, \"악!\" but realizes he is not attacking; he is clinging to her hand for help.")],
    },
    {
        "scene_id": "SC01-003", "clip_id": "SC01-003_M04", "title": "용심 공명", "seconds": 15,
        "source": "EP01 S#3 — 피와 깨진 비늘이 닿아 용심 공명과 환상 발생", "mode": "new_anchor", "refs": [ref(1, "mir")], "world": DREAM_STYLE,
        "anchor": "A single submerged vision of a ruined dragon palace, a broken ceremonial gate, sleeping colossal dragon silhouettes, black root-like corruption and a fading blue heart deep below. Young Mir's blue crown-wave mark is the visual key connecting these fragments. No human figure is visible.",
        "relay": [beat(5, "A drop of Lua's blood touches Young Mir's cracked scale outside the visible memory, and blue light erupts into this submerged vision."), beat(5, "The vision passes through the broken palace gate, sleeping giant dragons and black roots tightening around the ruins."), beat(5, "A blue heart-like light fades in the deep distance while a luminous connection pulls the vision abruptly back toward Lua and Young Mir.")],
    },
    {
        "scene_id": "SC01-003", "clip_id": "SC01-003_M05", "title": "내가 본 거야", "seconds": 16,
        "source": "EP01 S#3 — 공명 직후 루아와 미르의 반응", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(2, "mir")],
        "anchor": "Back in the wet cave, Lua kneels beside weak Young Mir after the blue flash. A fresh blue mark glows on Lua's wrist and Mir's chest mark answers faintly. Keep their bodies separate, their eye contact readable and the cave lighting stable.",
        "relay": [beat(8, "Lua gasps back into reality, stares at the new mark on her wrist and asks naturally in Korean, \"방금… 내가 본 거야?\""), beat(8, "Young Mir gives a weak cry. Lua looks between his eyes and chest mark and asks naturally in Korean, \"너 대체 뭐야?\"")],
    },
    {
        "scene_id": "SC01-003", "clip_id": "SC01-003_M06", "title": "사고를 품에 안고", "seconds": 14,
        "source": "EP01 S#3 — 마을 사람의 목소리, 루아가 미르를 감싸 동굴을 나감", "mode": "continuity_frame", "from": "SC01-003_M05", "refs": [ref(1, "lua"), ref(2, "mir")],
        "anchor": "Use a stable continuation frame in the cave: Lua close to Young Mir with enough cloth available to wrap him, the cave entrance visible behind her. Maintain the same lighting and anatomy separation; the off-screen villager is never shown.",
        "relay": [beat(7, "An unseen villager calls from outside in Korean, \"루아! 거기 있냐?\" Lua startles, looks toward the entrance and then back at Young Mir as he crawls weakly toward her."), beat(7, "Lua wraps Young Mir securely in part of her outer cloth, lifts him against her chest and sighs, \"하. 나 진짜 사고 쳤다.\" She carries him toward the cave exit.")],
    },
    {
        "scene_id": "SC01-004", "clip_id": "SC01-004_M01", "title": "용 키우기 첫날", "seconds": 20,
        "source": "EP01 S#4 — 집에 몰래 데려와 물그릇, 생선, 조개껍데기 반응", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(2, "mir")],
        "anchor": "Lua's small worn coastal house in daylight: wooden bed, small table, shallow water bowl, shells, dry fish, nets, water container and a cloth-covered window. Lua has just placed Young Mir near the bowl after secretly bringing him inside. The room has clear reachable paths between bowl, table and bed.",
        "relay": [beat(5, "Lua closes the door, listens for adults and sees Young Mir peek from the cloth. She says in Korean, \"진짜네. 꿈이면 지금쯤 깨야 하는데.\""), beat(5, "Lua settles Young Mir into the shallow water bowl. He relaxes slightly as she asks, \"너 물에서 자는 거야? 좋겠다. 난 그러면 죽는데.\""), beat(5, "Lua offers a dry fish. Young Mir recoils in alarm and Lua asks, \"아니, 바다에서 왔잖아. 생선 안 먹어?\""), beat(5, "Young Mir crawls to a shell, licks it and hugs it for comfort. Lua watches in disbelief and says, \"입맛도 귀족이네.\"")],
    },
    {
        "scene_id": "SC01-004", "clip_id": "SC01-004_M02", "title": "당분간 여기 있어", "seconds": 18,
        "source": "EP01 S#4 — 루아가 미르를 숨기기로 결정하고 밥값을 요구", "mode": "continuity_frame", "from": "SC01-004_M01", "refs": [ref(1, "lua"), ref(2, "mir")],
        "anchor": "Use a stable continuation frame inside Lua's house: Lua sits protectively between Young Mir and the closed door, her glowing wrist mark partly hidden, while Mir remains near the shallow bowl and shell. Keep the imagined adults off-screen as voices only.",
        "relay": [beat(6, "Lua checks her wrist mark and looks anxiously toward the door while imagined adult voices remain audio-only: \"불길하다! 바다에 돌려보내!\" She immediately blocks the doorway from Mir."), beat(6, "Lua returns her attention to Young Mir and says firmly in Korean, \"안 돼. 그러니까… 당분간 여기 있어.\""), beat(6, "Trying to sound responsible, Lua adds, \"근데 밥값은 해야 돼. 예를 들면, 물 좀 데워준다든가?\" Young Mir tilts his head.")],
    },
    {
        "scene_id": "SC01-004", "clip_id": "SC01-004_M03", "title": "가능성은 있다", "seconds": 15,
        "source": "EP01 S#4 — 미르의 작은 물방울과 두 문양의 반응", "mode": "continuity_frame", "from": "SC01-004_M02", "refs": [ref(1, "lua"), ref(2, "mir")],
        "anchor": "Use the same house continuity: Lua waits beside the water bowl while Young Mir faces her and prepares to try a tiny water ability. Keep the shell near Mir and preserve the room layout, lighting and character scale.",
        "relay": [beat(5, "Young Mir opens his small mouth while Lua waits hopefully. He produces only one floating water droplet."), beat(5, "The droplet hangs briefly and lands on Lua's forehead. Lua closes her eyes, pauses, then says, \"그래. 가능성은 있다.\""), beat(5, "Young Mir chirps with pride and Lua smiles despite herself. Mir's chest mark and Lua's wrist mark glow together; both notice the shared pulse and become still.")],
    },
    {
        "scene_id": "SC01-005", "clip_id": "SC01-005_M01", "title": "같은 꿈의 시작", "seconds": 18,
        "source": "EP01 S#5 — 밤, 루아와 미르가 잠든 채 공명이 시작", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(2, "mir")],
        "anchor": "Lua's house at night in one quiet coherent composition. Lua sleeps on the wooden bed while Young Mir sleeps curled in the shallow water bowl nearby. Their wrist and chest marks can faintly answer each other across the dark room. The window remains covered.",
        "relay": [beat(6, "The house is still. Lua sleeps on the bed and Young Mir sleeps curled in the bowl as their two marks begin glowing faintly in the same rhythm."), beat(6, "Young Mir starts trembling in a nightmare. Lua frowns in her sleep and unconsciously mirrors his distress."), beat(6, "The shared blue pulse strengthens until the dark room dissolves into the submerged ruins of Young Mir's dream.")],
    },
    {
        "scene_id": "SC01-005", "clip_id": "SC01-005_M02", "title": "버려진 새끼 용", "seconds": 18,
        "source": "EP01 S#5 — 무너진 용궁 꿈과 왕자용 그림자", "mode": "new_anchor", "refs": [ref(1, "mir")], "world": DREAM_STYLE,
        "anchor": "A ruined dragon palace dream with black roots around a blue heart stone. Young Mir stands small in the foreground while one enormous future prince-dragon shadow with crown-like horns stretches behind him as a symbolic silhouette of the same identity, not a second creature.",
        "relay": [beat(6, "Young Mir stands before the ruined palace and the blue heart stone while black roots tighten around the architecture."), beat(6, "A vast prince-dragon shadow belonging to Young Mir appears behind him. An unseen deep voice says in Korean, \"너는 왕자가 아니다.\""), beat(6, "The unseen voice continues, \"버려진 새끼 용이다.\" Young Mir trembles and the dream collapses around him.")],
    },
    {
        "scene_id": "SC01-005", "clip_id": "SC01-005_M03", "title": "너도 무서운 거구나", "seconds": 15,
        "source": "EP01 S#5 — 루아가 깨어 미르를 품에 안고 공포를 느낌", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(2, "mir")],
        "anchor": "Back in the dark house, Lua has awakened and holds trembling Young Mir securely against her chest beside the water bowl. Their blue marks glow softly. Preserve the night room layout and keep Lua human, Mir dragon and both identities clearly separate.",
        "relay": [beat(5, "Lua wakes sharply, sees Young Mir shaking and lifts him into her arms, saying in Korean, \"뭐야… 야. 괜찮아. 나 여기 있어.\""), beat(5, "Young Mir's fear passes through the bond. Lua grips her chest and realizes internally, \"이거… 내 무서움이 아니야.\""), beat(5, "Lua hugs Young Mir more tightly and says, \"너도 무서운 거구나.\" Mir gently licks the glowing mark on her wrist and the light softens.")],
    },
    {
        "scene_id": "SC01-005", "clip_id": "SC01-005_M04", "title": "창밖의 검은 해파리", "seconds": 18,
        "source": "EP01 S#5 — 바다 소리가 사라지고 검은 해파리가 집을 향함", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(2, "jellyfish")],
        "anchor": "A night view from inside Lua's house toward the window and silent sea. Lua stands at the window in the foreground while the Black Jellyfish floats above the distant water outside, translucent black body filled with ink-like smoke and long tentacles below. Young Mir is off-screen and heard only.",
        "relay": [beat(6, "Lua notices the sea has become unnaturally silent and approaches the window. Young Mir gives a low warning growl from off-screen."), beat(6, "Lua sees the Black Jellyfish floating above the night sea and asks naturally in Korean, \"저게… 널 찾으러 온 거야?\""), beat(6, "The Black Jellyfish slowly turns toward Lua's house as ink-like smoke rotates inside its body and the long tentacles trail beneath the water. Cut to black.")],
    },

]


RECONFIGURATION_PLAN: dict[str, dict[str, Any]] = {
    "SC01-001_M01": {"actions": ["유지"], "priority": "P2", "reason": "인물 없는 환경 중심의 두 단계 변화로 장시간 연출 부담이 낮음", "next": "폭풍과 푸른빛의 공간 깊이만 앵커에서 확인"},
    "SC01-001_M02": {"actions": ["컷 분할", "새 앵커 필요"], "priority": "P0", "reason": "기둥 붕괴·미르 공개·해류 이동이 한 클립에 중첩됨", "next": "붕괴와 발견 / 해류에 떠밀림 두 컷으로 분리"},
    "SC01-001_M03": {"actions": ["컷 분할", "새 앵커 필요"], "priority": "P0", "reason": "추격·검은 형상 변화·방어 파동·상승이 20초에 중첩됨", "next": "추격 접근 / 꼬리 결정 방어와 탈출로 분리"},
    "SC01-001_M04": {"actions": ["프롬프트 수정"], "priority": "P1", "reason": "꿈 장면은 컷 변화를 허용하지만 시각 상태와 음성 순서를 긍정형으로 정리해야 함", "next": "기억 파편과 두 음성 구간을 시각적 두 박자로 단순화"},
    "SC01-001_M05": {"actions": ["유지"], "priority": "P2", "reason": "파도에 실려 해안으로 이동하는 하나의 환경 주도 동작", "next": "해류 방향과 도착 지점이 앵커에서 이어지는지만 확인"},
    "SC01-002_M01": {"actions": ["프롬프트 수정", "새 앵커 필요"], "priority": "P0", "reason": "직접 찌르기보다 조준 컷과 다음 낙상 컷의 편집 연결이 안정적임", "next": "조준 전용 3~4초 컷과 작살·물고기 분리 앵커로 재작성"},
    "SC01-002_M01B": {"actions": ["유지"], "priority": "P2", "reason": "긍정형 낙상 프롬프트에서 앞으로 꼬꾸라지는 동작이 확보됨", "next": "선택 후보를 보존하고 카메라 강조는 후처리로 보완"},
    "SC01-002_M01C": {"actions": ["유지"], "priority": "P2", "reason": "회복 동작 후보 3개가 모두 사용 가능 수준으로 안정됨", "next": "현재 앵커·5초·무대사 설정 고정"},
    "SC01-002_M02": {"actions": ["유지"], "priority": "P2", "reason": "두 인물 고정 대화와 화자 분리 방식이 검증됨", "next": "정상 후보 선택 후 외형·대사 구조 고정"},
    "SC01-002_M03": {"actions": ["유지"], "priority": "P2", "reason": "단독 화자 구조에서 사용 가능한 후보가 확보됨", "next": "손과 작살을 함께 움직이는 제스처 없이 현재 후보 사용"},
    "SC01-002_M04": {"actions": ["컷 분할"], "priority": "P0", "reason": "호명·답변·훈계·동굴 경고·카메라 팬이 한 클립에 과밀함", "next": "호명과 짧은 답변 / 경고와 동굴 시선 이동 두 컷으로 분리"},
    "SC01-002_M05": {"actions": ["유지"], "priority": "P2", "reason": "육상 경로가 명확한 앵커에서 후보 선택 방식이 검증됨", "next": "돌길이 끝까지 보이는 후보와 시드 보존"},
    "SC01-003_M01": {"actions": ["컷 분할"], "priority": "P0", "reason": "동굴 진입·수심 확인·두 문장·미르 반응이 한 클립에 중첩됨", "next": "동굴 진입 / 허세 섞인 호출과 소리 반응으로 분리"},
    "SC01-003_M02": {"actions": ["컷 분할", "새 앵커 필요"], "priority": "P0", "reason": "접근·작살 내리기·미르 공개·세 문장이 첫 대면에 중첩됨", "next": "미르 실루엣 발견 / 눈맞춤과 짧은 반응으로 분리"},
    "SC01-003_M03": {"actions": ["컷 분할", "새 앵커 필요"], "priority": "P0", "reason": "손 내밀기·농담·물기·통증 반응이 복합 접촉 동작임", "next": "손을 내미는 안심 컷 / 이미 손가락을 문 상태의 반응 컷으로 분리"},
    "SC01-003_M04": {"actions": ["프롬프트 수정"], "priority": "P1", "reason": "꿈 영상은 유지 가능하지만 세 변화를 긍정형 시각 박자로 정리해야 함", "next": "푸른 폭발 / 용궁과 검은 뿌리 / 심장빛 귀환 순서를 간결화"},
    "SC01-003_M05": {"actions": ["프롬프트 수정"], "priority": "P1", "reason": "두 인물 반응과 두 문장은 가능하지만 표식·시선·발화 우선순위 조정이 필요함", "next": "루아 반응 중심으로 손동작을 줄이고 느린 접근 카메라 하나만 유지"},
    "SC01-003_M06": {"actions": ["컷 분할", "새 앵커 필요"], "priority": "P0", "reason": "외부 음성 반응·천 감싸기·들기·퇴장이 한 클립에 중첩됨", "next": "외부 부름과 결정 / 이미 감싼 미르를 안고 퇴장으로 분리"},
    "SC01-004_M01": {"actions": ["컷 분할", "새 앵커 필요"], "priority": "P0", "reason": "문 닫기·물그릇·생선 거부·조개 포옹과 네 대사가 20초에 과밀함", "next": "집 도착 / 물그릇 / 생선 반응 / 조개 선택으로 분리"},
    "SC01-004_M02": {"actions": ["컷 분할", "새 앵커 필요"], "priority": "P0", "reason": "상상 속 목소리·문 차단·숨김 결정·밥값 대사가 함께 있어 추가 인물 위험이 큼", "next": "문을 막는 불안 반응 / 미르에게 머물라고 말하는 대화로 분리"},
    "SC01-004_M03": {"actions": ["컷 분할", "새 앵커 필요"], "priority": "P0", "reason": "물방울 생성·이동·이마 충돌·대사·표식 공명이 연속 물리 사건임", "next": "물방울과 이마 접촉 / 루아 반응과 두 표식 공명으로 분리"},
    "SC01-005_M01": {"actions": ["프롬프트 수정"], "priority": "P1", "reason": "수면 상태의 느린 공명은 유지 가능하지만 꿈 전환을 단일 시각 흐름으로 정리해야 함", "next": "두 표식의 동시 박동과 방이 꿈으로 녹아드는 한 방향 전환으로 단순화"},
    "SC01-005_M02": {"actions": ["프롬프트 수정"], "priority": "P1", "reason": "꿈 장면의 상징적 컷 변화는 허용되나 그림자 정체성과 음성 순서가 중요함", "next": "미르와 미래 그림자의 동일 정체성을 앵커에서 분명히 하고 두 음성을 분리"},
    "SC01-005_M03": {"actions": ["컷 분할", "새 앵커 필요"], "priority": "P0", "reason": "깨기·들기·감정 공유·포옹·손목 핥기가 복합 2인 접촉 장면임", "next": "잠에서 깨 미르를 안기 / 공포 공유와 표식 진정으로 분리"},
    "SC01-005_M04": {"actions": ["컷 분할", "새 앵커 필요"], "priority": "P0", "reason": "실내 창가 반응과 외부 해파리 위협을 한 공간에서 동시에 처리하기 어려움", "next": "루아의 창가 발견 / 바다 위 해파리가 집을 향하는 외부 컷으로 분리"},
}

from scripts.ep01_msr_prompt_experiment_v2 import apply_reconfiguration

CLIPS, RECONFIGURATION_PLAN = apply_reconfiguration(CLIPS, RECONFIGURATION_PLAN, ref, beat)

SC01_002_REVIEW_EVIDENCE = {
    "review_count": 75,
    "verdicts": {"acceptable": 19, "needs_improvement": 17, "reject": 27, "unrated": 12},
    "by_clip": {
        "SC01-002_M01": {"reviews": 23, "acceptable": 0},
        "SC01-002_M01B": {"reviews": 9, "acceptable": 0},
        "SC01-002_M01C": {"reviews": 6, "acceptable": 4},
        "SC01-002_M02": {"reviews": 11, "acceptable": 3},
        "SC01-002_M03": {"reviews": 13, "acceptable": 3},
        "SC01-002_M04": {"reviews": 4, "acceptable": 2},
        "SC01-002_M05": {"reviews": 9, "acceptable": 7},
    },
    "rules": [
        "Preserve proven one- and two-speaker dialogue layouts instead of splitting them by default.",
        "Use visible traversable ground, one travel axis and one motivated tracking move for locomotion.",
        "Split only physical state transitions such as falling, lifting, biting, wrapping and small-object contact.",
        "Make the anchor describe the exact opening physical state before the primary action.",
        "Treat late reference-image reappearance as a workflow or post-production review issue, not prompt overload.",
    ],
}



def render_markdown(payload: dict[str, Any], title: str, source: str) -> str:
    return (
        f"# {payload['clip_id']} — {title}\n\n"
        "## Summary\n\n"
        f"{source}\n\n"
        "## MSR continuity intent\n\n"
        f"- Anchor mode: `{payload['continuity_mode']}`\n"
        f"- Primary references: {', '.join(str(item['role']) for item in payload['references'])}\n"
        f"- Duration: {payload['requested_seconds']} seconds at 24fps\n\n"
        "## Machine Payload\n\n"
        "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```\n"
    )


def build_payload(item: dict[str, Any], sequence: int, previous: str | None, following: str | None) -> dict[str, Any]:
    references = item["refs"]
    world = item.get("world") or STYLE
    anchor_id = item.get("anchor_id") or f"ANC_{item['clip_id']}"
    anchor = {
        "background_id": anchor_id,
        "description": item["anchor"],
        "source_path": None,
        "status": "missing",
        "review_status": "pending",
    }
    relay = [
        {"order": index, "seconds": row["seconds"], "prompt": row["prompt"]}
        for index, row in enumerate(item["relay"], 1)
    ]
    payload = {
        "schema_version": 3,
        "workflow": WORKFLOW,
        "prompt_strategy": PROMPT_STRATEGY,
        "director_prompt_inheritance": False,
        "project_id": PROJECT_ID,
        "scene_id": item["scene_id"],
        "clip_id": item["clip_id"],
        "sequence": sequence,
        "source_scene_refs": item["source"],
        "review_intent_ko": item.get("review_ko") or item["source"].split("—", 1)[-1].strip(),
        "prompt_experiment": {
            "version": 2,
            "basis": "SC01-002 full candidate review history",
            "source_clip": RECONFIGURATION_PLAN[item["clip_id"]].get("source_clip", item["clip_id"]),
            "implementation": RECONFIGURATION_PLAN[item["clip_id"]].get("implementation", "experiment_v2_ready"),
            "review_focus_ko": RECONFIGURATION_PLAN[item["clip_id"]]["next"],
        },
        "previous_clip": previous,
        "next_clip": following,
        "continuity_mode": item["mode"],
        "continuity_from_clip": item.get("from"),
        "fps": 24,
        "resolution": {"width": 1280, "height": 704},
        "maximum_duration_seconds": 20,
        "requested_seconds": item["seconds"],
        "world_prompt": world,
        "global_prompt": compile_global_prompt(world, references),
        "references": references,
        "anchor": dict(anchor),
        "background": dict(anchor),
        "background_generation": {
            "required": True,
            "suggested_filename": f"{anchor_id}.png",
            "aspect_ratio": "16:9",
            "recommended_resolution": {"width": 1280, "height": 704},
            "prompt": (
                "Single cinematic opening frame for premium stylized 3D video generation, widescreen 16:9. "
                "Depict the exact physical starting state before the clip's primary action, not a summary of later events. "
                "Make every required body, prop, contact point, travel path and screen direction clearly readable in one composition. "
                + item["anchor"]
                + " One coherent moment, not a storyboard, collage, motion trail or sequence of poses."
            ),
            "prompt_contract": {
                "opening_state_only": True,
                "single_primary_action_support": True,
                "readable_contact_geometry": True,
                "review_basis": "SC01-002 full candidate review set",
            },
            "negative_prompt": NEGATIVE,
            "continuity_notes": [
                "Use a selected stable end frame from the previous clip when continuity_mode is continuity_frame."
                if item["mode"] == "continuity_frame"
                else "Generate or supply a fresh integrated anchor because cast or environment changes here.",
                "The anchor conditions identity and spatial layout; it is not an exact timed frame guarantee.",
            ],
        },
        "relay_segments": relay,
        "review": {
            "status": "reviewed",
            "warnings": [],
            "unresolved_questions": [],
            "notes": [
                "Compiled directly from the EP01 source scenario.",
                "No Director or legacy MSR global prompt inheritance.",
                "Primary character slots are limited to 1 and 2; slots 3 and 4 are props only.",
            ],
        },
    }
    return payload


def main() -> None:
    project = ROOT / "prompt_projects" / PROJECT_ID
    project.mkdir(parents=True, exist_ok=True)
    backgrounds: dict[str, Any] = {}
    scene_seconds: dict[str, float] = {}
    continuity_count = 0
    for index, item in enumerate(CLIPS):
        previous = CLIPS[index - 1]["clip_id"] if index else None
        following = CLIPS[index + 1]["clip_id"] if index + 1 < len(CLIPS) else None
        payload = build_payload(item, index + 1, previous, following)
        scene_dir = project / item["scene_id"]
        scene_dir.mkdir(parents=True, exist_ok=True)
        (scene_dir / f"{item['clip_id']}.md").write_text(
            render_markdown(payload, item["title"], item["source"]), encoding="utf-8"
        )
        anchor_id = payload["anchor"]["background_id"]
        backgrounds[anchor_id] = {
            **payload["background_generation"],
            "background_id": anchor_id,
            "description": payload["anchor"]["description"],
            "continuity_mode": payload["continuity_mode"],
            "continuity_from_clip": payload.get("continuity_from_clip"),
        }
        scene_seconds[item["scene_id"]] = scene_seconds.get(item["scene_id"], 0) + item["seconds"]
        continuity_count += int(item["mode"] == "continuity_frame")
    action_counts: dict[str, int] = {}
    for plan in RECONFIGURATION_PLAN.values():
        for action in plan["actions"]:
            action_counts[action] = action_counts.get(action, 0) + 1
    manifest = {
        "schema_version": 3,
        "project_id": PROJECT_ID,
        "title": PROJECT_TITLE,
        "description": "EP01 source-scenario rewrite for clean-slate MSR continuity generation.",
        "scenario_source": SOURCE,
        "episode_coverage": ["EP01"],
        "workflow": WORKFLOW,
        "prompt_strategy": PROMPT_STRATEGY,
        "director_prompt_inheritance": False,
        "policy": {
            "fps": 24,
            "max_clip_seconds": 20,
            "max_primary_characters": 2,
            "reference_slots": {"1": "character_1", "2": "character_2", "3": "prop_3", "4": "prop_4"},
            "anchor_model": "one integrated anchor per generation unit",
            "language": "English visual/action prompts; Korean spoken dialogue only",
        },
        "scene_count": len(scene_seconds),
        "clip_count": len(CLIPS),
        "total_requested_seconds": sum(item["seconds"] for item in CLIPS),
        "scene_requested_seconds": scene_seconds,
        "new_anchor_count": len(CLIPS) - continuity_count,
        "continuity_frame_count": continuity_count,
        "status_summary": {"awaiting_background": len(CLIPS), "reviewed": 0, "invalid": 0},
        "reconfiguration_summary": action_counts,
        "prompt_experiment": {
            "version": 2,
            "basis": "SC01-002 full candidate review history",
            "evidence": SC01_002_REVIEW_EVIDENCE,
        },
        "notes": [
            "Built from RaisingaDragonSeason01/Raising a Dragon.md only.",
            "Legacy Director and MSR prompt projects were not used as prompt sources.",
            "Village child dialogue is split into Lua+Child1 and Lua+Child2 cuts to respect the two-character MSR limit.",
            "SC01-002_M04 is the 15-second Lua+Old Fisherman scene covering the warning dialogue.",
        ],
    }
    (project / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (project / "background_catalog.json").write_text(
        json.dumps({"schema_version": 2, "project_id": PROJECT_ID, "backgrounds": backgrounds}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    links_path = project / "background_links.json"
    if not links_path.exists():
        links_path.write_text(
            json.dumps({"schema_version": 1, "project_id": PROJECT_ID, "links": {}}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    plan_lines = [
        "# EP01 MSR 연속 생성 시나리오 플랜",
        "",
        "원본: `RaisingaDragonSeason01/Raising a Dragon.md` EP01",
        "",
        "- 기존 Director/MSR 프롬프트 상속 없음",
        "- 24fps, 구간당 최대 20초",
        "- 주요 캐릭터 최대 2명",
        "- 슬롯 1·2 캐릭터, 슬롯 3·4 소품",
        "- 행동 변화는 Relay로 처리하고 인물·환경 변화에서만 새 앵커 사용",
        "",
        f"총 {len(CLIPS)}개 구간 · {manifest['total_requested_seconds']}초 · 새 앵커 {manifest['new_anchor_count']}개 · 연결 프레임 {continuity_count}개",
        "",
        "| 순서 | 구간 | 길이 | 연결 | 제목 | 원본 시나리오 범위 |",
        "|---:|---|---:|---|---|---|",
    ]
    for index, item in enumerate(CLIPS, 1):
        plan_lines.append(
            f"| {index} | `{item['clip_id']}` | {item['seconds']}초 | `{item['mode']}` | "
            f"{item['title']} | {item['source']} |"
        )
    plan_lines.extend([
        "",
        "## SC01-002 전체 리뷰에서 확정한 생성 규칙",
        "",
        "- M02·M03·M04의 안정된 1·2인 대화 구조는 유지하며 화자와 입 동작만 명확히 분리합니다.",
        "- M05처럼 이동 경로가 화면에 보이고 한 방향 축과 동기 있는 추적 카메라가 있으면 이동 장면을 유지합니다.",
        "- M01 계열처럼 낙상·들기·물기·감싸기·작은 물체 접촉으로 물리 상태가 급변할 때만 컷을 분할합니다.",
        "- 이미지 프롬프트는 이후 행동을 요약하지 않고 영상 시작 직전의 자세·접촉점·이동 공간을 한 장에 고정합니다.",
        "- 참조 이미지가 영상 중후반에 다시 나타나는 현상은 프롬프트 과밀과 분리해 워크플로우·후처리 리뷰 항목으로 기록합니다.",
        "",
    ])
    plan_lines.extend([
        "## EP01 재구성 분류",
        "",
        "| 우선순위 | 구간 | 분류 | 판단 근거 | 다음 조치 |",
        "|---|---|---|---|---|",
    ])
    for item in CLIPS:
        plan = RECONFIGURATION_PLAN[item["clip_id"]]
        plan_lines.append(
            f"| {plan['priority']} | `{item['clip_id']}` | {', '.join(plan['actions'])} | "
            f"{plan['reason']} | {plan['next']} |"
        )
    plan_lines.extend([
        "",
        "## 재구성 실행 순서",
        "",
        "1. P0 컷 분할·새 앵커 대상의 렌더 단위를 먼저 다시 설계합니다.",
        "2. P1 프롬프트 수정 대상은 긍정형 상태 변화와 카메라 이동 하나로 단순화합니다.",
        "3. P2 유지 대상은 검증된 후보와 시드를 고정하고 재생성을 최소화합니다.",
        "4. 새 앵커는 자세·접촉점·소품 각도·이동 공간을 확인한 뒤 후보 생성을 등록합니다.",
        "5. 선택한 짧은 컷을 편집 스튜디오에서 조립한 뒤 전체 영상만 최종 검수합니다.",
        "",
    ])
    (project / "EP01_MSR_CONTINUITY_PLAN.md").unlink(missing_ok=True)
    (project / "EP01_MSR_CONTINUITY_PLAN.txt").write_text("\n".join(plan_lines), encoding="utf-8")
    print(json.dumps({"project_id": PROJECT_ID, "clips": len(CLIPS), "seconds": manifest["total_requested_seconds"], "scene_seconds": scene_seconds, "new_anchors": manifest["new_anchor_count"], "continuity_frames": continuity_count}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
