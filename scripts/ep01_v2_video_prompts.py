"""Detailed EP01 V2 video prompts, organized scene by scene.

These prompts preserve the video-first shot plan while restoring the action,
camera, continuity, dialogue, and end-state detail learned from candidate reviews.
"""

from __future__ import annotations

from typing import Any


def segment(seconds: float, prompt: str) -> dict[str, Any]:
    return {"seconds": seconds, "prompt": prompt.strip()}


SC01_001_VIDEO_BEATS = {
    "SC01-001_V01": [
        segment(6, """Begin in the supplied immense storm-ocean anchor. Keep the coast far screen-right and the foreground sea empty of any visible creature. Black wave ridges cross the frame at different depths while diagonal rain briefly appears in the lightning. The camera holds the horizon and descends very slowly toward the distant trough, creating scale without rushing forward. During this first half, the ocean and weather provide all visible movement; the tiny cobalt point remains deep below the surface and does not yet reveal a body."""),
        segment(6, """Continue the same unbroken coastward composition. As the nearest wave passes, the single cobalt-blue point becomes clearly readable beneath the distant trough, pulses once, and travels a short distance under the water toward screen-right. Let the light illuminate only a narrow volume of water around itself, suggesting a living presence without showing Young Mir's silhouette. The camera completes its restrained descent and settles with the signal still small against the vast storm. End before it reaches the shore."""),
    ],
    "SC01-001_V02": [
        segment(10, """Start from the supplied underwater wide with wounded Young Mir small in the lower third and the cracked coral pillar leaning above and behind him. Hold the immense palace scale for a quiet beat. One fracture travels up the pillar; loose coral breaks away, then the pillar collapses behind Mir in one heavy event without striking or covering him. A dense cloud of marine dust expands across the background while the camera makes one restrained forward drift through the settling particles. As the dust thins, reveal Mir's complete blue-silver dragon body, half-open eyes, damaged scales and dim tail crystal. He gives one weak breath and remains on the palace floor. End after the pillar has fully settled and Mir is clearly discovered."""),
    ],
    "SC01-001_V03": [
        segment(8, """Continue from the ruined palace with Young Mir already suspended sideways in one diagonal current channel. Keep his head, four legs, fin-like wings and crystal-tipped tail readable as one complete small dragon. The current takes physical control of his body and carries him steadily across frame while the palace columns recede in the opposite direction. Use one smooth side-tracking camera move at Mir's speed, with no sudden rotation. Halfway through, Mir weakly raises his head and opens his eyes; his tail crystal gives one faint flicker, then dims. He cannot swim free. End with the ruins farther behind him and open dark water ahead."""),
    ],
    "SC01-001_V04": [
        segment(12, """Begin on the established vertical pursuit axis: small Mir is high-center inside the blue shaft and one continuous Black Tide mass is far below, separated by a broad column of clear water. Mir notices the darkness, folds his legs close and forces his wings and tail into one weak upward swimming rhythm. The camera tracks upward beside him at a steady distance. Below, the Black Tide rises as water, briefly forming unstable mouth- and hand-like ridges that collapse back into the same mass; it never becomes a separate humanoid body. Let the gap shrink gradually while Mir's rhythm falters and his tail crystal grows brighter from strain. End at near contact with a narrow but still visible band of clean water between them."""),
    ],
    "SC01-001_V05": [
        segment(8, """Start with exhausted Mir curled around his bright tail crystal in the upper layer and the Black Tide pressing upward from the lower layer, with clean blue water still separating them. Hold one tense beat on Mir's frightened eyes. The crystal releases exactly one circular cobalt pulse. Show the pressure wave expanding through the water and flattening the nearest black ridges downward as one connected mass. At the same moment, Mir uncurls, catches the reopened current and rises toward the brighter upper water. The camera gives one short upward lift with him, then settles. End with the clean gap visibly wider, the Black Tide lower in frame and Mir escaping above it, not yet at the surface."""),
    ],
    "SC01-001_V06": [
        segment(6, """Begin in the supplied coherent memory palace with small Mir alone at center, the broken empty gate behind him, the blue heart-light on the central axis and thin black roots confined to the perimeter. Make a slow centered approach toward Mir while distant sleeping dragon silhouettes remain architectural shadows rather than foreground characters. The blue heart pulses once. An unseen deep voice says exactly once in natural Korean, "기억하지 마라." Only the voice is heard; Mir's mouth stays closed. Mir contracts around himself, lowers his head and looks toward the dark perimeter as fear reaches him."""),
        segment(6, """Continue the same centered memory-space without introducing a new face or creature. The perimeter roots advance a short distance across the floor while leaving the central path and Mir readable. The unseen voice says exactly once in natural Korean, "그러면 아프지 않다." Mir recoils from the words, the heart-light flickers, and a narrow tear of white-blue storm light opens directly behind him. Let the camera stop moving as the light widens and begins washing out the gate, roots and floor together. End at the moment the memory-space breaks apart around Mir."""),
    ],
    "SC01-001_V07": [
        segment(10, """Start in the distant storm-coast anchor with one incoming wave already containing Young Mir's complete small blue-silver silhouette and bright tail crystal. Keep wet black shore rocks ahead and the coastward direction clear. The camera remains in a stable coastal wide while the same wave advances through the frame; Mir rolls only with the water and makes no controlled swimming motion. As the wave breaks, foam briefly reveals his horned head, folded wings and tail crystal before carrying him into the channel behind the nearest rocks. His glow weakens continuously rather than blinking off. End after his body disappears behind the rocks and the final blue reflection fades from the foam."""),
    ],
}


