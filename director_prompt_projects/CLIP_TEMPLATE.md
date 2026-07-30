# Director Prompt: CLIP_ID

## Summary

한 문장으로 클립을 설명한다.

## Machine Payload

```json
{
  "schema_version": 1,
  "workflow": "director_prompt_v1",
  "project_id": "PROJECT_ID",
  "episode_id": "EP01",
  "scene_id": "SC01-001",
  "clip_id": "SC01-001_01",
  "sequence": 1,
  "status": "prompt_review_required",
  "fps": 24,
  "resolution": {
    "width": 1536,
    "height": 864
  },
  "requested_seconds": 10,
  "scenario_source": "RaisingaDragonSeason01/Raising a Dragon.md",
  "scenario_source_span": "L1-L10",
  "narrative_purpose": "Describe the narrative purpose.",
  "characters": [],
  "props": [],
  "location": {
    "location_id": "LOCATION_ID",
    "description": "Stable location description and visual anchors."
  },
  "continuity": {
    "start_state": "Opening state.",
    "end_state": "Closing state.",
    "carry_to_next": []
  },
  "global_prompt": "English global visual prompt. All spoken dialogue must be natural Korean.",
  "segments": [
    {
      "segment_id": "SEG01",
      "order": 1,
      "seconds": 5,
      "beat_type": "establishing",
      "narrative_purpose": "What this beat accomplishes.",
      "visible_characters": [],
      "visible_props": [],
      "start_state": "The state shown by the scene image.",
      "end_state": "The state reached at the end of this segment.",
      "director_prompt": "English motion and camera prompt. Korean dialogue stays quoted.",
      "dialogue": [],
      "scene_image": {
        "status": "missing",
        "suggested_filename": "SC01-001_01_SEG01.png",
        "source_path": null,
        "prompt": "English still-image generation prompt showing the segment start state.",
        "negative_prompt": "text, watermark, duplicate characters, fused anatomy, completed action",
        "review_status": "pending",
        "review_notes": [],
        "sha256": null
      }
    },
    {
      "segment_id": "SEG02",
      "order": 2,
      "seconds": 5,
      "beat_type": "action",
      "narrative_purpose": "What this beat accomplishes.",
      "visible_characters": [],
      "visible_props": [],
      "start_state": "Continuation from SEG01.",
      "end_state": "State carried to the next clip.",
      "director_prompt": "English motion and camera prompt. Korean dialogue stays quoted.",
      "dialogue": [],
      "scene_image": {
        "status": "missing",
        "suggested_filename": "SC01-001_01_SEG02.png",
        "source_path": null,
        "prompt": "English still-image generation prompt showing the segment start state.",
        "negative_prompt": "text, watermark, duplicate characters, fused anatomy, completed action",
        "review_status": "pending",
        "review_notes": [],
        "sha256": null
      }
    }
  ],
  "prompt_review": {
    "status": "pending",
    "scenario_consistent": false,
    "dialogue_preserved": false,
    "duration_valid": false,
    "identity_rules_valid": false,
    "segment_continuity_valid": false,
    "image_prompts_valid": false,
    "warnings": [],
    "review_notes": []
  },
  "image_review_summary": {
    "status": "pending",
    "approved_count": 0,
    "total_count": 2,
    "warnings": []
  }
}
```
