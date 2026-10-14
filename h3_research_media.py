"""Bound provider image count while preserving frame provenance in labeled sheets."""
import math
from pathlib import Path

MAX_ATTACHMENTS = 40
MAX_TILES = 8


def prepare_media(media, output_dir):
    media = [dict(m) for m in media]
    if len(media) <= MAX_ATTACHMENTS:
        return media
    frames = [m for m in media if m.get('kind') in {'source','candidate','previous_accepted_tail'}]
    refs = [m for m in media if m.get('kind') not in {'source','candidate','previous_accepted_tail'}]
    slots = MAX_ATTACHMENTS - len(refs)
    if slots <= 0 or not frames:
        raise ValueError('이미지 한도: 참조/개별 이미지가 너무 많습니다. 구간을 나누고 새 독립 요청으로 분석하세요.')
    per_sheet = max(2, math.ceil(len(frames) / slots))
    if per_sheet > MAX_TILES:
        raise ValueError('이미지 한도: 프레임을 버리지 않고 처리하려면 분석 시간 구간을 나누세요.')
    from PIL import Image, ImageDraw, ImageOps
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    attachments = []
    for offset in range(0, len(frames), per_sheet):
        group = frames[offset:offset+per_sheet]
        columns = min(2, len(group))
        # Keep each extracted 640px frame at its original display scale.
        canvas = Image.new('RGB', (columns*640, math.ceil(len(group)/columns)*680), '#181818')
        draw = ImageDraw.Draw(canvas)
        tiles = []
        for n, item in enumerate(group):
            with Image.open(item['path']) as source:
                source = ImageOps.exif_transpose(source).convert('RGB')
                fitted = ImageOps.contain(source, (640, 640))
                x, y = n % columns * 640, n // columns * 680
                canvas.paste(fitted, (x, y))
            label = f"tile {n+1} | {item.get('kind')} | t={item.get('time')} | source_t={item.get('absolute_time', 'NA')}"
            draw.text((x+4,y+645),label,fill='white')
            tiles.append({'tile':n+1,'row':n//columns+1,'column':n%columns+1,**item})
        path = output_dir / f'sheet_{len(attachments)+1:03d}.jpg'
        canvas.save(path, quality=92)
        attachments.append({'path':str(path),'kind':'labeled_frame_sheet','tiles':tiles})
    return attachments + refs