SC01_002_VIDEO_BEATS = {
    "SC01-002_V01": [
        segment(4, """Begin in the supplied low three-quarter side anchor with Lua's complete body, both feet, the complete spear and the separate fish readable together. Hold one brief aiming beat while the camera makes a subtle forward push along the existing diagonal spear line. Lua keeps both hands low, follows the fish with one small controlled adjustment and takes one silent breath. She then performs exactly one short forward-and-down thrust. The fish darts sideways across the clean water gap before the stone point arrives; the spear enters the vacated water with one compact splash. End immediately as the missed thrust pulls Lua's shoulders beyond her front foot."""),
    ],
    "SC01-002_V02": [
        segment(5, """Continue from the supplied off-balance pose with the spear point already in shallow water and both of Lua's hands supporting the same rigid shaft. Her existing forward momentum travels through shoulders and hips; her front sandal releases once from the slick stone lip and surprise flashes across her face. The camera performs one motivated continuous move: a quick push from the medium side view toward her upper body as the foot slips, followed by a close downward side-tracking sweep with the falling body. Use a brief cinematic slow-motion emphasis only during the loss of balance, then return to full impact speed as her knees and hip meet the shallow water in one weighted compact splash. The spear stays in her hands throughout. End with Lua fully settled in the shallow water and the single spear still supported by both hands."""),
    ],
    "SC01-002_V03": [
        segment(5, """Start after the completed fall with soaked Lua already seated in the shallow water beside the same stone edge, still holding the same spear. She exhales, checks that nobody is close, plants her free palm firmly on the nearby stone and draws one knee underneath her. In one continuous recovery she pushes to stable footing, brings the spear safely low and straightens her soaked tunic. The camera makes only a small upward correction to keep her complete recovery framed. Wet hair clings to her face as she forces an expression of dignity. End standing securely; there is no dialogue."""),
    ],
    "SC01-002_V04": [
        segment(6, """Keep exactly the same two children in the supplied stable medium two-shot: Village Child 1 frame-left with empty hands and Village Child 2 frame-right with her basket belonging only to her. Both look beyond the empty screen-right edge. The camera begins one restrained slow push without changing their positions. Child 1 points once toward the water, gives a contained laugh and says exactly once in natural Korean, "또 놓쳤다!" Only Child 1 moves his mouth; Child 2 watches with closed lips."""),
        segment(6, """Continue the same unbroken two-shot and preserve the two distinct faces, hair, clothing and basket ownership. Child 1 closes his mouth and lowers his pointing hand. Child 2 leans forward slightly, maintains the screen-right eyeline and says exactly once in natural Korean, "루아 누나는 바다랑 안 맞아!" Only Child 2 moves her mouth while Child 1 listens. They share one brief reaction as the camera finishes its gentle approach and settles. End with the same two children, positions and screen-right eyeline intact."""),
    ],
    "SC01-002_V05": [
        segment(6, """Begin in a stable waist-up solo shot of soaked Lua frame-right, facing the empty screen-left edge. She keeps the same rigid spear safely low, lifts only her chin and says exactly once in natural Korean, "안 맞긴 뭐가 안 맞아!" The camera starts one clearly visible but gentle continuous push toward chest-up framing. Lua is the only person in frame; wet stone and sea remain open along her eyeline."""),
        segment(6, """Continue the same solo take and the same gentle camera approach. Lua keeps both hands below chest level and physically supports the spear at her side. She squares her shoulders, raises her chin a little farther, forces a proud half-smile and says exactly once in natural Korean, "방금 건 일부러 빠진 거야." Her mouth closes after the line while her embarrassed eyes briefly betray the lie."""),
        segment(6, """Let the camera complete its move and settle into a chest-up medium close shot after one clear silent beat. Lua glances toward the shallow water using only her eyes, returns her gaze to the empty screen-left edge and adds dryly in natural Korean, "수심 확인." Hold on her deadpan attempt to preserve dignity. Her lips close, hands and spear remain low, and the surrounding breakwater stays empty. End on Lua alone holding the deadpan expression."""),
    ],
    "SC01-002_V06": [
        segment(5, """Start in the supplied grounded medium-wide two-shot with Lua and the Old Fisherman visible on the same wet breakwater axis. The fisherman takes his final two slow steps and stops beside Lua without covering her. He says exactly once in natural Korean, "루아야." Lua immediately straightens, keeps her spear pointed safely down and answers exactly once, "네!" The camera stays locked and only the current speaker moves their mouth."""),
        segment(5, """Maintain the same two-shot, distance and eyeline. The Old Fisherman studies Lua calmly and says exactly once in natural Korean, "바다는 고집으로 되는 게 아니다." Lua remains silent with closed lips; her defensive posture softens slightly, her eyes lower, and the familiar warning visibly stings. Keep both reactions and the complete spear readable in one composition."""),
        segment(5, """After a quiet beat, the fisherman turns his head toward the distant cliff. Perform the clip's only camera move: a slow motivated pan and slight lateral slide along his gaze until the cave mouth is clearly visible behind them. He alone warns in natural Korean, "오늘은 동굴 쪽 가지 마라. 폭풍 뒤에는 뭐가 밀려올지 몰라." Lua says nothing and follows his gaze. End in a settled composition connecting both characters to the cave."""),
    ],
    "SC01-002_V07": [
        segment(6, """Begin in the supplied medium-wide profile with Lua alone and the distant cave at the end of one continuous raised stone path. Keep the camera still as the cave emits one faint blue pulse; let its reflection travel across wet stone and catch in Lua's eyes. She stops, turns only her gaze toward the cave, then cautiously checks behind her without moving her feet. Holding the spear low, she thinks exactly once in Korean voice-over, "가라면 가지 말아야 하는데." Her lips remain closed."""),
        segment(6, """A stronger second blue pulse gives Lua a clear decision cue. Curiosity replaces hesitation and she thinks exactly once in the same Korean internal voice, "저렇게 빛나면 가야지." Her lips stay closed. She secures the spear along her side, pivots and runs on the visible raised stone route. On that pivot, the camera changes into one smooth low rear three-quarter tracking move at a steady distance. Every footfall lands on solid stone while the glowing cave grows larger ahead. End before Lua enters the cave."""),
    ],
}


