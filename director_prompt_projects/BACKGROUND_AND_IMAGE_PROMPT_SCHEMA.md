# Background Groups and Standalone Image Prompts

Director 프로젝트의 생성용 이미지는 두 계층으로 분리한다.

1. `location_registry.json`의 배경 그룹과 배경 원판 생성 Prompt
2. 각 클립 Segment의 독립형 장면 이미지 생성 Prompt

## Background Group

같은 `location_id`와 `background_id`를 사용하는 클립은 동일한 배경 그룹이다.
시간대, 조명, 파손 상태 또는 공간 배치가 달라지면 별도 그룹으로 분리한다.

```json
{
  "location_id": "LOC_EP01_COASTAL_CAVE_INTERIOR",
  "background_id": "BG_EP01_COASTAL_CAVE_INTERIOR",
  "display_name": "Coastal Cave Interior",
  "terrain": "Shallow seawater over uneven wet rock.",
  "structures": "Narrow damp stone cave and a distant cave mouth.",
  "lighting": "Cool blue cave-depth glow mixed with distant daylight.",
  "fixed_elements": [
    "central shallow-water path",
    "wet rock ledges",
    "distant cave mouth"
  ],
  "image_generation": {
    "generation_prompt": "A self-contained English prompt for an empty reusable background plate.",
    "negative_prompt": "characters, creatures, text, watermark, changing architecture",
    "suggested_filename": "BG_EP01_COASTAL_CAVE_INTERIOR.png",
    "source_path": null,
    "review_status": "pending",
    "review_notes": [],
    "sha256": null
  }
}
```

배경 원판은 캐릭터와 장면별 상호작용 소품을 넣지 않는다. 고정 지형, 구조물,
시간대, 조명, 색상, 카메라 방향과 이후 캐릭터가 배치될 여백을 명시한다.

## Segment Standalone Prompt

`scene_image.generation_prompt`는 Global Prompt를 따로 붙이지 않아도 이미지 모델이
이해할 수 있는 독립형 Prompt다. 기존 `scene_image.prompt`는 레거시 필드로 남기며
UI는 `generation_prompt`를 우선 표시한다.

```json
{
  "scene_image": {
    "generation_prompt": "A complete English image-generation prompt including style, location, background group, character identity, exact placement, pose, expression, props, lighting and the frozen opening moment.",
    "negative_prompt": "text, watermark, duplicate characters, fused anatomy",
    "background_id": "BG_EP01_COASTAL_CAVE_INTERIOR",
    "reference_paths": [
      "RaisingaDragonSeason01/Lua.png",
      "RaisingaDragonSeason01/YoungMir.png"
    ],
    "suggested_filename": "SC01-003_09_SEG01.png",
    "source_path": null,
    "review_status": "pending",
    "review_notes": [],
    "sha256": null
  }
}
```

Segment Prompt에는 배경 그룹의 핵심 시각 요소도 짧게 포함한다. 단순히
`use background BG_...`라고만 쓰지 않는다. 캐릭터별 참조 이미지가 없어도 외형을
구별할 수 있도록 핵심 외형을 문장에 포함하고, `reference_paths`에는 실제 첨부할
파일을 기록한다.
