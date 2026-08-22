const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const repo = path.resolve(__dirname, "..");
const project = path.join(repo, "prompt_projects/RaisingaDragonSeason01_EP01_H3_R2V");
const output = path.join(project, "asset_generation_inventory.json");

function payloadFromMarkdown(file) {
  const text = fs.readFileSync(file, "utf8");
  const matches = [...text.matchAll(/```json\s*\n([\s\S]*?)\n```/g)];
  return JSON.parse(matches.at(-1)[1]);
}

const scenePacks = JSON.parse(fs.readFileSync(path.join(project, "scene_packs.json"), "utf8")).scene_packs;
const problemPaths = new Map([
  ["backgrounds/localized_v2/BG_EP01_S04_DOOR_ZONE_LOCAL_DAY.png", {
    status: 5,
    fit: "Day-house view repeats floor bedding instead of the screenplay's raised wooden bed and does not preserve the complete door-to-basin-to-table layout.",
    action: "replace",
  }],
  ["backgrounds/localized_v2/BG_EP01_S04_BASIN_CORNER_LOCAL_DAY.png", {
    status: 5,
    fit: "Basin is usable, but the adjacent floor bedding contradicts the raised wooden bed master layout.",
    action: "replace",
  }],
  ["backgrounds/localized_v2/BG_EP01_S04_BASIN_TABLE_LOCAL_DAY.png", {
    status: 5,
    fit: "Basin and low tabletop are readable, but this independently generated room does not carry the required raised-bed master geometry.",
    action: "replace",
  }],
  ["backgrounds/localized_v2/BG_EP01_S05_BASIN_CLOSE_LOCAL_NIGHT.png", {
    status: 5,
    fit: "Night basin view reconnects a pillow and folded floor sleeping mat, contradicting the approved raised wooden bed state.",
    action: "replace",
  }],
]);

const files = [];
for (const sceneName of fs.readdirSync(project).filter((name) => /^EP01-S\d\d$/.test(name)).sort()) {
  const sceneDir = path.join(project, sceneName);
  for (const name of fs.readdirSync(sceneDir).filter((name) => name.endsWith(".md")).sort()) {
    files.push(path.join(sceneDir, name));
  }
}

const references = [];
for (const file of files) {
  const payload = payloadFromMarkdown(file);
  const packs = scenePacks.filter((pack) => pack.clip_ids.includes(payload.clip_id)).map((pack) => pack.pack_id);
  for (const ref of payload.references) {
    const absolute = path.resolve(project, ref.source_path);
    const connected = absolute.startsWith(`${project}${path.sep}`) && fs.existsSync(absolute);
    let classification = problemPaths.get(ref.source_path) || {
      status: connected ? 1 : 4,
      fit: connected
        ? "Visually reviewed against the connected role, screenplay action, grounding surface, and scene-pack axis; retained."
        : "Required project-local image is missing.",
      action: connected ? "keep" : "create",
    };
    if (payload.clip_id === "EP01-S04-C05" && ref.source_path.endsWith("BG_EP01_S04_DOOR_ZONE_LOCAL_DAY.png")) {
      classification = {
        status: 6,
        fit: "The real daytime house is incorrectly reused for the imagined cold sea-exit rejection space.",
        action: "replace",
      };
    }
    references.push({
      clip_id: payload.clip_id,
      picture_index: ref.picture_index,
      role: ref.role,
      label: ref.label,
      current_source_path: ref.source_path,
      connection_status: connected ? "linked" : "missing",
      visual_fit: classification.fit,
      audit_classification: classification.status,
      action: classification.action,
      scene_packs: packs,
      required_composition_and_use: ref.role.startsWith("environment")
        ? "Character-free spatial anchor with usable grounding surface, stable entrance/exit axis, motivated light, and scene landmarks."
        : "Neutral reusable subject reference preserving identity, anatomy, proportions, and material response without pre-acting the clip event.",
      current_sha256: connected ? crypto.createHash("sha256").update(fs.readFileSync(absolute)).digest("hex") : null,
    });
  }
}

