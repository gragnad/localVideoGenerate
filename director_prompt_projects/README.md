# Director Prompt Projects

LTX Director의 `01 생성`에 불러올 프롬프트·장면 이미지 프로젝트 저장소다.
MSR Prompt Project와 분리하며, 캐릭터 시트나 빈 배경 plate 대신 각 Relay
구간의 시작 상태를 보여주는 완성된 장면 이미지를 사용한다.

## Layout

```text
director_prompt_projects/
└── PROJECT_ID/
    ├── manifest.json
    ├── character_identity_registry.json
    ├── location_registry.json
    ├── SCENE_ID/
    │   └── CLIP_ID.md
    └── scene_images/
        └── CLIP_ID/
            ├── SEG01.png
            └── SEG02.png
```

## Workflow

1. 시나리오와 레퍼런스를 읽고 클립을 나눈다.
2. Global Prompt, Segment별 Director Prompt, 장면 이미지 생성 Prompt를 작성한다.
3. `prompt_review.status`를 `approved`로 변경하기 전에 시나리오·대사·구간 시간을 검수한다.
4. 생성한 장면 이미지를 `scene_images/CLIP_ID/`에 저장한다.
5. 각 이미지를 검수하고 `scene_image.review_status`와 `scene_image.sha256`을 기록한다.
6. 모든 이미지가 승인되면 검증기가 클립 상태를 `ready_for_director`로 계산한다.

클립 Markdown의 선언 상태보다 실제 프롬프트 검수, 이미지 존재, 이미지 검수,
SHA-256 일치 여부가 우선한다. 승인 후 이미지 파일이 변경되면 상태는 자동으로
`image_review_required`가 된다.

## Status

- `draft`: 작성 중
- `prompt_review_required`: 프롬프트 검수 필요
- `awaiting_scene_images`: 승인된 프롬프트에 연결할 장면 이미지 필요
- `image_review_required`: 이미지 파일은 있으나 검수 필요
- `image_changes_required`: 이미지 수정 필요
- `needs_confirmation`: 사용자 판단 필요
- `ready_for_director`: 01 생성에 등록 가능
- `registered`: 등록 이력 상태
- `invalid`: 구조 오류

## Authoring Rules

- 시각·행동·카메라 지시는 영어로 작성한다.
- 대사는 한국어 원문을 유지하고 `natural Korean`으로 표시한다.
- 한 Segment에는 하나의 핵심 행동만 둔다.
- 장면 이미지는 Segment 시작 자세를 표현하고 다음 행동을 위한 공간을 남긴다.
- 캐릭터별 독점 외형과 소품 소유권을 Global Prompt에 명시한다.
- 다중 캐릭터는 합체·복제·신체 특징 이전 금지 규칙을 포함한다.
- 배경, 동적 개체, 상호작용 소품을 구분한다.
- 한 클립은 30초 이하를 권장한다.

`CLIP_TEMPLATE.md`를 복사해 새 클립을 작성한다.