SC01_003_VIDEO_BEATS = {
    "SC01-003_V01": [
        segment(5, """Begin at the supplied behind-left cave entrance with Lua alone, the smooth basalt path and center water strip leading toward the distant blue crevice. Keep her complete body and spear readable as she advances at walking speed. She tests the shallow water once with the stone tip, places each foot on the broad stable rock planes and scans the darkness without changing direction. The camera performs one slow rear three-quarter track on the fixed entrance-to-crevice axis, matching her pace and preserving the exit behind her."""),
        segment(5, """Lua stops when the blue reflection strengthens across the rock ahead. The camera settles into a medium side composition that keeps Lua and the still-empty crevice in the same frame. Gathering false courage, she says exactly once in natural Korean, "나와라. 내가 마을에서 제일 무서운 사람은 아니지만, 상당히 귀찮은 사람이다." Only Lua speaks and her lips close after the line. A tiny squeak answers from the crevice; she freezes, lowers the spear tip and changes from forced confidence to curiosity. End with Lua stopped and the crevice still visually empty."""),
    ],
    "SC01-003_V02": [
        segment(7, """Start from the supplied separated two-character cave composition: Lua kneels left with the spear resting behind and small wounded Mir lies right beside the blue crevice. Preserve the broad wet-stone gap and complete anatomy of both. The camera makes one restrained low push across that open gap. Mir shifts weakly as one complete quadrupedal dragon, revealing horns, blue-silver face, folded fin-like wings and crystal tail. Lua keeps her hands low and whispers exactly once in natural Korean, "방금 귀여웠는데? 너… 도마뱀은 아니지?" Only Lua moves her mouth."""),
        segment(8, """Continue the same low two-shot and slow approach without crossing the open gap. Mir uses his front legs to lift his head, opens his large blue eyes and meets Lua's gaze. Lua's amused expression disappears; she inhales, lowers the spear completely onto the stone behind her and leans forward only a few centimeters. After one silent beat she says exactly once in natural Korean, "말도 안 돼." Mir remains weak but keeps eye contact. End on their first sustained mutual look with both bodies still separate."""),
    ],
    "SC01-003_V03": [
        segment(8, """Begin with Lua crouched left and Mir lying right, her open hand still near her own knee and a clear air gap between them. Lua notices that Mir cannot stand; concern replaces curiosity. Keeping her body low and the palm facing upward, she slowly extends exactly one open hand along the wet stone and stops before any contact. The camera makes one gentle low push following the hand while preserving both faces and the remaining gap. Lua says softly and exactly once in natural Korean, "야, 괜찮아. 안 잡아먹어. 나도 오늘 아침 못 먹었거든." Mir watches the approaching fingertips and gathers his remaining strength. End with the hand offered but untouched."""),
    ],
    "SC01-003_V04": [
        segment(6, """Start in the supplied tight side contact frame with only Lua's single index fingertip held gently between Mir's small dragon jaws. Mir remains on the stone and uses the fingertip as weak support rather than pulling or shaking. Lua gives one sharp flinch, steadies her wrist with the other hand and cries exactly once in natural Korean, "악!" The camera holds the contact point for a beat, then eases just wide enough to include Mir's exhausted eyes and Lua's changing expression. She recognizes the bite as a plea and stops trying to withdraw. End with the same gentle contact intact."""),
    ],
    "SC01-003_V05": [
        segment(5, """Open inside the supplied supernatural palace corridor as one blue pulse enters through the broken ceremonial gate. Use one continuous centered forward flight along the clear central path. The pulse travels ahead of the camera and illuminates coral reliefs in sequence while the surrounding darkness stays outside the path."""),
        segment(5, """Continue the same forward movement past distant sleeping dragon silhouettes embedded in the architecture. Keep them motionless and separated from the path. Thin black roots tighten only around the outer ruins as the blue pulse moves deeper toward the heart-light; the camera maintains one direction and does not cut to a new axis."""),
        segment(5, """Approach the central blue heart as it contracts once, then releases one luminous wave back toward the viewer. Let the returning wave overtake the camera, wash the corridor into white-blue light and pull the vision toward reality. End at full light before Lua or the cave reappears."""),
    ],
    "SC01-003_V06": [
        segment(7, """Return to the supplied cave side axis after the flash. Lua kneels left, breathing hard, with her lowered wrist mark turned toward the viewer; Mir lies separately at the same crevice with his chest mark visible. The camera begins one slow push toward Lua while she looks from her wrist to Mir and back. She asks exactly once in natural Korean, "방금… 내가 본 거야?" Only Lua moves her mouth. Mir answers with one weak short chirp and remains lying down."""),
        segment(7, """Continue the same two-shot and camera approach. The wrist mark and chest mark pulse together exactly once, lighting the open stone gap between them. Lua follows that light to Mir's eyes, steadies her breathing and asks exactly once in natural Korean, "너 대체 뭐야?" Mir does not speak; he gives one small exhausted head movement. Let the camera settle. End with both marks, both faces and their separate bodies still readable."""),
    ],
    "SC01-003_V07": [
        segment(8, """Begin with Mir already fully enclosed in the compact beige cloth bundle against Lua's chest, only his small horned dragon head visible. Lua supports the bundle with both arms, adjusts the same wrap once without exposing his body and sighs. She says exactly once in natural Korean, "하. 나 진짜 사고 쳤다." After her lips close, she turns onto the established smooth-rock path and walks toward the behind-left exit. Use one smooth rear-side tracking move at her walking speed, keeping her complete steps, Mir's visible face and the exit direction readable. End as she reaches the threshold with the wrap unchanged."""),
    ],
    "SC01-003_V08": [
        segment(7, """Start with Lua stopped at the cave threshold, still holding the identical intact cloth bundle between the dark cave and bright coast. An unseen villager calls exactly once from outside in natural Korean, "루아! 거기 있냐?" The caller remains off-screen. Lua startles but does not drop or uncover Mir; she tightens one supporting arm, rotates her torso slightly so her ordinary body shields the visible dragon head from the coast and listens with closed lips. The camera makes one small lateral move to preserve the cave/coast boundary. End on her guarded hold with the wrap unchanged."""),
    ],
}


