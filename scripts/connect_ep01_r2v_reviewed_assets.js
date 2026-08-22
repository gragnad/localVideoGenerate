const fs = require("fs");
const path = require("path");

const repo = path.resolve(__dirname, "..");
const project = path.join(repo, "prompt_projects/RaisingaDragonSeason01_EP01_H3_R2V");

const replacements = new Map([
  ["backgrounds/localized_v2/BG_EP01_S04_DOOR_ZONE_LOCAL_DAY.png", {
    source_path: "backgrounds/generated_v3/BG_EP01_S04_HOUSE_MASTER_DAY_V3.png",
    label: "Day house master",
    description: "Day house master with the raised wooden bed, floor basin, low table, door-to-window axis, and continuous floor route, used as the spatial environment anchor for character grounding, lighting, depth, and camera continuity",
  }],
  ["backgrounds/localized_v2/BG_EP01_S04_BASIN_CORNER_LOCAL_DAY.png", {
    source_path: "backgrounds/generated_v3/BG_EP01_S04_BASIN_CORNER_DAY_V3.png",
    label: "Day house basin corner",
    description: "Day house basin corner with a dry kneeling surface, raised-bed landmark, and stable window-to-door light axis, used as the spatial environment anchor for character grounding, lighting, depth, and camera continuity",
  }],
  ["backgrounds/localized_v2/BG_EP01_S04_BASIN_TABLE_LOCAL_DAY.png", {
    source_path: "backgrounds/generated_v3/BG_EP01_S04_BASIN_TABLE_DAY_V3.png",
    label: "Day house basin-to-table zone",
    description: "Day house basin-to-table zone with a continuous wood route, climbable low table, broad tabletop, shell, fish, and raised-bed landmark, used as the spatial environment anchor for character grounding, lighting, depth, and camera continuity",
  }],
  ["backgrounds/localized_v2/BG_EP01_S05_BASIN_CLOSE_LOCAL_NIGHT.png", {
    source_path: "backgrounds/generated_v3/BG_EP01_S05_BASIN_CLOSE_NIGHT_V3.png",
    label: "Night house basin lift zone",
    description: "Night house basin lift zone with unobstructed wet wood, the raised wooden bed, low table, and window route, used as the spatial environment anchor for character grounding, lighting, depth, and camera continuity",
  }],
]);

function extractPayload(text) {
  const matches = [...text.matchAll(/```json\s*\n([\s\S]*?)\n```/g)];
  if (matches.length !== 1) throw new Error("expected one JSON payload");
  return JSON.parse(matches[0][1]);
}

function environmentDefinition(index, ref) {
  return `<Subject ${index}>: ${ref.description}. Use <Picture ${index}> as the spatial environment anchor. Preserve its topology, landmarks, surface layout, lighting direction, and camera axis while allowing physically consistent depth integration and natural parallax.`;
}

function updatePromptDefinition(prompt, index, definition) {
  const expression = new RegExp(`^<Subject ${index}>:.*$`, "m");
  if (!expression.test(prompt)) throw new Error(`missing Subject ${index} definition`);
  return prompt.replace(expression, definition);
}

function picturePlan(references) {
  return references.map((ref) => `- Picture ${ref.picture_index}: \`${ref.role}\` · ${ref.label} · \`${ref.source_path}\``).join("\n");
}

function writeClip(file) {
  let text = fs.readFileSync(file, "utf8");
  const payload = extractPayload(text);
  let changed = false;

  for (const ref of payload.references) {
    const replacement = replacements.get(ref.source_path);
    if (!replacement) continue;
    if (payload.clip_id === "EP01-S04-C05") continue;
    Object.assign(ref, replacement);
    payload.video_prompt = updatePromptDefinition(payload.video_prompt, ref.picture_index, environmentDefinition(ref.picture_index, ref));
    changed = true;
  }

  if (payload.clip_id === "EP01-S04-C05" && !payload.references.some((ref) => ref.role === "carrying_basket")) {
    const environment = payload.references.find((ref) => ref.role === "environment_primary");
    Object.assign(environment, {
      picture_index: 5,
      label: "Imagined cold sea exit",
      description: "Imagined cold sea exit with an empty grounded foreground, two adult standing zones, and cold surf behind them, used as the spatial environment anchor for character grounding, lighting, depth, and camera continuity",
      source_path: "backgrounds/generated_v3/BG_EP01_S04_IMAGINED_SEA_EXIT_V3.png",
    });
    payload.references.splice(3, 0, {
      picture_index: 4,
      role: "carrying_basket",
      label: "Imagined carrying basket",
      description: "Empty handmade woven carrying basket with a stable flat base, open padded interior, and one sturdy arched handle",
      source_path: "assets/generated_v2/EP01_S04_CARRYING_BASKET_V2.png",
      required: true,
    });
    payload.video_prompt = payload.video_prompt
      .replace(/^<Subject 4>:.*$/m, [
        "<Subject 4>: Empty handmade woven carrying basket with a stable flat base, open padded interior, and one sturdy arched handle. Use <Picture 4> as the exact visual reference for this subject.",
        environmentDefinition(5, environment),
      ].join("\n"))
      .replace("<Subject 4> (appears in [Shot 1]): fully_preserved; preserve the established geometry, landmarks, lighting direction, depth, and screen axis.", [
        "<Subject 4> (appears in [Shot 1], [Shot 2]): fully_preserved; preserve the basket construction, handle, open interior, scale, grounding, and material response.",
        "<Subject 5> (appears in [Shot 1], [Shot 2]): fully_preserved; preserve the established geometry, landmarks, lighting direction, depth, and screen axis.",
      ].join("\n"))
      .replace(
        "Premium animated-feature rendering distinguishes worn house wood, coarse cloth, basin water, shell, dry fish, skin, and Mir's scales under warm directional daylight. Each material keeps its own restrained response without uniform gloss.",
        "Premium animated-feature rendering distinguishes wet coastal planks, woven reed, coarse cloth, cold surf, skin, and Mir's scales under desaturated sea backlight. Each material keeps its own restrained response without uniform gloss."
      )
      .replace(
        "Only <Subject 2>, <Subject 3>, and the basket containing <Subject 1> are visible in the imagined scene; no additional character appears. This is clearly an imagined fear sequence, marked by desaturated light and rippling frame edges. <Subject 4> remains the unchanged background. <Subject 2>, the first imagined village adult, recoils from <Subject 1>, the small juvenile dragon now contained in a simple carrying basket,",
        "Only <Subject 2>, <Subject 3>, and <Subject 4> containing <Subject 1> are visible in the imagined scene; no additional character appears. This is clearly an imagined fear sequence, marked by desaturated light and rippling frame edges. <Subject 5> holds the cold sea exit behind the two adult positions. <Subject 2>, the first imagined village adult, recoils from <Subject 1>, the small juvenile dragon now contained in <Subject 4>,"
      )
      .replace(
        "<Subject 3>, the second imagined adult, grabs the basket handle and turns toward the implied sea exit.",
        "Against <Subject 5>, <Subject 3>, the second imagined adult, grabs the handle of <Subject 4> and turns toward the cold sea exit."
      );
    changed = true;
  }

  if (!changed) return false;
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
