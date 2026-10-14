"""Narrow, backed-up H3 semantic-reference patch. Dry-run unless --apply.

Run with the Windows ComfyUI Python, then restart the idle render process.
This script never submits jobs, downloads models, or restarts services.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.request import urlopen


def transform(source):
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef)
               and n.name == 'MiniMaxH3ReferenceToVideo')
    lines = source.splitlines(keepends=True)
    block = ''.join(lines[cls.lineno - 1:cls.end_lineno])
    if 'semantic_ref_indexes' in block:
        raise ValueError('Existing semantic-reference customization found; review manually.')
    def once(old, new):
        nonlocal block
        if block.count(old) != 1:
            raise ValueError('Unexpected upstream source; refusing to modify: ' + old)
        block = block.replace(old, new, 1)
    once('                io.Autogrow.Input("ref_images",',
         '                io.String.Input("semantic_ref_indexes", default="", optional=True,\n'
         '                    tooltip="1-based Picture indexes: text encoder only, excluded from visual reference latents."),\n'
         '                io.Autogrow.Input("ref_images",')
    once('ref_image_size="match",', 'ref_image_size="match", semantic_ref_indexes="",')
    once('        for img in (ref_images or {}).values():',
         '        try:\n'
         '            semantic_indexes = {int(v.strip()) for v in str(semantic_ref_indexes or "").split(",") if v.strip()}\n'
         '        except ValueError as exc:\n'
         '            raise ValueError("semantic_ref_indexes must contain 1-based Picture numbers") from exc\n'
         '        if any(i < 1 or i > 9 for i in semantic_indexes):\n'
         '            raise ValueError("semantic_ref_indexes must contain Picture numbers 1 to 9")\n'
         '        picture_index = 0\n'
         '        for img in (ref_images or {}).values():')
    once('            h, w = img.shape[1], img.shape[2]',
         '            picture_index += 1\n            h, w = img.shape[1], img.shape[2]')
    start = block.index('        for img in (ref_images or {}).values():')
    end = block.index('        ref_video_audios =', start)
    image_loop = block[start:end]
    if image_loop.count('if vae is not None:') != 1:
        raise ValueError('Unexpected image VAE branch; refusing to modify.')
    image_loop = image_loop.replace('if vae is not None:', 'if vae is not None and picture_index not in semantic_indexes:')
    image_loop += ('        if semantic_indexes - set(range(1, picture_index + 1)):\n'
                   '            raise ValueError("semantic_ref_indexes contains missing Picture indexes")\n\n')
    block = block[:start] + image_loop + block[end:]
    result = ''.join(lines[:cls.lineno - 1]) + block + ''.join(lines[cls.end_lineno:])
    ast.parse(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comfy-root', type=Path, required=True)
    parser.add_argument('--url', default='http://100.78.202.37:8189')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    target = args.comfy_root.resolve() / 'comfy_extras' / 'nodes_minimax_h3.py'
    raw = target.read_bytes()
    source = raw.decode('utf-8')
    result = transform(source)
    digest = hashlib.sha256(raw).hexdigest()
    print('Validated target:', target, '\nOriginal SHA256:', digest)
    if not args.apply:
        print('Dry-run passed. No files changed. Use --apply after review.')
        return
    with urlopen(args.url.rstrip('/') + '/queue', timeout=10) as response:
        queue = json.load(response)
    if queue.get('queue_running') or queue.get('queue_pending'):
        raise RuntimeError('Queue is not empty. No files changed.')
    backup = target.with_name(target.name + '.before-semantic-' + digest[:12])
    if backup.exists() and backup.read_bytes() != raw:
        raise RuntimeError('Backup conflict. No files changed.')
    if not backup.exists():
        shutil.copy2(target, backup)
    if target.read_bytes() != raw:
        raise RuntimeError('Source changed during review. No patch applied.')
    target.write_bytes(result.encode('utf-8'))
    print('Patched; backup:', backup)
    print('Restart only the idle Windows render process, then verify object_info. No jobs submitted.')


if __name__ == '__main__':
    main()