SC01_004_VIDEO_BEATS = {
    "SC01-004_V01": [
        segment(8, """Begin in the supplied daylight house wide with Lua entering through the left door and carrying the same compact cloth-wrapped Mir bundle against her chest. Keep the empty bowl center-right and the single shell on the low table visible as fixed landmarks. Lua steps fully inside, turns and closes the door softly with one foot while both arms continue supporting the bundle. The camera makes one restrained lateral correction to keep door, Lua, bowl and table in the same geography. She listens toward the closed door for a silent beat, looks down as Mir's horned face peeks from the unchanged wrap and says exactly once in natural Korean, "진짜네. 꿈이면 지금쯤 깨야 하는데." End with the room secure and Mir still wrapped."""),
    ],
    "SC01-004_V02": [
        segment(8, """Start with Lua kneeling left and supporting Mir's complete curled dragon body directly above the empty shallow bowl. Keep the bowl rim, all four legs, folded wings and crystal tail readable before contact. Lua lowers him once with both hands in one slow continuous motion while the camera gives a small downward correction following his body. Mir's belly reaches the water, his limbs relax and his entire curled body settles inside the rim. Lua keeps one hand nearby and asks exactly once in natural Korean, "너 물에서 자는 거야? 좋겠다. 난 그러면 죽는데." End with Mir resting fully inside the bowl and the shell untouched on the table."""),
    ],
    "SC01-004_V03": [
        segment(7, """Begin in the stable bowl-axis two-shot with Mir fully inside the bowl right and Lua kneeling left, holding exactly one dry fish across a clear gap. The shell stays on the low table behind them. Lua slowly brings the fish to the bowl rim without touching Mir. Mir smells it, pulls his horned head back and recoils once with folded wings tightening against his body. The camera holds the two-shot so the offered fish and rejection remain readable together. Lua pauses, puzzled, and asks exactly once in natural Korean, "아니, 바다에서 왔잖아. 생선 안 먹어?" End with the fish still in Lua's hand outside the bowl."""),
    ],
    "SC01-004_V04": [
        segment(8, """Start with small Mir standing between the bowl and the low table, facing the one palm-sized spiral shell already resting at the table edge. Lua remains behind with empty hands. Mir notices the shell, takes a short continuous path from the bowl to the table and reaches upward with both front paws. Use one low camera track parallel to that route, keeping bowl, Mir and shell in the same order. Mir takes the single shell, lowers himself beside the table and hugs it against his chest as a comfort object. Lua watches the choice, tilts her head and says exactly once in natural Korean, "입맛도 귀족이네." End with the same shell securely held by Mir."""),
    ],
    "SC01-004_V05": [
        segment(9, """Begin with Mir beside the bowl holding the same shell and Lua seated between him and the closed left door, her wrist mark low and visible. Keep both characters in the quiet room while imagined adult voices remain muffled audio only. The voices say in natural Korean, "불길하다! 바다에 돌려보내!" Lua's eyes snap toward the closed door; her shoulders tighten and she pulls her marked wrist closer to her body. The camera makes one slow inward move that keeps the door, Lua and Mir on the same sightline. Lua then looks back at Mir's frightened face and shifts her seated body a little more directly into that line. End on her silent decision to protect him."""),
    ],
    "SC01-004_V06": [
        segment(6, """Start with the closed door left, Lua seated at center and Mir beside the bowl right, with Lua's ordinary body occupying the direct sightline between them. Keep the room free of visual effects. Lua turns away from the door to face Mir, softens her posture and says exactly once in natural Korean, "안 돼. 그러니까… 당분간 여기 있어." Only Lua moves her mouth. Mir continues holding the shell and watches her while the camera begins one gentle push across their conversational gap."""),
        segment(6, """Continue the same grounded composition and gentle push. Lua tries to recover a responsible tone, raises one finger no higher than her chest and adds exactly once in natural Korean, "근데 밥값은 해야 돼. 물 좀 데워준다든가?" Her hand then settles back onto her knee. Mir remains beside the bowl, keeps the shell against his chest and gives one slow puzzled head tilt. Hold after Lua closes her mouth. End with the closed door behind her, Lua physically centered and no magical effect in the room."""),
    ],
    "SC01-004_V07": [
        segment(7, """Begin in the supplied tight bowl-axis close-up with small Mir fully inside the bowl and exactly one clear water droplet already suspended halfway between his mouth and Lua's forehead. Keep visible air gaps on both sides of the droplet. Both characters stay physically still while their eyes follow it. The camera holds the aligned profile path without changing scale. The single droplet travels slowly and continuously toward Lua; its reflection crosses her eyes as it approaches. End immediately before contact, with the droplet still separate from her skin and no second droplet appearing."""),
    ],
    "SC01-004_V08": [
        segment(5, """Start immediately after contact with one clearly readable water bead at the center of Lua's forehead, no droplet remaining in the air, and Mir fully inside the same bowl. Lua blinks once, processes the tiny result and looks at Mir's hopeful face. Mir gives one proud short chirp. Lua's restrained smile appears and she says exactly once in natural Korean, "그래. 가능성은 있다." The camera holds the intimate two-shot with the bead visible."""),
        segment(5, """After Lua closes her mouth, she turns her wrist mark toward the viewer as Mir's chest mark answers from inside the bowl. Both marks brighten together in exactly one shared cobalt pulse, casting matching light across their separated bodies and the bowl rim. Lua and Mir notice the same event, exchange one still look and stop moving as the light softens. Let the camera make one very small final push toward the three focal points: forehead bead, wrist mark and chest mark. End with all three readable."""),
    ],
}


