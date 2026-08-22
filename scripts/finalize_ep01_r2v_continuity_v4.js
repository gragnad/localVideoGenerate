const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const repo = path.resolve(__dirname, "..");
const project = path.join(repo, "prompt_projects/RaisingaDragonSeason01_EP01_H3_R2V");
const inventoryPath = path.join(project, "asset_generation_inventory.json");
const inventory = JSON.parse(fs.readFileSync(inventoryPath, "utf8"));

const sha256 = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
function pngSize(file) {
  const data = fs.readFileSync(file);
  return { width: data.readUInt32BE(16), height: data.readUInt32BE(20) };
}
function payloadFromFile(file) {
  const text = fs.readFileSync(file, "utf8");
  const matches = [...text.matchAll(/```json\s*\n([\s\S]*?)\n```/g)];
  return JSON.parse(matches.at(-1)[1]);
}

const finalConnections = [];
for (const scene of fs.readdirSync(project).filter((name) => /^EP01-S\d\d$/.test(name)).sort()) {
  for (const name of fs.readdirSync(path.join(project, scene)).filter((name) => name.endsWith(".md")).sort()) {
    const payload = payloadFromFile(path.join(project, scene, name));
    for (const ref of payload.references) {
      const absolute = path.join(project, ref.source_path);
      finalConnections.push({
        clip_id: payload.clip_id,
        picture_index: ref.picture_index,
        role: ref.role,
        label: ref.label,
        source_path: ref.source_path,
        linked: fs.existsSync(absolute),
        sha256: fs.existsSync(absolute) ? sha256(absolute) : null,
      });
    }
  }
}

const approvedAssets = [
  {
    asset_id: "EP01-S02-VILLAGE-OVERCAST-V2",
    source_path: "backgrounds/generated_v4/BG_EP01_S02_VILLAGE_MASTER_OVERCAST_V2.png",
    generation_mode: "built-in image_gen environment lighting edit",
    generation_prompt: "Preserve the coastal village and breakwater geometry while replacing sunny golden light with cold diffuse post-storm overcast light, wet stone, gray surf, and no characters.",
    review_status: "approved",
    review_notes: "Matches the cold breakwater and cave-route weather family without changing the village route.",
  },
  {
    asset_id: "EP01-S01-S03-SLEEPING-HALL-V3",
    source_path: "backgrounds/generated_v4/Sleeping_Dragon_Hall_V3_APPROVED.png",
    generation_mode: "built-in image_gen",
    generation_prompt: "Create a dim ruined underwater palace memory hall with four motionless sleeping dragons in side alcoves, a clear central corridor, broken masonry, and no Heartstone or characters.",
    review_status: "approved",
    review_notes: "Selected over the darker candidate because all sleeping-dragon silhouettes remain readable.",
  },
  {
    asset_id: "EP01-LUA-CHILD-WRIST-MARK-V2",
    source_path: "assets/generated_v3/Dragon_Heart_Wrist_Mark_Lua_Child_V2.png",
    generation_mode: "built-in image_gen reference edit",
    generation_prompt: "Transfer the cyan Dragon Heart emblem to exactly one small child-proportioned Lua wrist and hand in a neutral reusable close-up; no adult anatomy, face, extra hand, text, or panel.",
    review_status: "approved",
    review_notes: "One complete child-scale hand, readable emblem, neutral framing.",
  },
  {
    asset_id: "EP01-S04-HOUSE-MASTER-DAY-V4",
    source_path: "backgrounds/generated_v4/BG_EP01_S04_HOUSE_MASTER_DAY_V4.png",
    generation_mode: "deterministic continuity promotion from reviewed master",
    generation_prompt: "Use the single reviewed day-house master without independent localized regeneration; camera crops are delegated to the video prompt so all object geometry and scale remain identical.",
    review_status: "approved",
    review_notes: "All S04 house references now resolve to these exact pixels.",
  },
  {
    asset_id: "EP01-S04-SEA-BASKET-SCALE-V4",
    source_path: "backgrounds/generated_v4/BG_EP01_S04_IMAGINED_SEA_BASKET_SCALE_V4.png",
    generation_mode: "built-in image_gen spatial composite edit",
    generation_prompt: "Preserve the stormy sea-exit plate and add exactly one grounded woven basket centered on wet planks at fixed adult-knee-width / shin-height scene scale with contact shadow and wet reflection.",
    review_status: "approved",
    review_notes: "Replaces separate environment and prop references; basket count, grounding, and scene scale are fixed in one plate.",
  },
  {
    asset_id: "EP01-S05-HOUSE-MASTER-NIGHT-V4",
    source_path: "backgrounds/generated_v4/BG_EP01_S05_HOUSE_MASTER_NIGHT_V4.png",
    generation_mode: "built-in image_gen lighting-only edit",
    generation_prompt: "Convert only the canonical day-house lighting to moonlit night while preserving the exact window, bed, table, basin, door, prop positions, sizes, counts, and camera axis.",
    review_status: "approved",
    review_notes: "All S05 house references now resolve to one night plate derived from the day master.",
  },
];
for (const asset of approvedAssets) {
  const absolute = path.join(project, asset.source_path);
  Object.assign(asset, pngSize(absolute), { sha256: sha256(absolute) });
}

