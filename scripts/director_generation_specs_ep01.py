"""Standalone generation specs for RaisingaDragonSeason01 EP01 Director project."""
from __future__ import annotations

from typing import Any

APPEARANCES: dict[str, str] = {'lua': 'Lua is a sun-browned human village girl with warm amber-brown eyes, a messy high loose brown hair bun, beige sleeveless tunic and shorts, a rope belt, a white shell pendant at her chest, and a faint blue mark on her left wrist. She is fully human with no dragon horns, wings, tail, or scales.', 'mir': 'Young Mir is a small silver-blue sea dragon hatchling with short curved horns, one pair of fin-like wings, four small dragon limbs, a long scaled tail ending in a water-drop crystal, and a faint crown-shaped wave mark on his chest. He is a dragon only, with no human clothing or human facial features.', 'child1': 'Village Child 1 is a boy with short tousled black-brown hair and a charcoal sleeveless V-neck tunic. He has no shoulder basket, no shell pendant, and no blue wrist mark.', 'child2': 'Village Child 2 is a girl with a high black ponytail tied with an ochre band, an indigo-blue tunic with a cream frill collar, and a woven shoulder basket resting at her right hip.', 'fisherman': 'The Old Fisherman is a tall elderly adult with gray hair and a full gray beard, wearing a navy work vest over simple coastal clothing.', 'black_tide': 'The Black Tide is a living supernatural mass of black water with brief hand-like and mouth-like shadow shapes forming and dissolving inside its form. It is a separate entity, not part of the background water.', 'jellyfish': 'The Black Jellyfish is a semi-transparent dark bell-shaped jellyfish with ink-smoke swirling inside its body and long trailing tentacles below the surface. It floats as a single separate entity over the sea.', 'spear': "Lua's handmade coastal fishing spear is a simple wooden shaft with a tied stone or bone tip, weathered from village use."}

REFERENCE_PATHS: dict[str, str] = {'lua': 'RaisingaDragonSeason01/Lua.png', 'mir': 'RaisingaDragonSeason01/YoungMir.png', 'child1': 'RaisingaDragonSeason01/villageChild01.png', 'child2': 'RaisingaDragonSeason01/village_child_2.png', 'fisherman': 'RaisingaDragonSeason01/old_fisherman.png', 'spear': 'RaisingaDragonSeason01/spear.png', 'black_tide': 'RaisingaDragonSeason01/BLACK TIDE — SUPERNATURAL .png', 'jellyfish': 'RaisingaDragonSeason01/BLACK JELLYFISH .png'}

BACKGROUND_NEGATIVE = 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality'

SEGMENT_NEGATIVE_BASE = 'text, subtitles, speech bubbles, watermark, logo, duplicate characters, merged bodies, fused anatomy, extra limbs, malformed hands, incorrect character count, incorrect prop ownership, motion blur, live action, photorealism'