SC01_005_VIDEO_BEATS = {
    "SC01-005_V01": [
        segment(8, """Begin in the supplied quiet night-house wide with Lua asleep on the back-left bed and small Mir curled completely inside the center-right bowl. Preserve the exact daytime room geometry under moonlight and keep a broad dark gap between them. Hold stillness for one beat, then let Lua's wrist mark and Mir's chest mark begin the same slow cobalt rhythm across the room. Mir's folded wings tighten and his body gives one small tremor inside the bowl. Lua remains asleep but her brow and fingers echo the same tension. The camera performs an almost imperceptible push while keeping both sleeping bodies and both marks visible."""),
        segment(7, """Continue the same room and synchronized rhythm. Mir's trembling grows into one frightened curl around his tail crystal; Lua turns slightly on the bed and mirrors his fear without waking. Each shared pulse spreads farther across the floor and fixed furniture, but the room layout remains stable. On the final pulse, blue light fills the open gap, softens the edges of bed, bowl, table and window, then dissolves the entire room into the architecture of the submerged palace dream. Complete the transition as one continuous visual transformation rather than an abrupt cut. End fully inside the palace dream with the house no longer visible."""),
    ],
    "SC01-005_V02": [
        segment(7, """Start in the supplied memory composition with small Mir alone before the blue heart and one flat translucent crown-horned cast shadow beginning exactly at his feet. Keep the shadow attached across the floor and broken wall as the camera slowly approaches Mir on the central axis. Black roots tighten around the outer architecture while leaving Mir and the heart clear. The attached shadow lengthens only because the heart-light brightens behind him; it remains textureless and has no eyes or separate movement. An unseen deep voice says exactly once in natural Korean, "너는 왕자가 아니다." Mir lowers his head and trembles."""),
        segment(7, """Continue the same approach and preserve the physical attachment between Mir's feet and the flat shadow. The unseen voice says exactly once in natural Korean, "버려진 새끼 용이다." Mir looks back at the enormous outline as it contracts toward him with the failing heart-light, still behaving only as his cast shadow. The perimeter roots close part of the empty space; Mir curls defensively and the blue heart cracks into a white-blue opening behind him. Let that light erase the shadow, roots and palace together. End as the dream collapses, with Mir still the only living body."""),
    ],
    "SC01-005_V03": [
        segment(8, """Begin back in the night house with Lua awake and kneeling beside the bowl, both empty hands already supporting the underside of trembling Mir's complete dragon body. Keep his horned head, four legs, folded wings and crystal tail distinct as one animal. Lua slides her palms fully beneath him and performs exactly one continuous lift from bowl to chest while the camera gives a restrained upward correction with the motion. She secures his weight in both arms and says exactly once in natural Korean, "뭐야… 야. 괜찮아. 나 여기 있어." Only Lua speaks. End with Mir safely held, the now-empty bowl below and both bodies anatomically separate."""),
    ],
    "SC01-005_V04": [
        segment(10, """Start with Lua already seated and securely cradling one small Mir against her torso. Keep Mir's dragon face beside Lua's visible wrist mark and his chest mark unobstructed. The camera begins one intimate slow push toward their faces and two marks. A wave of Mir's fear passes through the bond; Lua's breath catches and she presses her free hand lightly to her own chest without loosening the supporting arm. She says softly in natural Korean, "이거… 내 무서움이 아니야. 너도 무서운 거구나." Mir raises his head and touches his nose gently to her marked wrist. Both lights soften together as Lua's hold relaxes into reassurance. End on their shared calm look."""),
    ],
    "SC01-005_V05": [
        segment(9, """Begin in the unchanged night room with Lua standing between the bowl and the covered back-wall window while Mir remains safely on the floor beside the bowl behind her. Let the normal sea sound fade completely, creating a clear moment of silence. Mir lifts his head and gives one low warning growl. Lua hears it, looks back at him, then turns toward the window and walks the few visible steps across the stable floor. Use one slow side track from the bowl toward the window, keeping Mir behind her and the room geography readable. Lua lifts only the lower edge of the window cloth and cold sea light falls across her face. End before the outside creature is shown."""),
    ],
    "SC01-005_V06": [
        segment(6, """Start in the supplied exterior night-coast wide with the warm house fixed far-left and one translucent Black Jellyfish alone above the screen-right sea. Keep the open distance and destination direction readable. Ink-like smoke begins rotating slowly inside its bell while the long tentacles hang with the water current. The creature turns its bell and body toward the house in one deliberate orientation change. Use one restrained parallel camera drift that preserves the full coastline and never overtakes the jellyfish."""),
        segment(6, """Continue the same exterior wide after the turn. The Black Jellyfish begins one slow continuous glide leftward toward the distant warm house; its tentacles trail behind and remain connected to the same body. The house grows only slightly closer while the sea stays unnaturally still. From inside the distant house, Lua asks off-screen exactly once in natural Korean, "저게… 널 찾으러 온 거야?" The exterior creature gives no voice. End with the jellyfish still separated from the house and visibly approaching, then cut to black."""),
    ],
}


VIDEO_BEATS_BY_CLIP = {
    **SC01_001_VIDEO_BEATS,
    **SC01_002_VIDEO_BEATS,
    **SC01_003_VIDEO_BEATS,
    **SC01_004_VIDEO_BEATS,
    **SC01_005_VIDEO_BEATS,
}

DIALOGUE_OVERRIDES = {
    "SC01-003_V01": "나와라. / 내가 마을에서 제일 무서운 사람은 아니지만, 상당히 귀찮은 사람이다.",
}
