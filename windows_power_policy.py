"""Persistent UI-controlled policy for automatic Windows candidate hibernation."""
from pathlib import Path
import json
from job_queue import atomic_write_json


def get_policy(root):
    path = Path(root) / 'runtime/h3/windows_power_policy.json'
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return {'auto_hibernate_enabled': True}
    except (OSError, ValueError):
        return {'auto_hibernate_enabled': False, 'error': '자동 종료 설정을 읽지 못해 자동 최대절전을 중단했습니다.'}
    if not isinstance(data, dict) or not isinstance(data.get('auto_hibernate_enabled'), bool):
        return {'auto_hibernate_enabled': False, 'error': '자동 종료 설정 형식이 올바르지 않습니다.'}
    return {'auto_hibernate_enabled': data['auto_hibernate_enabled']}


def set_policy(root, enabled):
    if not isinstance(enabled, bool):
        raise ValueError('auto_hibernate_enabled는 true 또는 false여야 합니다.')
    data = {'auto_hibernate_enabled': enabled}
    atomic_write_json(Path(root) / 'runtime/h3/windows_power_policy.json', data)
    return data