BACKGROUND_IMAGE_GENERATION: dict[str, dict[str, str]] = {'LOC_EP01_STORM_SEA_SURFACE_NIGHT': {'generation_prompt': 'Premium stylized 3D animated feature-film environment plate, cinematic 16:9. Eye-level extreme wide shot facing open storm sea. Foreground: churning dark waves with white foam crests, diagonal rain streaks, and spray particles leaving a broad open performance space across the center water. Middle ground: towering wave walls rolling under heavy black storm clouds with lightning-lit edges. Background: distant lightning-lit horizon line and layered grey storm clouds receding into depth. Terrain is open ocean only with no land, structures, or vessels. Fixed elements include rain curtains, foam ribbons, and a cool-white lightning flash direction from upper left. Time of night during a violent moonless storm. Lighting comes from upper-left lightning and faint ambient bounce off wet wave surfaces. Palette: deep blue-black sea, grey storm clouds, white foam highlights, cold desaturated atmosphere. The plate is explicitly empty — no people, creatures, dragons, animals, boats, faces, silhouettes, props, text, or characters anywhere in frame.', 'negative_prompt': 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality', 'suggested_filename': 'BG_EP01_STORM_SEA_SURFACE_NIGHT.png'}, 'LOC_EP01_DEEP_SEA_RUINS_NIGHT': {'generation_prompt': 'Premium stylized 3D animated feature-film environment plate, cinematic 16:9. Eye-level wide underwater shot looking into deep sea dragon palace ruins. Foreground: open drifting water with marine snow particles and a clear central performance volume for later character placement. Middle ground: a cracked ancient coral palace pillar with bioluminescent blue veins, chipped stone, and small debris drifting from the fracture. Background: dark teal abyss with faint silhouettes of more ruined coral architecture, broken arches, and collapsed hall fragments receding into depth. Terrain is deep underwater abyss with no surface storm visible. Structures are ruined coral palace remains only. Fixed elements include the central cracked pillar, drifting sediment motes, and soft caustic shimmer. Underwater night with no sunlight. Lighting is cold cyan ambient fill from above with soft blue bioluminescence on coral edges. Palette: dark teal abyss, cyan bioluminescent accents, muted sacred ruin tones. Explicitly empty — no people, creatures, dragons, animals, faces, silhouettes, props, or characters.', 'negative_prompt': 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality', 'suggested_filename': 'BG_EP01_DEEP_SEA_RUINS_NIGHT.png'}, 'LOC_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY': {'generation_prompt': 'Premium stylized 3D animated feature-film environment plate, cinematic 16:9. Eye-level medium-wide underwater shot angled slightly upward along a deep teal corridor. Foreground: open teal water with a clear diagonal ascent path marked by a faint blue light beam leaving room for a small swimming subject later. Middle ground: wide open channel with faint ruined coral edges at both sides but no living black water mass. Background: deep abyss below fading to black with subtle particulate haze. Terrain is an underwater passage with no floor visible, only water volume. Structures are partial ruined coral wall edges framing the corridor. Fixed elements include the diagonal blue ascent light from upper left, side ruin silhouettes, and empty central channel. Underwater night. Lighting: cold cyan ambient from above-left and deep teal shadow below. Palette: teal water, cyan beam, dark abyss. Explicitly empty — no Black Tide, shadow creatures, dragons, people, animals, faces, silhouettes, props, or characters in the plate.', 'negative_prompt': 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality', 'suggested_filename': 'BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY.png'}, 'LOC_EP01_MIR_VISION_PALACE_RUINS': {'generation_prompt': 'Premium stylized 3D animated feature-film environment plate, cinematic 16:9. Eye-level wide shot with slight dutch unsettling tilt through a surreal memory void. Foreground: floating debris, dust motes, and open central vision space for later subject placement. Middle ground: broken dragon palace gate, fractured hall columns, and cracked floor fragments suspended over abyss. Background: endless black void with enormous sleeping dragon shadow silhouettes curled on ledges without readable faces or eyes. Terrain is surreal floating ruin fragments over void rather than solid ground. Structures are broken palace architecture in desaturated stone. Fixed elements include gate ruins, column rows, shadow silhouettes, fog, and drifting memory dust. Timeless dream-memory moment with no physical weather. Lighting: cold blue memory-light with deep black void and soft fog edges wrapping the ruins. Palette: desaturated blue-grey, deep black void, faint cyan accents, low saturation nightmare calm. Explicitly empty — no people, creatures, dragons with readable faces, animals, props, text, or characters in the plate.', 'negative_prompt': 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality', 'suggested_filename': 'BG_EP01_MIR_VISION_PALACE_RUINS.png'}, 'LOC_EP01_COASTAL_VILLAGE_MORNING': {'generation_prompt': 'Premium stylized 3D animated feature-film environment plate, cinematic 16:9. Eye-level medium-wide shot from wet stone breakwater facing calm sea. Foreground: damp breakwater stones with scattered wet rope at edges and a clear open standing area at center for later character placement. Middle ground: overturned boats, tangled nets, broken wood, and village repair debris on damp sand without people. Background: soft post-storm morning sky, calm sea horizon, and distant cliff with cave entrance hint at far right. Terrain combines wet stone breakwater and damp beach sand. Structures are fishing village work-shore elements only. Fixed elements include breakwater edge, rope coils, boat hulls, and cliff silhouette. Morning after storm. Lighting: soft diffused sunlight from frame right with cool blue bounce on wet stone. Palette: warm morning light on grey wet stone, soft sky blues, gentle post-storm calm. Explicitly empty — no people, creatures, animals, faces, silhouettes, props held by characters, text, or characters.', 'negative_prompt': 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality', 'suggested_filename': 'BG_EP01_COASTAL_VILLAGE_MORNING.png'}, 'LOC_EP01_COASTAL_CAVE_INTERIOR': {'generation_prompt': 'Premium stylized 3D animated feature-film environment plate, cinematic 16:9. Eye-level medium shot looking from cave entrance toward deeper tunnel. Foreground: shallow seawater over uneven rock with reflective ripples and a clear central approach path for later character placement. Middle ground: damp stone walls with droplets, rocky crevices, and wet ledges catching soft blue light. Background: tunnel receding into shadow with stronger mystical blue glow from cave depth behind camera view. Terrain is wet cave floor with shallow water pools and uneven stone. Structures are natural stone cave walls and low ceiling with no built furniture. Fixed elements include water ripples, wall droplets, blue-teal ambient glow stronger toward depth, and daylight hint behind camera. Daytime exterior light outside with cool cave interior. Lighting: cool blue-teal ambient from depth plus faint daylight rim behind camera. Palette: blue-teal wet stone, soft cyan glow, dark recess shadows, moist coastal cave atmosphere. Explicitly empty — no people, creatures, dragons, animals, faces, silhouettes, props, or characters.', 'negative_prompt': 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality', 'suggested_filename': 'BG_EP01_COASTAL_CAVE_INTERIOR.png'}, 'LOC_EP01_COASTAL_CAVE_TOWARD_MOUTH': {'generation_prompt': 'Premium stylized 3D animated feature-film environment plate, cinematic 16:9. Eye-level medium-wide reverse shot from deeper inside the coastal cave looking toward the bright cave mouth and daylight exit ahead. Foreground: shallow seawater over uneven wet rock with a clear central walking path opening toward the glowing exit for later character placement. Middle ground: damp stone walls narrowing toward the mouth, droplets catching daylight, and wet floor reflections. Background: bright overexposed daylight through the cave mouth opening with soft coastal haze outside, while cool blue-teal shadow remains behind the camera in the deeper cave. Terrain is wet cave floor with shallow pools. Structures are natural stone cave walls forming a tunnel toward exit. Fixed elements include the luminous mouth opening, wet rock path, wall crevices, and reflective puddles. Daytime with exterior daylight through mouth. Lighting: strong forward daylight from mouth center and cool blue ambient fill from deeper cave behind camera. Palette: warm daylight white at mouth, blue-teal interior shadow, wet stone greys. Explicitly empty — no people, creatures, dragons, animals, faces, silhouettes, props, or characters.', 'negative_prompt': 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality', 'suggested_filename': 'BG_EP01_COASTAL_CAVE_TOWARD_MOUTH.png'}, 'LOC_EP01_LUA_HOUSE_INTERIOR_DAY': {'generation_prompt': 'Premium stylized 3D animated feature-film environment plate, cinematic 16:9. Eye-level medium-wide interior shot of a humble coastal house room. Foreground: wooden floor boards with open floor space for later character placement. Middle ground: wooden bed, small table, and shallow water basin at consistent side positions without occupants. Background: window with warm daylight view and simple wall planks. Terrain is flat wooden floor with worn coastal texture. Structures include bed frame, table, basin, and window frame in fixed layout continuity. Fixed elements: basin at consistent side, table with scattered shells and dried fish as environment props only, water jar, cloth scrap, and daylight through window. Daytime with soft coastal sunlight. Lighting: warm daylight from window with gentle interior fill and soft shadow under furniture. Palette: warm wood tones, cream shells, soft daylight yellows and gentle brown shadows. Explicitly empty — no people, creatures, dragons, animals, faces, silhouettes, held props, or characters.', 'negative_prompt': 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality', 'suggested_filename': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY.png'}, 'LOC_EP01_LUA_HOUSE_IMAGINED_VILLAGE': {'generation_prompt': 'Premium stylized 3D animated feature-film environment plate, cinematic 16:9. Eye-level medium interior shot of the same humble house room overlaid with a fearful dream tint. Foreground: open wooden floor blending into ghostly sand at the edges with clear center space for characters later. Middle ground: blurred village shore shapes, ghostly baskets, and rope coils at frame edges without readable adult faces. Background: washed-out house walls and window light diffused into desaturated fog. Terrain mixes literal wooden floor with imagined shore blur at the periphery. Structures include faint house bed and table silhouettes plus ghostly village forms dissolving into mist. Fixed elements: desaturated overlay, edge blur, no distinct adult faces, ghost props at periphery, and anxiety-red tint in shadow corners. Dream overlay time with unstable edges. Lighting: cold desaturated light with faint red anxiety tint and soft dreamlike edges. Palette: washed-out grey-blue, muted nightmare tint, low saturation, faint rose shadow. Explicitly empty — no people, creatures, readable faces, animals, silhouettes with identity, or characters.', 'negative_prompt': 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality', 'suggested_filename': 'BG_EP01_LUA_HOUSE_IMAGINED_VILLAGE.png'}, 'LOC_EP01_LUA_HOUSE_INTERIOR_NIGHT': {'generation_prompt': 'Premium stylized 3D animated feature-film environment plate, cinematic 16:9. Eye-level medium-wide interior night shot matching the day house layout. Foreground: dim wooden floor with open space for later character placement. Middle ground: wooden bed, small table, and shallow water basin in the same fixed positions as the day variant. Background: window facing dark night sea with cool moonlight rim. Terrain is wooden floor with soft worn planks. Structures: bed, table, basin, window in unchanged layout continuity. Fixed elements include bed linens, basin water surface, table edge, window frame with night sea view, and faint interior lamp glow near the table edge. Nighttime with quiet coastal house atmosphere and distant sea hush beyond the window. Lighting: low warm interior fill mixed with cool blue moonlight from window at frame right. Palette: warm interior shadows, cool blue moonlight accents, deep night tones, soft amber bedside darkness. Explicitly empty — no people, creatures, dragons, animals, faces, silhouettes, or characters.', 'negative_prompt': 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality', 'suggested_filename': 'BG_EP01_LUA_HOUSE_INTERIOR_NIGHT.png'}, 'LOC_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW': {'generation_prompt': 'Premium stylized 3D animated feature-film environment plate, cinematic 16:9. Elevated eye-level medium-wide shot from a coastal house window toward the night sea. Foreground: minimal window frame edge at sides leaving open view space. Middle ground: dark calm sea surface with gentle ripples and open water for later creature placement as separate subject. Background: faint stars and deep night horizon with unnaturally still atmosphere and no vessels. Terrain is open sea surface only beneath a clear night sky. Structures limited to partial interior window frame edges and faint sill shadow. Fixed elements: empty sea surface, moonlit ripple pattern, faint star field, still air, and elevated coastal house window perspective. Night with quiet ominous calm. Lighting: cool blue moonlight on sea with soft interior darkness at frame edges. Palette: deep night blue sea, silver moon highlights, black sky, subtle interior warmth at frame sides. Explicitly empty — no jellyfish, people, creatures, dragons, animals, faces, silhouettes, boats, or characters in the background plate.', 'negative_prompt': 'people, characters, creatures, dragons, animals, faces, silhouettes, text, subtitles, watermark, logo, readable signs, duplicated structures, changing architecture, inconsistent lighting, distorted perspective, live action, photorealism, 3D render artifacts, blurry, low quality', 'suggested_filename': 'BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW.png'}}

LOCATION_META: dict[str, dict[str, Any]] = {'LOC_EP01_COASTAL_CAVE_TOWARD_MOUTH': {'location_id': 'LOC_EP01_COASTAL_CAVE_TOWARD_MOUTH', 'background_id': 'BG_EP01_COASTAL_CAVE_TOWARD_MOUTH', 'display_name': 'Coastal Cave — Toward Mouth Exit', 'terrain': 'Shallow seawater over uneven wet rock leading toward bright exit', 'structures': 'Natural stone cave walls narrowing toward daylight mouth opening', 'time_of_day': 'Daytime — exterior daylight through cave mouth', 'lighting': 'Strong daylight from cave mouth ahead, cool blue-teal ambient from deeper cave behind camera', 'color_palette': 'Warm daylight at mouth, blue-teal interior shadow, wet stone greys', 'fixed_elements': ['Bright cave mouth opening centered ahead', 'Central wet-rock walking path toward exit', 'Cool blue shadow in deeper cave behind camera', 'Reflective shallow pools on cave floor'], 'dynamic_entities': [], 'interactive_props': ["Lua's fishing spear when held by Lua"], 'environment_props': ['Water ripples', 'Wall droplets catching daylight']}}

SEGMENT_BEATS: dict[tuple[str, str], dict[str, Any]] = {('SC01-001_01', 'SEG01'): {'background_id': 'BG_EP01_STORM_SEA_SURFACE_NIGHT',
                            'bg_brief': 'Churning black storm ocean with white foam, diagonal '
                                        'rain, lightning from upper left, grey storm clouds, and '
                                        'open central water beneath a cold moonless palette.',
                            'entities': [],
                            'moment': 'Night storm sea with no character visible.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, characters, dragons, faces, '
                                               'silhouettes, duplicate figures, live-action, '
                                               'photorealistic, motion blur',
                            'reference_paths': [],
                            'shot': 'Extreme wide shot at eye level across a violent storm night '
                                    'ocean.',
                            'subjects': []},
 ('SC01-001_01', 'SEG02'): {'background_id': 'BG_EP01_STORM_SEA_SURFACE_NIGHT',
                            'bg_brief': 'Churning black storm ocean with white foam, diagonal '
                                        'rain, lightning from upper left, grey storm clouds, and '
                                        'open central water beneath a cold moonless palette.',
                            'entities': [],
                            'moment': 'Wide storm ocean; a tiny blue pulse glows far below the '
                                      'surface.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, visible dragon body, character face, '
                                               'duplicate glows, live-action, photorealistic, '
                                               'motion blur, camera motion lines',
                            'reference_paths': [],
                            'shot': 'High-angle wide shot looking down into a storm-wave trough.',
                            'subjects': []},
 ('SC01-001_01', 'SEG03'): {'background_id': 'BG_EP01_STORM_SEA_SURFACE_NIGHT',
                            'bg_brief': 'Churning black storm ocean with white foam, diagonal '
                                        'rain, lightning from upper left, grey storm clouds, and '
                                        'open central water beneath a cold moonless palette.',
                            'entities': [],
                            'moment': 'High view of storm sea; the blue undersea pulse is slightly '
                                      'brighter beneath a wave trough.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, dragon silhouette, human figure, '
                                               'duplicate lights, live-action, photorealistic, '
                                               'motion blur',
                            'reference_paths': [],
                            'shot': 'High-angle wide composition over storm-dark water.',
                            'subjects': []},
 ('SC01-001_02', 'SEG01'): {'background_id': 'BG_EP01_DEEP_SEA_RUINS_NIGHT',
                            'bg_brief': 'Deep teal underwater abyss with a cracked ancient coral '
                                        'palace pillar, bioluminescent blue veins, marine snow '
                                        'particles, and ruined coral architecture receding into '
                                        'depth.',
                            'entities': [],
                            'moment': 'Deep underwater ruins; a sacred coral pillar is cracking.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, characters, dragons, faces, '
                                               'live-action, photorealistic, motion blur',
                            'reference_paths': [],
                            'shot': 'Wide underwater shot in deep sea dragon palace ruins.',
                            'subjects': []},
 ('SC01-001_02', 'SEG02'): {'background_id': 'BG_EP01_DEEP_SEA_RUINS_NIGHT',
                            'bg_brief': 'Deep teal underwater abyss with a cracked ancient coral '
                                        'palace pillar, bioluminescent blue veins, marine snow '
                                        'particles, and ruined coral architecture receding into '
                                        'depth.',
                            'entities': [],
                            'moment': 'Deep ruins; Young Mir appears in faint blue glow, battered '
                                      'and half-conscious.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, duplicate Mir, human child, human '
                                               'clothing, Lua, wings on human, fused anatomy, '
                                               'live-action, photorealistic, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium underwater shot.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned center in faint blue glow. He '
                                                   'floats battered and half-conscious with folded '
                                                   'fin-like wings, wet silver-blue scales, '
                                                   'half-closed clear blue eyes, and a dim '
                                                   'water-drop tail crystal.',
                                          'who': 'mir'}]},
 ('SC01-001_02', 'SEG03'): {'background_id': 'BG_EP01_DEEP_SEA_RUINS_NIGHT',
                            'bg_brief': 'Deep teal underwater abyss with a cracked ancient coral '
                                        'palace pillar, bioluminescent blue veins, marine snow '
                                        'particles, and ruined coral architecture receding into '
                                        'depth.',
                            'entities': [],
                            'moment': 'Young Mir floats battered in the current, eyes half closed, '
                                      'tail crystal dim.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, duplicate Mir, human face, human hair, '
                                               'clothing on dragon, Lua merged with Mir, '
                                               'live-action, photorealistic, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium close shot on Young Mir suspended in teal water column '
                                    'center frame.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned center in the teal water column. '
                                                   'His body angles diagonally as if tumbling but '
                                                   'frozen, with half-closed blue eyes and a '
                                                   'weakly flickering tail crystal, folded wings '
                                                   'against his scaled sides.',
                                          'who': 'mir'}]},
 ('SC01-001_02', 'SEG04'): {'background_id': 'BG_EP01_DEEP_SEA_RUINS_NIGHT',
                            'bg_brief': 'Deep teal underwater abyss with a cracked ancient coral '
                                        'palace pillar, bioluminescent blue veins, marine snow '
                                        'particles, and ruined coral architecture receding into '
                                        'depth.',
                            'entities': [],
                            'moment': 'Young Mir floats weakly, oriented upward toward a blue '
                                      'light diagonal above.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, duplicate Mir, human body, wings on '
                                               'human, live-action, photorealistic, motion blur, '
                                               'completed escape',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Low-angle medium shot looking up past Young Mir in lower '
                                    'center frame.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned lower center. He is oriented upward '
                                                   'with head and snout aimed toward a faint blue '
                                                   'diagonal light beam in the upper frame, fins '
                                                   'and wings slack from exhaustion, eyes barely '
                                                   'open.',
                                          'who': 'mir'}]},
 ('SC01-001_03', 'SEG01'): {'background_id': 'BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY',
                            'bg_brief': 'Teal underwater corridor with a diagonal blue ascent '
                                        'light path, faint ruined coral edges at the sides, and an '
                                        'empty open channel with no living black water mass in the '
                                        'plate.',
                            'entities': ['The Black Tide rises two body lengths below Young Mir in '
                                         'the deep background as a separate supernatural mass of '
                                         'living black water with faint hand-like shadow shapes '
                                         'inside its form.'],
                            'moment': 'Young Mir weak in deep corridor; Black Tide rises below '
                                      'him.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Black Tide merged into background '
                                               'plate, duplicate Mir, Mir with black water body, '
                                               'human anatomy, live-action, photorealistic, motion '
                                               'blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png',
                                                'RaisingaDragonSeason01/BLACK TIDE — SUPERNATURAL '
                                                '.png'],
                            'shot': 'High-angle medium-wide underwater shot.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned upper-center in the water column. '
                                                   'He hangs weakly with folded wings and tail '
                                                   'crystal visible, exhausted expression.',
                                          'who': 'mir'}]},
 ('SC01-001_03', 'SEG02'): {'background_id': 'BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY',
                            'bg_brief': 'Teal underwater corridor with a diagonal blue ascent '
                                        'light path, faint ruined coral edges at the sides, and an '
                                        'empty open channel with no living black water mass in the '
                                        'plate.',
                            'entities': ['The Black Tide occupies the lower third as a rising '
                                         'black mass with shadow shapes, one body length below '
                                         'Mir, clearly separate from the dragon.'],
                            'moment': 'Young Mir clings to a faint blue diagonal beam; Black Tide '
                                      'looms below.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, merged bodies, Mir absorbed by tide, '
                                               'duplicate characters, human features on Mir, '
                                               'live-action, photorealistic, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png',
                                                'RaisingaDragonSeason01/BLACK TIDE — SUPERNATURAL '
                                                '.png'],
                            'shot': 'Medium underwater shot angled slightly upward.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned upper third. He grips a faint blue '
                                                   'diagonal light beam with trembling fins, body '
                                                   'barely offset from the beam, exhausted '
                                                   'expression.',
                                          'who': 'mir'}]},
 ('SC01-001_03', 'SEG03'): {'background_id': 'BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY',
                            'bg_brief': 'Teal underwater corridor with a diagonal blue ascent '
                                        'light path, faint ruined coral edges at the sides, and an '
                                        'empty open channel with no living black water mass in the '
                                        'plate.',
                            'entities': ['The Black Tide is pulled back in lower-right deep water '
                                         'with shadow shapes contracting away from the blue burst, '
                                         'separate from Mir.'],
                            'moment': "Young Mir's tail crystal emits a bright flash; Black Tide "
                                      'pulls back below.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, fused anatomy, tide covering Mir, '
                                               'duplicate Mir, human on dragon, live-action, '
                                               'photorealistic, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png',
                                                'RaisingaDragonSeason01/BLACK TIDE — SUPERNATURAL '
                                                '.png'],
                            'shot': 'Medium underwater shot.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned center-left. His tail-end '
                                                   'water-drop crystal emits one bright blue flash '
                                                   'while his body remains on the diagonal beam.',
                                          'who': 'mir'}]},
 ('SC01-001_03', 'SEG04'): {'background_id': 'BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY',
                            'bg_brief': 'Teal underwater corridor with a diagonal blue ascent '
                                        'light path, faint ruined coral edges at the sides, and an '
                                        'empty open channel with no living black water mass in the '
                                        'plate.',
                            'entities': [],
                            'moment': "Extreme close on Young Mir's eye reflecting blue light and "
                                      'black shadow.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, human eye, duplicate eyes, full body '
                                               'cramming frame, live-action, photorealistic, '
                                               'motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': "Extreme close shot filling frame with Young Mir's dragon eye "
                                    '— clear blue iris and trembling vertical pupil.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned frame-filling eye close-up. His '
                                                   'clear blue iris and trembling vertical pupil '
                                                   'fill the frame, with scaled brow ridge at the '
                                                   'edges and no full body shown.',
                                          'who': 'mir'}]},
 ('SC01-001_04', 'SEG01'): {'background_id': 'BG_EP01_MIR_VISION_PALACE_RUINS',
                            'bg_brief': 'Surreal broken dragon palace gate and ruined hall columns '
                                        'over a black abyss, enormous sleeping dragon shadow '
                                        'silhouettes without faces, floating debris, and cold blue '
                                        'memory light.',
                            'entities': [],
                            'moment': 'Surreal vision of broken palace gate and sleeping dragon '
                                      'shadows.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, readable dragon faces, human children, '
                                               'Lua, live-action, photorealistic, motion blur',
                            'reference_paths': [],
                            'shot': 'Wide shot with slight dutch tilt through a surreal black '
                                    'abyss.',
                            'subjects': []},
 ('SC01-001_04', 'SEG02'): {'background_id': 'BG_EP01_MIR_VISION_PALACE_RUINS',
                            'bg_brief': 'Surreal broken dragon palace gate and ruined hall columns '
                                        'over a black abyss, enormous sleeping dragon shadow '
                                        'silhouettes without faces, floating debris, and cold blue '
                                        'memory light.',
                            'entities': [],
                            'moment': "Young Mir's eye fills the frame; memory reflections in the "
                                      'pupil.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Korean text, dialogue captions, human '
                                               'eye, duplicate eyes, live-action, photorealistic, '
                                               'motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': "Extreme close shot — Young Mir's dragon eye occupies most of "
                                    'frame.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned eye occupying most of the frame. '
                                                   'His pupil trembles while faint ghostly palace '
                                                   'shapes reflect on the eye surface, scaled skin '
                                                   'texture at the edges.',
                                          'who': 'mir'}]},
 ('SC01-001_04', 'SEG03'): {'background_id': 'BG_EP01_MIR_VISION_PALACE_RUINS',
                            'bg_brief': 'Surreal broken dragon palace gate and ruined hall columns '
                                        'over a black abyss, enormous sleeping dragon shadow '
                                        'silhouettes without faces, floating debris, and cold blue '
                                        'memory light.',
                            'entities': [],
                            'moment': "Close on Young Mir's eye at the instant a disembodied voice "
                                      'speaks.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, visible mouth, speech bubble, human '
                                               'face, Deep Sea King body, live-action, '
                                               'photorealistic, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': "Extreme close shot on Young Mir's dragon eye — pupil "
                                    'contracted in fear, micro-shudder texture in iris.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned eye extreme close-up. His pupil is '
                                                   'contracted in fear with micro-shudder texture '
                                                   'in the iris; no visible speaker or mouth '
                                                   'anywhere in frame.',
                                          'who': 'mir'}]},
 ('SC01-001_04', 'SEG04'): {'background_id': 'BG_EP01_MIR_VISION_PALACE_RUINS',
                            'bg_brief': 'Surreal broken dragon palace gate and ruined hall columns '
                                        'over a black abyss, enormous sleeping dragon shadow '
                                        'silhouettes without faces, floating debris, and cold blue '
                                        'memory light.',
                            'entities': [],
                            'moment': 'Young Mir trembles in fear as storm light intrudes into the '
                                      'vision.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, duplicate Mir, human child, Lua, '
                                               'live-action, photorealistic, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium close shot on Young Mir in vision space — small '
                                    'silver-blue dragon head and upper body at center, eyes wide '
                                    'with fear, wings pressed tight.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned center. His small silver-blue '
                                                   'dragon head and upper body show eyes wide with '
                                                   'fear, wings pressed tight against his scaled '
                                                   'sides.',
                                          'who': 'mir'}]},
 ('SC01-001_05', 'SEG01'): {'background_id': 'BG_EP01_STORM_SEA_SURFACE_NIGHT',
                            'bg_brief': 'Churning black storm ocean with white foam, diagonal '
                                        'rain, lightning from upper left, grey storm clouds, and '
                                        'open central water beneath a cold moonless palette.',
                            'entities': [],
                            'moment': 'Young Mir strains upward through churning water toward '
                                      'storm-lit surface light.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, duplicate Mir, human swimmer, wings on '
                                               'human, live-action, photorealistic, motion blur, '
                                               'Mir already on surface',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Low-angle underwater shot.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned lower-center. His small body angles '
                                                   'upward toward bright storm-lit surface above '
                                                   'with fins spread, tail trailing, and strained '
                                                   'expression.',
                                          'who': 'mir'}]},
 ('SC01-001_05', 'SEG02'): {'background_id': 'BG_EP01_STORM_SEA_SURFACE_NIGHT',
                            'bg_brief': 'Churning black storm ocean with white foam, diagonal '
                                        'rain, lightning from upper left, grey storm clouds, and '
                                        'open central water beneath a cold moonless palette.',
                            'entities': [],
                            'moment': 'Storm night sea surface; a small blue glow rides in the '
                                      'waves, creature not yet identifiable.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, clear dragon silhouette, human figure, '
                                               'duplicate glows, live-action, photorealistic, '
                                               'motion blur',
                            'reference_paths': [],
                            'shot': 'Wide shot at water surface level — rain, lightning flash '
                                    'upper left, white foam.',
                            'subjects': []},
 ('SC01-001_05', 'SEG03'): {'background_id': 'BG_EP01_STORM_SEA_SURFACE_NIGHT',
                            'bg_brief': 'Churning black storm ocean with white foam, diagonal '
                                        'rain, lightning from upper left, grey storm clouds, and '
                                        'open central water beneath a cold moonless palette.',
                            'entities': [],
                            'moment': 'Wide horizon; distant blue glow drifts toward far coastal '
                                      'cliffs.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, identifiable Mir face, human on shore, '
                                               'duplicate glows, live-action, photorealistic, '
                                               'motion blur',
                            'reference_paths': [],
                            'shot': 'Extreme wide horizon shot — storm night sea under dark '
                                    'clouds, faint coastal cliff silhouette far right.',
                            'subjects': []},
 ('SC01-002_01', 'SEG01'): {'background_id': 'BG_EP01_COASTAL_VILLAGE_MORNING',
                            'bg_brief': 'Post-storm morning coastal shore with wet stone '
                                        'breakwater, damp sand, overturned boats, tangled nets, '
                                        'soft sunlight from frame right, and a distant cliff with '
                                        'cave entrance hint.',
                            'entities': [],
                            'moment': 'Post-storm village morning on wet breakwater; three '
                                      'children in separate positions.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, identical children, swapped hairstyles, '
                                               'Lua with basket or gray tunic, Child 2 with shell '
                                               'pendant, spear held by children, fused bodies, '
                                               'duplicate faces, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/villageChild01.png',
                                                'RaisingaDragonSeason01/village_child_2.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium-wide eye-level shot on wet stone breakwater after '
                                    'storm.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'center foreground on the wet breakwater. Both '
                                                   'hands grip her handmade coastal fishing spear '
                                                   '— a simple wooden shaft with tied stone tip — '
                                                   'raised or lowered per the beat. She wears her '
                                                   'white shell pendant and the blue mark on her '
                                                   'left wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Village Child 1, Village Child 1 is a boy with '
                                                   'short tousled black-brown hair and a charcoal '
                                                   'sleeveless V-neck tunic. He has no shoulder '
                                                   'basket, no shell pendant, and no blue wrist '
                                                   'mark. He stands left midground three steps '
                                                   'behind Lua. He watches Lua with a separate '
                                                   "silhouette and clear arm's-length gap.",
                                          'who': 'child1'},
                                         {'block': 'Village Child 2, Village Child 2 is a girl '
                                                   'with a high black ponytail tied with an ochre '
                                                   'band, an indigo-blue tunic with a cream frill '
                                                   'collar, and a woven shoulder basket resting at '
                                                   'her right hip. She stands right midground. She '
                                                   'watches separately with her woven shoulder '
                                                   'basket at her right hip.',
                                          'who': 'child2'}]},
 ('SC01-002_01', 'SEG02'): {'background_id': 'BG_EP01_COASTAL_VILLAGE_MORNING',
                            'bg_brief': 'Post-storm morning coastal shore with wet stone '
                                        'breakwater, damp sand, overturned boats, tangled nets, '
                                        'soft sunlight from frame right, and a distant cliff with '
                                        'cave entrance hint.',
                            'entities': [],
                            'moment': 'Lua stands feet apart on breakwater, spear gripped with '
                                      'both hands, eyes on fish shadow in shallow water.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, spear in child hands, merged children, '
                                               'trait swap, Lua with ponytail, Child 1 with bun, '
                                               'live-action, motion blur, splash on face',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/villageChild01.png',
                                                'RaisingaDragonSeason01/village_child_2.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium shot on wet breakwater.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'center foreground on the wet breakwater. Both '
                                                   'hands grip her handmade coastal fishing spear '
                                                   '— a simple wooden shaft with tied stone tip — '
                                                   'raised or lowered per the beat. She wears her '
                                                   'white shell pendant and the blue mark on her '
                                                   'left wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Village Child 1, Village Child 1 is a boy with '
                                                   'short tousled black-brown hair and a charcoal '
                                                   'sleeveless V-neck tunic. He has no shoulder '
                                                   'basket, no shell pendant, and no blue wrist '
                                                   'mark. He stands left midground three steps '
                                                   'behind Lua. He watches Lua with a separate '
                                                   "silhouette and clear arm's-length gap.",
                                          'who': 'child1'},
                                         {'block': 'Village Child 2, Village Child 2 is a girl '
                                                   'with a high black ponytail tied with an ochre '
                                                   'band, an indigo-blue tunic with a cream frill '
                                                   'collar, and a woven shoulder basket resting at '
                                                   'her right hip. She stands right midground. She '
                                                   'watches separately with her woven shoulder '
                                                   'basket at her right hip.',
                                          'who': 'child2'}]},
 ('SC01-002_01', 'SEG03'): {'background_id': 'BG_EP01_COASTAL_VILLAGE_MORNING',
                            'bg_brief': 'Post-storm morning coastal shore with wet stone '
                                        'breakwater, damp sand, overturned boats, tangled nets, '
                                        'soft sunlight from frame right, and a distant cliff with '
                                        'cave entrance hint.',
                            'entities': [],
                            'moment': 'Lua holds spear overhead aimed downward; fish shadow still '
                                      'in water before the strike.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, wet face splash, missed strike '
                                               'completed, spear in wrong hands, identical '
                                               'children, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/villageChild01.png',
                                                'RaisingaDragonSeason01/village_child_2.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'center foreground on the wet breakwater. Both '
                                                   'hands grip her handmade coastal fishing spear '
                                                   '— a simple wooden shaft with tied stone tip — '
                                                   'raised or lowered per the beat. She wears her '
                                                   'white shell pendant and the blue mark on her '
                                                   'left wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Village Child 1, Village Child 1 is a boy with '
                                                   'short tousled black-brown hair and a charcoal '
                                                   'sleeveless V-neck tunic. He has no shoulder '
                                                   'basket, no shell pendant, and no blue wrist '
                                                   'mark. He stands left midground three steps '
                                                   'behind Lua. He watches Lua with a separate '
                                                   "silhouette and clear arm's-length gap.",
                                          'who': 'child1'},
                                         {'block': 'Village Child 2, Village Child 2 is a girl '
                                                   'with a high black ponytail tied with an ochre '
                                                   'band, an indigo-blue tunic with a cream frill '
                                                   'collar, and a woven shoulder basket resting at '
                                                   'her right hip. She stands right midground. She '
                                                   'watches separately with her woven shoulder '
                                                   'basket at her right hip.',
                                          'who': 'child2'}]},
 ('SC01-002_01', 'SEG04'): {'background_id': 'BG_EP01_COASTAL_VILLAGE_MORNING',
                            'bg_brief': 'Post-storm morning coastal shore with wet stone '
                                        'breakwater, damp sand, overturned boats, tangled nets, '
                                        'soft sunlight from frame right, and a distant cliff with '
                                        'cave entrance hint.',
                            'entities': [],
                            'moment': 'Lua frozen embarrassed with wet face, spear in both hands; '
                                      'Village Child 1 points at empty water.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Korean subtitles, identical children, '
                                               'spear transfer, fused bodies, live-action, motion '
                                               'blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/villageChild01.png',
                                                'RaisingaDragonSeason01/village_child_2.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium two-shot toward three children.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'center foreground on the wet breakwater. Both '
                                                   'hands grip her handmade coastal fishing spear '
                                                   '— a simple wooden shaft with tied stone tip — '
                                                   'raised or lowered per the beat. She wears her '
                                                   'white shell pendant and the blue mark on her '
                                                   'left wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Village Child 1, Village Child 1 is a boy with '
                                                   'short tousled black-brown hair and a charcoal '
                                                   'sleeveless V-neck tunic. He has no shoulder '
                                                   'basket, no shell pendant, and no blue wrist '
                                                   'mark. He stands left midground three steps '
                                                   'behind Lua. He watches Lua with a separate '
                                                   "silhouette and clear arm's-length gap.",
                                          'who': 'child1'},
                                         {'block': 'Village Child 2, Village Child 2 is a girl '
                                                   'with a high black ponytail tied with an ochre '
                                                   'band, an indigo-blue tunic with a cream frill '
                                                   'collar, and a woven shoulder basket resting at '
                                                   'her right hip. She stands right midground. She '
                                                   'watches separately with her woven shoulder '
                                                   'basket at her right hip.',
                                          'who': 'child2'}]},
 ('SC01-002_02', 'SEG01'): {'background_id': 'BG_EP01_COASTAL_VILLAGE_MORNING',
                            'bg_brief': 'Post-storm morning coastal shore with wet stone '
                                        'breakwater, damp sand, overturned boats, tangled nets, '
                                        'soft sunlight from frame right, and a distant cliff with '
                                        'cave entrance hint.',
                            'entities': [],
                            'moment': 'Lua sits in shallow water on breakwater edge, wet, gripping '
                                      'spear; off-screen children laughing.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, Old Fisherman in '
                                               'frame, text, subtitles, watermark, Old Fisherman '
                                               'present, spear not in Lua hands, duplicate Lua, '
                                               'live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium shot at wet breakwater edge.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'foreground in shallow water. She grips her '
                                                   'fishing spear vertically in both hands with '
                                                   'wet beige tunic and defiant or forced-bravado '
                                                   'expression. She wears her white shell pendant '
                                                   'and the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'}]},
 ('SC01-002_02', 'SEG02'): {'background_id': 'BG_EP01_COASTAL_VILLAGE_MORNING',
                            'bg_brief': 'Post-storm morning coastal shore with wet stone '
                                        'breakwater, damp sand, overturned boats, tangled nets, '
                                        'soft sunlight from frame right, and a distant cliff with '
                                        'cave entrance hint.',
                            'entities': [],
                            'moment': 'Lua stands in shallows gripping spear, speaking with forced '
                                      'confidence.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, Old Fisherman in '
                                               'frame, text, subtitles, watermark, fisherman in '
                                               'frame, spear dropped, duplicate Lua, live-action, '
                                               'motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'center in knee-deep shallows. She grips her '
                                                   'fishing spear vertically in both hands with '
                                                   'wet beige tunic and defiant or forced-bravado '
                                                   'expression. She wears her white shell pendant '
                                                   'and the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'}]},
 ('SC01-002_02', 'SEG03'): {'background_id': 'BG_EP01_COASTAL_VILLAGE_MORNING',
                            'bg_brief': 'Post-storm morning coastal shore with wet stone '
                                        'breakwater, damp sand, overturned boats, tangled nets, '
                                        'soft sunlight from frame right, and a distant cliff with '
                                        'cave entrance hint.',
                            'entities': [],
                            'moment': 'Old Fisherman stands left midground; Lua straightens in '
                                      'shallows right foreground with spear.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Lua with beard, fisherman child-sized, '
                                               'spear in fisherman hands, trait exchange, fused '
                                               'bodies, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/old_fisherman.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium-wide shot on breakwater shallows.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'right foreground in shallows. She holds her '
                                                   'fishing spear in both hands with attentive or '
                                                   'conflicted expression directed toward the '
                                                   'fisherman. She wears her white shell pendant '
                                                   'and the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'The Old Fisherman, The Old Fisherman is a tall '
                                                   'elderly adult with gray hair and a full gray '
                                                   'beard, wearing a navy work vest over simple '
                                                   'coastal clothing. He stands left midground on '
                                                   'the breakwater. He stands tall with gray beard '
                                                   'and navy vest, calm stern teaching expression '
                                                   'or profile gaze toward the distant cliff cave.',
                                          'who': 'fisherman'}]},
 ('SC01-002_02', 'SEG04'): {'background_id': 'BG_EP01_COASTAL_VILLAGE_MORNING',
                            'bg_brief': 'Post-storm morning coastal shore with wet stone '
                                        'breakwater, damp sand, overturned boats, tangled nets, '
                                        'soft sunlight from frame right, and a distant cliff with '
                                        'cave entrance hint.',
                            'entities': [],
                            'moment': 'Old Fisherman speaks sternly; Lua grips spear with hardened '
                                      'expression.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Korean subtitles, merged faces, child '
                                               'beard, Lua taller than fisherman, spear transfer, '
                                               'live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/old_fisherman.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium two-shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'right foreground in shallows. She holds her '
                                                   'fishing spear in both hands with attentive or '
                                                   'conflicted expression directed toward the '
                                                   'fisherman. She wears her white shell pendant '
                                                   'and the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'The Old Fisherman, The Old Fisherman is a tall '
                                                   'elderly adult with gray hair and a full gray '
                                                   'beard, wearing a navy work vest over simple '
                                                   'coastal clothing. He stands left midground on '
                                                   'the breakwater. He stands tall with gray beard '
                                                   'and navy vest, calm stern teaching expression '
                                                   'or profile gaze toward the distant cliff cave.',
                                          'who': 'fisherman'}]},
 ('SC01-002_02', 'SEG05'): {'background_id': 'BG_EP01_COASTAL_VILLAGE_MORNING',
                            'bg_brief': 'Post-storm morning coastal shore with wet stone '
                                        'breakwater, damp sand, overturned boats, tangled nets, '
                                        'soft sunlight from frame right, and a distant cliff with '
                                        'cave entrance hint.',
                            'entities': [],
                            'moment': 'Old Fisherman gazes toward distant cliff cave; Lua silent '
                                      'with spear, listening.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Lua looking away from cave, fisherman '
                                               'missing, duplicate figures, live-action, motion '
                                               'blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/old_fisherman.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium-wide shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'right foreground in shallows. She holds her '
                                                   'fishing spear in both hands with attentive or '
                                                   'conflicted expression directed toward the '
                                                   'fisherman. She wears her white shell pendant '
                                                   'and the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'The Old Fisherman, The Old Fisherman is a tall '
                                                   'elderly adult with gray hair and a full gray '
                                                   'beard, wearing a navy work vest over simple '
                                                   'coastal clothing. He stands left midground on '
                                                   'the breakwater. He stands tall with gray beard '
                                                   'and navy vest, calm stern teaching expression '
                                                   'or profile gaze toward the distant cliff cave.',
                                          'who': 'fisherman'}]},
 ('SC01-002_02', 'SEG06'): {'background_id': 'BG_EP01_COASTAL_VILLAGE_MORNING',
                            'bg_brief': 'Post-storm morning coastal shore with wet stone '
                                        'breakwater, damp sand, overturned boats, tangled nets, '
                                        'soft sunlight from frame right, and a distant cliff with '
                                        'cave entrance hint.',
                            'entities': [],
                            'moment': "Faint blue flicker in far cave; Lua's eyes widen, spear in "
                                      'hand.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Lua running, cave glow absent, spear '
                                               'not in Lua hands, trait swap, live-action, motion '
                                               'blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/old_fisherman.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium shot with depth.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'right foreground in shallows. She holds her '
                                                   'fishing spear in both hands with attentive or '
                                                   'conflicted expression directed toward the '
                                                   'fisherman. She wears her white shell pendant '
                                                   'and the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'The Old Fisherman, The Old Fisherman is a tall '
                                                   'elderly adult with gray hair and a full gray '
                                                   'beard, wearing a navy work vest over simple '
                                                   'coastal clothing. He stands left midground on '
                                                   'the breakwater. He stands tall with gray beard '
                                                   'and navy vest, calm stern teaching expression '
                                                   'or profile gaze toward the distant cliff cave.',
                                          'who': 'fisherman'}]},
 ('SC01-003_01', 'SEG01'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Wide establishing view from cave entrance looking inward: '
                                        'central shallow-water path, damp stone walls, daylight '
                                        'rim behind camera, deep blue-teal glow in tunnel center '
                                        'ahead. Droplets on upper walls.',
                            'entities': [],
                            'moment': 'Lua enters wet coastal cave with spear held forward.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Young Mir visible, spear not in Lua '
                                               'hands, duplicate Lua, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Wide shot at cave entrance looking inward — Lua small in '
                                    'right third along center path.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'right third midground, small in frame, '
                                                   'entering along the center path. She holds her '
                                                   'fishing spear forward in both hands with '
                                                   'cautious wide eyes. She wears her white shell '
                                                   'pendant and the blue mark on her left wrist is '
                                                   'visible when her arm is exposed.',
                                          'who': 'lua'}]},
 ('SC01-003_01', 'SEG02'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Camera low beside reflective shallow water; wet rock '
                                        'foreground, dark crevice with blue glow in right '
                                        'background, damp walls rising above.',
                            'entities': [],
                            'moment': 'Lua stands on wet rock in cave, spear angled toward '
                                      'shadows, afraid but forcing bravery.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Mir visible, spear dropped, duplicate '
                                               'Lua, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Low-angle medium shot from wet rock floor level.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'center-left on wet rock viewed from below. She '
                                                   'angles her spear toward a dark crevice with '
                                                   'forced brave expression and tense shoulders. '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'}]},
 ('SC01-003_01', 'SEG03'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Camera beside crevice alcove at shoulder height; '
                                        'shadowed cave depth ahead, blue glow in distant tunnel, '
                                        'wet wall edge in left foreground.',
                            'entities': [],
                            'moment': 'Lua in cave calls toward shadows, spear lowered slightly, '
                                      'mouth open mid-call.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Korean text overlay, Mir in frame, '
                                               'spear missing, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Over-the-shoulder shot from behind Lua left shoulder toward '
                                    'cave depth.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'foreground with back and shoulder toward '
                                                   'camera, facing cave depth. Her spear is in one '
                                                   'hand pointed down while her other hand is '
                                                   'cupped near her mouth in a calling expression. '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'}]},
 ('SC01-003_01', 'SEG04'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Camera close to crevice opening; blue rim light from '
                                        'depth on Lua face, dark crevice gap right frame, water '
                                        'ripples at feet.',
                            'entities': [],
                            'moment': 'Lua freezes listening after calling; eyes wide toward '
                                      'crevice where a squeak came from.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Mir fully revealed, duplicate Lua, '
                                               'live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium close shot at crevice mouth.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'center-left. Her body is frozen mid-lean toward '
                                                   'a dark crevice right frame with wide curious '
                                                   'eyes, spear forgotten at her side in one hand. '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'}]},
 ('SC01-003_02', 'SEG01'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Camera at crevice alcove beside Lua shoulder; narrow wet '
                                        'stone framing, blue glow deeper in crevice where Mir '
                                        'rests on wet rock.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua peers into crevice; Young Mir visible on wet stone at '
                                      'frame right.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Lua with wings, Mir in human '
                                               'clothes, merged bodies, duplicate figures, spear '
                                               'in Mir hands, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Over-the-shoulder shot from behind Lua as she peers into '
                                    'crevice — Young Mir visible inside ahead.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'foreground with back and shoulder toward '
                                                   'camera, leaning into crevice. curious cautious '
                                                   'face, spear lowered tip resting on wet stone. '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right midground inside crevice on '
                                                   'wet rock. half-open clear blue eyes, tail '
                                                   'crystal dim, folded wings',
                                          'who': 'mir'}]},
 ('SC01-003_02', 'SEG02'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Camera along wet rock wall at eye level; cave depth '
                                        'receding behind both figures, reflective shallow water in '
                                        'lower frame.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua exhales shakily staring at Mir; spear resting on stone '
                                      'beside her.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Korean subtitles, trait '
                                               'exchange, Lua scaled, Mir human, live-action, '
                                               'motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Profile two-shot from lateral cave wall — both subjects in '
                                    'side silhouette.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She kneels left '
                                                   'in profile toward Mir. shoulders slack with '
                                                   'shaky exhale, wide brown eyes fixed on Mir, '
                                                   'spear lying on wet stone near her right foot. '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right in profile on wet stone. '
                                                   'watching her, wings folded, vulnerable posture',
                                          'who': 'mir'}]},
 ('SC01-003_02', 'SEG03'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Camera close at whisper distance; shallow depth of field '
                                        'on faces, crevice stone soft in background.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua whispers toward Mir, lips parted on first word, spear '
                                      'on ground.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, dialogue text, merged '
                                               'anatomy, wings on Lua, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium close two-shot at whisper distance.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She kneels left '
                                                   'three-quarter view. lips parted whispering, one '
                                                   'hand empty and hovering, spear visible on ground '
                                                   'left-bottom. She wears her white shell pendant '
                                                   'and the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right close midground. head tilted, '
                                                   'frightened intelligent blue eyes toward Lua',
                                          'who': 'mir'}]},
 ('SC01-003_02', 'SEG04'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Camera low near wet stone beside Mir; Mir fills right '
                                        'foreground, Lua partially visible left background, cave '
                                        'ceiling implied above.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Young Mir opens wide eyes toward Lua; Lua breath held in '
                                      'awe.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, identical eyes on both, '
                                               'human Mir, dragon Lua, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': "Low-angle medium shot at Young Mir's eye level — Mir "
                                    'foreground emphasis.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She kneels left '
                                                   'background smaller in frame. lips slightly '
                                                   'parted, awed expression, hands empty at sides. '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right foreground larger in frame on '
                                                   'wet stone. large clear blue eyes open wide '
                                                   'toward Lua, folded wings',
                                          'who': 'mir'}]},
 ('SC01-003_02', 'SEG05'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Tight framing on hands and snout space; wet stone and '
                                        'cave blur behind, blue ambient edge light.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua extends open human hand toward Mir; Mir weak on stone, '
                                      'not yet touching.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, hand merged with dragon, '
                                               'wings on Lua, Mir human child, contact completed, '
                                               'live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Close shot on extended hand zone between Lua and Mir.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She kneels left '
                                                   'with open human hand extended in lower frame, '
                                                   'palm low toward Mir, worried gentle face, blue '
                                                   'wrist mark visible, no spear in hand. She wears '
                                                   'her white shell pendant and the blue mark on '
                                                   'her left wrist is visible when her arm is '
                                                   'exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right upper frame on wet stone '
                                                   'leaning back weakly, wings tight to body, eyes '
                                                   'on her hand',
                                          'who': 'mir'}]},
 ('SC01-003_03', 'SEG01'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Narrow damp coastal cave with shallow seawater over '
                                        'uneven rock, droplets on stone walls, cool blue-teal '
                                        'ambient light stronger toward the tunnel depth behind '
                                        'camera.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua kneels left with spear set down; Mir rests against '
                                      'stone right.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, spear in Mir hands, kneeling '
                                               'dragon, standing merged figures, live-action, '
                                               'motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png',
                                                'RaisingaDragonSeason01/spear.png'],
                            'shot': 'Medium-wide two-shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'foreground kneeling. spear laid flat on stone '
                                                   'beside her, human body fully visible She wears '
                                                   'her white shell pendant and the blue mark on '
                                                   'her left wrist is visible when her arm is '
                                                   'exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right midground resting against '
                                                   'stone. folded wings, separate dragon '
                                                   'silhouette',
                                          'who': 'mir'}]},
 ('SC01-003_03', 'SEG02'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Narrow damp coastal cave with shallow seawater over '
                                        'uneven rock, droplets on stone walls, cool blue-teal '
                                        'ambient light stronger toward the tunnel depth behind '
                                        'camera.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua extends open hand low toward Mir; Mir watches with wide '
                                      'eyes, wings close.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, dragon wings on Lua, human '
                                               'clothing on Mir, fused hands, live-action, motion '
                                               'blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'kneeling. open human hand extended low at '
                                                   "Mir's eye level with soft expression She wears "
                                                   'her white shell pendant and the blue mark on '
                                                   'her left wrist is visible when her arm is '
                                                   'exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right on stone. small wings pressed '
                                                   'to scaled sides, blue eyes fixed on her '
                                                   'fingers',
                                          'who': 'mir'}]},
 ('SC01-003_03', 'SEG03'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Narrow damp coastal cave with shallow seawater over '
                                        'uneven rock, droplets on stone walls, cool blue-teal '
                                        'ambient light stronger toward the tunnel depth behind '
                                        'camera.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua and Mir in medium two-shot; Lua speaks softly with hand '
                                      'extended.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Korean captions, merged '
                                               'silhouettes, trait transfer, live-action, motion '
                                               'blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot framing both full silhouettes.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'kneeling. hand extended palm open with gentle '
                                                   'reassuring expression She wears her white '
                                                   'shell pendant and the blue mark on her left '
                                                   'wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right on wet stone. body still, '
                                                   'watching her fingers, wings folded',
                                          'who': 'mir'}]},
 ('SC01-003_03', 'SEG04'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Narrow damp coastal cave with shallow seawater over '
                                        'uneven rock, droplets on stone walls, cool blue-teal '
                                        'ambient light stronger toward the tunnel depth behind '
                                        'camera.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua touches her own stomach; Mir still watching from stone '
                                      'without approaching.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Mir moved closer, Lua dragon '
                                               'traits, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'left. one hand on her own stomach, half-smile '
                                                   'explaining expression She wears her white '
                                                   'shell pendant and the blue mark on her left '
                                                   'wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right on stone. unchanged distance, '
                                                   'eyes on Lua',
                                          'who': 'mir'}]},
 ('SC01-003_04', 'SEG01'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Narrow damp coastal cave with shallow seawater over '
                                        'uneven rock, droplets on stone walls, cool blue-teal '
                                        'ambient light stronger toward the tunnel depth behind '
                                        'camera.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': "Mir shifted slightly forward on stone; Lua's steady open "
                                      'hand waits.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, biting contact, blood, fused '
                                               'fingers, dragon arm on Lua, live-action, motion '
                                               'blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium close two-shot on hands zone.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'left. human hand steady palm-up with fingers '
                                                   'relaxed She wears her white shell pendant and '
                                                   'the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right. snout a few centimeters from '
                                                   'her open index finger, wings folded',
                                          'who': 'mir'}]},
 ('SC01-003_04', 'SEG02'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Narrow damp coastal cave with shallow seawater over '
                                        'uneven rock, droplets on stone walls, cool blue-teal '
                                        'ambient light stronger toward the tunnel depth behind '
                                        'camera.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': "Mir's mouth closed weakly on tip of Lua's index finger; Lua "
                                      'flinches.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, severed finger, violent '
                                               'bite, merged mouth-hand, extra limbs, live-action, '
                                               'motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Close shot on contact point.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. Her face is '
                                                   'visible upper left with flinching surprise '
                                                   'expression.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. His scaled '
                                                   'head is lower right with small dragon mouth '
                                                   'gently closed on tip of her human index '
                                                   'finger.',
                                          'who': 'mir'}]},
 ('SC01-003_05', 'SEG01'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Narrow damp coastal cave with shallow seawater over '
                                        'uneven rock, droplets on stone walls, cool blue-teal '
                                        'ambient light stronger toward the tunnel depth behind '
                                        'camera.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': "One blood drop forms on Lua's fingertip at Mir contact "
                                      'point.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, excessive blood, fused hand '
                                               'and snout, wings on hand, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Close shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. Her human hand '
                                                   'is one small blood drop forming on index '
                                                   'fingertip.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is lower '
                                                   'right with mouth just released, separate '
                                                   'scaled snout.',
                                          'who': 'mir'}]},
 ('SC01-003_05', 'SEG02'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Narrow damp coastal cave with shallow seawater over '
                                        'uneven rock, droplets on stone walls, cool blue-teal '
                                        'ambient light stronger toward the tunnel depth behind '
                                        'camera.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': "Blood drop suspended above broken scale on Mir's shoulder; "
                                      'ripples starting in cave water.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, blood on Lua chest, human '
                                               'scales, merged bodies, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Close shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. Her human hand '
                                                   'is human hand separate at frame edge.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'shoulder focus with one blood drop suspended '
                                                   'above broken scale on left shoulder.',
                                          'who': 'mir'}]},
 ('SC01-003_05', 'SEG03'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Narrow damp coastal cave with shallow seawater over '
                                        'uneven rock, droplets on stone walls, cool blue-teal '
                                        'ambient light stronger toward the tunnel depth behind '
                                        'camera.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': "Blue mark glows on Lua's wrist; Mir's chest mark glows on "
                                      'his scales; bodies separate.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, chest mark on Lua, wrist '
                                               'mark on Mir, fused glow, trait exchange, '
                                               'live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'left. blue mark glowing on left wrist only, '
                                                   'fully human She wears her white shell pendant '
                                                   'and the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right. crown-shaped chest wave mark '
                                                   'glowing on scales only, fully dragon',
                                          'who': 'mir'}]},
 ('SC01-003_06', 'SEG01'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Narrow damp coastal cave with shallow seawater over '
                                        'uneven rock, droplets on stone walls, cool blue-teal '
                                        'ambient light stronger toward the tunnel depth behind '
                                        'camera.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': "Thin blue light line connects Lua's wrist mark and Mir's "
                                      'chest mark across open space.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, bodies fused, single '
                                               'silhouette, wings on Lua, human Mir, live-action, '
                                               'motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot in cave.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'kneeling. left wrist forward with blue mark '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right on stone. glowing chest mark '
                                                   'on stone',
                                          'who': 'mir'}]},
 ('SC01-003_06', 'SEG02'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Narrow damp coastal cave with shallow seawater over '
                                        'uneven rock, droplets on stone walls, cool blue-teal '
                                        'ambient light stronger toward the tunnel depth behind '
                                        'camera.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Resonance line active; Lua human and Mir dragon remain '
                                      'fully separate.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, anatomy transfer, duplicate '
                                               'Lua, duplicate Mir, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'left. human child with beige tunic, high bun, '
                                                   'blue wrist glow, no dragon parts She wears her '
                                                   'white shell pendant and the blue mark on her '
                                                   'left wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right. small dragon with horns, '
                                                   'wings, tail crystal, chest glow, no human '
                                                   'clothes',
                                          'who': 'mir'}]},
 ('SC01-003_07', 'SEG01'): {'background_id': 'BG_EP01_MIR_VISION_PALACE_RUINS',
                            'bg_brief': 'Surreal broken dragon palace gate and ruined hall columns '
                                        'over a black abyss, enormous sleeping dragon shadow '
                                        'silhouettes without faces, floating debris, and cold blue '
                                        'memory light.',
                            'entities': [],
                            'moment': 'Surreal collapsed dragon palace vision space; no human Lua '
                                      'present.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Lua, human child, readable dragon '
                                               'faces, live-action, motion blur',
                            'reference_paths': [],
                            'shot': 'Wide shot with slight dutch tilt — surreal vision of '
                                    'collapsed dragon palace.',
                            'subjects': []},
 ('SC01-003_07', 'SEG02'): {'background_id': 'BG_EP01_MIR_VISION_PALACE_RUINS',
                            'bg_brief': 'Surreal broken dragon palace gate and ruined hall columns '
                                        'over a black abyss, enormous sleeping dragon shadow '
                                        'silhouettes without faces, floating debris, and cold blue '
                                        'memory light.',
                            'entities': [],
                            'moment': 'Black roots wrap a fading blue heart-stone at ruined hall '
                                      'center; no Lua.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, human characters, Lua, Young Mir full '
                                               'body in foreground, live-action, motion blur',
                            'reference_paths': [],
                            'shot': 'Medium shot on vision hall center.',
                            'subjects': []},
 ('SC01-003_07', 'SEG03'): {'background_id': 'BG_EP01_MIR_VISION_PALACE_RUINS',
                            'bg_brief': 'Surreal broken dragon palace gate and ruined hall columns '
                                        'over a black abyss, enormous sleeping dragon shadow '
                                        'silhouettes without faces, floating debris, and cold blue '
                                        'memory light.',
                            'entities': [],
                            'moment': 'Nightmare memory abyss with sleeping dragon silhouettes; no '
                                      'physical contact shown.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, human child, contact scene, readable '
                                               'faces on shadow dragons, live-action, motion blur',
                            'reference_paths': [],
                            'shot': 'Wide shot down black abyss in vision space — sleeping dragon '
                                    'silhouettes curled on ledges without faces, broken columns '
                                    'receding into void fog.',
                            'subjects': []},
 ('SC01-003_08', 'SEG01'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Tight framing on Lua only; wet cave wall blur background, '
                                        'no Mir visible, soft blue ambient from depth.',
                            'entities': [],
                            'moment': 'Lua alone in cave gasps staring at blue mark on her wrist.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Lua with wings horns tail, duplicate '
                                               'Lua, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png'],
                            'shot': 'Medium close shot on glowing wrist mark.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She fills '
                                                   'center-left frame. She gasps with mouth open, '
                                                   'eyes fixed on the blue mark glowing on her '
                                                   'raised left wrist before her face. She wears '
                                                   'her white shell pendant and the blue mark on '
                                                   'her left wrist is visible when her arm is '
                                                   'exposed.',
                                          'who': 'lua'}]},
 ('SC01-003_08', 'SEG02'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
                            'bg_brief': 'Camera pulled back from crevice area; more cave interior '
                                        'visible, shallow water path between subjects, faint '
                                        'fading blue line across gap.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Mir whimpers on wet stone right; Lua stares at wrist; '
                                      'connection light fading.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, merged bodies, human Mir, '
                                               'dragon Lua, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium-wide two-shot pulled back — full silhouettes with '
                                    'fading connection line.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She kneels left '
                                                   'midground. wrist mark dimming, stunned eyes '
                                                   'downward. She wears her white shell pendant and '
                                                   'the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right midground on wet stone. '
                                                   'whimpering with folded wings',
                                          'who': 'mir'}]},
 ('SC01-003_09', 'SEG01'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
 'bg_brief': 'Grounded virtual 35mm opening view of the fixed wet cave meeting patch. Dark wet '
             'ledge foreground lower left, deep blue crevice glow background left, distant '
             'cave-mouth daylight rim far right, and a clear clockwise route around the '
             'characters.',
 'entities': ['Lua and Young Mir remain separated on the same fixed wet rock patch with a readable '
              'gap and layered foreground-midground-background depth.'],
 'identity_lock': 'Lua remains fully human with no dragon anatomy, and Young Mir remains fully '
                  'dragon with no human clothing or human facial features; do not transfer marks, '
                  'wings, horns, scales, clothing or limbs between them.',
 'moment': 'Lua kneels left midground, breathless and studying her raised marked wrist; Young Mir '
           'rests weakly right midground with wings tucked.',
 'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, duplicate characters, '
                    'merged bodies, fused anatomy, extra limbs, malformed hands, incorrect '
                    'character count, incorrect prop ownership, motion blur, live action, '
                    'photorealism, flat centered poster composition, symmetrical character lineup, '
                    'inconsistent cave layout, reversed light direction, identity exchange, live '
                    'action, photorealism, close-up crop, overhead view, cave mouth on left',
 'reference_paths': ['RaisingaDragonSeason01/Lua.png', 'RaisingaDragonSeason01/YoungMir.png'],
 'shot': 'Grounded virtual 35mm, eye-level medium-wide opening anchor with Lua left, Mir right and '
         'layered cave depth.',
 'subjects': [{'who': 'lua',
               'block': 'Lua is a sun-browned human village girl with warm amber-brown eyes, a '
                        'messy high loose brown hair bun, beige sleeveless tunic and shorts, a '
                        'rope belt, a white shell pendant at her chest, and a faint blue mark on '
                        'her left wrist. She is fully human with no dragon horns, wings, tail, or '
                        'scales. She kneels in the left midground in three-quarter profile, left '
                        'wrist raised into her own gaze, right hand braced on wet rock, body open '
                        'toward Young Mir rather than posed toward the viewer.'},
              {'who': 'mir',
               'block': 'Young Mir is a small silver-blue sea dragon hatchling with short curved '
                        'horns, one pair of fin-like wings, four small dragon limbs, a long scaled '
                        'tail ending in a water-drop crystal, and a faint crown-shaped wave mark '
                        'on his chest. He is a dragon only, with no human clothing or human facial '
                        'features. He rests separately in the right midground on the same patch, '
                        'weak posture, wings tucked, watching Lua.'}]},
 ('SC01-003_09', 'SEG02'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
 'bg_brief': 'Same cave from the mouth-side looking inward with a grounded virtual 35mm lens. Wet '
             'near rock provides foreground parallax, deep blue alcove planes recede background '
             'left, and the off-frame cave mouth behind camera creates a soft daylight rim.',
 'entities': ['Same wet rock patch and unchanged world positions; only the camera has completed a '
              'physically continuous clockwise arc.'],
 'identity_lock': 'Lua remains fully human with no dragon anatomy, and Young Mir remains fully '
                  'dragon with no human clothing or human facial features; do not transfer marks, '
                  'wings, horns, scales, clothing or limbs between them.',
 'moment': 'Lua kneels frame right in three-quarter rear profile, startled toward the off-frame '
           'entrance; Young Mir remains frame left watching her.',
 'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, duplicate characters, '
                    'merged bodies, fused anatomy, extra limbs, malformed hands, incorrect '
                    'character count, incorrect prop ownership, motion blur, live action, '
                    'photorealism, flat centered poster composition, symmetrical character lineup, '
                    'inconsistent cave layout, reversed light direction, identity exchange, live '
                    'action, photorealism, overhead view, visible village person, bright cave '
                    'mouth visible, Lua on left, Mir on right',
 'reference_paths': ['RaisingaDragonSeason01/Lua.png', 'RaisingaDragonSeason01/YoungMir.png'],
 'shot': 'Grounded virtual 35mm, eye-level mouth-side interior-facing medium arrival anchor.',
 'subjects': [{'who': 'lua',
               'block': 'Lua is a sun-browned human village girl with warm amber-brown eyes, a '
                        'messy high loose brown hair bun, beige sleeveless tunic and shorts, a '
                        'rope belt, a white shell pendant at her chest, and a faint blue mark on '
                        'her left wrist. She is fully human with no dragon horns, wings, tail, or '
                        'scales. She kneels frame right in three-quarter rear profile, head '
                        'snapped toward the off-frame entrance behind camera, startled eyes, one '
                        'hand braced on rock.'},
              {'who': 'mir',
               'block': 'Young Mir is a small silver-blue sea dragon hatchling with short curved '
                        'horns, one pair of fin-like wings, four small dragon limbs, a long scaled '
                        'tail ending in a water-drop crystal, and a faint crown-shaped wave mark '
                        'on his chest. He is a dragon only, with no human clothing or human facial '
                        'features. He remains separately frame left on the same patch, weak with '
                        'wings tucked and eyes fixed on Lua.'}]},
 ('SC01-003_09', 'SEG03'): {'background_id': 'BG_EP01_COASTAL_CAVE_INTERIOR',
 'bg_brief': 'Same wet cave patch with grounded virtual 35mm eye-level depth. Damp near rock and '
             'loose beige cloth occupy the lower foreground, blue cave layers recede background '
             'left, and a narrow daylight rim appears only at the far right edge.',
 'entities': ['The cloth edge forms a foreground passage while the exit-side space behind Lua '
              'remains open for the camera to settle onto the rear axis.'],
 'identity_lock': 'Lua remains fully human with no dragon anatomy, and Young Mir remains fully '
                  'dragon with no human clothing or human facial features; do not transfer marks, '
                  'wings, horns, scales, clothing or limbs between them.',
 'moment': 'Lua kneels frame right in three-quarter rear-side view, opening cloth toward Young '
           'Mir; Mir is frame left close to her knees and not wrapped yet.',
 'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, duplicate characters, '
                    'merged bodies, fused anatomy, extra limbs, malformed hands, incorrect '
                    'character count, incorrect prop ownership, motion blur, live action, '
                    'photorealism, flat centered poster composition, symmetrical character lineup, '
                    'inconsistent cave layout, reversed light direction, identity exchange, live '
                    'action, photorealism, overhead view, high-angle shot, Mir already wrapped, '
                    'Lua already standing, cloth covering faces',
 'reference_paths': ['RaisingaDragonSeason01/Lua.png', 'RaisingaDragonSeason01/YoungMir.png'],
 'shot': 'Grounded virtual 35mm, eye-level medium three-quarter rear-side action-transition '
         'anchor.',
 'subjects': [{'who': 'lua',
               'block': 'Lua is a sun-browned human village girl with warm amber-brown eyes, a '
                        'messy high loose brown hair bun, beige sleeveless tunic and shorts, a '
                        'rope belt, a white shell pendant at her chest, and a faint blue mark on '
                        'her left wrist. She is fully human with no dragon horns, wings, tail, or '
                        'scales. She kneels frame right in three-quarter rear-side view, left hand '
                        'pulling loose beige cloth diagonally across the lower foreground, right '
                        'hand open near Mir, weight shifted forward over one knee ready to wrap '
                        'him and rise.'},
              {'who': 'mir',
               'block': 'Young Mir is a small silver-blue sea dragon hatchling with short curved '
                        'horns, one pair of fin-like wings, four small dragon limbs, a long scaled '
                        'tail ending in a water-drop crystal, and a faint crown-shaped wave mark '
                        'on his chest. He is a dragon only, with no human clothing or human facial '
                        'features. He remains separately frame left close to Lua’s knees, crawling '
                        'weakly toward her open hand and not wrapped yet.'}]},
 ('SC01-003_09', 'SEG04'): {'background_id': 'BG_EP01_COASTAL_CAVE_TOWARD_MOUTH',
 'bg_brief': 'Grounded virtual 35mm exit-facing view in the same cave. Dark wet foreground rocks '
             'frame both sides, a reflective walking path runs center-ahead to the bright mouth, '
             'and cool blue shadow remains along the left wall.',
 'entities': ['Lua has risen through continuous action and now stands on the right third of the '
              'same exit path with wrapped Mir held securely.'],
 'identity_lock': 'Lua remains fully human with no dragon anatomy, and Young Mir remains fully '
                  'dragon with no human clothing or human facial features; do not transfer marks, '
                  'wings, horns, scales, clothing or limbs between them.',
 'moment': 'Lua is seen from behind at the start of a natural walking step, cradling wrapped Mir '
           'toward daylight.',
 'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, duplicate characters, '
                    'merged bodies, fused anatomy, extra limbs, malformed hands, incorrect '
                    'character count, incorrect prop ownership, motion blur, live action, '
                    'photorealism, flat centered poster composition, symmetrical character lineup, '
                    'inconsistent cave layout, reversed light direction, identity exchange, live '
                    'action, photorealism, front-facing Lua, Mir unwrapped, exposed wings outside '
                    'cloth, blocked walking path, cave mouth off-center left',
 'reference_paths': ['RaisingaDragonSeason01/Lua.png', 'RaisingaDragonSeason01/YoungMir.png'],
 'shot': 'Grounded virtual 35mm, eye-level medium-wide rear tracking start with layered foreground '
         'parallax.',
 'subjects': [{'who': 'lua',
               'block': 'Lua is a sun-browned human village girl with warm amber-brown eyes, a '
                        'messy high loose brown hair bun, beige sleeveless tunic and shorts, a '
                        'rope belt, a white shell pendant at her chest, and a faint blue mark on '
                        'her left wrist. She is fully human with no dragon horns, wings, tail, or '
                        'scales. She stands on the right third with back to camera, weight '
                        'entering a natural first walking step, both arms securely cradling a '
                        'beige cloth bundle against her chest.'},
              {'who': 'mir',
               'block': 'Young Mir is a small silver-blue sea dragon hatchling with short curved '
                        'horns, one pair of fin-like wings, four small dragon limbs, a long scaled '
                        'tail ending in a water-drop crystal, and a faint crown-shaped wave mark '
                        'on his chest. He is a dragon only, with no human clothing or human facial '
                        'features. He is securely wrapped inside Lua’s bundle; only a small tail '
                        'crystal and restrained hint of blue scale may show at the cloth edge.'}]},
 ('SC01-004_01', 'SEG01'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua closes house door listening; Mir peeks from cloth at '
                                      'frame right.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Mir human child, Lua dragon '
                                               'parts, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium interior shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'foreground at wooden door. one hand on latch, '
                                                   'ear turned listening She wears her white shell '
                                                   'pendant and the blue mark on her left wrist is '
                                                   'visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right midground on floor in wrapped '
                                                   'cloth. one small horn and blue eye visible '
                                                   'from cloth bundle',
                                          'who': 'mir'}]},
 ('SC01-004_01', 'SEG02'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua stares at Mir with disbelief; Mir peeking from cloth at '
                                      'right.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Korean captions, merged '
                                               'bodies, trait swap, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot in house day interior.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'center crouched. disbelieving stare with amber '
                                                   'eyes wide and blue wrist mark visible She '
                                                   'wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right in partial cloth wrap on '
                                                   'wooden floor. small dragon face visible',
                                          'who': 'mir'}]},
 ('SC01-004_01', 'SEG03'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua lowers Mir into shallow water basin; Mir '
                                      'half-submerged.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Lua in basin, Mir standing '
                                               'human, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'leaning over basin edge. both human hands on '
                                                   'basin rim, amazed expression She wears her '
                                                   'white shell pendant and the blue mark on her '
                                                   'left wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right midground half-submerged in '
                                                   'basin. silver-blue scales glistening, relaxed '
                                                   'eyes at water surface',
                                          'who': 'mir'}]},
 ('SC01-004_01', 'SEG04'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Mir relaxed in basin; Lua kneels beside watching with tired '
                                      'sigh.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Korean text, human Mir, '
                                               'dragon Lua, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'kneeling beside basin. chin on one fist, '
                                                   'wistful tired expression She wears her white '
                                                   'shell pendant and the blue mark on her left '
                                                   'wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned center-right floating calm in '
                                                   'basin. crown chest mark visible at waterline',
                                          'who': 'mir'}]},
 ('SC01-004_02', 'SEG01'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua holds dried fish toward Mir in basin; Mir calm in '
                                      'water.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, fish fused to hand, Mir '
                                               'human, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium interior shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'holding dried fish extended. gentle offering '
                                                   'posture with both human hands She wears her '
                                                   'white shell pendant and the blue mark on her '
                                                   'left wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right in shallow basin. calm at '
                                                   'water surface, eyes on fish',
                                          'who': 'mir'}]},
 ('SC01-004_02', 'SEG02'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua offers fish; Mir recoils in basin with disgusted '
                                      'expression.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Mir eating fish, Korean '
                                               'subtitles, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'with dried fish extended. flustered eyebrows '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right in basin recoiled backward. '
                                                   'scaled snout wrinkled away from fish',
                                          'who': 'mir'}]},
 ('SC01-004_02', 'SEG03'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua holds fish confused; Mir turns body toward pale cream '
                                      'shell on table.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, shell worn as clothing, Mir '
                                               'licking shell already, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'with fish lowered. puzzled frown She wears her '
                                                   'white shell pendant and the blue mark on her '
                                                   'left wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned climbing basin edge toward table '
                                                   'center. dragon body oriented toward pale cream '
                                                   'comfort shell on table, not yet touching',
                                          'who': 'mir'}]},
 ('SC01-004_02', 'SEG04'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Mir reaches pale cream shell on table; Lua deadpan beside '
                                      'basin.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, shell merged with scales, '
                                               'human Mir, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'at basin rim. deadpan flat expression watching '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned on table edge center. both small '
                                                   'limbs reaching toward pale cream comfort '
                                                   'shell, snout inches from shell',
                                          'who': 'mir'}]},
 ('SC01-004_03', 'SEG01'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua wraps cloth over blue wrist mark; Mir watches from '
                                      'basin.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, desaturated overlay, ghost '
                                               'village, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium interior day shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'foreground. She wraps cloth over her left '
                                                   'wrist mark with worried downward gaze. She '
                                                   'wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned in basin right background. He '
                                                   'watches her from still water.',
                                          'who': 'mir'}]},
 ('SC01-004_03', 'SEG02'): {'background_id': 'BG_EP01_LUA_HOUSE_IMAGINED_VILLAGE',
                            'bg_brief': 'Literal house floor overlaid with desaturated ghostly '
                                        'village shore shapes and blurred baskets at the edges, '
                                        'cold grey-blue dream tint without readable adult faces.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Desaturated overlay with ghostly village shore at edges; '
                                      'Mir flinches in basin.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, readable adult faces, Korean '
                                               'text, normal warm lighting, live-action, motion '
                                               'blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium shot with desaturated fearful overlay.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'foreground. She has cloth on wrist with tense '
                                                   'shoulders under desaturated overlay. She wears '
                                                   'her white shell pendant and the blue mark on '
                                                   'her left wrist is visible when her arm is '
                                                   'exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned in basin right. He flinches with '
                                                   'wings tight under overlay tint.',
                                          'who': 'mir'}]},
 ('SC01-004_03', 'SEG03'): {'background_id': 'BG_EP01_LUA_HOUSE_IMAGINED_VILLAGE',
                            'bg_brief': 'Literal house floor overlaid with desaturated ghostly '
                                        'village shore shapes and blurred baskets at the edges, '
                                        'cold grey-blue dream tint without readable adult faces.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua blocks Mir protectively with arms extended; overlay '
                                      'still partially visible.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Lua with dragon wings, Mir '
                                               'in front of Lua, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'center foreground. Her human body shields '
                                                   'Young Mir in the basin right behind her arm. '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned in basin right. He is behind her '
                                                   'blocking arm in the basin.',
                                          'who': 'mir'}]},
 ('SC01-004_03', 'SEG04'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Normal house day light; Lua protective over Mir; Mir looks '
                                      'up trustingly.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, overlay remains, trait '
                                               'exchange, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'foreground. One arm still extended toward Mir '
                                                   'with soft resolved expression down toward him. '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned in basin right. He looks up with '
                                                   'trusting blue eyes.',
                                          'who': 'mir'}]},
 ('SC01-004_04', 'SEG01'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua clears throat with mock-adult posture; Mir tilts head '
                                      'in basin.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Korean captions, merged '
                                               'figures, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot house interior.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'standing straight. mock-serious adult posture '
                                                   'with one finger raised She wears her white '
                                                   'shell pendant and the blue mark on her left '
                                                   'wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right in basin. head tilted '
                                                   'curious, water at chest mark height',
                                          'who': 'mir'}]},
 ('SC01-004_04', 'SEG02'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua points at water jar on table; Mir watches from basin.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, jar in Mir claws, Lua dragon '
                                               'traits, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'pointing at clay water jar on table center. '
                                                   'matter-of-fact expression She wears her white '
                                                   'shell pendant and the blue mark on her left '
                                                   'wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right in basin background. watching '
                                                   'jar direction',
                                          'who': 'mir'}]},
 ('SC01-004_04', 'SEG03'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua gestures explaining; Mir in basin with tilted head '
                                      'watching.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, dialogue subtitles, trait '
                                               'swap, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium two-shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'mid-gesture with open palm. explaining '
                                                   'expression She wears her white shell pendant '
                                                   'and the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned right in basin. head tilted, '
                                                   'attentive blue eyes',
                                          'who': 'mir'}]},
 ('SC01-004_04', 'SEG04'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Mir opens small dragon mouth; Lua leans hopeful; no droplet '
                                      'yet.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, droplet on forehead already, '
                                               'human mouth on Mir, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium close two-shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'leaning forward hopeful. hands on basin rim '
                                                   'She wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned center-right in basin. small dragon '
                                                   'mouth open empty, expectant posture',
                                          'who': 'mir'}]},
 ('SC01-004_04', 'SEG05'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_DAY',
                            'bg_brief': 'Humble coastal house interior with wooden floor, bed, '
                                        'small table, shallow water basin, and warm daylight '
                                        'entering through a side window.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': "One tiny water droplet floats between Mir's open mouth and "
                                      "Lua's forehead.",
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, droplet already on forehead, '
                                               'fused faces, wings on Lua, live-action, motion '
                                               'blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium close shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'upper left forehead. hopeful expression She '
                                                   'wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned lower right in basin. open dragon '
                                                   'mouth with one tiny water droplet suspended '
                                                   'mid-air between them',
                                          'who': 'mir'}]},
 ('SC01-005_01', 'SEG01'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_NIGHT',
                            'bg_brief': 'Same humble house layout at night with dim warm interior '
                                        'fill, bed and basin in fixed positions, and cool blue '
                                        'moonlight from the window facing the night sea.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Night house interior; Lua asleep in bed; Mir curled in '
                                      'basin.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, both awake, Mir in bed, Lua '
                                               'in basin, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium-wide interior night shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'asleep in wooden bed left background. blanket '
                                                   'to chin, high bun loose on pillow She wears '
                                                   'her white shell pendant and the blue mark on '
                                                   'her left wrist is visible when her arm is '
                                                   'exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned curled in shallow water basin right '
                                                   'foreground. small dragon ball shape, fin wings '
                                                   'folded',
                                          'who': 'mir'}]},
 ('SC01-005_01', 'SEG02'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_NIGHT',
                            'bg_brief': 'Same humble house layout at night with dim warm interior '
                                        'fill, bed and basin in fixed positions, and cool blue '
                                        'moonlight from the window facing the night sea.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Faint synchronized glow from Mir chest mark and Lua wrist '
                                      'under cloth.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, bright blinding glow, merged '
                                               'sleeping bodies, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium night interior.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'sleeping bed left. faint blue glow through '
                                                   'cloth at left wrist She wears her white shell '
                                                   'pendant and the blue mark on her left wrist is '
                                                   'visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned in basin right. matching faint blue '
                                                   'glow at chest wave mark',
                                          'who': 'mir'}]},
 ('SC01-005_01', 'SEG03'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_NIGHT',
                            'bg_brief': 'Same humble house layout at night with dim warm interior '
                                        'fill, bed and basin in fixed positions, and cool blue '
                                        'moonlight from the window facing the night sea.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': "Mir trembles in sleep; Lua's brow furrowed still asleep.",
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, both sitting awake, dream '
                                               'overlay visible, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium close night shot split focus.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands bed '
                                                   'background with furrowed brow asleep. eyes '
                                                   'closed She wears her white shell pendant and '
                                                   'the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned basin foreground trembling in '
                                                   'sleep. wings twitching',
                                          'who': 'mir'}]},
 ('SC01-005_02', 'SEG01'): {'background_id': 'BG_EP01_MIR_VISION_PALACE_RUINS',
                            'bg_brief': 'Surreal broken dragon palace gate and ruined hall columns '
                                        'over a black abyss, enormous sleeping dragon shadow '
                                        'silhouettes without faces, floating debris, and cold blue '
                                        'memory light.',
                            'entities': [],
                            'moment': 'Dream palace ruins; Mir small before fading blue '
                                      'heart-stone.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Lua present, human Mir, live-action, '
                                               'photorealistic, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Wide dream shot.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned small figure foreground center '
                                                   'facing heart-stone.  back partly toward '
                                                   'camera, horns and tail crystal visible',
                                          'who': 'mir'}]},
 ('SC01-005_02', 'SEG02'): {'background_id': 'BG_EP01_MIR_VISION_PALACE_RUINS',
                            'bg_brief': 'Surreal broken dragon palace gate and ruined hall columns '
                                        'over a black abyss, enormous sleeping dragon shadow '
                                        'silhouettes without faces, floating debris, and cold blue '
                                        'memory light.',
                            'entities': [],
                            'moment': 'Enormous prince-dragon shadow silhouette behind small Mir.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, detailed prince face, human shadow, '
                                               'Lua, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium dream shot.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned small in lower center foreground.  '
                                                   'head turned slightly upward toward enormous '
                                                   'prince-dragon shadow silhouette',
                                          'who': 'mir'}]},
 ('SC01-005_02', 'SEG03'): {'background_id': 'BG_EP01_MIR_VISION_PALACE_RUINS',
                            'bg_brief': 'Surreal broken dragon palace gate and ruined hall columns '
                                        'over a black abyss, enormous sleeping dragon shadow '
                                        'silhouettes without faces, floating debris, and cold blue '
                                        'memory light.',
                            'entities': [],
                            'moment': 'Mir shudders before prince-dragon shadow; no visible '
                                      'speaker.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, visible speaking mouth, Korean text, '
                                               'human Mir, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium dream shot.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned center foreground shuddering with '
                                                   'wings pulled in and eyes squeezed. center '
                                                   'foreground shuddering with wings pulled in and '
                                                   'eyes squeezed',
                                          'who': 'mir'}]},
 ('SC01-005_02', 'SEG04'): {'background_id': 'BG_EP01_MIR_VISION_PALACE_RUINS',
                            'bg_brief': 'Surreal broken dragon palace gate and ruined hall columns '
                                        'over a black abyss, enormous sleeping dragon shadow '
                                        'silhouettes without faces, floating debris, and cold blue '
                                        'memory light.',
                            'entities': [],
                            'moment': 'Mir trembles violently as dream fractures toward reality '
                                      'light.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, text, subtitles, '
                                               'watermark, Lua awake in frame, human child, '
                                               'live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium close dream shot.',
                            'subjects': [{'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned center with violent tremble posture '
                                                   'frozen.  eyes wide, mouth open silent',
                                          'who': 'mir'}]},
 ('SC01-005_03', 'SEG01'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_NIGHT',
                            'bg_brief': 'Same humble house layout at night with dim warm interior '
                                        'fill, bed and basin in fixed positions, and cool blue '
                                        'moonlight from the window facing the night sea.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Mir shakes in basin; Lua jolts awake in bed.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Lua in basin, Mir in bed, '
                                               'live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium night interior.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands bed '
                                                   'left background sitting up sudden. blanket '
                                                   'fallen, startled eyes She wears her white '
                                                   'shell pendant and the blue mark on her left '
                                                   'wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned basin right foreground shaking. '
                                                   'water rippling around him',
                                          'who': 'mir'}]},
 ('SC01-005_03', 'SEG02'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_NIGHT',
                            'bg_brief': 'Same humble house layout at night with dim warm interior '
                                        'fill, bed and basin in fixed positions, and cool blue '
                                        'moonlight from the window facing the night sea.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua holds Mir in her arms standing beside basin.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, merged embrace anatomy, '
                                               'wings on Lua, human Mir, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium night shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'center standing. both human arms cradling Mir '
                                                   'with reassuring expression She wears her white '
                                                   'shell pendant and the blue mark on her left '
                                                   'wrist is visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned cradled against beige tunic chest. '
                                                   'small dragon body fully separate, wings '
                                                   'against her arms',
                                          'who': 'mir'}]},
 ('SC01-005_03', 'SEG03'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_NIGHT',
                            'bg_brief': 'Same humble house layout at night with dim warm interior '
                                        'fill, bed and basin in fixed positions, and cool blue '
                                        'moonlight from the window facing the night sea.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua clutches her chest feeling foreign dread; still holding '
                                      'Mir.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, chest claw on Lua from Mir '
                                               'wrongly, fused torsos, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium close shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'center. one arm holding Mir, other hand '
                                                   'clutched to her own chest with frightened wide '
                                                   'eyes She wears her white shell pendant and the '
                                                   'blue mark on her left wrist is visible when '
                                                   'her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned held at lower frame hip. dragon '
                                                   'head visible, separate body',
                                          'who': 'mir'}]},
 ('SC01-005_03', 'SEG04'): {'background_id': 'BG_EP01_LUA_HOUSE_INTERIOR_NIGHT',
                            'bg_brief': 'Same humble house layout at night with dim warm interior '
                                        'fill, bed and basin in fixed positions, and cool blue '
                                        'moonlight from the window facing the night sea.',
                            'entities': [],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua holds Mir tighter; Mir licks Lua wrist mark softly '
                                      'glowing.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, mark on Mir wrist, Lua '
                                               'scaled arm, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png'],
                            'shot': 'Medium night interior.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands left '
                                                   'holding Mir in both arms. gentle relieved '
                                                   'smile She wears her white shell pendant and '
                                                   'the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned against her left wrist. small snout '
                                                   'touching her left wrist mark with soft blue '
                                                   'glow at contact point',
                                          'who': 'mir'}]},
 ('SC01-005_04', 'SEG01'): {'background_id': 'BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW',
                            'bg_brief': 'Elevated view through a house window toward a dark calm '
                                        'empty night sea with gentle ripples, cool blue moonlight, '
                                        'faint stars, and no creatures in the background plate.',
                            'entities': [],
                            'moment': 'Lua at window; unnaturally still empty night sea outside.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, jellyfish in sea, '
                                               'text, subtitles, watermark, jellyfish in sea '
                                               'background, duplicate sea creatures, live-action, '
                                               'motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png'],
                            'shot': 'Medium interior night shot toward window.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'right foreground profile approaching window. '
                                                   'She has cautious eyes directed toward the '
                                                   'empty night sea through the window. She wears '
                                                   'her white shell pendant and the blue mark on '
                                                   'her left wrist is visible when her arm is '
                                                   'exposed.',
                                          'who': 'lua'}]},
 ('SC01-005_04', 'SEG02'): {'background_id': 'BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW',
                            'bg_brief': 'Elevated view through a house window toward a dark calm '
                                        'empty night sea with gentle ripples, cool blue moonlight, '
                                        'faint stars, and no creatures in the background plate.',
                            'entities': ['The Black Jellyfish floats centered outside over the '
                                         'dark sea with semi-transparent dark bell, ink smoke '
                                         'inside, and long tentacles below the surface.'],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Black Jellyfish floats above still sea; Lua at window with '
                                      'Mir in arms.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, duplicate jellyfish, '
                                               'jellyfish in background plate repetition, Mir '
                                               'human, Lua wings, live-action, motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png',
                                                'RaisingaDragonSeason01/BLACK JELLYFISH .png'],
                            'shot': 'Medium shot through window composition.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'lower right interior. holding Mir in arms, '
                                                   'both facing window She wears her white shell '
                                                   'pendant and the blue mark on her left wrist is '
                                                   'visible when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned held at chest facing window. '
                                                   'growling low expression toward the sea',
                                          'who': 'mir'}]},
 ('SC01-005_04', 'SEG03'): {'background_id': 'BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW',
                            'bg_brief': 'Elevated view through a house window toward a dark calm '
                                        'empty night sea with gentle ripples, cool blue moonlight, '
                                        'faint stars, and no creatures in the background plate.',
                            'entities': ['The Black Jellyfish is visible outside upper center '
                                         'through the window glass with tentacles trailing over '
                                         'the still sea.'],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Lua protective arm around Mir at window, whispering toward '
                                      'jellyfish.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, Korean subtitles, merged '
                                               'Lua-Mir, jellyfish inside room, live-action, '
                                               'motion blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png',
                                                'RaisingaDragonSeason01/BLACK JELLYFISH .png'],
                            'shot': 'Medium close interior window shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'left-center. tense lips parted whisper, eyes '
                                                   'on sea She wears her white shell pendant and '
                                                   'the blue mark on her left wrist is visible '
                                                   'when her arm is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned held at chest under protective arm. '
                                                   'separate dragon body under her arm',
                                          'who': 'mir'}]},
 ('SC01-005_04', 'SEG04'): {'background_id': 'BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW',
                            'bg_brief': 'Elevated view through a house window toward a dark calm '
                                        'empty night sea with gentle ripples, cool blue moonlight, '
                                        'faint stars, and no creatures in the background plate.',
                            'entities': ['The Black Jellyfish bell is oriented toward the house '
                                         'window with tentacles spread below the dark still sea.'],
                            'identity_lock': 'Lua remains fully human with no dragon anatomy, and '
                                             'Young Mir remains fully dragon with no human '
                                             'clothing or human facial features; do not transfer '
                                             'marks, wings, horns, or scales between them.',
                            'moment': 'Marks flash on Mir chest and Lua wrist; jellyfish oriented '
                                      'toward house.',
                            'negative_prompt': 'text, subtitles, speech bubbles, watermark, logo, '
                                               'duplicate characters, merged bodies, fused '
                                               'anatomy, extra limbs, malformed hands, incorrect '
                                               'character count, incorrect prop ownership, motion '
                                               'blur, live action, photorealism, wings on Lua, '
                                               'horns on Lua, tail on Lua, human clothing on Mir, '
                                               'trait exchange between Lua and Mir, text, '
                                               'subtitles, watermark, fade to black bar, duplicate '
                                               'jellyfish, trait exchange, live-action, motion '
                                               'blur',
                            'reference_paths': ['RaisingaDragonSeason01/Lua.png',
                                                'RaisingaDragonSeason01/YoungMir.png',
                                                'RaisingaDragonSeason01/BLACK JELLYFISH .png'],
                            'shot': 'Medium window shot.',
                            'subjects': [{'block': 'Lua is a sun-browned human village girl with '
                                                   'warm amber-brown eyes, a messy high loose '
                                                   'brown hair bun, beige sleeveless tunic and '
                                                   'shorts, a rope belt, a white shell pendant at '
                                                   'her chest, and a faint blue mark on her left '
                                                   'wrist. She is fully human with no dragon '
                                                   'horns, wings, tail, or scales. She stands '
                                                   'right foreground. wrist mark bright blue She '
                                                   'wears her white shell pendant and the blue '
                                                   'mark on her left wrist is visible when her arm '
                                                   'is exposed.',
                                          'who': 'lua'},
                                         {'block': 'Young Mir is a small silver-blue sea dragon '
                                                   'hatchling with short curved horns, one pair of '
                                                   'fin-like wings, four small dragon limbs, a '
                                                   'long scaled tail ending in a water-drop '
                                                   'crystal, and a faint crown-shaped wave mark on '
                                                   'his chest. He is a dragon only, with no human '
                                                   'clothing or human facial features. He is '
                                                   'positioned held in her arms. chest mark '
                                                   'matching glow visible on dragon body',
                                          'who': 'mir'}]}}


