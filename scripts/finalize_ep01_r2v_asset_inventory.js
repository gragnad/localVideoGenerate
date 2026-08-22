const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const repo = path.resolve(__dirname, "..");
const project = path.join(repo, "prompt_projects/RaisingaDragonSeason01_EP01_H3_R2V");
const inventoryPath = path.join(project, "asset_generation_inventory.json");
const inventory = JSON.parse(fs.readFileSync(inventoryPath, "utf8"));

function sha256(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

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
        subject_index: ref.picture_index,
        role: ref.role,
        label: ref.label,
        source_path: ref.source_path,
        linked: fs.existsSync(absolute),
        sha256: fs.existsSync(absolute) ? sha256(absolute) : null,
      });
    }
  }
}

const approved = [
  {
    asset_id: "EP01-S04-HOUSE-MASTER-DAY-V3",
    source_path: "backgrounds/generated_v3/BG_EP01_S04_HOUSE_MASTER_DAY_V3.png",
    review_status: "approved",
    candidate_count: 2,
    generation_prompt: "Create the complete character-free daytime fishing house as one coherent premium stylized 3D animated-feature space: left sea window, right closed door, raised wooden bed, center floor basin, genuinely low climbable table, water container, shell and dried fish; continuous door-to-basin and basin-to-table floor routes; warm left-window light; prohibit floor bedding, extra openings, characters, text, watermark, UI and split panels.",
  },
  {
    asset_id: "EP01-S04-BASIN-CORNER-DAY-V3",
    source_path: "backgrounds/generated_v3/BG_EP01_S04_BASIN_CORNER_DAY_V3.png",
    review_status: "approved",
    candidate_count: 1,
    generation_prompt: "From the approved day master, create a character-free child-knee-height basin-corner anchor with basin rim foreground, broad dry kneeling floor, raised-bed post and low-table landmarks, identical left-window/right-door axis and materials; prohibit floor bedding, duplicate furniture, text, watermark and split panels.",
  },
  {
    asset_id: "EP01-S04-BASIN-TABLE-DAY-V3",
    source_path: "backgrounds/generated_v3/BG_EP01_S04_BASIN_TABLE_DAY_V3.png",
    review_status: "approved",
    candidate_count: 1,
    generation_prompt: "From the approved day master, create a character-free tiny-dragon-eye-height anchor showing basin foreground-left, dry landing, continuous four-foot wood route, climbable low table leg and edge, broad tabletop, shell, fish, water container and raised-bed landmark; prohibit floor bedding, high table, blocked route, text, watermark and split panels.",
  },
  {
    asset_id: "EP01-S04-IMAGINED-SEA-EXIT-V3",
    source_path: "backgrounds/generated_v3/BG_EP01_S04_IMAGINED_SEA_EXIT_V3.png",
    review_status: "approved_with_notes",
    candidate_count: 2,
    generation_prompt: "Create a character-free subjective cold coastal sea-exit anchor at basket height with an empty wet-plank grounding foreground, two adult standing zones, and desaturated storm surf on one deep axis, separate from the real house; remove the accidentally generated basket while preserving all environment geometry and lighting; prohibit people, creatures, baskets, house furniture, text, watermark and split panels.",
  },
  {
    asset_id: "EP01-S04-CARRYING-BASKET-V2",
    source_path: "assets/generated_v2/EP01_S04_CARRYING_BASKET_V2.png",
    review_status: "approved",
    candidate_count: 1,
    generation_prompt: "Create exactly one empty handmade oval woven carrying basket for a tiny juvenile sea dragon, with stable flat base, open undyed cloth-lined interior and one sturdy arched handle, neutral three-quarter prop view, premium stylized 3D materials; prohibit characters, animals, food, lid, extra baskets, text, logo, watermark and split panels.",
  },
  {
    asset_id: "EP01-S05-BASIN-CLOSE-NIGHT-V3",
    source_path: "backgrounds/generated_v3/BG_EP01_S05_BASIN_CLOSE_NIGHT_V3.png",
    review_status: "approved",
    candidate_count: 1,
    generation_prompt: "Using the approved day master topology and existing night mood, create a character-free basin support-and-lift zone with floor basin foreground, broad wet kneeling floor, raised wooden bed on legs background-left, low table, clear window route and right door; moonlight from left; prohibit every floor mat, sleeping mat, floor pillow or blanket, extra opening, character, text, watermark and split panel.",
  },
];

