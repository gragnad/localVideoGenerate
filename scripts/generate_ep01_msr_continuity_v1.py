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
    "mir": ("YoungMir.png", "Young Mir, a small blue-silver sea dragon with short dark horns, fin-like wings, bright blue eyes, a teardrop crystal at the tail tip and a faint crown-wave chest mark; dragon anatomy only."),
    "child1": ("villageChild01.png", "Village Child 1, the coastal village boy shown in the reference sheet; preserve his exact face, hair, clothing, age and human anatomy, clearly distinct from Lua."),
    "child2": ("village_child_2.png", "Village Child 2, the coastal village girl shown in the reference sheet with her woven shoulder basket; preserve her exact face, hair, clothing, age and human anatomy, clearly distinct from Lua."),
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
        "scene_id": "SC01-002", "clip_id": "SC01-002_M01", "title": "바다에게 거절당한 루아", "seconds": 20,
        "source": "EP01 S#2 — 폭풍 다음 날, 루아 단독 등장부터 물고기 실패 후 일어나기까지", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(3, "spear", prop=True)],
        "anchor": "A post-storm coastal village morning on a wet stone breakwater. Lua has room to enter, stalk a small fish shadow below the edge, thrust her fishing spear, fall into shallow water and stand again. Damaged nets, broken wood and small boats establish the storm aftermath. No village children or adults are visible.",
        "relay": [beat(5, "The wet breakwater and storm-damaged village are briefly established before Lua enters alone carrying her fishing spear."), beat(5, "Lua spots a small fish shadow below the breakwater, plants her feet and raises the spear with awkward overconfidence."), beat(5, "Lua thrusts too early. The fish escapes and water splashes across her face as her balance fails."), beat(5, "Lua slips into the shallow water, then pushes herself upright with wet hair across her face, embarrassed but trying to look composed. End after she is standing again.")],
    },
    {
        "scene_id": "SC01-002", "clip_id": "SC01-002_M02", "title": "첫 번째 놀림", "seconds": 12,
        "source": "EP01 S#2 — 마을아이 1이 새로 등장해 루아를 놀림", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(2, "child1"), ref(3, "spear", prop=True)],
        "anchor": "The same wet breakwater after Lua has climbed from the shallows. Lua stands wet with her spear while Village Child 1 has newly entered at a separate distance behind her. Their silhouettes and identities are clearly separated; no second village child is present.",
        "relay": [beat(6, "Village Child 1 enters, points toward the empty water and laughs while Lua turns toward him, still wet and gripping her spear."), beat(6, "Village Child 1 says naturally in Korean, \"또 놓쳤다!\" Lua absorbs the embarrassment and prepares to defend herself without moving closer to him.")],
    },
    {
        "scene_id": "SC01-002", "clip_id": "SC01-002_M03", "title": "두 번째 놀림과 루아의 허세", "seconds": 18,
        "source": "EP01 S#2 — 마을아이 2 등장, 루아의 반박과 수심 확인 변명", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(2, "child2"), ref(3, "spear", prop=True)],
        "anchor": "A fresh conversational angle on the wet breakwater. Lua stands damp and defensive with her fishing spear; Village Child 2 faces her with a woven shoulder basket at her own hip. Keep both girls visually distinct and exclude Village Child 1 from the frame.",
        "relay": [beat(6, "Village Child 2 looks at wet Lua and says naturally in Korean, \"루아 누나는 바다랑 안 맞아!\""), beat(6, "Lua snaps back naturally in Korean, \"안 맞긴 뭐가 안 맞아!\" She tries to recover her pride while keeping the spear under control."), beat(6, "Lua pushes wet hair from her face and claims naturally in Korean, \"방금 건 일부러 빠진 거야.\" After a short pause she adds, \"수심 확인.\"")],
    },
    {
        "scene_id": "SC01-002", "clip_id": "SC01-002_M04", "title": "늙은 어부의 경고", "seconds": 15,
        "source": "EP01 S#2 — SC01-002_02 씬 3·4·5, 루아와 늙은 어부", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(2, "fisherman"), ref(3, "spear", prop=True)],
        "anchor": "A grounded two-person composition on the wet coastal breakwater. Lua stands with her fishing spear while the Old Fisherman has approached and calmly faces her. The cliff cave is visible far along their shared sightline. No village children are visible.",
        "relay": [beat(5, "The Old Fisherman approaches with slow stable steps and says naturally in Korean, \"루아야.\" Lua immediately straightens and answers, \"네!\""), beat(5, "The Old Fisherman tells her naturally in Korean, \"바다는 고집으로 되는 게 아니다.\" Lua's expression hardens but she stays quiet."), beat(5, "The Old Fisherman looks toward the cliff cave and warns naturally in Korean, \"오늘은 동굴 쪽 가지 마라. 폭풍 뒤에는 뭐가 밀려올지 몰라.\" Lua follows his gaze without answering.")],
    },
    {
        "scene_id": "SC01-002", "clip_id": "SC01-002_M05", "title": "푸른 동굴을 향해", "seconds": 12,
        "source": "EP01 S#2 — 루아 단독, 동굴 빛을 보고 몰래 달려감", "mode": "new_anchor", "refs": [ref(1, "lua"), ref(3, "spear", prop=True)],
        "anchor": "Lua alone at the edge of the coastal village with the distant cliff cave visible beyond wet rocks. A faint blue pulse comes from the cave mouth. Lua holds her fishing spear and has a clear hidden route away from the adults. No fisherman or children are visible.",
        "relay": [beat(6, "Lua notices the faint blue pulse inside the cliff cave, checks that the adults are distracted and thinks naturally in Korean, \"가라면 가지 말아야 하는데.\""), beat(6, "The blue light flashes again. Lua thinks, \"저렇게 빛나면 가야지.\" She grips her spear and runs toward the cave.")],
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
    anchor_id = f"ANC_{item['clip_id']}"
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
                "Premium stylized 3D animated feature-film video anchor, cinematic widescreen 16:9. "
                + item["anchor"]
                + " One coherent moment, not a storyboard or collage."
            ),
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
        "## 중요 컷 경계",
        "",
        "- `SC01-002_M01`: 루아 단독으로 등장해 물고기를 놓치고 얕은 물에서 다시 일어나는 순간까지 한 번에 처리합니다.",
        "- `SC01-002_M02`: 마을아이 1이 새로 등장하므로 새 앵커로 시작합니다.",
        "- `SC01-002_M03`: 마을아이 2의 대사는 루아+마을아이 2 전용 컷으로 분리합니다.",
        "- `SC01-002_M04`: 루아+늙은 어부의 경고 대화를 15초 한 구간으로 처리합니다.",
        "- `SC01-002_M05`: 다시 루아 단독이 되고 동굴이 새 목표가 되므로 새 앵커로 시작합니다.",
        "- 같은 집·동굴에서 동일한 두 인물이 이어질 때만 안정적인 이전 영상 프레임을 계승합니다.",
        "",
    ])
    (project / "EP01_MSR_CONTINUITY_PLAN.md").unlink(missing_ok=True)
    (project / "EP01_MSR_CONTINUITY_PLAN.txt").write_text("\n".join(plan_lines), encoding="utf-8")
    print(json.dumps({"project_id": PROJECT_ID, "clips": len(CLIPS), "seconds": manifest["total_requested_seconds"], "scene_seconds": scene_seconds, "new_anchors": manifest["new_anchor_count"], "continuity_frames": continuity_count}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
