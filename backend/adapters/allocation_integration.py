"""Read-only dispatch of the independently frozen face and cell allocations.

Transport metadata keeps canonical domains, definitions and masks. Gate sources
are observed before and after each read; neither scientific package is changed.
"""
from datetime import datetime, timezone
import hashlib

import numpy as np

from backend.adapters.case8_allocation import Case8AllocationAdapter
from backend.adapters.gate_allocation import GateAllocationAdapter
from backend.core.errors import missing_asset, system_error, unsupported_representation
from backend.models import EvidenceRecord, ResultProvenance, known, unresolved
from backend.models.allocation import AllocationMetadata, AllocationComparison
from backend.registry import case8_allocation as R, gate_registry as G, gate_evidence as EV


class IntegratedAllocationAdapter:
    def __init__(self, case8_root=None, gate_root=None):
        self.face = Case8AllocationAdapter() if case8_root is None else Case8AllocationAdapter(case8_root)
        self.cell = GateAllocationAdapter() if gate_root is None else GateAllocationAdapter(gate_root)

    def _adapter(self, result_id):
        if result_id.startswith('case8.'):
            return self.face
        if result_id.startswith('gate.'):
            return self.cell
        raise missing_asset('Allocation identity is not registered', resource_type='allocation', identity=known(result_id))

    def _gate_assets(self, config):
        return [EV.pi_at_source_asset(config), EV.entropy_source_asset(config),
                EV.matched_qat_source_asset(), EV.analysis_source_asset(), EV.readme_source_asset()]

    def _observe_gate(self, config):
        assets = self._gate_assets(config)
        observed = datetime.now(timezone.utc)
        for asset in assets:
            path = self.cell._root / asset['relative_origin']['value']
            try:
                current = hashlib.sha256(path.read_bytes()).hexdigest()
            except FileNotFoundError:
                raise missing_asset('Recorded Gate dependency is absent', resource_type='allocation', identity=known(config)) from None
            if current != asset['recorded_data_hash']['value']:
                raise system_error('SOURCE_DATA_DRIFT', 'Gate dependency differs from its frozen hash', domain='SCIENTIFIC')
            asset.update(current_data_hash=known(current), data_drift=known(False))
            asset['verification']['observation_at'] = known(observed)
        return assets, observed

    def _read(self, method, result_id, *args, **kwargs):
        adapter = self._adapter(result_id)
        if adapter is self.face:
            return getattr(adapter, method)(result_id, *args, **kwargs)
        config = adapter._config_from_result(result_id)
        self._observe_gate(config)
        value = getattr(adapter, method)(result_id, *args, **kwargs)
        assets, _ = self._observe_gate(config)
        payload = value.model_dump(mode='python')
        def bind_sources(node):
            if isinstance(node, dict):
                if 'provenance' in node:
                    node['provenance']['source_asset_ids'] = [a['asset_id'] for a in assets]
                    node['provenance']['source_drift'] = known(False)
                for child in node.values():
                    bind_sources(child)
            elif isinstance(node, list):
                for child in node:
                    bind_sources(child)
        bind_sources(payload)
        return type(value).model_validate(payload)

    def describe_allocation(self, experiment_id, config_id, **kwargs):
        adapter = self._adapter(f'{experiment_id}.{config_id}.allocation')
        return adapter.describe_allocation(experiment_id, config_id, **kwargs)

    def load_allocation_metadata(self, result_id, **kwargs):
        return self._read('load_allocation_metadata', result_id, **kwargs)

    def load_allocation_array(self, result_id, array_id, **kwargs):
        return self._read('load_allocation_array', result_id, array_id, **kwargs)

    def load_summary_metrics(self, result_id, **kwargs):
        value = self._read('load_summary_metrics', result_id, **kwargs)
        if result_id.startswith('gate.'):
            value = value.model_copy(update={'evidence_refs': [f'ev.gate.{value.total_budget.root.value.result.config_id}.allocation']})
        return value

    def load_mask(self, mask_id, **kwargs):
        if mask_id == R.MASK_ID:
            return self.face.load_mask(mask_id, **kwargs)
        if mask_id == G.MASK_ID:
            return self.cell.load_mask(mask_id, **kwargs)
        raise missing_asset('Mask identity is not registered', resource_type='mask', identity=known(mask_id))

    @staticmethod
    def _cell_mask():
        x = (np.arange(G.GRID_NX) + .5) / G.GRID_NX
        y = (np.arange(G.GRID_NY) + .5) / G.GRID_NY
        front = G.FRONT_X0 + G.FRONT_AMPLITUDE * np.sin(G.FRONT_WAVENUMBER * np.pi * y)
        return np.abs(x[None, :] - front[:, None]) <= G.FRONT_WINDOW_HALF_WIDTH

    def load_allocation_metadata_view(self, result_id, **kwargs):
        value = self.load_allocation_metadata(result_id, **kwargs).root
        description = self.describe_allocation(value.result.experiment_id, value.result.config_id, **kwargs)
        masks = [self.load_mask(identity, **kwargs) for identity in value.summary.mask_refs]
        if value.representation_type == 'FACE_FIELD':
            counts = [sum(self.face.load_allocation_array(ref.result_id, ref.descriptor.array_id).values)
                      for ref in masks[0].mask_array_refs]
        else:
            counts = [int(self._cell_mask().sum())]
        return AllocationMetadata(
            result_id=value.result.result_id, experiment_id=value.result.experiment_id,
            config_id=value.result.config_id, semantic_id=value.result.semantic_id,
            representation_type=value.representation_type, wire_representation=value.representation_type,
            measure_definition=description.measure_definition, measure=value.summary.measure,
            coordinate_convention=description.coordinate_convention, mask_definition=description.mask_definition,
            mask_refs=value.summary.mask_refs, domains=[field.domain.id for field in value.fields],
            array_refs=[field.array_ref for field in value.fields], evidence_refs=value.result.provenance.evidence_refs,
            scope=value.result.scope, result=value.result, fields=value.fields,
            definition=description.definition, masks=masks, mask_counts=counts)

    def load_allocation_comparison(self, experiment_id, *, representation_type=None, **kwargs):
        if experiment_id != 'gate' or representation_type not in (None, 'CELL_FIELD'):
            raise unsupported_representation('Only the three frozen Gate cell maps share a comparison', resource_type='allocation', identity=known(experiment_id))
        entries, arrays = [], []
        for config in G.CONFIG_ORDER:
            identity = f'gate.{config}.allocation'
            metadata = self.load_allocation_metadata_view(identity, **kwargs)
            summary = self.load_summary_metrics(identity, **kwargs)
            arrays.extend(self.load_allocation_array(identity, metadata.array_refs[0].descriptor.array_id, **kwargs).values)
            entries.append(dict(result_id=identity, config_id=config, representation_type='CELL_FIELD',
                                wire_representation='CELL_FIELD', array_ref=metadata.array_refs[0],
                                summary={'availability': 'AVAILABLE', 'value': summary}))
        extent = []
        for name, number in [('min', min(arrays)), ('max', max(arrays))]:
            metric = summary.total_budget.root.value.model_dump(mode='python')
            metric.update(metric_id=f'gate.comparison.{name}', display_label=f'Cell Pi_at {name}',
                          definition_id=G.SEMANTIC_ID, value=known(number))
            metric['result']['result_id'] = f'gate.comparison.{name}'
            metric['result']['semantic_id'] = G.SEMANTIC_ID
            metric['result']['config_id'] = 'comparison'
            metric['result']['scope'].update(description=f'{name} across all three saved cell Pi_at maps',
                                             mask_refs=[], definition_refs=[G.SEMANTIC_ID])
            metric['result']['provenance']['evidence_refs'] = [f'ev.gate.{c}.allocation' for c in G.CONFIG_ORDER]
            metric['result']['provenance']['source_asset_ids'] = sorted({
                a['asset_id'] for c in G.CONFIG_ORDER for a in self._gate_assets(c)})
            extent.append({'availability': 'AVAILABLE', 'value': metric})
        return AllocationComparison(comparison_id='gate.allocation.comparison', experiment_id='gate',
                                    representation_type='CELL_FIELD', shared_extent=extent,
                                    colour_scale='SHARED_COMPARISON_SCALE', entries=entries,
                                    measure=metadata.measure, evidence_refs=[f'ev.gate.{c}.allocation' for c in G.CONFIG_ORDER])

    def owns_evidence(self, identity):
        return identity == R.EVIDENCE_ID or identity in {f'ev.gate.{c}.allocation' for c in G.CONFIG_ORDER}

    def owns_result(self, identity):
        return (identity.startswith('case8.') and '.allocation' in identity
                or identity.startswith('gate.') and ('.allocation' in identity or '.summary.' in identity))

    def load_evidence(self, evidence_id, **kwargs):
        if evidence_id == R.EVIDENCE_ID:
            return self.face.load_evidence(evidence_id, **kwargs)
        configs = {f'ev.gate.{c}.allocation': c for c in G.CONFIG_ORDER}
        if evidence_id not in configs:
            raise system_error('UNKNOWN_EVIDENCE_ID', 'Allocation evidence is not registered', status=404)
        config = configs[evidence_id]
        assets, observed = self._observe_gate(config)
        allocation = self.load_allocation_metadata(f'gate.{config}.allocation', **kwargs).root
        description = self.describe_allocation('gate', config, **kwargs)
        contexts = [allocation.result, *(slot.root.value.result for slot in
                    (allocation.summary.total_budget, allocation.summary.inside, allocation.summary.outside))]
        verification = allocation.result.verification.model_dump(mode='python')
        verification['observation_at'] = known(observed)
        definitions = [description.definition]
        for slot, rule in [(allocation.summary.total_budget, 'sum(saved Pi_at cells)=E_at; no extra dx/dy/dt'),
                           (allocation.summary.inside, 'sum(saved Pi_at cells in the fixed Gate mask)/E_at'),
                           (allocation.summary.outside, 'sum(saved Pi_at cells outside the fixed Gate mask)/E_at')]:
            metric = slot.root.value
            definitions.append(description.definition.model_copy(update={
                'id': metric.definition_id, 'semantic_id': metric.result.semantic_id,
                'title': metric.display_label, 'definition': rule, 'spatial_rule': rule,
                'unit': metric.result.unit}))
        self._observe_gate(config)
        return EvidenceRecord.model_validate(dict(
            schema_version='1.0.0', evidence_id=evidence_id,
            result_ids=[c.result_id for c in contexts], result_contexts=contexts,
            experiment_id=known('gate'), config_id=known(config),
            config=known(G.configs()[list(G.CONFIG_ORDER).index(config)]),
            definitions=definitions, masks=[self.load_mask(G.MASK_ID)],
            method_name=known(G.METHOD_NAME), method_hash=known(G.METHOD_SHA256),
            recorded_source_hash=assets[0]['recorded_data_hash'], current_source_hash=assets[0]['current_data_hash'],
            data_hash=assets[0]['recorded_data_hash'], source_assets=assets,
            source_observations=[dict(asset_id=a['asset_id'], recorded_hash=a['recorded_data_hash'],
                                      current_hash=a['current_data_hash'], drift=known(False), observation_at=known(observed)) for a in assets],
            freeze_reference=unresolved('No manifest hash binding supplied by Gate registry'), processing=[],
            verification=verification, limitations=allocation.result.limitations, source_drift=known(False),
            created_at=unresolved('No authoritative creation timestamp'), verified_at=verification['verified_at'],
            related_evidence_refs=[], superseded_by=unresolved('No known replacement', 'NOT_APPLICABLE')))

    def load_provenance(self, result_id, **kwargs):
        if result_id.startswith('case8.'):
            return self.face.load_provenance(result_id, **kwargs)
        parts = result_id.split('.')
        if len(parts) < 2 or parts[1] not in G.CONFIG_ORDER:
            raise system_error('INVALID_RESULT_ID', 'Allocation result is not registered', status=404)
        config = parts[1]
        evidence = self.load_evidence(f'ev.gate.{config}.allocation', **kwargs)
        for context in evidence.result_contexts:
            if context.result_id == result_id:
                return ResultProvenance(result_id=result_id, provenance=context.provenance, evidence_records=[evidence])
        raise system_error('INVALID_RESULT_ID', 'Allocation result is not registered', status=404)