const unique = new Set(finalConnections.map((item) => item.source_path));
const generated = [...unique].filter((item) => item.includes("/generated_v"));
inventory.phase = "continuity_reaudit_reviewed_and_linked";
inventory.continuity_reaudit = {
  review_date: "2026-08-09",
  scope: "All 42 Clips and every connected Picture were reopened scene-by-scene after the first review.",
  findings: [
    "Independent S04 basin variants drifted in room geometry and apparent prop scale.",
    "The S04 imagined basket lacked a stable scene-scale relationship when supplied as a separate prop.",
    "The S02 village master was sunny while the connected breakwater was cold and overcast.",
    "The sleeping hall was too bright and pristine for a broken memory hall.",
    "The wrist-mark close-up used adult hand proportions.",
    "The S05 night family drifted in basin and furniture placement relative to the day room.",
  ],
  resolution: "Reconnected house families to one master per time of day, baked the single basket into one scale plate, and replaced the three additional anomalous asset families.",
};
inventory.final_summary = {
  clips: 42,
  reference_instances: finalConnections.length,
  linked_reference_instances: finalConnections.filter((item) => item.linked).length,
  approved_unique_assets: unique.size,
  newly_generated_unique_assets: generated.length,
  reused_unique_assets: unique.size - generated.length,
  approved_new_assets: approvedAssets.length,
  rejected_candidates: 4,
  reconnected_clips: 19,
};
inventory.candidates = [
  { candidate_id: "S02_OVERCAST_A", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-1fab4098-def8-48ad-8413-a7626fb70c4a.png", review_status: "approved", final_source_path: approvedAssets[0].source_path },
  { candidate_id: "S02_OVERCAST_B", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-94d9cdeb-8873-4b34-9532-10186d266712.png", review_status: "rejected_lighting", notes: "Dramatic bright cloud break was less consistent with diffuse breakwater light." },
  { candidate_id: "SLEEPING_HALL_A", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-1359f3ee-09cb-4cce-bfcb-582cf4351ade.png", review_status: "approved", final_source_path: approvedAssets[1].source_path },
  { candidate_id: "SLEEPING_HALL_B", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-54d8c788-8510-4fde-8b36-052395086b05.png", review_status: "rejected_readability", notes: "Sleeping dragons were too faint at production reference size." },
  { candidate_id: "LUA_CHILD_WRIST_A", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-9c8e55d1-eb80-426f-a2fc-525a23b8e16e.png", review_status: "approved", final_source_path: approvedAssets[2].source_path },
  { candidate_id: "S04_SEA_BASKET_COMPOSITE_A", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-3f4ec7b8-f3f8-4e26-a310-63c62c43b962.png", review_status: "approved", final_source_path: approvedAssets[4].source_path },
  { candidate_id: "S05_NIGHT_MASTER_A", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-8f049e0b-8ad6-493a-aa27-ddd2a11512e0.png", review_status: "approved", final_source_path: approvedAssets[5].source_path },
  { candidate_id: "S04_BASIN_CORNER_V3", source_path: "backgrounds/generated_v3/BG_EP01_S04_BASIN_CORNER_DAY_V3.png", review_status: "rejected_continuity", notes: "Independent generation changed room geometry; retained on disk but disconnected." },
  { candidate_id: "S04_BASIN_TABLE_V3", source_path: "backgrounds/generated_v3/BG_EP01_S04_BASIN_TABLE_DAY_V3.png", review_status: "rejected_continuity", notes: "Independent generation changed room geometry and apparent prop scale; retained on disk but disconnected." },
];
inventory.approved_assets = approvedAssets;
inventory.final_connections = finalConnections;
inventory.provenance.postprocess = "Approved built-in outputs were non-destructively scaled/cropped to 1280x704 with ffmpeg; prior and original assets remain on disk.";
inventory.provenance.visual_review = "All referenced assets were reviewed in five scene contact sheets; every new candidate and the six-asset continuity-v4 contact sheet were opened at original detail before connection.";

fs.writeFileSync(inventoryPath, `${JSON.stringify(inventory, null, 2)}\n`, "utf8");
console.log(JSON.stringify(inventory.final_summary, null, 2));