for (const asset of approved) {
  const absolute = path.join(project, asset.source_path);
  Object.assign(asset, pngSize(absolute), { sha256: sha256(absolute), generation_mode: "built-in image_gen" });
}

inventory.phase = "final_reviewed_and_linked";
inventory.final_summary = {
  clips: 42,
  reference_instances: finalConnections.length,
  linked_reference_instances: finalConnections.filter((item) => item.linked).length,
  approved_unique_assets: new Set(finalConnections.map((item) => item.source_path)).size,
  newly_generated_unique_assets: approved.length,
  reused_unique_assets: new Set(finalConnections.filter((item) => !item.source_path.includes("/generated_v")).map((item) => item.source_path)).size,
  approved: 5,
  approved_with_notes: 1,
  rejected_candidates: 2,
  regeneration_count: 1,
};
inventory.candidates = [
  { candidate_id: "S04_MASTER_A", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-158e6329-61fd-416a-a7f8-f1ddebc6c9e7.png", review_status: "rejected_continuity", notes: "Introduced an extra full-height table in addition to the required low table." },
  { candidate_id: "S04_MASTER_B", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-2a42b296-07e2-4aab-8106-e9cad54d1c09.png", review_status: "approved", final_source_path: approved[0].source_path },
  { candidate_id: "S04_BASIN_CORNER_A", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-6be11ca0-013d-4fed-80e0-a58d0e1093fc.png", review_status: "approved", final_source_path: approved[1].source_path },
  { candidate_id: "S04_BASIN_TABLE_A", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-3dc2290c-3cc2-4e0a-9d41-e4c7047e4de2.png", review_status: "approved", final_source_path: approved[2].source_path },
  { candidate_id: "S04_IMAGINED_EXIT_A", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-1c6cecff-44bc-4133-a920-de660e020437.png", review_status: "rejected_extra_subject", notes: "Environment candidate baked a basket into the foreground." },
  { candidate_id: "S04_BASKET_A", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-0be256f0-6c23-4ae3-a16d-8db41354c2fd.png", review_status: "approved", final_source_path: approved[4].source_path },
  { candidate_id: "S05_BASIN_CLOSE_A", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-d60a4bf4-6caf-4c04-91b4-0a9e8c6dfe87.png", review_status: "approved", final_source_path: approved[5].source_path },
  { candidate_id: "S04_IMAGINED_EXIT_B_EDIT", output_path: "/home/nalstudio/.codex/generated_images/019fe52a-bdc0-79e3-b7c8-b2ec1cb050e9/exec-f0888907-df90-4cb9-bd42-420d4eb457c6.png", review_status: "approved_with_notes", notes: "Basket removed; coastal rendering is slightly more realistic than the interior anchors but matches existing coastal backgrounds.", final_source_path: approved[3].source_path },
];
inventory.approved_assets = approved;
inventory.final_connections = finalConnections;
inventory.provenance.postprocess = "Approved built-in outputs were non-destructively scaled/cropped or padded to 1280x704 with ffmpeg; originals remain in the Codex generated-images directory.";
inventory.provenance.visual_review = "Every candidate and the final six-asset contact sheet were opened and inspected at original detail before connection.";

fs.writeFileSync(inventoryPath, `${JSON.stringify(inventory, null, 2)}\n`, "utf8");
console.log(JSON.stringify(inventory.final_summary, null, 2));
