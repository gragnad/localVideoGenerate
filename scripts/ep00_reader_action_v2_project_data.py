from __future__ import annotations

"""Independent production data for the new EP00 reader-action V2 project."""

from typing import Any


SOURCE_SHA256 = "22786cca1be10f0ecf37caf9db23daf63279d6b66efbdad4f64d260f241d785e"


def row(
    clip_id: str,
    duration: float,
    summary: str,
    panels: tuple[str, str, str, str],
    actions: tuple[str, str, str, str],
    dialogue: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    return {
        "clip_id": clip_id,
        "scene_id": clip_id.rsplit("-", 1)[0],
        "duration": duration,
        "summary": summary,
        "panels": list(panels),
        "actions": list(actions),
        "dialogue": [dict(value) for value in dialogue],
    }


CLIPS = [
    row("EP00V2-S00-C01", 7.5, "Cyan water routes die in sequence until the last passage behind the fighter closes.", (
        "Extreme close view of one cyan current racing through a carved wet stone channel in complete darkness.",
        "The current reaches the giant black right palm pressing the channel at the circular altar centre.",
        "Cyan light breaks under the black fingers while the outermost rear passage begins to darken.",
        "Extreme wide: the blue-scaled young spear fighter stands with her back to the last dark passage opposite the three-times-taller black humanoid.",
    ), (
        "The cyan current rounds the final bend toward the altar.",
        "The black palm presses one fraction lower and cuts the moving light.",
        "The final rear route extinguishes from front to back.",
        "The fighter fixes both feet and holds the single wooden spear across the closing space.",
    )),
    row("EP00V2-S00-C02", 7.0, "The enemy speaks while the fighter reads shoulder, elbow, and hand; his shoulder starts the first sweep.", (
        "Wide two-shot: the towering black humanoid owns the altar centre while the fighter remains at the outer ring.",
        "Over-shoulder from the fighter: her gaze bypasses the face and aligns shoulder, elbow, and channel-contact hand.",
        "Tight enemy shoulder view: the right shoulder begins rotating before the palm leaves the channel.",
        "Low fighter view: both knees compress beneath an over-tight spear grip as the long arm begins crossing the room.",
    ), (
        "The black humanoid lowers its bright gaze and speaks without advancing.",
        "The fighter's eyes complete one continuous shoulder-to-elbow-to-hand read while her mouth stays closed.",
        "The shoulder rotation opens the elbow into a horizontal attack line.",
        "The fighter initiates her jump a fraction late as the arm accelerates.",
    ), ({"shot": 1, "speaker": 2, "listener": 1, "line": "혼자서도 여기까지 왔구나.", "delivery": "in a low restrained voice"},)),
    row("EP00V2-S01-C01", 7.0, "The horizontal sweep announces itself through water and grit before the fighter clears the wrist.", (
        "Low wide: the black arm begins a horizontal sweep and channel water bursts outward ahead of it.",
        "Close floor view: the fighter's scaled right foot drives off wet stone as grit tears sideways.",
        "Side action view: the fighter rises above the black wrist with knees folded and spear tight to her chest.",
        "Wide silhouette: her body clears the outside edge of the arm while a broad pressure wake catches up from behind.",
    ), (
        "Water, grit, and clothing snap away from the approaching arm.",
        "The planted leg releases the fighter upward in one explosive push.",
        "She folds tighter and passes over the wrist without swinging the spear.",
        "The delayed pressure wake strikes her airborne torso from the side.",
    )),
    row("EP00V2-S01-C02", 7.0, "A correct evasion becomes a damaged landing, and the fighter brakes with the spear.", (
        "Airborne medium: pressure bends the fighter's body axis sideways beyond the missed arm.",
        "Foot close-up: only the toe of her scaled right foot catches the altar edge.",
        "Low impact wide: her shoulder hits first as water and stone dust erupt.",
        "Floor-level medium: the spear butt scores a long line and stops her on one knee.",
    ), (
        "Her hips and shoulders twist out of alignment under the lateral wake.",
        "The toe slips and converts the landing into a shoulder-first fall.",
        "She rebounds once and forces the spear shaft against the floor.",
        "The scraping shaft arrests the slide while she raises her head immediately.",
    )),
    row("EP00V2-S01-C03", 7.0, "The enemy resets the route, and the fighter commits to a three-step torso test.", (
        "Wide: the black right hand has returned to the channel and the brief cyan light dies again.",
        "Medium on the kneeling fighter: her spear point shifts from the channel to the black chest.",
        "Measured wide: exactly three wet floor intervals separate the fighter from the torso.",
        "Low side view: the fighter is coiled into the first step with the spear held behind the hip.",
    ), (
        "The enemy remains still and leaves one deliberate pause instead of attacking again.",
        "The fighter settles on the torso as the wrong but testable target.",
        "Her gaze measures all three steps without changing the attack line.",
        "She launches and accelerates across the three-step distance.",
    )),
    row("EP00V2-S01-C04", 7.0, "The spear reaches the black chest but creates only indentation, a submerged impact tone, and concentric waves.", (
        "Low tracking profile: the fighter crosses the final step with hips and shoulders aligned behind the spear.",
        "Impact medium: the single spear point is already pressed deep into the black chest with no puncture spray.",
        "Extreme contact close-up: the black surface cups around the metal point like dense liquid stone.",
        "Chest-wide view: concentric dark ripples spread far beyond the stopped weapon while the channel remains unlit.",
    ), (
        "The final step drives the whole body into one direct thrust.",
        "The chest deforms inward and releases one deep muted impact through the chamber.",
        "The indentation rebounds and begins pushing the point outward.",
        "The waves continue spreading as the fighter recognizes that no wound or route change exists.",
    )),
    row("EP00V2-S01-C05", 7.0, "The enemy catches the shaft, orders release, and uses the fighter's refusal to lift both weapon and body.", (
        "Shaft close-up: one black left hand closes around the spear midpoint while the fighter still owns the rear grip.",
        "Two-shot at hand level: the enemy looks down the shaft as the fighter faces him with locked hands.",
        "Grip close-up: the fighter's knuckles turn pale as both hands tighten instead of opening.",
        "Full-axis wide: the enemy raises one wrist and fighter and spear leave the floor together.",
    ), (
        "The hand closure stops thrust, recoil, and the fighter's next correction at once.",
        "The black humanoid gives one quiet command while the fighter keeps her mouth closed.",
        "She answers physically by tightening every finger around the shaft.",
        "The enemy lifts the captured spear until both fighter feet kick in open air.",
    ), ({"shot": 2, "speaker": 2, "listener": 1, "line": "놓아라.", "delivery": "as one quiet command"},)),
    row("EP00V2-S01-C06", 8.0, "The spear becomes a lever for a low throw; the fighter breakfalls but loses distance and the final passage.", (
        "Wide: the towering enemy rotates shoulder and torso while the suspended fighter hangs from the spear rear.",
        "Dynamic side view: fighter and spear travel together along one low circular throw arc.",
        "Airborne close view: the fighter pulls the spear to her chest and presents shoulder and back instead of head and spine.",
        "Extreme wide aftermath: the fighter has stopped far away with the spear, while the last route now lies behind the enemy.",
    ), (
        "The rotating shoulder accelerates the spear and fighter as one rigid lever.",
        "The enemy releases at the arc edge and adds a final burst of speed.",
        "She strikes shoulder-first, rebounds, hits again, and skids through shallow water.",
        "She retains the spear but sees that the spatial defeat is worse than before.",
    )),
    row("EP00V2-S02-C01", 7.0, "A vertical palm forces the fighter to build one curved water shield from the floor.", (
        "Floor-level wide: the enemy shadow grows over the fallen fighter without an arm swing.",
        "Upward view: the black right palm descends vertically from above.",
        "Hand-and-water close-up: the fighter plants her left palm and nearby channel water converges into one point.",
        "Medium: one irregular curved transparent water shield stands between the kneeling fighter and descending palm.",
    ), (
        "The shadow closes while the enemy keeps the rest of its body economical.",
        "The open palm drops directly toward the fighter's occupied space.",
        "She pulls only nearby water upward without releasing the spear.",
        "The palm meets the completed curved shield and begins compressing it.",
    )),
    row("EP00V2-S02-C02", 7.0, "The shield cannot stop the palm, so the fighter rotates it and sends the hand into the floor.", (
        "Tight side view: the black palm has depressed the curved shield and the fighter's left elbow is folding.",
        "Wide impact view: delayed force bursts through the shield and slides the fighter backward.",
        "Top-side view: the fighter moves her left foot and twists waist and shoulder to steepen the shield angle.",
        "Low wide: the palm has slipped past her head and is about to strike bare stone beside the channel.",
    ), (
        "Layered water pressure drives the elbow toward its limit.",
        "The compressed shield releases a late heavy impact and the spear tip scores the floor.",
        "Her body rotation turns resistance into a lateral flow path.",
        "The palm leaves the curved surface and crashes into the floor, breaking stone and channel wall.",
    )),
    row("EP00V2-S02-C03", 7.0, "The displaced right hand relights one route, and the fighter enters before the second hand arrives.", (
        "Channel insert: the enemy right hand is fully off its contact point and one cyan line has just relit.",
        "Medium fighter reaction: her eyes lock on hand-to-channel causality rather than the damaged floor.",
        "Lane wide: the fighter kicks the shield flow aside and takes the first running step into the open light.",
        "Forward tracking view: she completes the second step with the open route directly ahead and the spear close to her body.",
    ), (
        "The single cyan route brightens beneath the absent palm.",
        "She completes the new tactical inference in one eye movement.",
        "She abandons the idea of torso damage and accelerates into the opening.",
        "A sharp warning pain begins cutting across her lower-left wrist before the third step.",
    )),
    row("EP00V2-S02-C04", 7.0, "The low left hand arrives faster than the warning can resolve, tearing shield and numbing the spear wrist.", (
        "Reverse-axis wide: the enemy left hand is already low across the lane while the fighter remains committed forward.",
        "Tight profile: the fighter leans back only a few degrees under the directional pain warning.",
        "Impact medium: one fingertip has grazed shoulder and wet clothing, rotating her body without a deep wound.",
        "Close aftermath: the shield rim is torn into heavy drops and two spear-hand fingers remain half-open and numb.",
    ), (
        "The low hand sweeps the remaining gap before she can stop her entry.",
        "Her partial lean saves the centreline but not the shoulder.",
        "The graze turns her half a rotation and transmits shock into the right wrist.",
        "The damaged shield fails to reform while numb fingers refuse a clean grip correction.",
    )),
    row("EP00V2-S02-C05", 7.0, "As the hands exchange route and attack roles, the fighter decides to move both together.", (
        "Medium: the fighter retreats three uneven steps while only large broken shield droplets fall from her left hand.",
        "Wide: the right black hand presses the newly opened channel again and the left hand occupies the fighter's side exit.",
        "Overhead: each hand exchange removes another visible wedge of traversable floor around the fighter.",
        "Front fighter medium: she holds both enemy shoulders in one eyeline and lowers the spear into a new plan.",
    ), (
        "She makes one failed attempt to gather the same shield shape.",
        "The cyan route dies while the second hand seals the lateral escape.",
        "The room appears to shrink faster than either full body moves.",
        "She commits to forcing both attached hands away at the same time.",
    )),
    row("EP00V2-S03-C01", 7.0, "Dragon Eye reveals the current force paths while breath, scales, water, and spear prepare without a shared beat.", (
        "Medium: the fighter plants the spear tip like a support while the enemy hands adjust around the channel centre.",
        "Eye close-up: a restrained cyan ring opens at the iris edge with no prediction images.",
        "Tactical over-shoulder: thin cyan force paths connect shoulder, elbow, wrist, and channel contact points.",
        "Full-body profile: breath condenses, right-side scales tighten, torn water circles the left hand, and spear tremor stops.",
    ), (
        "The enemy reads the apparent support posture and shifts both hand routes.",
        "Dragon Eye isolates only present force origins and contacts.",
        "The fighter maps what is pressing what without seeing the future.",
        "She aligns every prepared resource but still lacks one rhythm that corrects their differences.",
    )),
    row("EP00V2-S03-C02", 7.0, "A false right run becomes a spear-butt plant and an explosive reverse vault.", (
        "Wide: the fighter takes the first hard step to the right and the enemy right shoulder follows.",
        "Tracking medium: the second step commits the enemy right hand while the left lowers toward centre.",
        "Ground close-up: instead of a third step, the spear butt strikes one altar groove.",
        "Sweeping profile: the fighter has thrown her body to the opposite side around the planted shaft.",
    ), (
        "Her first step sells a full right-side entry.",
        "The second step draws both hands onto separate expected routes.",
        "The shaft stores her forward momentum in one abrupt plant.",
        "She releases that stored force into a reverse vault while hair and cloth lag behind.",
    )),
    row("EP00V2-S03-C03", 7.0, "Both hands leave their contacts, and one low Dragon Word creates a single suspended beat.", (
        "Impact wide: the enemy right hand strikes the place the fighter abandoned and bursts the floor.",
        "Central wide: the left hand moves from centre to close the new gap while the right remains displaced.",
        "Overhead: for the first time both hands are simultaneously clear of the cyan channel contacts.",
        "Dynamic medium: the fighter's lips are open on one nonhuman syllable as droplets and both hands visibly slow.",
    ), (
        "The missed right-hand impact carries past the feint location.",
        "The left hand abandons its contact to intercept the vault exit.",
        "Every chamber channel takes one simultaneous cyan breath.",
        "One low Dragon Word suspends droplets and hand motion for only a single beat.",
    )),
    row("EP00V2-S03-C04", 7.0, "The fighter enters the slowed interval and brings eye, scales, water, and spear onto one path.", (
        "Side action view: the fighter slips past the outside of the slowed right arm.",
        "Spear close view: she pulls the planted shaft free while torn shield water streams toward her left palm.",
        "Forward wide: the first of two steps carries her into the exposed channel gap.",
        "Low foot view: the scaled right foot lands exactly beyond the altar groove while the human left leg trails.",
    ), (
        "She crosses the arm boundary before the slowed beat ends.",
        "The freed spear and gathered water align with the force paths in her eye.",
        "She takes the first clean step toward the contact gap.",
        "The right leg completes its step as the slower human left foot begins descending.",
    )),
    row("EP00V2-S03-C05", 8.0, "A tiny depth mismatch collapses the combined technique; the enemy names the slow gap between powers.", (
        "Foot close-up: the human left toes have caught the shallow groove edge by a few centimetres.",
        "Medium collapse: the fighter's waist drops and the spear point falls one hand-width below the contact target.",
        "Two-shot: broken scale light and a voiceless breath frame the enemy looking directly at the fighter's face.",
        "Low fighter view: fallen but conscious, she has redirected the spear from the chest to the exact contact point.",
    ), (
        "The caught toes halt the left side while the scaled right side continues.",
        "Depth, breath, temperature, and segmented scale light fail in one cascade.",
        "The enemy delivers two measured diagnostic lines while the fighter cannot answer.",
        "She answers only by changing the physical target to contact separation.",
    ), (
        {"shot": 3, "speaker": 2, "listener": 1, "line": "힘이 아니라.", "delivery": "in a measured diagnostic tone"},
        {"shot": 3, "speaker": 2, "listener": 1, "line": "힘과 힘 사이가 느리구나.", "delivery": "continuing at the same low volume"},
    )),
    row("EP00V2-S04-C01", 7.0, "The falling fighter converts torn shield water into a thin wedge under the right palm.", (
        "Low medium: the fighter is falling forward and drives her left palm toward the wet altar.",
        "Water insert: torn shield residue races like one thin stream beneath the enemy right palm.",
        "Extreme contact close-up: the stream becomes a flat wedge between black palm and carved stone.",
        "Channel-side medium: the fighter raises her left arm as the wedge starts lifting one side of the hand.",
    ), (
        "She uses the fall itself to strike and redirect the remaining water.",
        "The residue enters the microscopic contact gap without exploding.",
        "The thin wedge expands laterally under the same palm.",
        "The right hand rises by one fingernail and one cyan line relights.",
    )),
    row("EP00V2-S04-C02", 7.0, "A spear lever lifts the left wrist so both hands leave the channels and the whole altar ignites.", (
        "Shaft-level view: the fighter has abandoned the blade and is sliding the spear midpoint beneath the enemy left wrist.",
        "Ground close-up: the spear rear locks into one altar groove while the scaled right thigh moves under the shaft.",
        "Full-body side view: the fighter extends the scaled leg, bending the wooden shaft and raising the left wrist.",
        "Extreme overhead wide: both black hands are clear and every cyan channel across the circular altar is brightly lit.",
    ), (
        "She seats the shaft against the underside of the left wrist.",
        "The groove and scaled thigh complete one physical lever.",
        "Her leg extension lifts the second contact hand despite the trembling water wedge.",
        "The chamber channels ignite together and reveal the full heart-like altar structure.",
    )),
    row("EP00V2-S04-C03", 7.0, "For one moment the black lower edge lifts and the fighter sees a real escape chance.", (
        "Brilliant wide: the circular cyan network is fully visible beneath the separated hands.",
        "Low altar view: the black liquid lower-body edge has lifted enough to reveal a thin gap over stone and water.",
        "Tight fighter face: exhaustion remains, but the eyes register the first credible opening.",
        "Lever close-up: the spear shaft bends, the scaled leg keeps extending, and the water wedge visibly trembles.",
    ), (
        "The full light exposes every route across the chamber.",
        "The lifted lower edge widens by only a small measurable amount.",
        "The fighter commits to one final increase instead of celebrating.",
        "The lever reaches maximum strain immediately before the enemy changes form.",
    )),
    row("EP00V2-S04-C04", 7.0, "The enemy liquefies one wrist around the shaft, reforms behind it, and steals the contact exchange.", (
        "Extreme shaft close-up: the enemy left wrist is beginning to soften around both sides of the wooden spear.",
        "Contact medium: the same wrist is split into two black liquid streams passing around the shaft with no extra limb.",
        "Reaction wide: the lever suddenly has no resistance and the fighter pitches forward while retaining the spear.",
        "Channel view: the two streams have rejoined as the same left hand behind the shaft and now press the route vacated by the right hand.",
    ), (
        "The left wrist releases its rigid outline without changing ownership or limb count.",
        "Both liquid halves flow around the obstacle instead of resisting it.",
        "The missing load pulls the fighter's body and bent shaft forward.",
        "The wrist reforms as one hand, completes the role exchange, and extinguishes half the cyan network.",
    )),
    row("EP00V2-S04-C05", 7.0, "The free right hand takes the spear and flips the fighter because her numbed fingers cannot release.", (
        "Wide: the reformed left hand owns the channel while the free black right hand reaches down toward the spear shaft.",
        "Shaft close-up: the right hand grips from above as the fighter's two numb fingers remain visibly half-closed.",
        "Full-axis medium: the right hand pulls upward and fighter and spear rise from the floor together.",
        "Dynamic overhead: the spear is a rotating axis and the fighter's body is passing over it as floor and ceiling exchange places.",
    ), (
        "The free hand closes on the exact lever the fighter created.",
        "Her hand receives the command to release one beat too late.",
        "The enemy turns one wrist and converts the shaft into a flip axis.",
        "The fighter rotates past the apex while still attached by the delayed grip.",
    )),
    row("EP00V2-S04-C06", 8.0, "The same right palm slams the falling fighter; the spear escapes and the channels die from outside inward.", (
        "Airborne medium: the enemy has released the spear and opened that same right hand over the falling fighter's side and scaled arm.",
        "High impact wide: the palm has driven the fighter into the outer altar, depressing stone and throwing a circular wall of water.",
        "Lateral insert: the intact spear has left her grip, hit two channel lips, and is spinning toward the far darkness.",
        "Final chamber wide: the fighter lies motionless, the spear is distant, and cyan light is dying from the outer ring toward her fingertips.",
    ), (
        "The open palm overtakes the falling body and covers side and scaled arm together.",
        "She rebounds once as the outer floor settles under the impact.",
        "The spear completes its second bounce and transitions into a long rotating slide.",
        "The last light disappears before her hand while the enemy body remains completely unwounded.",
    )),
    row("EP00V2-S05-C01", 7.0, "In the post-impact silence the fighter fails two separate attempts to rise.", (
        "Quiet floor wide: the fighter lies in shallow water with the enemy distant and the spear across the altar.",
        "Arm medium: her right palm is planted and the torso has risen by only one hand-width while the elbow shakes.",
        "Impact aftermath close-up: scale light goes out as the palm slips and the torso returns to stone.",
        "Side medium: a second attempt has begun but the shoulder cannot clear the floor.",
    ), (
        "Only late droplets and shallow breathing move in the chamber.",
        "She holds the incomplete lift until the scaled elbow loses stability.",
        "Her body settles back down without recovering the hand position.",
        "The second effort fails earlier and ends all attempts to stand.",
    )),
    row("EP00V2-S05-C02", 8.0, "The enemy advances under a descending hand, speaks, and receives the fighter's exhausted refusal.", (
        "Ground view: the fighter looks first at the distant spear and then at the dark wrist mark while no ability answers.",
        "Extreme wide: the enemy's connected black lower mass moves across the altar as remaining water retreats from it.",
        "Low fighter POV: the open right palm descends until its shadow covers her entire body.",
        "Tight fighter face under the hand shadow: pain remains but her mouth forms a quiet refusal.",
    ), (
        "Dragon Eye, shield water, wrist mark, and damaged voice each remain inactive.",
        "The enemy closes distance without creating legs or separate tendrils.",
        "The black humanoid speaks while the fighter keeps her mouth closed.",
        "The fighter answers in two broken phrases and the palm descends farther.",
    ), (
        {"shot": 3, "speaker": 2, "listener": 1, "line": "놓았더라면 아프지 않았을 것이다.", "delivery": "without haste"},
        {"shot": 4, "speaker": 1, "listener": 2, "line": "그 말….", "delivery": "through a damaged breath"},
        {"shot": 4, "speaker": 1, "listener": 2, "line": "진짜 싫어.", "delivery": "with exhausted refusal"},
    )),
    row("EP00V2-S05-C03", 7.0, "One unfamiliar heartbeat stops both the descending palm and the fighter's breath without creating visible power.", (
        "Dark hand-shadow close-up: only one thin cyan line remains visible between descending black fingers.",
        "Tight two-level composition: the black palm has stopped above the fighter at the same instant her breath has stopped.",
        "Wrist-and-channel insert: the wrist mark and dead cyan routes remain completely unlit after the beat.",
        "Face close-up: the fighter listens inward while recognizing that her own rapid heartbeat is still separate.",
    ), (
        "The palm narrows the final visible cyan gap.",
        "One low internal heartbeat interrupts both motions at once.",
        "No weapon, aura, figure, miracle, or external light appears.",
        "Her eyes move from the chest sensation back toward the darkness beyond the fingers.",
    )),
    row("EP00V2-S05-C04", 7.0, "The enemy's gaze splits, the hand reveals one questioning eye, and the second heartbeat is withheld by complete blackout.", (
        "Enemy face close-up: one cyan eye looks down at the fighter while the other turns toward the dead channel's distant darkness.",
        "Low two-shot: the black palm has lifted a small amount, opening a narrow gap over the fighter's face.",
        "Extreme fighter eye close-up through the finger gap: the eye holds a new question, not victory or an answer.",
        "Nearly black full frame: the descending palm edge is completing a physical wipe over the last visible cyan sliver.",
    ), (
        "The two eyes hold their separate targets without adding another body or power.",
        "The hand rises only enough to reveal one side of the fighter's face.",
        "A second unfamiliar heartbeat begins somewhere beyond the visible moment.",
        "The palm closes the frame to complete black and all sound cuts before that heartbeat arrives.",
    )),
]


DIALOGUE_LOCK = [
    {"clip_id": clip["clip_id"], **dialogue}
    for clip in CLIPS
    for dialogue in clip["dialogue"]
]


assert len(CLIPS) == 28
assert len(DIALOGUE_LOCK) == 7
assert [value["line"] for value in DIALOGUE_LOCK] == [
    "혼자서도 여기까지 왔구나.",
    "놓아라.",
    "힘이 아니라.",
    "힘과 힘 사이가 느리구나.",
    "놓았더라면 아프지 않았을 것이다.",
    "그 말….",
    "진짜 싫어.",
]
