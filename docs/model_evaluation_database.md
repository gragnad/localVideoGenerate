# 모델 평가 데이터베이스

`runtime/evaluation/evaluation.db`는 H3 생성 결과와 모델 테스트 리뷰를 공통 형식으로 저장한다.
영상과 이미지는 파일시스템에 두고 DB에는 경로와 해시만 기록한다. 현재 스키마 버전은 10이다.

## 현재 데이터 계층

- `models`, `model_runtimes`: 모델 및 실행 환경
- `workflow_profiles`, `workflow_adapters`: 원본 워크플로우 해시와 입력 바인딩
- `benchmark_suites`, `benchmark_case_versions`, `suite_cases`: 버전 고정 테스트 세트
- `benchmark_cases`, `benchmark_case_prompts`: 모델 중립 의도와 실행 프롬프트
- `assets`, `benchmark_case_assets`, `run_assets`: 테스트 참조 자산 연결
- `test_sessions`, `test_session_cases`, `test_session_runs`: 실행 계획, 세션 공통 워크플로우 설정과 H3 작업 연결
- `generation_runs`: 출력, 해시, 설정 및 성능
- `reviews`, `review_issues`, `capability_scores`: 사람·AI 검수 리비전
- `prompt_policies`, `prompt_policy_scopes`: 검수 결과에서 정리한 모델별 규칙

새 DB에는 이전 제작 배치용 `test_session_batches`와 소스 문서 라이브러리용
`source_documents`를 만들지 않는다. 이미 존재하는 DB의 과거 테이블과 행은 이력 보존을 위해
자동 삭제하지 않으며, 현재 실행 경로에서도 사용하지 않는다.

## 화면과 실행 흐름

1. `06 모델 관리`에서 모델, 워크플로우 프로필과 어댑터를 등록한다.
2. `07 모델 테스트` 또는 `08 R2V 테스트`에서 테스트 세션을 만든다.
3. 가상 컴파일·사전검사 후 H3 전용 큐에 등록한다.
4. `03 큐 · 진행`에서 H3 worker 상태와 그룹 진행률을 확인한다.
5. 생성 완료 후 모델 테스트 화면에서 결과를 재생하고 사람 검수를 저장한다.
6. 필요할 때만 AI 검수 버튼을 눌러 별도 검수 큐에 등록한다.

모델 테스트 생성은 제작 후보 생성과 같은 `runtime/h3` FIFO를 사용한다. 제작 배치,
자동 Retake, 편집·조립 단계는 없다. AI 검수 역시 생성 뒤 자동 실행되지 않는다.

## R2V 규칙

R2V 테스트는 일반 I2V 세트와 분리한다. MiniMax H3 R2V 워크플로우와 최대 9개의 순서 있는
Picture 입력을 사용하며, 지원 테스트 해상도는 608×352, 736×416, 832×480, 1280×736이다. 캐릭터·배경·소품 등
각 참조 역할과 Picture 순서는 테스트 계약에 저장된다. 전역 공유 이미지는 여러 케이스에서
재사용할 수 있다.

PINT8 + Sol-Attn 워크플로우를 선택하면 `08 R2V 테스트`에서 Patch Sol-Attn 설정을 조정할 수
있다. 설정은 세션에 고정 저장되며 사전검사와 큐 등록 시 복제된 실행 워크플로우에만 적용된다.
기준 R2V 워크플로우에는 이 설정을 전달할 수 없고, 등록 원본 워크플로우 파일은 변경하지 않는다.
폼의 초기값은 등록된 API 워크플로우의 `SolAttnPatch` 노드에서 읽는다. 설정은 런타임 ID와
생성 실행 기록에도 포함하며, 모델·워크플로우 비교에서는 서로 다른 Sol-Attn 설정을 별도
구성으로 집계한다. 스키마 10 이전 PINT8 세션의 빈 설정은 등록 그래프의 실제 기본값으로
해석한다.

R2V AI 검수는 스토리보드 전용 계약을 요구하지 않는다. 캐릭터·배경·소품 참조, 프롬프트
이해, 동작, 시각적 일관성, 카메라 제어와 일반 숏 구조를 평가한다.

## 보존 및 삭제 원칙

- 프로젝트·테스트 자산과 과거 출력은 명시적인 사용자 삭제 요청 없이는 제거하지 않는다.
- 세션 삭제는 현재 H3 작업과 현재 평가 DB 연결만 대상으로 한다.
- 이전 `jobs` 출력은 과거 모델 테스트 영상을 재생하기 위한 읽기 전용 fallback으로만 조회한다.
- 리뷰 수정은 기존 행을 덮어쓰지 않고 새 revision으로 저장한다.

## 실행 서비스

- `h3-video-ui.service`: 웹 UI/API
- `h3-video-worker.service`: H3 생성 큐
- `model-test-review-worker.service`: 사용자가 요청한 모델 테스트 AI 검수 큐

세 서비스는 `%h/.config/h3-video-engine/runtime.env`를 공통 환경 파일로 사용한다.
