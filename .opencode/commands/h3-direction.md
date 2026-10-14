---
description: Muse Spark 1.3로 H3 R2V 연출 비교 실험을 시작·재개·정리
agent: build
model: opencode/muse-spark-1.3-contributor-free
subtask: false
---

사용자 요청: $ARGUMENTS

한국어로 응답한다. 먼저 `/home/nalstudio/local-ai/video-engine/docs/H3_DIRECTION_RESEARCH.md`와 적용되는 AGENTS.md를 읽는다.
이 명령은 OpenCode에서 원본 경로·구간을 받아 기존 루아·미르·해파리 자산으로 연출 연구를 실행하는 진입점이다.
원본과 구간이 없으면 실행 시 필요한 정보만 질문한다. 작품 이름만으로 영상 내용을 지어내지 않는다.

기존 제작 정본과 프로젝트 클립 참조 목록을 읽어 배경·캐릭터 Picture 번호와 역할 대응을 정한다.
실행기는 `/home/nalstudio/local-ai/video-engine/.venv/bin/python /home/nalstudio/local-ai/video-engine/h3_direction_research.py`다.
먼저 doctor를 확인하고 사용자 입력으로 JSON을 작성한 뒤 create, start, launch 순서로 실행한다.
반복 연구의 기본 생성 해상도는 608×352, 24fps로 사용한다. 사용자가 별도 해상도를 지정한 경우에만 입력의 width·height를 변경한다.
사용자가 이미 지정한 생성·평가 범위와 한도 안에서는 승인 질문을 반복하지 않는다. 기존 실험이면 새로 만들지 말고 status부터 확인한다.
등록한 ID와 로그 경로를 기록해 대화가 끝나도 resume/launch할 수 있도록 한다. 소스나 기존 제작 클립을 덮어쓰지 않는다.
대표 고위험 구간의 실제 결과를 확인한 뒤 기존 승인 범위를 이어받아 자동 반복한다. AI 통과를 사용자 확인으로 꾸미지 않는다.
완료되면 preview로 전체 연결을 확인하고, 사용자 확인을 기록한 뒤 assemble, export, summarize로 결과와 근거 기반 프롬프트 방법을 정리한다.
정체·실패·한도 초과는 구체적인 이유와 최소 수정안을 보고한다. 무제한 재시도나 다른 모델 자동 대체를 하지 않는다.

01~04 파일럿을 재개할 때는 `trainAssets/research_01_04/generation_pilot_state.json`, `evaluation_criteria_04.json`, `candidate_reviews.json`, `reports/reassessment_v2.md`를 먼저 읽는다.
현재 6개 생성 한도는 소진되었고 queue_hold=true다. 검토 수정 요청을 추가 생성 허가로 해석하지 않는다.
기존 candidate_reviews.json의 previous_provisional과 reports/before_review_v2는 이력이며 현재 통과 증거가 아니다. scripts/evaluate.py의 judge() v2 판정이 현재 기준이다.
별도 파일럿 요청을 준비할 때는 width=608, height=352, fps=24를 명시하고 아래 사전 검증을 실행한다:
`.venv/bin/python trainAssets/research_01_04/scripts/pilot_submission.py <요청.json> --output-dir <검증결과폴더>`
이 명령은 제출하지 않는다. 생성 범위가 새로 지정되기 전에는 큐를 호출하지 않는다. 허용된 생성 시에는 검증 결과 request.json을 그대로 사용하고, 등록된 request.json 및 workflow_api.json을 같은 verify_workflow_resolution 함수로 재검사한다. 입력이나 설정을 바꿨으면 사전 검증부터 다시 한다. 기존 832×480 request.json을 복사해 바로 제출하지 않는다.
출력은 ffprobe로 영상 스트림의 크기·길이를 검사한다. 608×352 출력 실측 전에는 해상도 적용 완료라고 기록하지 않는다.
컷은 영상 프레임 PTS로 측정하고 오차 범위를 기록한다. 2fps 샘플 시각을 정확한 컷 시각으로 쓰지 않는다. 붙잡기 대상과 폭발 화면 가림을 독립 평가하고 근거 없는 항목은 미확인으로 남긴다.

DS_Assets 자료를 다룰 때는 trainAssets/research_DS/README.md, timeline_overview.md, coverage_ledger.json을 먼저 읽는다. 특정 효과만 선별하지 말고 DS01-04→05→06→07 순서로 전체 연출 흐름을 우선 검토한다. 기존 45개 흐름 묶음은 10초 표본의 1차 조사이며 정확한 쇼트 경계가 아니다. 대화·설명·이동·대기·반응을 포함하여 구간별 공간→정보→행동→반응→전환을 확인한다. 작품별 근거는 분리하고 trainAssets/direction_dictionary/catalog.py로 통합 검색한다. DS H3 문구는 현재 모두 미검증이며 이 자료 등록만으로 생성 예산이나 승인 범위를 늘리지 않는다. 루아–심해왕 실험 후 근거를 연결하여 검증 상태를 갱신한다.

이미지 요청 한도: docs/H3_IMAGE_REQUEST_LIMIT.md를 읽는다. 주 세션은 텍스트 조정용으로 유지하고 프레임을 계속 직접 열지 않는다. 이미지 분석은 세션 이력을 재사용하지 않는 독립 opencode run 호출 및 h3_research_media.prepare_media 경로로 수행한다. 요청당 이미지 최대 40개를 적용하고 원본·후보·참조·이전 연결 프레임을 합산한다. h3_direction_research.muse_call에는 이 전처리가 연결되어 있다. 일반 OpenCode 도구로 주 세션에 이미지를 누적하는 별도 경로에는 자동 적용되지 않으므로 사용하지 않는다. 시트로 세부가 불명확하면 좁은 시간 구간의 원본 프레임을 별도 독립 요청으로 확인한다. 한도 오류를 같은 요청의 무한 재시도로 처리하지 않는다. 세션 재개 시 파일에서 진행·예산·큐를 조회하고 완료 작업을 재등록하지 않는다.
