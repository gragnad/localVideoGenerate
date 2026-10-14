"""Server-owned, editable frame annotations and immutable composite revisions."""
from __future__ import annotations

import fcntl
import hashlib
import math
import re
import uuid
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw
import h3_frame_export
from job_queue import atomic_write_json, now_iso, read_json


def context(root, data):
    job = str(data.get('job_id', ''))
    tag = str(data.get('tag', ''))
    filename = str(data.get('filename', ''))
    original = h3_frame_export.export_file(root, job, tag, filename)
    manifest = read_json(original.parent / 'frames.json', {})
    frame = next((f for f in manifest.get('frames', []) if f['filename'] == filename), None)
    if frame is None:
        raise ValueError('검수할 원본 프레임을 찾을 수 없습니다.')
    source = original.parent / (frame.get('labeled_filename') or filename)
    # Include export identity so a replaced source never inherits unrelated marks.
    identity = f"{manifest.get('source_video_size')}:{manifest.get('source_video_mtime_ns')}"
    directory = root / 'runtime/h3/frame_annotations' / job / tag / filename / hashlib.sha256(identity.encode()).hexdigest()[:16]
    return directory, source, manifest, frame


def public_record(record, data):
    out = {k: v for k, v in record.items() if k != 'image_path'}
    if out.get('revision'):
        base = '/api/h3/jobs/' + quote(data['job_id'], safe='') + '/frames/' + quote(data['tag'], safe='') + '/' + quote(data['filename'], safe='') + '/annotation'
        out['image_url'] = base + '/image?revision=' + out['revision']
    return out


def load(root, data):
    directory, source, manifest, frame = context(root, data)
    record = read_json(directory / 'latest.json', None)
    if record is None:
        record = {'revision': None, 'strokes': [], 'saved_at': None}
    return public_record(record, data)


def validate(strokes):
    if not isinstance(strokes, list) or len(strokes) > 3000:
        raise ValueError('그리기 데이터는 최대 3000개의 선이어야 합니다.')
    total = 0
    cleaned = []
    for stroke in strokes:
        if not isinstance(stroke, dict) or not re.fullmatch(r'#[0-9a-fA-F]{6}', str(stroke.get('color', ''))):
            raise ValueError('허용되지 않는 펜 색상입니다.')
        width = stroke.get('width')
        if isinstance(width, bool) or not isinstance(width, (int, float)) or not math.isfinite(width) or not .0005 <= width <= .08:
            raise ValueError('허용되지 않는 펜 굵기입니다.')
        points = stroke.get('points')
        if not isinstance(points, list) or not points:
            raise ValueError('선 좌표가 필요합니다.')
        total += len(points)
        if total > 100000:
            raise ValueError('그리기 좌표가 너무 많습니다.')
        for point in points:
            if not isinstance(point, list) or len(point) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in point):
                raise ValueError('프레임 밖이거나 유효하지 않은 좌표입니다.')
        cleaned.append({'color': stroke['color'], 'width': width, 'points': points})
    return cleaned


def save(root, data):
    strokes = validate(data.get('strokes'))
    directory, source, manifest, frame = context(root, data)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = read_json(directory / 'latest.json', {})
        if data.get('expected_revision') != previous.get('revision'):
            return {'conflict': True, 'error': '다른 화면에서 수정되었습니다. 현재 표시를 유지한 채 서버 기록을 다시 확인하세요.'}
        revision = uuid.uuid4().hex
        with Image.open(source) as source_image:
            image = source_image.convert('RGB')
        draw = ImageDraw.Draw(image)
        w, h = image.size
        for stroke in strokes:
            points = [(round(x * (w - 1)), round(y * (h - 1))) for x, y in stroke['points']]
            width = max(1, round(stroke['width'] * w))
            if len(points) > 1:
                draw.line(points, fill=stroke['color'], width=width, joint='curve')
            radius = width / 2
            for x, y in points:
                draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=stroke['color'])
        image_path = directory / f'{revision}.png'
        image.save(image_path, 'PNG')
        record = {'revision': revision, 'strokes': strokes, 'saved_at': now_iso(),
                  'image_path': str(image_path), 'job_id': manifest['job_id'],
                  'source_project_id': manifest.get('source_project_id'),
                  'source_scene_id': manifest.get('source_scene_id'),
                  'source_clip_id': manifest.get('source_clip_id'),
                  'candidate_index': manifest.get('candidate_index'),
                  'filename': frame['filename'], 'frame_index': frame['frame_index'],
                  'time_seconds': frame['time_seconds'], 'width': w, 'height': h}
        atomic_write_json(directory / f'{revision}.json', record)
        atomic_write_json(directory / 'latest.json', record)
    return public_record(record, data)


def image_file(root, data):
    directory, _, _, _ = context(root, data)
    revision = str(data.get('revision', ''))
    if not re.fullmatch(r'[a-f0-9]{32}', revision):
        raise ValueError('유효하지 않은 검수 revision입니다.')
    record = read_json(directory / f'{revision}.json', {})
    image = directory / f'{revision}.png'
    if record.get('revision') != revision or not image.is_file():
        raise ValueError('저장된 검수 이미지를 찾을 수 없습니다.')
    return {'path': str(image)}


def listing(root, data):
    job = str(data.get('job_id', ''))
    tag = str(data.get('tag', ''))
    # Validate the directory even when no frame has been annotated.
    import h3_queue
    job = h3_queue._safe_id(job, '작업 ID')
    if tag not in {'0p25s', '0p5s', '1s'}:
        raise ValueError('허용되지 않는 프레임 간격입니다.')
    manifest = read_json(h3_frame_export.exports_root(root) / job / tag / 'frames.json', {})
    saved = []
    for frame in manifest.get('frames', []):
        item = {**data, 'filename': frame['filename']}
        directory, _, _, _ = context(root, item)
        if (directory / 'latest.json').is_file():
            saved.append(frame['filename'])
    return {'saved': saved}
