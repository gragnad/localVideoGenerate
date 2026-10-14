from __future__ import annotations

"""MiniMax H3 full-reference prompt renderer and validator.

The contract deliberately knows nothing about a specific episode.  Narrative
authoring happens in a structured clip spec; this module only renders and
validates the official six-section prompt format.
"""

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable


SECTION_NAMES = (
    "subject_definitions",
    "summary",
    "retention_analysis",
    "detailed_description",
    "overall_soundscape",
    "non_diegetic_music",
)
LEGACY_CONTRACT_VERSION = "h3_ref_minimal_v1"
GRID_STORYBOARD_CONTRACT_VERSION = "h3_ref_storyboard_v2"
GRID_FREE_STORYBOARD_CONTRACT_VERSION = "h3_ref_storyboard_v3"
CONTRACT_VERSION = "h3_ref_storyboard_v4"
PASSTHROUGH_CONTRACT_VERSION = "h3_user_supplied_passthrough_v1"
PASSTHROUGH_CONTRACT_VERSION_V2 = "h3_user_supplied_passthrough_v2"
PASSTHROUGH_CONTRACT_VERSION_V3 = "h3_user_supplied_passthrough_v3"
PASSTHROUGH_CONTRACT_VERSION_V4 = "h3_user_supplied_passthrough_v4"
PASSTHROUGH_CONTRACT_VERSION_V5 = "h3_user_supplied_passthrough_v5"
PASSTHROUGH_CONTRACT_VERSIONS = frozenset({
    PASSTHROUGH_CONTRACT_VERSION,
    PASSTHROUGH_CONTRACT_VERSION_V2,
    PASSTHROUGH_CONTRACT_VERSION_V3,
    PASSTHROUGH_CONTRACT_VERSION_V4,
    PASSTHROUGH_CONTRACT_VERSION_V5,
})
SUPPORTED_CONTRACT_VERSIONS = frozenset({
    LEGACY_CONTRACT_VERSION,
    GRID_STORYBOARD_CONTRACT_VERSION,
    GRID_FREE_STORYBOARD_CONTRACT_VERSION,
    CONTRACT_VERSION,
    *PASSTHROUGH_CONTRACT_VERSIONS,
})
RETENTION_MARKERS = {
    "fully_preserved",
    "partially_preserved",
    "attribute_transfer",
    "weak_reference",
}
SECTION_RE = re.compile(
    rf"^({'|'.join(SECTION_NAMES)}):[ \t]*$", re.MULTILINE
)
SUBJECT_DEFINITION_RE = re.compile(
    r"^<Subject (\d+)>\s*(?::|is)\s*(.+)$", re.MULTILINE
)
PICTURE_DEFINITION_RE = re.compile(
    r"^<Picture (\d+)>\s*(?::|is)\s*(.+)$", re.MULTILINE
)
PICTURE_REFERENCE_RE = re.compile(r"<Picture (\d+)>")
RETENTION_RE = re.compile(
    r"^<(Subject|Picture) (\d+)>\s*\(([^\n]+)\):\s*([a-z_]+)\s+-\s+(.+)$",
    re.MULTILINE,
)
SHOT_RE = re.compile(
    r"^\[Shot (\d+)\](?: At (\d{2}):(\d{2}\.\d{3}),)?[ \t]*(.*?)"
    r"(?=^\[Shot \d+\]|\Z)",
    re.MULTILINE | re.DOTALL,
)
DIALOGUE_RE = re.compile(r"<d>\[([^\]]+)]\s*(.*?)</d>", re.DOTALL)
SPEAKER_RE = re.compile(r"<Subject \d+>\s*\(S\d+\)")
LEGACY_INLINE_LABEL_RE = re.compile(r"\b(?:CAMERA|ACTION):")
ABSTRACT_STYLE_RE = re.compile(
    r"\b(?:premium contemporary animated-feature rendering|"
    r"premium animated-feature rendering)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    code: str
    message: str
    shot: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationReport:
    errors: tuple[ValidationIssue, ...]
    warnings: tuple[ValidationIssue, ...]
    section_names: tuple[str, ...]
    shot_count: int

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [issue.as_dict() for issue in self.errors],
            "warnings": [issue.as_dict() for issue in self.warnings],
            "section_names": list(self.section_names),
            "shot_count": self.shot_count,
        }


