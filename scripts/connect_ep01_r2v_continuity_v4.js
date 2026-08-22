const fs = require("fs");
const path = require("path");

const repo = path.resolve(__dirname, "..");
const project = path.join(repo, "prompt_projects/RaisingaDragonSeason01_EP01_H3_R2V");

const DAY_MASTER = {
  source_path: "backgrounds/generated_v4/BG_EP01_S04_HOUSE_MASTER_DAY_V4.png",
  label: "Canonical day house master",
  description: "Canonical daytime house plate with the fixed left window, raised bed, low table, floor basin, right door, baskets, shells, and one continuous wood-floor route",
};
const NIGHT_MASTER = {
  source_path: "backgrounds/generated_v4/BG_EP01_S05_HOUSE_MASTER_NIGHT_V4.png",
  label: "Canonical night house master",
  description: "Lighting-only night version of the canonical house plate with the identical window, raised bed, low table, floor basin, right door, props, positions, sizes, and camera axis",
};

const replacements = new Map([
  ["backgrounds/BG_EP01_COASTAL_VILLAGE_MORNING.png", {
    source_path: "backgrounds/generated_v4/BG_EP01_S02_VILLAGE_MASTER_OVERCAST_V2.png",
    label: "Post-storm overcast village master",
    description: "Cold overcast post-storm coastal village plate with wet stone, gray surf, fishing houses, boats, and the clear breakwater route",
  }],
  ["backgrounds/Sleeping_Dragon_Hall_v2.png", {
    source_path: "backgrounds/generated_v4/Sleeping_Dragon_Hall_V3_APPROVED.png",
    label: "Ruined sleeping dragon hall",
    description: "Dim broken underwater palace hall with four motionless sleeping dragons in side alcoves and a clear central corridor",
  }],
  ["assets/Dragon_Heart_Wrist_Mark.png", {
    source_path: "assets/generated_v3/Dragon_Heart_Wrist_Mark_Lua_Child_V2.png",
    label: "Lua child Dragon Heart wrist mark",
    description: "Lua's small child-proportioned hand and wrist bearing the readable cyan Dragon Heart emblem",
  }],
  ["backgrounds/generated_v3/BG_EP01_S04_HOUSE_MASTER_DAY_V3.png", DAY_MASTER],
  ["backgrounds/generated_v3/BG_EP01_S04_BASIN_CORNER_DAY_V3.png", DAY_MASTER],
  ["backgrounds/generated_v3/BG_EP01_S04_BASIN_TABLE_DAY_V3.png", DAY_MASTER],
  ["backgrounds/BG_EP01_LUA_HOUSE_INTERIOR_NIGHT.png", NIGHT_MASTER],
  ["backgrounds/generated_v3/BG_EP01_S05_BASIN_CLOSE_NIGHT_V3.png", NIGHT_MASTER],
  ["backgrounds/localized_v2/BG_EP01_S05_BASIN_WINDOW_ROUTE_LOCAL_NIGHT.png", NIGHT_MASTER],
]);

function extractPayload(text) {
  const matches = [...text.matchAll(/```json\s*\n([\s\S]*?)\n```/g)];
  if (matches.length !== 1) throw new Error("expected one JSON payload");
  return JSON.parse(matches[0][1]);
}

function definition(index, ref) {
  if (ref.role === "environment_primary") {
    return `<Subject ${index}>: ${ref.description}. Use <Picture ${index}> as the spatial environment anchor. Preserve its topology, landmarks, object positions, object scale, lighting direction, and camera axis while allowing physically consistent depth integration and natural parallax.`;
  }
  return `<Subject ${index}>: ${ref.description}. Use <Picture ${index}> as the exact visual reference for this subject.`;
}

function replaceDefinition(prompt, index, value) {
  const expression = new RegExp(`^<Subject ${index}>:.*$`, "m");
  if (!expression.test(prompt)) throw new Error(`missing Subject ${index}`);
  return prompt.replace(expression, value);
}

function picturePlan(references) {
  return references.map((ref) => `- Picture ${ref.picture_index}: \`${ref.role}\` · ${ref.label} · \`${ref.source_path}\``).join("\n");
}

