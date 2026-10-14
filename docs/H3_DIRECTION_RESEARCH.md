# OpenCode · Muse Spark 1.3 연출 연구

## 시작점

원본 영상 경로와 분석 구간은 **실제 시작할 때 OpenCode에서 입력**한다. 설치·개발 중에는 원본을 지정하거나 실제 생성 큐를 실행하지 않는다.

OpenCode에서 `/h3-direction`을 호출하고 영상 경로, 시간 구간, 등장 대상의 루아·미르·해파리 대응을 전달한다. 명령은 이 문서를 읽고 아래 실행기를 사용한다. 기존 OpenCode 설정의 `opencode/muse-spark-1.3-contributor-free`를 명시적으로 사용하며 다른 모델로 자동 대체하지 않는다.

실행기: `/home/nalstudio/local-ai/video-engine/h3_direction_research.py`
파이썬: `/home/nalstudio/local-ai/video-engine/.venv/bin/python`

## 동작 범위

- 기존 프로젝트 클립에서 **선택한 캐릭터·배경 이미지**를 실험 폴더에 복사한다. 기존 프롬프트·자산·선택 결과를 덮어쓰지 않는다.
- 원본을 시간별로 샘플링하고 Muse에 실제 이미지와 시각을 전달한다. 전체 구간의 1차 분석과 프롬프트를 먼저 만든다.
- H3 공식 여섯 구역, Shot 표기와 Picture 연결을 검사한 뒤 기존 `h3_queue`에 `local_generation` / `r2v`로 등록한다. 기존 Windows 후보 경로로 암묵적으로 보내지 않는다.
- Muse가 원본·후보·캐릭터 참조·직전 확정 결과의 끝부분을 비교한다. 구도, 카메라, 행동 인과, 타이밍, 충격, 정체성, 연결의 **모든 항목**이 기준을 넘어야 한다. 한 항목을 다른 항목의 높은 점수로 상쇄하지 않는다.
- 대표 첫 구간의 사용자 확인 후 다음 구간을 자동 진행한다. 통과 구간을 유지하고 실패한 구간의 가설 하나를 수정한다. 다음 구간 시작은 직전 결과의 실제 끝 상태로 보정한다.
- 나머지 자동 통과는 `auto_accepted`이며 사용자 승인이 아니다. 전체 미리보기를 확인한 뒤 일괄 확인한다.
- 생성 수·Muse 호출 수·클립별 회차를 제한한다. 점수 정체나 렌더 대기 시간 초과는 원인을 기록하고 멈춘다. 예산을 자동 증액하지 않는다.
- 중단 후 저장된 상태로 재개한다. 큐 등록 도중 종료된 경우 `reconcile`로 실제 후보·작업 ID를 대조하며 불명확한 등록은 중복 제출하지 않는다.
- 작업 기록과 최종 프롬프트·성공/실패 근거를 Markdown으로 내보낸다. 결과는 관찰 사례이며 H3 가중치 학습이나 모든 장면의 재현성 입증이 아니다.

## 입력 만들기

반복 연구의 기본 생성 해상도는 **608×352, 24fps**다. 별도의 width·height를 지정한 실험은 해당 값을 사용한다.

`create --input /절대/경로/input.json`을 호출한다. JSON 예시의 경로와 ID는 실행 시 실제 값으로 교체한다.

```json
{
  "title": "전투 연출 연구 01",
  "source_path": "/실제/원본.mp4",
  "start": 190,
  "end": 222,
  "boundaries": [190, 198, 206, 214, 222],
  "project_id": "실제 프로젝트 ID",
  "clip_id": "루아 미르 해파리 참조가 있는 실제 클립 ID",
  "picture_indices": [1, 2, 3, 4],
  "character_mapping": "원본의 공격자는 루아, 지원자는 미르, 상대는 해파리. 기존 실사 자산 외형 유지.",
  "width": 608,
  "height": 352,
  "candidate_count": 2,
  "max_rounds": 4,
  "max_generations": 32,
  "max_model_calls": 80,
  "stagnation_rounds": 3,
  "threshold": 4,
  "min_confidence": 0.75,
  "sample_fps": 4,
  "render_timeout_seconds": 7200
}
```