class PromptContractError(ValueError):
    def __init__(self, report: ValidationReport):
        self.report = report
        message = "; ".join(issue.message for issue in report.errors)
        super().__init__(message or "H3 prompt contract validation failed")


def _issue(
    items: list[ValidationIssue],
    code: str,
    message: str,
    *,
    level: str = "error",
    shot: int | None = None,
) -> None:
    items.append(ValidationIssue(level=level, code=code, message=message, shot=shot))


def _sections(prompt: str) -> tuple[dict[str, str], tuple[str, ...]]:
    matches = list(SECTION_RE.finditer(prompt))
    names = tuple(match.group(1) for match in matches)
    if names != SECTION_NAMES:
        return {}, names
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(prompt)
        sections[match.group(1)] = prompt[match.end():end].strip()
    return sections, names


def _subject_alias(definition: str) -> str:
    alias = re.split(
        r"\s+(?:from|in)\s+<Picture \d+>|[;,]",
        definition,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return alias.strip().rstrip(".")


def _timestamp(minutes: str | None, seconds: str | None) -> float | None:
    if minutes is None or seconds is None:
        return None
    return int(minutes) * 60 + float(seconds)


def max_shots_for_duration(duration_seconds: float) -> int:
    """Return a readability budget, not a request-format limitation."""
    if duration_seconds <= 3:
        return 1
    if duration_seconds <= 6:
        return 2
    if duration_seconds < 6.5:
        return 3
    return 4


def _banned_directive(line: str) -> bool:
    value = line.strip()
    upper = value.upper()
    if not value:
        return False
    return (
        upper.startswith("ACTION / VFX")
        or upper.startswith("CAMERA PLAN")
        or upper.startswith("INDEPENDENT ")
        or upper.startswith("END CAMERA PLAN")
        or (" LOCK" in upper and upper.endswith(":"))
        or (upper.startswith("END ") and "LOCK" in upper)
    )


def _alias_position(text: str, alias: str) -> int | None:
    if not alias:
        return None
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_]){re.escape(alias)}(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    return match.start() if match else None


def _validate_first_subject_mentions(
    body: str,
    definitions: dict[int, str],
    errors: list[ValidationIssue],
    shot_number: int,
) -> None:
    visible_text = DIALOGUE_RE.sub("", body)
    for subject_id, definition in definitions.items():
        alias = _subject_alias(definition)
        alias_position = _alias_position(visible_text, alias)
        if alias_position is None:
            continue
        label_position = visible_text.find(f"<Subject {subject_id}>")
        if label_position < 0:
            _issue(
                errors,
                "subject_name_without_label",
                f"[Shot {shot_number}]에서 {alias} 이름을 사용했지만 "
                f"<Subject {subject_id}> 라벨이 없습니다.",
                shot=shot_number,
            )
        elif alias_position < label_position:
            _issue(
                errors,
                "subject_label_after_name",
                f"[Shot {shot_number}]의 첫 지칭은 {alias} 이름보다 "
                f"<Subject {subject_id}> 라벨이 먼저여야 합니다.",
                shot=shot_number,
            )


def _validate_dialogue(
    body: str,
    errors: list[ValidationIssue],
    shot_number: int,
) -> None:
    previous_end = 0
    for dialogue in DIALOGUE_RE.finditer(body):
        lead = body[previous_end:dialogue.start()]
        if not SPEAKER_RE.search(lead):
            _issue(
                errors,
                "dialogue_speaker_missing",
                f"[Shot {shot_number}]의 각 발화 앞에는 "
                "<Subject N> (Sx) 화자 표기가 필요합니다.",
                shot=shot_number,
            )
        if not dialogue.group(1).strip():
            _issue(
                errors,
                "dialogue_language_missing",
                f"[Shot {shot_number}] 대사 언어 태그가 비어 있습니다.",
                shot=shot_number,
            )
        previous_end = dialogue.end()


def validate_prompt(
    prompt: str,
    *,
    duration_seconds: float | None = None,
    require_shot_timestamps: bool = True,
    allow_four_shots: bool = False,
    allow_six_shots: bool = False,
) -> ValidationReport:
    prompt = str(prompt or "").strip()
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    sections, names = _sections(prompt)
    if names != SECTION_NAMES:
        _issue(
            errors,
            "section_contract",
            "프롬프트는 공식 6개 섹션을 정확한 순서로 한 번씩 가져야 합니다: "
            + ", ".join(SECTION_NAMES),
        )
        return ValidationReport(tuple(errors), tuple(warnings), names, 0)

    if not sections["summary"].startswith("[reference generation] "):
        _issue(
            errors,
            "summary_prefix",
            "summary는 [reference generation] 접두사로 시작해야 합니다.",
        )

    definition_rows = list(SUBJECT_DEFINITION_RE.finditer(sections["subject_definitions"]))
    definitions = {
        int(match.group(1)): match.group(2).strip() for match in definition_rows
    }
    expected_subjects = list(range(1, len(definitions) + 1))
    if list(definitions) != expected_subjects or not definitions:
        _issue(
            errors,
            "subject_sequence",
            "subject_definitions는 <Subject 1>부터 빈 번호 없이 정의해야 합니다.",
        )
    subject_picture_ids: set[int] = set()
    for subject_id, definition in definitions.items():
        picture_ids = [int(value) for value in PICTURE_REFERENCE_RE.findall(definition)]
        if not picture_ids:
            _issue(
                errors,
                "subject_picture_missing",
                f"<Subject {subject_id}> 정의에는 하나 이상의 Picture 참조가 필요합니다.",
            )
        subject_picture_ids.update(picture_ids)

    picture_rows = list(PICTURE_DEFINITION_RE.finditer(sections["subject_definitions"]))
    pictures = {int(match.group(1)): match.group(2).strip() for match in picture_rows}
    if len(pictures) != len(picture_rows):
        _issue(errors, "picture_duplicate", "독립 Picture 정의 번호는 중복될 수 없습니다.")
    definition_lines = [
        line.strip()
        for line in sections["subject_definitions"].splitlines()
        if line.strip()
    ]
    if len(definition_lines) != len(definition_rows) + len(picture_rows):
        _issue(
            errors,
            "definition_line_contract",
            "subject_definitions의 각 줄은 <Subject N> 또는 <Picture N> 정의여야 합니다.",
        )
    known_picture_ids = subject_picture_ids | set(pictures)
    referenced_picture_ids = {
        int(value) for value in PICTURE_REFERENCE_RE.findall(prompt)
    }
    unknown_picture_ids = sorted(referenced_picture_ids - known_picture_ids)
    if unknown_picture_ids:
        _issue(
            errors,
            "undefined_picture_reference",
            "정의되지 않은 Picture 참조가 있습니다: "
            + ", ".join(str(value) for value in unknown_picture_ids),
        )

    retention_rows = list(RETENTION_RE.finditer(sections["retention_analysis"]))
    retention_labels = [
        (match.group(1), int(match.group(2))) for match in retention_rows
    ]
    expected_labels = [
        *(('Subject', subject_id) for subject_id in expected_subjects),
        *(('Picture', picture_id) for picture_id in pictures),
    ]
    if retention_labels != expected_labels:
        _issue(
            errors,
            "retention_labels",
            "retention_analysis는 정의된 Subject와 독립 Picture를 같은 순서로 한 번씩 기록해야 합니다.",
        )
    for match in retention_rows:
        if match.group(4) not in RETENTION_MARKERS:
            _issue(
                errors,
                "retention_marker",
                f"<{match.group(1)} {match.group(2)}>의 retention marker가 공식 값이 아닙니다.",
            )

    detail = sections["detailed_description"]
    first_shot = re.search(r"^\[Shot 1]", detail, re.MULTILINE)
    if not first_shot:
        _issue(errors, "shot_one_missing", "detailed_description에는 [Shot 1]이 필요합니다.")
        return ValidationReport(tuple(errors), tuple(warnings), names, 0)
    preamble = detail[:first_shot.start()].strip()
    preamble_lines = [line.strip() for line in preamble.splitlines() if line.strip()]
    if len(preamble_lines) > 2:
        _issue(
            errors,
            "style_preamble_too_long",
            "detailed_description의 Shot 전 문장은 최대 2개입니다.",
        )
    for line in detail.splitlines():
        if _banned_directive(line):
            _issue(
                errors,
                "legacy_directive_block",
                f"레거시 제작 지시 블록을 사용할 수 없습니다: {line.strip()}",
            )
    if LEGACY_INLINE_LABEL_RE.search(detail):
        _issue(
            errors,
            "legacy_camera_action_labels",
            "CAMERA:/ACTION: 라벨 대신 각 Shot을 자연어 재생 순서로 작성해야 합니다.",
        )
    if ABSTRACT_STYLE_RE.search(preamble):
        _issue(
            warnings,
            "abstract_style_boilerplate",
            "추상적인 Premium 렌더링 문구보다 실제 조명과 재질을 구체적으로 작성하세요.",
            level="warning",
        )

    shot_rows = list(SHOT_RE.finditer(detail[first_shot.start():]))
    shot_numbers = [int(match.group(1)) for match in shot_rows]
    if shot_numbers != list(range(1, len(shot_rows) + 1)):
        _issue(errors, "shot_sequence", "Shot 번호는 1부터 빈 번호 없이 증가해야 합니다.")
    previous_time = -1.0
    for index, match in enumerate(shot_rows):
        shot_number = int(match.group(1))
        start = _timestamp(match.group(2), match.group(3))
        body = match.group(4).strip()
        if not body:
            _issue(errors, "empty_shot", f"[Shot {shot_number}] 내용이 비어 있습니다.", shot=shot_number)
            continue
        if index == 0 and start is not None:
            _issue(errors, "shot_one_timestamp", "[Shot 1]에는 시작 시간이 없어야 합니다.", shot=1)
        if index > 0 and start is None and require_shot_timestamps:
            _issue(
                errors,
                "shot_timestamp_missing",
                f"[Shot {shot_number}]에는 At MM:SS.mmm 시간이 필요합니다.",
                shot=shot_number,
            )
        if start is not None:
            if start <= previous_time:
                _issue(
                    errors,
                    "shot_timestamp_order",
                    "Shot 시작 시간은 엄격히 증가해야 합니다.",
                    shot=shot_number,
                )
            if duration_seconds is not None and start >= duration_seconds:
                _issue(
                    errors,
                    "shot_timestamp_outside_duration",
                    f"[Shot {shot_number}] 시작 시간이 클립 길이 밖입니다.",
                    shot=shot_number,
                )
            previous_time = start
        _validate_first_subject_mentions(body, definitions, errors, shot_number)
        _validate_dialogue(body, errors, shot_number)

    if duration_seconds is not None:
        if duration_seconds <= 0 or duration_seconds > 15:
            _issue(errors, "duration_range", "클립 길이는 0초 초과 15초 이하여야 합니다.")
        budget = max_shots_for_duration(duration_seconds)
        if not require_shot_timestamps:
            budget = max(budget, 3)
        if allow_four_shots:
            budget = max(budget, 4)
        if allow_six_shots:
            budget = max(budget, 6)
        if len(shot_rows) > budget:
            _issue(
                errors,
                "shot_budget",
                f"{duration_seconds:g}초 클립은 최대 {budget}개 Shot만 허용합니다.",
            )
        if duration_seconds < 4:
            _issue(
                warnings,
                "official_api_duration",
                "공식 MiniMax H3 API 생성 길이는 4초부터입니다. 로컬 워크플로 지원을 확인하세요.",
                level="warning",
            )

    word_count = len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", detail))
    if word_count > 500:
        _issue(
            warnings,
            "detail_over_500_words",
            f"detailed_description이 {word_count}단어입니다. 중복보다 실제 Shot 정보를 우선하세요.",
            level="warning",
        )
    for name in ("overall_soundscape", "non_diegetic_music"):
        if not sections[name]:
            _issue(errors, f"{name}_empty", f"{name} 섹션은 비워둘 수 없습니다.")

    return ValidationReport(tuple(errors), tuple(warnings), names, len(shot_rows))


def assert_valid_prompt(
    prompt: str,
    *,
    duration_seconds: float | None = None,
    require_shot_timestamps: bool = True,
    allow_four_shots: bool = False,
    allow_six_shots: bool = False,
) -> str:
    report = validate_prompt(
        prompt,
        duration_seconds=duration_seconds,
        require_shot_timestamps=require_shot_timestamps,
        allow_four_shots=allow_four_shots,
        allow_six_shots=allow_six_shots,
    )
    if not report.valid:
        raise PromptContractError(report)
    return prompt


def _with_period(value: str) -> str:
    value = str(value or "").strip()
    if value and value[-1] not in ".?!":
        value += "."
    return value


def _format_time(value: float) -> str:
    minutes = int(value // 60)
    seconds = value - minutes * 60
    return f"{minutes:02d}:{seconds:06.3f}"


def _require_list(spec: dict[str, Any], key: str) -> list[Any]:
    value = spec.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{key}는 비어 있지 않은 배열이어야 합니다.")
    return value


def render_prompt(spec: dict[str, Any]) -> str:
    """Render one prompt from a structured, episode-independent clip spec."""
    if not isinstance(spec, dict):
        raise ValueError("H3 prompt spec은 JSON 객체여야 합니다.")
    duration = float(spec.get("duration_seconds") or 0)
    subjects = _require_list(spec, "subjects")
    pictures = spec.get("pictures") or []
    if not isinstance(pictures, list):
        raise ValueError("pictures는 배열이어야 합니다.")
    retention = _require_list(spec, "retention_analysis")
    shots = _require_list(spec, "shots")

    subject_lines: list[str] = []
    for expected_id, row in enumerate(subjects, start=1):
        if not isinstance(row, dict):
            raise ValueError("subjects 항목은 JSON 객체여야 합니다.")
        subject_id = int(row.get("subject_id") or 0)
        raw_picture_ids = row.get("picture_ids")
        if raw_picture_ids is None:
            raw_picture_ids = [row.get("picture_id")]
        if not isinstance(raw_picture_ids, list):
            raise ValueError("각 Subject의 picture_ids는 배열이어야 합니다.")
        picture_ids = [int(value or 0) for value in raw_picture_ids]
        if subject_id != expected_id:
            raise ValueError("Subject 번호는 1부터 빈 번호 없이 이어져야 합니다.")
        if not picture_ids or any(value <= 0 for value in picture_ids):
            raise ValueError("각 Subject에는 하나 이상의 올바른 Picture 번호가 필요합니다.")
        if len(set(picture_ids)) != len(picture_ids):
            raise ValueError("한 Subject의 Picture 번호는 중복될 수 없습니다.")
        name = str(row.get("name") or "").strip()
        description = _with_period(str(row.get("description") or ""))
        if not name or not description:
            raise ValueError("각 Subject에는 name과 description이 필요합니다.")
        picture_text = " and ".join(f"<Picture {value}>" for value in picture_ids)
        subject_lines.append(
            f"<Subject {subject_id}> is {name} from {picture_text}. {description}"
        )

    picture_lines: list[str] = []
    seen_picture_ids: set[int] = set()
    for row in pictures:
        if not isinstance(row, dict):
            raise ValueError("pictures 항목은 JSON 객체여야 합니다.")
        picture_id = int(row.get("picture_id") or 0)
        if picture_id <= 0 or picture_id in seen_picture_ids:
            raise ValueError("독립 Picture 번호는 중복 없는 양수여야 합니다.")
        seen_picture_ids.add(picture_id)
        name = str(row.get("name") or "").strip()
        description = _with_period(str(row.get("description") or ""))
        if not name or not description:
            raise ValueError("각 독립 Picture에는 name과 description이 필요합니다.")
        picture_lines.append(f"<Picture {picture_id}> is {name}. {description}")

    summary = str(spec.get("summary") or "").strip()
    if not summary:
        raise ValueError("summary가 필요합니다.")
    if not summary.startswith("[reference generation] "):
        summary = "[reference generation] " + summary

    retention_lines: list[str] = []
    expected_retention_labels = [
        *(('Subject', int(row.get('subject_id') or 0)) for row in subjects),
        *(('Picture', int(row.get('picture_id') or 0)) for row in pictures),
    ]
    for expected_label, row in zip(expected_retention_labels, retention, strict=True):
        if not isinstance(row, dict):
            raise ValueError("retention_analysis 항목은 JSON 객체여야 합니다.")
        if row.get("subject_id") not in (None, ""):
            actual_label = ("Subject", int(row.get("subject_id") or 0))
        elif row.get("picture_id") not in (None, ""):
            actual_label = ("Picture", int(row.get("picture_id") or 0))
        else:
            raise ValueError("retention_analysis에는 subject_id 또는 picture_id가 필요합니다.")
        if actual_label != expected_label:
            raise ValueError("retention_analysis는 Subject 다음 독립 Picture 순서로 작성해야 합니다.")
        marker = str(row.get("marker") or "")
        if marker not in RETENTION_MARKERS:
            raise ValueError(f"지원하지 않는 retention marker입니다: {marker}")
        appearances = [int(value) for value in row.get("shots") or []]
        if not appearances:
            raise ValueError("retention_analysis의 shots가 비어 있습니다.")
        shot_text = ", ".join(f"[Shot {value}]" for value in appearances)
        description = _with_period(str(row.get("description") or ""))
        retention_lines.append(
            f"<{actual_label[0]} {actual_label[1]}> (appears in {shot_text}): "
            f"{marker} - {description}"
        )
    if len(retention) != len(expected_retention_labels):
        raise ValueError("retention_analysis는 모든 Subject와 독립 Picture를 한 번씩 포함해야 합니다.")

    style = spec.get("style_opening") or []
    if not isinstance(style, list) or len(style) > 2:
        raise ValueError("style_opening은 최대 2개 문장 배열이어야 합니다.")
    style_lines = [_with_period(str(value or "")) for value in style if str(value or "").strip()]

    allow_untimed_shots = bool(spec.get("allow_untimed_shots"))
    shot_lines: list[str] = []
    for expected_number, row in enumerate(shots, start=1):
        if not isinstance(row, dict) or int(row.get("number") or 0) != expected_number:
            raise ValueError("shots는 Shot 1부터 순서대로 작성해야 합니다.")
        description = str(row.get("description") or "").strip()
        if not description:
            raise ValueError(f"Shot {expected_number} description이 비어 있습니다.")
        if expected_number == 1:
            if row.get("start_seconds") not in (None, ""):
                raise ValueError("Shot 1에는 start_seconds를 지정하지 않습니다.")
            shot_lines.append(f"[Shot 1] {description}")
        else:
            if allow_untimed_shots and row.get("start_seconds") in (None, ""):
                shot_lines.append(f"[Shot {expected_number}] {description}")
            else:
                start = float(row.get("start_seconds"))
                shot_lines.append(
                    f"[Shot {expected_number}] At {_format_time(start)}, {description}"
                )

    soundscape = str(spec.get("overall_soundscape") or "").strip()
    music = str(spec.get("non_diegetic_music") or "").strip()
    if not soundscape or not music:
        raise ValueError("overall_soundscape와 non_diegetic_music이 필요합니다.")

    detail_blocks: Iterable[str] = [*style_lines, *shot_lines]
    prompt = (
        "subject_definitions:\n"
        + "\n".join([*subject_lines, *picture_lines])
        + "\n\nsummary:\n"
        + summary
        + "\n\nretention_analysis:\n"
        + "\n".join(retention_lines)
        + "\n\ndetailed_description:\n"
        + "\n\n".join(detail_blocks)
        + "\n\noverall_soundscape:\n"
        + soundscape
        + "\n\nnon_diegetic_music:\n"
        + music
    )
    return assert_valid_prompt(
        prompt,
        duration_seconds=duration,
        require_shot_timestamps=not allow_untimed_shots,
        allow_four_shots=bool(spec.get("allow_four_shots")),
        allow_six_shots=bool(spec.get("allow_six_shots")),
    )