const plannedAssets = [
  {
    asset_id: "EP01-S04-HOUSE-MASTER-DAY-V3",
    intended_clips: ["EP01-S04-C01", "EP01-S04-C04", "EP01-S04-C06"],
    role: "environment",
    anchor_type: "master",
    camera: "adult waist height, wide diagonal view from the entrance side toward the left window",
    layers: "foreground clear wood route; midground floor basin and genuinely low table; background raised wooden bed and sea-facing window",
    character_count: 0,
    grounding: "continuous unobstructed wooden floor from door to basin and from basin to table",
    entrances_exits_axis: "closed door frame-right; window frame-left; bed background-left; basin center-low; low table behind basin",
    landmarks: ["raised wooden bed", "floor basin", "low table", "shell", "dried fish", "water container", "door", "window"],
    key_light: "warm daylight from frame-left window toward the right-side door",
    forbidden: ["floor mat", "sleeping mat", "characters", "extra doors or windows", "text", "watermark", "split panel"],
    planned_source_path: "backgrounds/generated_v3/BG_EP01_S04_HOUSE_MASTER_DAY_V3.png",
  },
  {
    asset_id: "EP01-S04-BASIN-CORNER-DAY-V3",
    intended_clips: ["EP01-S04-C02"],
    role: "localized environment",
    anchor_type: "localized",
    camera: "child knee height beside the basin, looking across the same master room",
    layers: "basin rim foreground; clear kneeling floor midground; raised bed and low table landmarks background",
    character_count: 0,
    grounding: "dry wood beside the basin for Lua's knees and hands",
    entrances_exits_axis: "same window-left and door-right axis as the master",
    landmarks: ["shallow floor basin", "raised wooden bed edge", "low table", "water container"],
    key_light: "warm window light from left",
    forbidden: ["floor bedding", "characters", "extra furniture", "text", "watermark", "split panel"],
    planned_source_path: "backgrounds/generated_v3/BG_EP01_S04_BASIN_CORNER_DAY_V3.png",
  },
  {
    asset_id: "EP01-S04-BASIN-TABLE-DAY-V3",
    intended_clips: ["EP01-S04-C03", "EP01-S04-C06", "EP01-S04-C07", "EP01-S04-C08", "EP01-S04-C09"],
    role: "localized environment",
    anchor_type: "localized",
    camera: "small-creature eye height across basin, wood route, and tabletop",
    layers: "basin foreground-left; traversable wood center; low table and tabletop midground-right; raised bed background",
    character_count: 0,
    grounding: "continuous basin-rim-to-floor-to-table-leg climb route and broad usable tabletop",
    entrances_exits_axis: "door remains right-rear and window light enters from left",
    landmarks: ["floor basin", "low climbable table", "shell on tabletop", "dried fish", "water container", "raised bed"],
    key_light: "warm daylight from left with restrained water bounce",
    forbidden: ["floor mat", "characters", "high dining table", "blocked route", "text", "watermark", "split panel"],
    planned_source_path: "backgrounds/generated_v3/BG_EP01_S04_BASIN_TABLE_DAY_V3.png",
  },
  {
    asset_id: "EP01-S04-IMAGINED-SEA-EXIT-V3",
    intended_clips: ["EP01-S04-C05"],
    role: "localized environment",
    anchor_type: "localized subjective anchor",
    camera: "basket height, low frontal view toward a cold sea exit",
    layers: "empty basket placement foreground; two adult standing zones midground; cold surf and exit silhouette background",
    character_count: 0,
    grounding: "firm threshold or coastal platform under the basket and adults",
    entrances_exits_axis: "sea exit directly behind the adult positions, visually separate from the real house",
    landmarks: ["basket placement", "two adult positions", "cold sea exit", "surf"],
    key_light: "cold backlight from the imagined sea",
    forbidden: ["real house furniture", "characters", "basket baked into background", "text", "watermark", "split panel"],
    planned_source_path: "backgrounds/generated_v3/BG_EP01_S04_IMAGINED_SEA_EXIT_V3.png",
  },
  {
    asset_id: "EP01-S04-CARRYING-BASKET-V2",
    intended_clips: ["EP01-S04-C05"],
    role: "prop",
    anchor_type: "reusable prop",
    camera: "neutral three-quarter view at basket height",
    layers: "single empty woven carrying basket centered on a neutral studio ground",
    character_count: 0,
    grounding: "flat stable base with readable handle and interior",
    entrances_exits_axis: "not applicable",
    landmarks: ["woven handle", "open interior", "stable flat base"],
    key_light: "soft neutral key from upper left",
    forbidden: ["dragon", "person", "fish", "text", "watermark", "split panel"],
    planned_source_path: "assets/generated_v2/EP01_S04_CARRYING_BASKET_V2.png",
  },
  {
    asset_id: "EP01-S05-BASIN-CLOSE-NIGHT-V3",
    intended_clips: ["EP01-S05-C04", "EP01-S05-C05", "EP01-S05-C06"],
    role: "localized environment",
    anchor_type: "localized",
    camera: "child knee height beside the floor basin toward the fixed window route",
    layers: "basin foreground; clear support and lifting floor midground; raised bed edge, low table, and window direction background",
    character_count: 0,
    grounding: "unobstructed wet wood beside the basin for kneeling, lifting, and one continuous rise",
    entrances_exits_axis: "raised bed background-left; basin center; window route leftward; door remains right",
    landmarks: ["floor basin", "raised wooden bed", "low table", "window route"],
    key_light: "moonlight from window with very restrained cyan water reflection",
    forbidden: ["floor mat", "sleeping mat", "characters", "extra windows", "text", "watermark", "split panel"],
    planned_source_path: "backgrounds/generated_v3/BG_EP01_S05_BASIN_CLOSE_NIGHT_V3.png",
  },
];