시간은 원본 기준 초다. 각 경계 구간은 4–15초이며 시작부터 끝까지 빈틈 없이 포함한다. `boundaries`를 생략하면 `clip_seconds`(기본 8초)를 기준으로 균등한 **임시 분석 창**을 만든다. 이것은 컷 자동 검출이 아니다. 전투의 접촉·반격 중간을 자르지 않도록 OpenCode에서 원본을 확인하고 사건 경계를 지정하는 편이 좋다.

`picture_indices` 순서가 새 실험의 Picture 1, 2, 3 순서가 된다. 배경을 먼저 두고 현재 쓸 정체성·소품을 선택한다. 생략 시 기존 클립의 storyboard 종류 참조를 제외한다. `adapter_id` 생략 시 현재 기본 R2V 어댑터를 사용한다. 액션 영상이 필수인 어댑터는 이 이미지 R2V 실행기에서 거부한다. `workflow_settings`로 현재 승인된 설정을 전달할 수 있다.

20분을 시작할 때에는 전체 분석 호출 수만 해도 클립 수만큼 필요하다. 예산은 대표 구간의 실제 생성 시간·통과율을 측정한 뒤 명시적으로 정한다. 기본값은 20분 전체를 무제한 실행하는 설정이 아니다.

## 명령 순서

아래 명령은 실행기 경로 뒤에 붙이는 인자다. 모든 결과는 JSON으로 반환한다.

1. `doctor` — OpenCode/ffmpeg 경로, 모델 ID, 로컬 렌더 주소와 실험 목록. 모델 실제 호출이나 GPU 가동을 뜻하지 않는다.
2. `create --input INPUT.json` — 실험을 생성하고 ID를 얻는다. 생성 작업 없음.
3. `start ID` — 원본·참조 해시 검사 후 실행 상태로 변경.
4. `launch ID` — 별도 프로세스로 실행. OpenCode 대화가 끝나도 계속되며 `runner.log`에 기록한다. `run ID`는 전경 실행, `tick ID`는 한 단계 실행이다.
5. `status ID` — 진행, 오류, 후보 ID, 점수·근거 조회. 후보 영상은 기존 제작기의 후보 화면에서도 확인 가능하다.
6. 첫 구간에서 `awaiting_acceptance`가 되면 실제 후보를 확인하고 `accept ID --input ACCEPT.json`. 입력은 `{"segment_id":"segment_0001","job_id":"실제 후보 ID"}`. 확인 후 `launch ID`로 나머지 자동 진행.
7. `awaiting_final_review`에서 `preview ID`로 전체 연결 영상을 만들고 확인한다. 이후 `accept_sequence ID --input REVIEW.json`, 입력은 `{"feedback":"사용자의 전체 연결 확인 내용"}`.
8. `assemble ID` — 전체 확인된 결과를 조립. `export ID` — 실험별 프롬프트와 평가 근거 문서 생성. `summarize ID` — Muse가 평가된 후보만 근거로 적용 조건·영어 프롬프트 패턴·실패 한계를 정리한다. 이 단계도 모델 호출 예산을 사용한다.

`pause ID`는 새 실험 단계 진행을 멈춘다. 이미 등록된 H3 렌더는 취소하지 않는다. 현재 모델 호출·평가 중에는 잠금 오류가 반환될 수 있으므로 해당 단계가 끝난 뒤 다시 호출한다. 큐 취소가 필요하면 기존 제작기의 작업 취소를 사용한다. `resume ID` 뒤 `launch ID`로 재개한다.

`reject ID --input FEEDBACK.json`은 `{"segment_id":"segment_0002","feedback":"접촉 전에 컷이 넘어감. 접촉 후에 전환"}`처럼 실패 원인을 받는다. 정체/실패 구간을 수정 상태로 바꾸며 이후 `resume`·`launch`로 진행한다. 사용자 확정 구간은 잠긴 상태로 유지한다. 잘못된 자동 통과 구간은 전체 확정 전에 reject할 수 있다. 이때 후속 자동 통과 구간은 연결 재검사 대상으로 바뀐다. 기존 결과가 새 연결도 통과하면 다시 생성하지 않는다.

