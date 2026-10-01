"""Validate the frozen content foundation without loading numerical data."""
import json
import re

from backend import create_app
from backend.registry.content_bindings import resolve_evidence, resolve_target
from backend.registry.content_registry import load_foundation, scene_requests


def audit():
    mechanism, scenes = load_foundation()
    app = create_app(case8_adapter=None, allocation_adapter=None,
                     spectral_adapter=None, cylinder_adapter=None)
    catalog = {operation.operation_id: operation for operation in app.extensions['operation_catalog'].operations}
    bindings = {resolve_evidence(ref) for ref in mechanism.evidence_refs}
    target_count = 0
    for scene in scenes.items:
        bindings.update(scene_requests(scene.scene_id))
        bindings.update(resolve_evidence(ref) for ref in scene.evidence_refs)
        for target in scene.targets:
            target_count += len(target.result_ids)
            bindings.update(resolve_target(target))
    for binding in bindings:
        operation = catalog[binding.operation_id]
        pattern = re.sub(r'\{[^}]+\}', '[^/]+', operation.path)
        if operation.method != 'GET' or not re.fullmatch(pattern, binding.path):
            raise ValueError(f'Content binding does not match registered operation: {binding.operation_id}')
    return {
        'status': 'PASS', 'mechanism_origin': mechanism.data_origin,
        'supported_states': mechanism.supported_states,
        'scene_count': len(scenes.items), 'scene_ids': [scene.scene_id for scene in scenes.items],
        'real_targets': target_count, 'registered_api_bindings': len(bindings),
        'near1d_numerical_scan': 'MISSING', 'gap_code': 'NO_AUTHORITATIVE_NEAR1D_RAW_SCAN',
        'numerical_data_duplicated': False, 'numerical_reads': 0, 'cfd_runs_started': 0,
    }


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
