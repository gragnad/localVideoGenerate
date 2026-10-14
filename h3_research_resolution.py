"""Inspect actual R2V dimensions before submission, without submitting a job."""

def verify_workflow_resolution(workflow, width, height):
    def literal(value):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        if isinstance(value, list) and len(value) == 2 and value[1] == 0:
            node = workflow.get(str(value[0]), {})
            if node.get('class_type') in {'easy int', 'PrimitiveInt'}:
                return literal(node.get('inputs', {}).get('value'))
        raise ValueError('해상도 연결값을 확인할 수 없어 제출을 중단합니다.')
    nodes = [n for n in workflow.values() if n.get('class_type') == 'MiniMaxH3ReferenceToVideo']
    if not nodes:
        raise ValueError('R2V 해상도 노드가 없습니다.')
    for node in nodes:
        inputs = node['inputs']
        actual = (literal(inputs.get('width')), literal(inputs.get('height')))
        if actual != (width, height):
            raise ValueError(f'워크플로우 해상도 불일치: {actual}, 요청: {(width, height)}')
    return {'width': width, 'height': height, 'nodes_checked': len(nodes)}