`limits ID --input LIMITS.json`으로 명시적으로 한도를 늘린다. 예: `{"max_generations":60,"max_model_calls":120,"max_rounds":6}`. 모델 호출 실패는 이미 소비된 시도로 기록되며 무한 재시도하지 않는다. 생성 대기 한도 초과 시 기존 H3 작업을 확인해야 하며 새 작업을 자동 제출하지 않는다.

## 기록과 검증 한계

저장 위치: `runtime/direction_research/research_*/`

- `experiment.json`: 원본 해시, 캐릭터 대응, 복사 참조, 설정, 상태, 모든 후보 회차·평가와 작업 ID.
- `model_calls/`: 각 Muse 요청의 입력·첨부 시각·구조화된 응답. 인증 값은 저장하지 않는다.
- `segment_*/`: 원본/후보 시간별 분석 이미지.
- `prompt_findings.md`: `export`로 만드는 성공·실패 기록과 프롬프트 원문.
- `prompt_methods.md`: `summarize`로 만드는 실사용 방법·적용 조건·영어 패턴·한계. 실제 평가 후보 ID가 없는 요약은 거부한다.
- `direction_review_silent.mp4`: 전체 연출 검토용 **무음** 영상. 24fps 시간축으로 조립하며 허용된 작은 길이 오차는 끝 프레임 유지/잘라내기로 맞춘다.

기본 4fps 샘플은 프레임 사이의 고속 동작, 임팩트 프레임, 정확한 접촉 타이밍이나 음향을 완전히 검증하지 못한다. 점수는 원본 시청을 대체하지 않는 잠정 평가다. 필요 시 최대 8fps로 늘릴 수 있다. 원본 영상 파일 자체를 H3 동작 참조로 전달하지 않으며 원본 프레임은 Muse의 분석용이다. 같은 Muse 모델의 작성·평가 편향도 남는다.

이 버전은 이미지 기반 R2V 실험과 무음 연출 검토를 끝까지 수행한다. 음향 비교/믹싱, 원본 전체의 자동 쇼트 경계 검출, 액션 참조 비디오 자동 전환, 다른 장면에서의 재현성 실험은 별도 확장이다.

## 설치와 점검

OpenCode는 PATH 또는 `H3_RESEARCH_OPENCODE_BIN`을 사용하며, 이 환경의 `local-ai/opencode-web/node_modules/opencode-linux-*/bin/opencode`도 찾는다. 영상 분석 호출은 `opencode run --pure --model opencode/muse-spark-1.3-contributor-free --format json`으로 수행한다. 각 분석 요청은 도구 사용을 금지하고 첨부 미디어에서 JSON만 반환하게 한다. OpenCode의 기존 로그인/모델 제공 정책이 적용된다.

실제 실행에는 Muse 모델 사용 가능 상태, 로컬 ComfyUI와 `local_generation` H3 Worker, 현재 R2V 어댑터·가중치가 필요하다. 실행기는 GPU 서버를 임의로 교체하거나 Windows 호스트를 켜지 않는다.

공식 근거: https://opencode.ai/docs/cli/ · https://opencode.ai/docs/commands/ · https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md

## 이미지 수 제한과 장기 세션

[이미지 요청 한도 운용](H3_IMAGE_REQUEST_LIMIT.md)을 따른다. 연구 실행기는 최대 40개 첨부로 프레임 시트를 준비하고 독립 OpenCode 호출을 사용한다. 원본과 실제 첨부 목록은 input.json에 보존한다. 정밀 시각 판정이 어려운 시트는 개별 원본의 작은 구간으로 다시 확인한다. 일반 대화에서 계속 이미지를 여는 경로의 이력 누적은 이 실행기 수정으로 해결되지 않으므로 주 세션에는 텍스트 결과만 전달한다.