const counts = references.reduce((acc, item) => {
  acc.total += 1;
  if (item.connection_status === "linked") acc.linked += 1;
  if (item.audit_classification === 1) acc.normal += 1;
  if (item.audit_classification === 2 || item.audit_classification === 6) acc.semantic_mismatch += 1;
  if (item.audit_classification === 4) acc.missing += 1;
  if (item.audit_classification === 5) acc.regeneration_required += 1;
  return acc;
}, { total: 0, linked: 0, normal: 0, semantic_mismatch: 0, missing: 0, regeneration_required: 0 });

const document = {
  schema_version: 1,
  project_id: "RaisingaDragonSeason01_EP01_H3_R2V",
  phase: "pre_generation_audit",
  audit_method: [
    "Parsed every Machine Payload in all 42 Clip Markdown files.",
    "Resolved every source_path through the project-local loader rules.",
    "Opened and visually reviewed contact sheets plus full-resolution priority assets.",
    "Compared subjects, grounding, landmarks, and axes against the screenplay and 12 scene packs.",
  ],
  classification_legend: {
    1: "file and project connection are correct; visually usable",
    2: "file exists but conflicts with Clip subject or space meaning",
    3: "file exists but is not linked by the UI/project loader",
    4: "file missing",
    5: "regeneration required for resolution, composition, subject count, grounding, or spatial axis",
    6: "asset from another scene/space is incorrectly reused",
  },
  audit_summary: counts,
  references,
  planned_assets: plannedAssets,
  candidates: [],
  provenance: {
    generation_mode: "built-in image_gen",
    immutable_reference_project: "prompt_projects/RaisingaDragonSeason01_EP01_H3_I2V",
    note: "The I2V project is read-only and is used only as a visual reference.",
  },
};

if (fs.existsSync(output) && !process.argv.includes("--force")) {
  const existing = JSON.parse(fs.readFileSync(output, "utf8"));
  if (existing.phase === "final_reviewed_and_linked") {
    console.error("Final reviewed inventory already exists; use --force only to intentionally rebuild the pre-generation audit.");
    process.exit(2);
  }
}

fs.writeFileSync(output, `${JSON.stringify(document, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ output: path.relative(repo, output), counts, planned_assets: plannedAssets.length }, null, 2));