function writeClip(file) {
  let text = fs.readFileSync(file, "utf8");
  const payload = extractPayload(text);
  let changed = false;

  if (payload.prompt_revision !== "ep01_r2v_continuity_reaudit_v5") {
    payload.prompt_revision = "ep01_r2v_continuity_reaudit_v5";
    changed = true;
  }

  if (payload.clip_id === "EP01-S04-C05") {
    const environment = payload.references.find((ref) => ref.role === "environment_primary");
    payload.references = payload.references.filter((ref) => ref.role !== "carrying_basket");
    Object.assign(environment, {
      picture_index: 4,
      label: "Imagined sea exit with fixed-scale basket",
      description: "Cold imagined sea-exit plate containing exactly one grounded woven basket at a fixed scene scale on the wet foreground planks",
      source_path: "backgrounds/generated_v4/BG_EP01_S04_IMAGINED_SEA_BASKET_SCALE_V4.png",
    });
    payload.video_prompt = payload.video_prompt
      .replace(/^<Subject 4>:[\s\S]*?(?=\n\nsummary:)/m, definition(4, environment))
      .replace(/^<Subject 4> \(appears in \[Shot 1\], \[Shot 2\]\):.*\n<Subject 5> \(appears in \[Shot 1\], \[Shot 2\]\):.*$/m,
        "<Subject 4> (appears in [Shot 1], [Shot 2]): fully_preserved; preserve the sea-exit geometry and exactly one basket's construction, handle, open interior, fixed scene scale, plank contact, lighting, depth, and screen axis.")
      .replace(/Only <Subject 2>, <Subject 3>, and <Subject 4> containing <Subject 1> are visible/g,
        "Only <Subject 2>, <Subject 3>, and the single basket inside <Subject 4> containing <Subject 1> are visible")
      .replace(/<Subject 5> holds the cold sea exit behind the two adult positions\./g,
        "<Subject 4> holds the cold sea exit and its single fixed-scale basket behind the two adult positions.")
      .replace(/now contained in <Subject 4>/g, "now contained in the single basket inside <Subject 4>")
      .replace(/Against <Subject 5>, <Subject 3>, the second imagined adult, grabs the handle of <Subject 4>/g,
        "Against <Subject 4>, <Subject 3>, the second imagined adult, grabs the handle of its single basket");
    changed = true;
  }

  for (const ref of payload.references) {
    const replacement = replacements.get(ref.source_path);
    if (!replacement) continue;
    Object.assign(ref, replacement);
    payload.video_prompt = replaceDefinition(payload.video_prompt, ref.picture_index, definition(ref.picture_index, ref));
    changed = true;
  }

  if (!changed) return false;
  payload.prompt_revision = "ep01_r2v_continuity_reaudit_v5";
  const promptBlock = `## Final English H3 R2V Prompt\n\n\`\`\`text\n${payload.video_prompt}\n\`\`\``;
  const payloadBlock = `## Machine Payload\n\`\`\`json\n${JSON.stringify(payload, null, 2)}\n\`\`\``;
  text = text
    .replace(/## Picture Plan\n\n[\s\S]*?\n\n## Final English H3 R2V Prompt/, `## Picture Plan\n\n${picturePlan(payload.references)}\n\n## Final English H3 R2V Prompt`)
    .replace(/## Final English H3 R2V Prompt\n\n```text\n[\s\S]*?\n```/, promptBlock)
    .replace(/## Machine Payload\n```json\n[\s\S]*?\n```/, payloadBlock);
  fs.writeFileSync(file, text, "utf8");
  return true;
}

const changed = [];
for (const scene of fs.readdirSync(project).filter((name) => /^EP01-S\d\d$/.test(name)).sort()) {
  for (const name of fs.readdirSync(path.join(project, scene)).filter((name) => name.endsWith(".md")).sort()) {
    const file = path.join(project, scene, name);
    if (writeClip(file)) changed.push(path.relative(project, file).split(path.sep).join("/"));
  }
}

console.log(JSON.stringify({ changed_count: changed.length, changed }, null, 2));