def _polish_subject_block(block: str) -> str:
    """Fix duplicated names, missing punctuation, and meta pose language."""
    import re

    text = block.strip()
    # "Village Child 1, Village Child 1 is" -> "Village Child 1 is"
    text = re.sub(
        r"\b(Village Child [12]|Lua|Young Mir|The Old Fisherman),\s+\1\b",
        r"\1",
        text,
    )
    # Missing period before capital "She/He" mid-sentence
    text = re.sub(r"([a-z])\s+(She|He|Both|Her|His)\b", r"\1. \2", text)
    # Meta spear phrasing
    text = text.replace(
        "raised or lowered per the beat",
        "held firmly in both hands",
    )
    # Collapse repeated spaces
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def build_generation_prompt(beat: dict[str, Any]) -> str:
    """Assemble standalone scene image generation prompt from a beat dict."""
    parts = [
        "Premium stylized 3D animated feature-film keyframe, cinematic 16:9 composition. "
        + str(beat.get("shot") or "").strip(),
        str(beat.get("bg_brief") or "").strip(),
    ]
    who_set: set[str] = set()
    for subject in beat.get("subjects") or []:
        block = _polish_subject_block(str(subject.get("block") or ""))
        if block:
            parts.append(block)
        who = str(subject.get("who") or "")
        if who:
            who_set.add(who)
    for entity in beat.get("entities") or []:
        text = str(entity or "").strip()
        if text:
            parts.append(text)
    moment = str(beat.get("moment") or "").strip()
    if moment:
        parts.append(moment)
    identity_lock = beat.get("identity_lock")
    if identity_lock:
        parts.append(str(identity_lock).strip())
    elif {"lua", "mir"}.issubset(who_set):
        parts.append(
            "Lua remains fully human with no dragon anatomy, and Young Mir remains fully dragon "
            "with no human clothing or human facial features; do not transfer marks, wings, horns, "
            "or scales between them."
        )
    elif {"lua", "child1", "child2"}.issubset(who_set):
        parts.append(
            "Keep the three children as separate identities with unshared hairstyles, clothing colors, "
            "and accessories. Lua alone has the messy brown bun, beige sleeveless outfit, white shell "
            "pendant and blue wrist marking. Village Child 1 alone has short tousled hair and the dark "
            "charcoal sleeveless tunic. Village Child 2 alone has the high ponytail, indigo-blue tunic "
            "and woven shoulder basket. The fishing spear belongs only to Lua."
        )
    parts.append(
        "Match the supplied character reference sheets exactly for every visible character and prop. "
        "Keep each identity's exclusive anatomy, clothing and accessories attached only to that character."
    )
    return "\n\n".join(p for p in parts if p)

