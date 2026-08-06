#!/usr/bin/env python3
"""EP01 MSR prompt experiment V2.

This module keeps the original scenario compiler readable while replacing only the
clips selected by the M01 review study.  Each generated unit has one opening
state, one primary action and one motivated camera purpose.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable


def apply_reconfiguration(
    base_clips: list[dict[str, Any]],
    base_plan: dict[str, dict[str, Any]],
    ref: Callable[..., dict[str, Any]],
    beat: Callable[[float, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    originals = {item["clip_id"]: item for item in base_clips}

    def make(
        base_id: str,
        *,
        clip_id: str | None = None,
        title: str,
        seconds: int,
        anchor: str,
        relay: list[tuple[float, str]],
        mode: str = "new_anchor",
        continuity_from: str | None = None,
        source: str | None = None,
        refs: list[dict[str, Any]] | None = None,
        review_ko: str | None = None,
        priority: str = "P0",
        actions: list[str] | None = None,
        reason: str,
        next_step: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        item = deepcopy(originals[base_id])
        item.update({
            "clip_id": clip_id or base_id,
            "title": title,
            "seconds": seconds,
            "anchor": anchor.strip(),
            "relay": [beat(duration, prompt) for duration, prompt in relay],
            "mode": mode,
        })
        item["anchor_id"] = f"ANC_{item['clip_id']}_EXP_V2"
        item.pop("from", None)
        if continuity_from:
            item["from"] = continuity_from
        if source:
            item["source"] = source
        if refs is not None:
            item["refs"] = refs
        if review_ko:
            item["review_ko"] = review_ko
        else:
            item.pop("review_ko", None)
        plan = {
            "actions": actions or ["프롬프트 수정"],
            "priority": priority,
            "reason": reason,
            "next": next_step,
            "implementation": "experiment_v2_ready",
            "source_clip": base_id,
        }
        return item, plan

    rewrites: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}

    rewrites["SC01-001_M02"] = [
        make(
            "SC01-001_M02", title="무너진 용궁에서의 발견", seconds=9,
            anchor="""A single cinematic opening frame inside an immense ruined deep-sea dragon palace. A cracked coral pillar leans above an empty stone floor; cold blue light cuts through drifting marine dust. Young Mir lies motionless but clearly readable beside the pillar, small against the architecture, with his wounded blue-silver body and tail crystal unobstructed.""",
            relay=[(9, "Begin in the supplied wide underwater composition. The cracked pillar gives way and settles behind Young Mir in one heavy collapse, sending a slow cloud of marine dust across the blue light. The camera performs one restrained forward drift through the settling dust until wounded Young Mir becomes the clear subject. He remains on the floor, opens his eyes only slightly and gives one weak breath. End on the discovery of his face and faint tail-crystal glow.")],
            actions=["컷 분할", "새 앵커 필요"], reason="붕괴와 미르 발견을 하나의 시각 사건으로 제한", next_step="붕괴 뒤 미르 얼굴과 꼬리 결정이 읽히는 후보를 비교",
        ),
        make(
            "SC01-001_M02", clip_id="SC01-001_M02B", title="해류에 떠밀리는 미르", seconds=7,
            source="EP01 S#1 — 무너진 용궁에서 의식을 잃고 해류에 떠밀리는 미르",
            anchor="""A cinematic underwater medium-wide opening frame beyond the collapsed palace pillar. Wounded Young Mir is already suspended sideways in a clear current channel, limbs loose, eyes barely open and tail crystal dim. Ruined palace stones recede behind him while an unobstructed diagonal path leads upward into darker water.""",
            relay=[(7, "Begin with Young Mir already weightless in the visible current. The current carries his whole body along the open diagonal path in one continuous drift while the camera tracks beside him at the same slow speed. His limbs and fin-like wings trail naturally; he makes one weak attempt to lift his head, and the tail crystal flickers once before dimming. End with the palace ruins falling farther behind him.")],
            actions=["컷 분할", "새 앵커 필요"], reason="해류 이동을 붕괴와 분리해 한 방향의 신체 운동만 생성", next_step="몸이 회전·복제되지 않고 측면으로 떠밀리는지 리뷰",
        ),
    ]

    rewrites["SC01-001_M03"] = [
        make(
            "SC01-001_M03", title="검은 물결의 추격", seconds=10,
            anchor="""A vertical deep-sea pursuit opening frame. Young Mir is already swimming weakly upward inside a narrow diagonal shaft of blue light. Far below, the Black Tide rises as one coherent mass of living black water. A broad band of clear water separates Mir from the threat and the ascent route remains unobstructed.""",
            relay=[(10, "Continue from the supplied pursuit geometry. Young Mir climbs weakly but continuously through the blue shaft while the camera tracks upward beside him. The Black Tide closes part of the clear gap from below, its water surface briefly forming unstable hand-like ridges before flowing back into the same mass. Mir looks down once, then forces one stronger upward stroke. End before physical contact.")],
            actions=["컷 분할", "새 앵커 필요"], reason="추격 접근만 남겨 이동축과 두 피사체의 깊이 분리를 고정", next_step="검은 물결이 별도 인간 캐릭터로 변하지 않는지 리뷰",
        ),
        make(
            "SC01-001_M03", clip_id="SC01-001_M03B", title="꼬리 결정의 방어", seconds=8,
            source="EP01 S#1 — 검은 물결이 닿기 직전 미르의 꼬리 결정이 방어 파동을 냄",
            anchor="""A tense underwater opening frame at the moment before contact. Exhausted Young Mir hangs above the rising Black Tide with his bright tail crystal positioned between his body and the nearest black-water ridge. The blue ascent path is visible above him and both entities remain physically separate.""",
            relay=[(8, "Begin at the supplied near-contact state. Young Mir curls protectively around his brightening tail crystal. The crystal releases one expanding blue pulse that presses the nearest black water downward as a single fluid mass. The camera gives one short upward lift with Mir as the clear water gap reopens. Mir uses that opening for one final ascent toward the brighter water above. End with the Black Tide below and Mir still moving upward.")],
            actions=["컷 분할", "새 앵커 필요"], reason="방어 파동과 탈출만 한 인과 단위로 분리", next_step="한 번의 파동과 미르의 상승이 명확한 후보를 비교",
        ),
    ]

    rewrites["SC01-001_M04"] = [make(
        "SC01-001_M04", title="기억하지 마라", seconds=12,
        anchor="""A single submerged memory-space with Young Mir floating at center. Behind him, one broken dragon-palace gate and distant sleeping dragon silhouettes are visible through blue haze; black root-like darkness already frames the outer edges. The center remains open around Mir and every element belongs to one coherent dream space.""",
        relay=[
            (6, "The camera slowly approaches Young Mir while the broken gate behind him becomes clearer. The distant sleeping dragon silhouettes remain still. A deep unseen voice says once in Korean, \"기억하지 마라.\" Mir draws his limbs inward and looks toward the unseen source."),
            (6, "Black root-like darkness advances from the outer edges toward the open blue center. The same unseen voice says once in Korean, \"그러면 아프지 않다.\" Mir recoils as one bright seam of storm light opens behind him and pulls the memory apart."),
        ],
        reason="추상적 플래시 대신 공간 안에서 진행되는 두 개의 명확한 시각 박자로 재작성", next_step="음성 순서와 검은 뿌리의 가장자리 침범 정도를 리뷰",
    )]

    rewrites["SC01-002_M01"] = [make(
        "SC01-002_M01", title="물고기를 겨누는 루아", seconds=4,
        anchor="""A cinematic low side opening frame on a wet stone breakwater. Lua is already in a compact low aiming stance with both hands below her shoulders. Her complete fishing spear points toward a clearly visible small fish under the shallow water, with a broad clean gap between spear tip and fish. Her front sandal is secure on the stone; feet, spear tip, fish and water contact area are readable together.""",
        relay=[(4, "Begin in the supplied low aiming state and hold the spatial relationship long enough to read Lua, the complete spear and the separate fish. The fish moves gently sideways under the shallow water while Lua follows it with only a small controlled adjustment of the low spear point. The camera makes one subtle forward push along the existing spear line and settles on Lua's focused eyes. End on the held breath immediately before the thrust.")],
        review_ko="루아·작살 전체·분리된 물고기·얕은 물 접촉점이 한 프레임에서 먼저 읽힌다. 루아는 낮은 자세를 유지하며 물고기의 옆 이동을 작살 끝으로 천천히 따라간다. 카메라는 작살선을 따라 짧게 접근하고 실제 찌르기 직전의 숨을 멈춘 순간에 끝난다.",
        actions=["프롬프트 수정", "새 앵커 필요"], reason="SC01-002 전체 리뷰 결론대로 실패율이 높은 찌르기·낙상을 제거하고 조준 상태만 독립", next_step="M01은 조준용 편집 컷, M01B는 낙상 결과, M01C는 회복으로 평가",
    )]

    rewrites["SC01-002_M04"] = [
        make(
            "SC01-002_M04", title="늙은 어부의 부름", seconds=7,
            anchor="""A grounded medium-wide two-shot on the wet morning breakwater. Lua stands frame-left holding her fishing spear safely down. The Old Fisherman has nearly reached her from frame-right. Both full upper bodies, their clear eye line and open space between them are visible; the distant cave is not the subject yet.""",
            relay=[(7, "The Old Fisherman completes two calm steps and stops in the open space beside Lua. The camera remains steady. He looks directly at her and says once in natural Korean, \"루아야.\" Lua straightens, keeps the spear down and answers once, \"네!\" Hold their different reactions in the same two-shot.")],
            actions=["컷 분할"], reason="호명과 답변을 독립된 짧은 2인 연기 컷으로 분리", next_step="화자 입 모양과 루아의 즉각적인 자세 변화만 리뷰",
        ),
        make(
            "SC01-002_M04", clip_id="SC01-002_M04B", title="동굴을 향한 경고", seconds=10,
            source="EP01 S#2 — 늙은 어부가 루아에게 바다와 동굴을 경고함",
            anchor="""A cinematic side two-shot on the same wet breakwater. The Old Fisherman and Lua are already standing together, both angled toward a distant cliff cave visible across the open background. Lua holds her spear low. The Fisherman's calm profile, Lua's listening reaction and the cave share one clear sightline.""",
            relay=[(10, "Begin from the shared cave sightline. The Old Fisherman says in natural Korean, \"바다는 고집으로 되는 게 아니다. 오늘은 동굴 쪽 가지 마라.\" Lua remains silent and lowers her eyes for one beat. As he adds, \"폭풍 뒤에는 뭐가 밀려올지 몰라.\" the camera performs one slow motivated lateral slide that strengthens the visual line from both characters to the distant cave. End with Lua following his gaze.")],
            actions=["컷 분할", "새 앵커 필요"], reason="경고와 동굴 시선을 하나의 카메라 목적으로 통합", next_step="대사 중 인물 고정과 동굴이 읽히는 최종 구도를 리뷰",
        ),
    ]

    rewrites["SC01-003_M01"] = [
        make(
            "SC01-003_M01", title="동굴의 푸른 길", seconds=8,
            anchor="""A cinematic cave-entry opening frame. Lua stands just inside a dark wet coastal cave, alone, with the entrance light behind her and a faint blue glow far ahead. Her complete spear touches the shallow water in front of her. A continuous open path connects her feet to the distant glow.""",
            relay=[(8, "Lua advances alone through the supplied open cave path, using the spear tip to test the shallow water before each careful step. The camera performs one slow rear three-quarter tracking move at walking speed. Reflected blue light gradually strengthens on the wet rock and Lua's face. She stops when a small sound comes from ahead.")],
            actions=["컷 분할"], reason="진입과 수심 확인만 남겨 하나의 탐색 이동으로 구성", next_step="작살 접촉점·발걸음·푸른빛 방향이 유지되는지 리뷰",
        ),
        make(
            "SC01-003_M01", clip_id="SC01-003_M01B", title="동굴 속의 대답", seconds=8,
            source="EP01 S#3 — 루아가 동굴 안에서 허세 섞인 호출을 하고 작은 울음소리를 들음",
            anchor="""A medium opening frame deeper inside the same coastal cave. Lua has stopped beside a wet rock wall, spear held low, and faces an empty dark crevice illuminated by a faint blue reflection. Her cautious face and the empty crevice are readable together.""",
            relay=[(8, "Begin with Lua studying the empty crevice. The camera makes one very slow push toward her and the blue reflection. Lua gathers courage and says in natural Korean, \"나와라. 내가 마을에서 제일 무서운 사람은 아니지만, 상당히 귀찮은 사람이다.\" She closes her mouth. A tiny squeak answers from inside the crevice, and Lua's forced confidence changes into surprised curiosity. End before the creature is revealed.")],
            actions=["컷 분할", "새 앵커 필요"], reason="허세 대사와 보이지 않는 소리 반응을 한 연기 단위로 분리", next_step="추가 생물 생성 없이 루아의 표정 변화가 읽히는지 리뷰",
        ),
    ]

    rewrites["SC01-003_M02"] = [
        make(
            "SC01-003_M02", title="푸른 실루엣의 발견", seconds=8,
            anchor="""A low over-Lua-shoulder opening frame inside the wet cave. Lua kneels at a respectful distance, her spear resting safely along the ground. Inside a blue-lit rock crevice, only the clear outline of wounded Young Mir's horns, face and curled tail is visible. A clean strip of wet stone separates them.""",
            relay=[(8, "Begin with the supplied separation between Lua and the crevice. The camera makes one slow low push past Lua's shoulder toward the blue-lit opening. Young Mir shifts weakly, revealing his horns, blue-silver face and tail crystal as parts of one small dragon body. Lua lowers her shoulders and whispers once in natural Korean, \"방금 귀여웠는데?\" End with Mir still inside the crevice.")],
            actions=["컷 분할", "새 앵커 필요"], reason="접근과 미르 공개를 하나의 발견 동작으로 제한", next_step="미르 신체가 조각나지 않고 한 개체로 드러나는지 리뷰",
        ),
        make(
            "SC01-003_M02", clip_id="SC01-003_M02B", title="첫 눈맞춤", seconds=7,
            source="EP01 S#3 — 루아와 어린 미르가 처음 눈을 맞춤",
            anchor="""An intimate but clearly separated two-character opening frame in the cave. Wounded Young Mir is already fully visible on the wet stone at frame-right, eyes partly closed. Lua kneels at frame-left with empty open hands near her knees and her spear resting behind her. Their faces and the open gap between them are readable.""",
            relay=[(7, "Young Mir slowly opens his large blue eyes and raises his gaze to Lua. The camera performs one restrained arc that settles into their shared eye line without closing the physical gap. Lua holds still, then quietly says in natural Korean, \"너… 도마뱀은 아니지?\" After one breath she adds, \"말도 안 돼.\" End on sustained eye contact.")],
            actions=["컷 분할", "새 앵커 필요"], reason="첫 눈맞춤과 루아의 반응만 독립시켜 2인 정체성 혼합을 줄임", next_step="루아 인간·미르 용의 신체 분리와 시선 연결을 리뷰",
        ),
    ]

    rewrites["SC01-003_M03"] = [
        make(
            "SC01-003_M03", title="도움을 내미는 손", seconds=8,
            anchor="""A quiet cave-floor opening frame. Lua crouches frame-left with one empty hand resting near her own knee; Young Mir lies weakly frame-right beyond a clear gap of wet stone. Lua's spear is set down behind her. Both complete bodies and the path between her hand and Mir are unobstructed.""",
            relay=[(8, "Lua sees Young Mir try and fail to stand. Her expression softens. Keeping her body low, she slowly extends one open hand across the clear gap and stops before touching him. The camera makes one gentle low push along the path of her hand. Lua says softly in natural Korean, \"야, 괜찮아. 안 잡아먹어. 나도 오늘 아침 못 먹었거든.\" Mir watches her fingers and gathers strength.")],
            actions=["컷 분할"], reason="접촉 전 안심과 손 내밀기만 보여 주어 손·입 접촉 오류를 차단", next_step="손가락 수와 두 신체 사이 간격을 우선 리뷰",
        ),
        make(
            "SC01-003_M03", clip_id="SC01-003_M03B", title="살려달라는 이빨", seconds=6,
            source="EP01 S#3 — 미르가 이미 루아의 손가락을 약하게 물고 도움을 청함",
            anchor="""A close side opening frame on the cave floor after contact. Young Mir's small mouth is already gently closed around the tip of one clearly visible Lua finger, while Lua supports her wrist with the other hand. Mir's weak body remains on the stone and the contact point is unobstructed; this is a desperate hold, not an attack.""",
            relay=[(6, "Begin with the gentle bite already established. Lua gives one startled flinch and cries once in natural Korean, \"악!\" The camera holds close on the readable contact point as Mir's jaw remains weak and his body pulls closer to her hand for support. Lua's fear changes into understanding; she steadies her wrist instead of pulling away. End with Mir still clinging gently and both bodies anatomically separate.")],
            actions=["컷 분할", "새 앵커 필요"], reason="생성하기 어려운 순간 접촉을 이미지에서 이미 성립시킨 뒤 반응만 생성", next_step="손가락 변형과 미르의 공격적 움직임 여부를 리뷰",
        ),
    ]

    rewrites["SC01-003_M04"] = [make(
        "SC01-003_M04", title="용심 공명", seconds=15,
        anchor="""A coherent submerged vision space. One broken dragon-palace gate frames a distant blue heart-light. Sleeping colossal dragon silhouettes line the deep background while black roots already wrap the outer architecture. A clear open corridor leads from the gate toward the blue heart; no human or small dragon body is visible.""",
        relay=[
            (5, "A single blue pulse enters through the broken gate and illuminates the open central corridor. The camera accelerates gently forward with that pulse."),
            (5, "The same forward move passes the still sleeping dragon silhouettes while black roots tighten around the outer columns. The blue path remains clear at center."),
            (5, "The camera reaches the distant heart-light as it contracts once, then releases one luminous wave back through the corridor, carrying the vision toward waking reality."),
        ],
        reason="공명을 하나의 전진 카메라 축과 세 개의 긍정형 공간 변화로 통일", next_step="장면 점프보다 동일 공간의 전진 이동으로 보이는지 리뷰",
    )]

    rewrites["SC01-003_M05"] = [make(
        "SC01-003_M05", title="내가 본 거야", seconds=14,
        anchor="""A stable post-vision cave opening frame. Lua kneels frame-left, breathing hard and staring at a fresh blue mark on her lowered wrist. Wounded Young Mir lies separately frame-right with his chest mark faintly glowing. Their faces, both marks and the open wet stone between them are readable.""",
        relay=[
            (7, "The camera begins one slow continuous push toward Lua while keeping Young Mir readable at the edge of the frame. Lua studies the mark without lifting her hand toward her face and asks once in natural Korean, \"방금… 내가 본 거야?\" Mir answers with one weak chirp."),
            (7, "Continue the same slow push. Lua moves only her eyes from her wrist to Mir's matching chest mark, then meets his gaze and asks once in natural Korean, \"너 대체 뭐야?\" Both remain physically separate and still as the two blue marks pulse together once."),
        ],
        reason="손동작을 줄이고 루아의 시선과 동일한 느린 카메라 접근으로 반응을 집중", next_step="두 문양 위치와 화자 한 명이 안정적으로 유지되는지 리뷰",
    )]

    rewrites["SC01-003_M06"] = [
        make(
            "SC01-003_M06", title="동굴 밖의 부름", seconds=7,
            anchor="""A full-body opening frame inside the clean coastal cave. Lua is already standing and carrying Young Mir securely wrapped in one continuous piece of her outer cloth against her chest. Mir's small dragon face remains visible, and his nose-to-tail-base body length is no longer than Lua's torso. The bright cave exit and the smooth dark rock path are directly ahead.""",
            relay=[(7, "Begin with Young Mir already wrapped and supported in Lua's arms. Lua adjusts the same cloth once, sighs and says in natural Korean, \"하. 나 진짜 사고 쳤다.\" She walks along the visible smooth-rock path toward the bright cave exit. The camera performs one steady rear-side tracking move at her walking speed, keeping Mir's dragon face, Lua's complete steps and the exit direction readable.")],
            actions=["컷 분할"], reason="외부 부름과 루아의 결정을 접촉 없는 반응 컷으로 분리", next_step="화면 밖 인물이 생성되지 않고 루아의 결정이 읽히는지 리뷰",
        ),
        make(
            "SC01-003_M06", clip_id="SC01-003_M06B", title="사고를 품에 안고", seconds=7,
            source="EP01 S#3 — 이미 천에 감싼 미르를 안고 루아가 동굴을 나감",
            anchor="""A cinematic opening frame at the clean coastal cave entrance. Lua has stopped at the threshold while still holding Young Mir securely wrapped in the exact same continuous outer cloth against her chest. Mir remains a small dragon hatchling, fully wrapped except for his visible face. Smooth dark cave rock is behind them and the bright coast is ahead.""",
            relay=[(7, "Begin with Lua already stopped at the threshold and Young Mir still secured inside the same cloth wrap. An unseen villager calls once from outside in Korean, \"루아! 거기 있냐?\" Lua tightens her supporting arm, turns her body slightly to shield Mir and listens toward the coast. The camera makes one restrained lateral move that keeps the wrapped dragon, Lua's guarded profile and the empty exit visible. End with the wrap unchanged.")],
            actions=["컷 분할", "새 앵커 필요"], reason="감싸는 순간을 이미지에서 완료하고 운반·퇴장만 생성", next_step="천·팔·미르 신체가 합쳐지지 않는지 리뷰",
        ),
    ]

    rewrites["SC01-004_M01"] = [
        make("SC01-004_M01", title="비밀스러운 귀가", seconds=7,
             anchor="""Inside Lua's small coastal house in daylight, Lua has just entered while already holding cloth-wrapped Young Mir securely. The open door is directly behind her; a clear path leads to a shallow water bowl. Mir's small dragon face remains visible and separate from the cloth. One palm-sized spiral shell is already established on the low table beside the bowl.""",
             relay=[(7, "Lua steps fully inside with wrapped Young Mir, closes the door with one foot and listens in stillness for adults outside. The camera makes one small lateral move that reveals the empty room and the water bowl ahead. Mir peeks from the cloth. Lua looks down and says once in natural Korean, \"진짜네. 꿈이면 지금쯤 깨야 하는데.\"")],
             actions=["컷 분할", "새 앵커 필요"], reason="도착·문 닫기·상태 확인만 한 컷으로 제한", next_step="문 동작과 품 안의 미르 신체 분리를 리뷰"),
        make("SC01-004_M01", clip_id="SC01-004_M01B", title="물그릇의 첫 휴식", seconds=7,
             source="EP01 S#4 — 루아가 미르를 얕은 물그릇에 내려놓음",
             anchor="""A low side opening frame beside the shallow water bowl. Young Mir is already supported just above the water by Lua's two hands, feet and tail clear of the bowl rim. His small dragon body fits completely inside the bowl. The same palm-sized spiral shell remains visible on the low table farther behind them.""",
             relay=[(7, "Lua lowers Young Mir the final short distance into the shallow bowl in one careful continuous motion. The camera holds low on the readable contact as his feet and tail enter the water and his tense body visibly relaxes. Lua releases support only after he is stable and asks in natural Korean, \"너 물에서 자는 거야? 좋겠다. 난 그러면 죽는데.\"")],
             actions=["컷 분할", "새 앵커 필요"], reason="들기와 내려놓기를 분리하고 물 접촉을 단일 동작으로 생성", next_step="손·날개·그릇 테두리의 교차 오류를 리뷰"),
        make("SC01-004_M01", clip_id="SC01-004_M01C", title="마른 생선의 거절", seconds=7,
             source="EP01 S#4 — 미르가 루아가 내민 마른 생선을 거부함",
             anchor="""A clean medium two-shot beside the same bowl. Young Mir's small dragon body sits fully inside the shallow water at frame-right. Lua kneels frame-left and holds one small dry fish at arm's length, with a clear air gap between the fish and Mir's face. The same palm-sized spiral shell is already visible on the low table in the background.""",
             relay=[(7, "Lua moves the single dry fish slightly closer across the clear gap. Young Mir smells it, recoils once with a clear disgusted expression and settles back inside the bowl. Lua stops her hand and asks in natural Korean, \"아니, 바다에서 왔잖아. 생선 안 먹어?\" The camera remains steady so the fish ownership and rejection are readable.")],
             actions=["컷 분할", "새 앵커 필요"], reason="생선 제안과 거부만 독립시켜 소품 복제와 접촉 오류를 제한", next_step="생선 한 개·루아 손·미르 얼굴 사이 간격을 리뷰"),
        make("SC01-004_M01", clip_id="SC01-004_M01D", title="조개껍데기의 선택", seconds=7,
             source="EP01 S#4 — 미르가 조개껍데기를 선택해 품음",
             anchor="""A low intimate opening frame inside the same house. Young Mir stands beside the bowl facing the same palm-sized spiral shell already resting on the edge of the low table. Lua kneels behind him at a respectful distance with empty hands. A short unobstructed floor path leads from Mir to the low table, and the shell is small enough for the dragon hatchling to hold.""",
             relay=[(7, "Young Mir crawls along the short clear path to the low table, reaches the already established single shell, touches it with his nose and curls both forelimbs around it in one affectionate choice. The camera makes one gentle low push toward Mir and the shell. Lua watches with amused disbelief and says in natural Korean, \"입맛도 귀족이네.\" End with Mir resting against the same shell.")],
             actions=["컷 분할", "새 앵커 필요"], reason="이동과 조개 선택을 하나의 짧은 소품 상호작용으로 분리", next_step="조개가 신체와 합쳐지지 않고 한 개로 유지되는지 리뷰"),
    ]

    rewrites["SC01-004_M02"] = [
        make("SC01-004_M02", title="문을 막는 루아", seconds=8,
             anchor="""A tense interior opening frame. Lua stands between the closed house door and Young Mir, who remains beside the water bowl with his shell. Lua's glowing wrist is low at her side. The straight spatial line door–Lua–Mir is clearly readable.""",
             relay=[(8, "Muffled adult voices outside say in Korean, \"불길하다! 바다에 돌려보내!\" Lua looks from her wrist to the closed door, then takes one firm sideways step into the center of the door–Mir line. The camera makes one slow push toward her protective stance. Mir stays beside the bowl and watches her. End with Lua fully blocking the door.")],
             actions=["컷 분할", "새 앵커 필요"], reason="상상 목소리와 문 차단을 하나의 명확한 보호 행동으로 제한", next_step="추가 성인 생성 없이 공간선과 루아의 차단 자세를 리뷰"),
        make("SC01-004_M02", clip_id="SC01-004_M02B", title="당분간 여기 있어", seconds=10,
             source="EP01 S#4 — 루아가 미르를 숨겨주되 밥값을 요구함",
             anchor="""A quiet medium two-shot inside the same house after the danger passes. Lua sits on the floor facing Young Mir beside the bowl. The closed door remains behind Lua, and the shell remains beside Mir. Their faces and the open conversational space are clear.""",
             relay=[(10, "Lua leans slightly toward Young Mir and says in natural Korean, \"안 돼. 그러니까… 당분간 여기 있어.\" She lets the promise settle, then straightens with mock responsibility and adds, \"근데 밥값은 해야 돼. 물 좀 데워준다든가?\" The camera performs one gentle push across the conversational space. Mir tilts his head once after she finishes.")],
             actions=["컷 분할", "새 앵커 필요"], reason="보호 결정과 밥값 농담을 안정적인 앉은 대화 컷으로 분리", next_step="루아 단독 화자와 미르의 마지막 반응을 리뷰"),
    ]

    rewrites["SC01-004_M03"] = [
        make("SC01-004_M03", title="작은 물방울", seconds=7,
             anchor="""A close side opening frame beside the bowl. Young Mir faces Lua with his mouth slightly open; one small clear water droplet is already floating halfway between Mir and Lua's forehead. Lua waits completely still. The droplet path and both faces are unobstructed.""",
             relay=[(7, "Begin with the single droplet already suspended between them. It travels slowly along the clear path and touches the center of Lua's forehead with one tiny splash. The camera holds the side geometry without chasing the droplet. Lua closes her eyes at contact and remains still for one silent beat; Mir watches hopefully.")],
             actions=["컷 분할", "새 앵커 필요"], reason="생성하기 어려운 물방울 발생은 앵커에서 완료하고 이동·접촉만 생성", next_step="물방울 한 개와 이마 접촉 위치를 리뷰"),
        make("SC01-004_M03", clip_id="SC01-004_M03B", title="가능성은 있다", seconds=9,
             source="EP01 S#4 — 물방울 뒤 루아의 반응과 두 문양의 공명",
             anchor="""A stable medium two-shot immediately after the droplet lands. Lua sits with one tiny bead of water on her forehead; Young Mir waits beside the bowl. Lua's wrist mark and Mir's chest mark are both visible but dim, with their bodies clearly separated.""",
             relay=[(9, "Lua opens her eyes, looks at hopeful Young Mir and says dryly in natural Korean, \"그래. 가능성은 있다.\" Mir gives one proud chirp and lifts his chest. Lua smiles despite herself. Their two visible marks then brighten in the same single pulse, drawing both gazes downward. The camera makes one slow push toward the shared blue light and settles as they become still.")],
             actions=["컷 분할", "새 앵커 필요"], reason="대사·자부심 반응·표식 공명을 물리 접촉 뒤 별도 컷으로 분리", next_step="두 표식 위치와 동일한 한 번의 발광을 리뷰"),
    ]

    rewrites["SC01-005_M01"] = [make(
        "SC01-005_M01", title="같은 꿈의 시작", seconds=15,
        anchor="""A quiet cinematic night interior. Lua sleeps on the wooden bed at frame-left while Young Mir sleeps curled in the shallow bowl at frame-right. Their wrist and chest marks are both visible across a clear dark gap; the covered window and room layout remain still.""",
        relay=[
            (8, "The camera makes one almost imperceptible push through the still room. Lua and Young Mir remain asleep as their two marks begin one slow synchronized pulse across the dark gap. Mir starts trembling and Lua's sleeping expression mirrors the same fear."),
            (7, "The synchronized blue light expands gently across the floor and walls in one continuous wave. The physical room remains visible while its edges gradually become submerged palace shapes, carrying both sleepers into the same dream without an abrupt cut."),
        ],
        reason="세 사건을 동시 박동에서 공간 용해로 이어지는 한 방향 전환으로 단순화", next_step="집 구조가 갑자기 교체되지 않고 점진적으로 꿈에 녹는지 리뷰",
    )]

    rewrites["SC01-005_M02"] = [make(
        "SC01-005_M02", title="버려진 새끼 용", seconds=14,
        anchor="""A coherent ruined dragon-palace dream. Young Mir stands small before a blue heart stone wrapped by black roots. One enormous crown-horned shadow rises directly from Mir's feet onto the broken wall behind him, clearly his possible future silhouette rather than a second creature.""",
        relay=[
            (7, "The camera slowly approaches Young Mir and the blue heart while the black roots tighten around the outer ruins. The single enormous shadow remains physically connected to Mir's feet. A deep unseen voice says once in Korean, \"너는 왕자가 아니다.\" Mir lowers his head."),
            (7, "Continue the same approach. The unseen voice says once in Korean, \"버려진 새끼 용이다.\" The connected future shadow contracts toward Mir as the heart-light dims. Mir trembles, and one crack of blue light opens through the dream behind him."),
        ],
        reason="미래 그림자를 미르 발에서 이어진 단일 정체성으로 고정하고 음성을 두 박자로 분리", next_step="두 번째 용으로 인식되지 않는지와 음성 순서를 리뷰",
    )]

    rewrites["SC01-005_M03"] = [
        make("SC01-005_M03", title="잠에서 깬 루아", seconds=8,
             anchor="""A night house opening frame immediately after the nightmare. Lua is already awake and kneeling beside the shallow bowl. Trembling Young Mir remains inside the bowl within reach. Lua's two empty hands are open near him, and both complete bodies are clearly separated.""",
             relay=[(8, "Lua sees Young Mir trembling, slides both hands beneath his complete body and lifts him once into a secure hold against her chest. The camera makes one restrained upward correction with the lift. Lua says in natural Korean, \"뭐야… 야. 괜찮아. 나 여기 있어.\" Mir remains frightened but settles slightly in her arms.")],
             actions=["컷 분할", "새 앵커 필요"], reason="깨기와 안아 들기만 한 번의 접촉 동작으로 제한", next_step="팔·날개·꼬리의 분리와 들어 올리는 한 번의 동작을 리뷰"),
        make("SC01-005_M03", clip_id="SC01-005_M03B", title="너도 무서운 거구나", seconds=9,
             source="EP01 S#5 — 품에 안긴 미르와 루아가 공포를 공유하고 표식이 진정됨",
             anchor="""An intimate stable opening frame in the night house. Lua is already seated with Young Mir securely cradled against her chest. Lua's wrist mark rests near Mir's face and Mir's chest mark is visible; both glow softly and their anatomies remain distinct.""",
             relay=[(9, "Begin with the embrace already stable. A shared pulse passes between the two visible marks. Lua feels the unfamiliar fear, takes one breath and says in natural Korean, \"이거… 내 무서움이 아니야. 너도 무서운 거구나.\" She tightens the embrace slightly. Mir touches his nose gently to her glowing wrist, and both lights soften together. The camera makes one slow intimate push and holds.")],
             actions=["컷 분할", "새 앵커 필요"], reason="복잡한 들어 올리기 뒤 감정 공유·표식 진정만 별도 컷으로 분리", next_step="접촉점과 두 표식의 동시 약화를 리뷰"),
    ]

    rewrites["SC01-005_M04"] = [
        make("SC01-005_M04", title="고요해진 바다", seconds=8,
             anchor="""A night interior opening frame. Lua stands a few steps from the covered window while Young Mir remains safely behind her near the bowl. The room is still, and a thin cold reflection outlines the window. Lua and the window share one clear sightline.""",
             relay=[(8, "The ordinary sea sound fades into unnatural silence. Young Mir gives one low warning growl behind Lua. She turns toward the window and walks the short clear path to it while the camera tracks slowly beside her. Lua lifts only the edge of the covering and looks outside; cold sea light reaches her face. End before the outside creature is shown.")],
             refs=[ref(1, "lua"), ref(2, "mir")], actions=["컷 분할", "새 앵커 필요"], reason="실내 발견 반응과 외부 위협 공개를 서로 다른 공간 컷으로 분리", next_step="실내 이동과 창가 시선만 생성되는지 리뷰"),
        make("SC01-005_M04", clip_id="SC01-005_M04B", title="집을 향하는 검은 해파리", seconds=10,
             source="EP01 S#5 — 검은 해파리가 밤바다 위에서 루아의 집을 향함",
             anchor="""An exterior cinematic night-coast opening frame. The Black Jellyfish floats alone above the silent sea, its large translucent black bell filled with rotating ink-like smoke and long tentacles trailing into the water. Lua's small warmly lit house is visible far across the shore, establishing one clear direction between creature and destination.""",
             relay=[(10, "Begin with the Black Jellyfish suspended above the silent water and the distant house fixed in the same wide composition. Ink-like smoke rotates once inside its translucent bell. The creature slowly turns its front toward the house, then begins one deliberate glide along the established coastal direction while the camera makes a restrained parallel drift. Lua's off-screen voice asks in natural Korean, \"저게… 널 찾으러 온 거야?\" End with the house slightly closer and the tentacles still trailing through the water.")],
             refs=[ref(1, "jellyfish")], actions=["컷 분할", "새 앵커 필요"], reason="외부 위협을 단일 피사체와 명확한 목적지로 구성", next_step="해파리 해부학·이동 방향·집의 위치 관계를 리뷰"),
    ]

    # SC01-002 전체 리뷰 보정:
    # 안정된 1·2인 대화와 명확한 육상 이동은 분할하지 않는다.
    # 실제 분할은 접촉·낙상·들기처럼 물리 상태가 급변하는 구간에만 적용한다.
    rewrites.pop("SC01-002_M04", None)
    base_plan = deepcopy(base_plan)
    base_plan["SC01-002_M04"] = {
        "actions": ["유지"],
        "priority": "P2",
        "reason": "저장 리뷰 4개 중 정상 후보 2개가 확보됐고 실패는 참조 이미지 재등장 현상임",
        "next": "15초 2인 대화 구조는 유지하고 참조 이미지 재등장은 후보 리뷰·후처리 항목으로 분리",
    }

    rewrites["SC01-003_M01"] = [make(
        "SC01-003_M01", title="해안 동굴 진입", seconds=16,
        anchor="""A cinematic cave-entry opening frame. Lua stands alone just inside a dark wet coastal cave, with the entrance light behind her and one faint blue glow far ahead. Her complete fishing spear touches the shallow water in front of her. A continuous unobstructed path connects her feet, the wet cave floor and the distant glow.""",
        relay=[
            (8, "Begin from the supplied path. Lua advances alone, using the spear tip to test the shallow water before each careful step. The camera performs one smooth rear three-quarter tracking move at her walking speed, keeping every foot contact on the visible cave floor and the blue glow on the same travel axis."),
            (8, "Lua stops when the blue reflection strengthens on the rock ahead. The camera settles into a medium side composition with Lua and an empty crevice readable together. She gathers courage and says in natural Korean, \"나와라. 내가 마을에서 제일 무서운 사람은 아니지만, 상당히 귀찮은 사람이다.\" Her lips close. A tiny squeak answers from the empty crevice, and her expression changes from forced confidence to curiosity."),
        ],
        actions=["프롬프트 수정"], priority="P1",
        reason="M05에서 성공한 가시적 경로·한 방향 이동·동기 있는 추적과 M03의 단독 화자 구조를 결합",
        next_step="추가 인물·생물 없이 발 접촉, 작살 소유, 마지막 표정 변화만 리뷰",
    )]

    rewrites["SC01-003_M02"] = [make(
        "SC01-003_M02", title="작은 용과의 첫 눈맞춤", seconds=15,
        anchor="""A low cinematic two-character opening frame inside the wet cave. Lua kneels frame-left at a respectful distance with her complete spear resting safely behind her. Wounded Young Mir lies frame-right inside weak blue light, already readable as one complete small dragon body. A broad clean strip of wet stone separates Lua's empty hands from Mir.""",
        relay=[
            (7, "Begin from the supplied separated two-character composition. The camera makes one restrained slow push across the clean strip of wet stone. Young Mir shifts weakly, revealing his horns, blue-silver face and tail crystal as parts of the same body. Lua keeps her hands low and whispers once in natural Korean, \"방금 귀여웠는데? 너… 도마뱀은 아니지?\""),
            (8, "Continue the same slow push without changing positions. Young Mir opens his large blue eyes and raises his gaze to Lua. Lua becomes still, sustains the eye line and says once in natural Korean, \"말도 안 돼.\" Only Lua speaks; Mir answers with one small breath. End on their first clear eye contact with the physical gap preserved."),
        ],
        actions=["프롬프트 수정", "새 앵커 필요"], priority="P1",
        reason="M02의 두 피사체 고정과 화자 분리, M03의 단일 느린 푸시를 첫 대면에 확장",
        next_step="루아 인간·미르 용의 정체성 분리, 한 명의 화자, 열린 간격을 리뷰",
    )]

    final_clips: list[dict[str, Any]] = []
    final_plan: dict[str, dict[str, Any]] = {}
    for item in base_clips:
        replacements = rewrites.get(item["clip_id"])
        if replacements:
            for replacement, plan in replacements:
                final_clips.append(replacement)
                final_plan[replacement["clip_id"]] = plan
        else:
            kept = deepcopy(item)
            final_clips.append(kept)
            plan = deepcopy(base_plan[item["clip_id"]])
            plan["implementation"] = "locked_from_review"
            plan["source_clip"] = item["clip_id"]
            final_plan[item["clip_id"]] = plan
    return final_clips, final_plan
