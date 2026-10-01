"""TEST-ONLY allocation adapter standing in for the Window 1 scientific loader.

Confined to the test tree and never imported by ``backend``. Every payload is MOCK and
uses the ``mock.`` result namespace so its numbers can never be mistaken for reproduced
science. It exists to prove the four ALLOC operations return ``representation_type`` on
every response and map failures onto MISSING_ASSET / UNSUPPORTED_REPRESENTATION /
SOURCE_ERROR without ever asking the client to guess face vs cell.
"""
from backend.adapters.allocation import AllocationDescription
from backend.models import (ArrayDescriptor, ArrayRef, MeasureConvention, ScientificArray,
                            ScientificDefinition, ScientificResult, SpatialDomain, UnitSpec,
                            known, unresolved)
from backend.models.allocation import (AllocationArrayResponse, AllocationComparison,
                                       AllocationComparisonEntry, AllocationMetadata,
                                       AllocationResult, AllocationSummary)


def _unknown(reason: str) -> dict:
    return unresolved(reason)


def _na(reason: str) -> dict:
    return unresolved(reason, "NOT_APPLICABLE")


def _unit(quantity: str) -> UnitSpec:
    return UnitSpec(id=f"mock.unit.{quantity}", system="MODEL", quantity=quantity,
                    label=f"model {quantity}", si_mapping=_unknown("No SI mapping in mock data"))


def _measure(face: bool) -> MeasureConvention:
    return MeasureConvention.model_validate({
        "id": "mock.face-measure" if face else "mock.cell-measure",
        "description": "Test-only integrated measure",
        "integral_rule": "dy*sum(x)+dx*sum(y)" if face else "sum(cells)",
        "measure_parameters": [{"name": "dx", "value": known(1.0 / 128)},
                               {"name": "dy", "value": known(1.0 / 32)}],
        "includes_time_weights": True,
        "includes_spatial_measure": not face,
    })


def _result(result_id: str, *, experiment_id: str, config_id: str, semantic_id: str,
            face: bool) -> ScientificResult:
    return ScientificResult.model_validate({
        "schema_version": "1.0.0", "result_id": result_id, "experiment_id": experiment_id,
        "config_id": config_id, "semantic_id": semantic_id, "data_origin": "MOCK",
        "availability": "AVAILABLE",
        "time": {"sampling": "TERMINAL" if face else "STATIC", "accumulation": "TRAJECTORY_INTEGRATED",
                 "physical_time": known(0.08), "interval": known({"start": 0.0, "end": 0.08}),
                 "step_index": known(1912), "stage_index": _na("No stage"),
                 "snapshot_index": _na("No snapshot"),
                 "index_convention": "USER_VISIBLE_1_BASED_RECORDED_INDEX"},
        "scope": {"id": "mock.scope", "description": "Test-only allocation scope",
                  "boundary_scope": _unknown("Mock boundary"), "spatial_domain_ref": _unknown("Mock domain"),
                  "mask_refs": ["mock.face-mask" if face else "mock.cell-mask"], "definition_refs": []},
        "unit": _unit("integrated_entropy"), "verification": {"status": "NOT_APPLICABLE",
                                                              "basis": ["Test-only fake adapter"],
                                                              "verified_at": _na("Mock"), "observation_at": _na("Mock"),
                                                              "evidence_refs": ["mock.evidence.allocation"]},
        "provenance": {"evidence_refs": ["mock.evidence.allocation"], "source_asset_ids": ["mock.asset"],
                       "registry_revision": "mock.registry", "data_revision": "mock.data",
                       "release_id": _na("Mock release"), "source_drift": _na("No drift check")},
        "limitations": [],
    })


def _array_ref(result_id: str, array_id: str, shape: list[int]) -> ArrayRef:
    return ArrayRef.model_validate({
        "result_id": result_id, "descriptor": {
            "array_id": array_id, "dtype": "float64", "shape": shape, "order": "C",
            "axes": ["y", "x"], "encoding": "FLAT_JSON",
            "element_count": shape[0] * shape[1]}})


def _summary(face: bool) -> AllocationSummary:
    measure = _measure(face)
    missing = {"availability": "MISSING", "error": {
        "domain": "SCIENTIFIC", "code": "MISSING_SCIENTIFIC_ASSET",
        "message": "Test-only missing metric",
        "target": {"resource_type": "metric", "identity": _na("Mock metric")},
        "retryable": False, "details": [], "evidence_refs": ["mock.evidence.allocation"]}}
    return AllocationSummary.model_validate({
        "total_budget": missing, "inside": missing, "outside": missing,
        "fraction_format": "FRACTION", "mask_refs": ["mock.face-mask" if face else "mock.cell-mask"],
        "measure": measure, "spatial_cumulative_curve": missing,
        "evidence_refs": ["mock.evidence.allocation"]})


class FakeAllocationAdapter:
    """Implements AllocationAdapterProtocol shape for the three case scenarios.

    ``mode`` selects the scenario:
      * ``valid``       -> face metadata/array/summary/comparison all resolve
      * ``missing``     -> a recognized identity with no saved asset (MISSING_ASSET)
      * ``unsupported`` -> a representation that cannot be rendered (UNSUPPORTED_REPRESENTATION)
      * ``source``      -> the controlled source read fails (SOURCE_ERROR)
    """

    FACE_RESULT_ID = "mock.case8.D_u.allocation"
    ARRAY_ID = "mock.pi_at_x_faces"

    def __init__(self, mode: str = "valid"):
        self.mode = mode

    def _guard(self, result_id: str) -> None:
        if self.mode == "missing":
            raise KeyError(result_id)
        if self.mode == "source":
            raise OSError("mock source unreadable")

    def _representation(self, representation_type: str) -> bool:
        if self.mode == "unsupported":
            raise NotImplementedError(representation_type)
        return representation_type == "FACE_FIELD"

    def describe_allocation(self, experiment_id: str, config_id: str, *,
                            registry_revision: str | None = None) -> AllocationDescription:
        face = True
        return AllocationDescription(
            capability=None, representation_type="FACE_FIELD",
            measure_definition="face integrated", coordinate_convention="Cartesian [y,x]",
            mask_definition="mock native-face mask",
            definition=ScientificDefinition.model_validate({
                "id": "Case8_face_Pi_at_integrated", "semantic_id": "Case8_face_Pi_at_integrated",
                "title": "Mock allocation", "definition": "Test-only allocation definition",
                "time_rule": "time/RK weights included", "spatial_rule": "spatial measure still required",
                "unit": _unit("integrated_entropy"), "mask_refs": ["mock.face-mask"],
                "detector": _na("Allocation is not a detector metric"),
                "evidence_refs": ["mock.evidence.allocation"], "limitations": []}))

    def load_allocation_metadata_view(self, result_id: str, *,
                                      registry_revision: str | None = None) -> AllocationMetadata:
        self._guard(result_id)
        face = self._representation("FACE_FIELD")
        header = _result(result_id, experiment_id="case8", config_id="D_u",
                         semantic_id="Case8_face_Pi_at_integrated", face=face)
        return AllocationMetadata.model_validate({
            "result_id": result_id, "experiment_id": "case8", "config_id": "D_u",
            "semantic_id": "Case8_face_Pi_at_integrated", "representation_type": "FACE_FIELD",
            "wire_representation": "FACE_FIELD", "measure_definition": "face integrated",
            "measure": _measure(face), "coordinate_convention": "Cartesian [y,x], C order",
            "mask_definition": "mock native-face mask", "mask_refs": ["mock.face-mask"],
            "domains": ["mock.native-x-faces"], "array_refs": [
                _array_ref(f"{result_id}.pi_at_x_faces", "pi_at_x_faces", [2, 2])],
            "evidence_refs": ["mock.evidence.allocation"],
            "scope": {"id": "mock.scope", "description": "Test-only allocation scope",
                      "boundary_scope": _unknown("Mock boundary"), "spatial_domain_ref": _unknown("Mock domain"),
                      "mask_refs": ["mock.face-mask"], "definition_refs": []},
            "result": header})

    def load_allocation_metadata(self, result_id: str, *,
                                 registry_revision: str | None = None) -> AllocationResult:
        self._guard(result_id)
        self._representation("FACE_FIELD")
        raise NotImplementedError("Result union not exercised by Window 3 API tests")

    def load_allocation_array(self, result_id: str, array_id: str, *,
                              registry_revision: str | None = None) -> AllocationArrayResponse:
        self._guard(result_id)
        face = self._representation("FACE_FIELD")
        header = _result(result_id, experiment_id="case8", config_id="D_u",
                         semantic_id="Case8_face_Pi_at_integrated", face=face)
        return AllocationArrayResponse.model_validate({
            "result": header, "representation_type": "FACE_FIELD", "field_id": "mock.x_face",
            "array_ref": _array_ref(result_id, array_id, [2, 2]),
            "values": [0.0, 1.0, 2.0, 3.0]})

    def load_mask(self, mask_id: str, *, registry_revision: str | None = None):
        self._guard(mask_id)
        raise NotImplementedError("Mask loading is exercised by MASK01, not Window 3")

    def load_summary_metrics(self, result_id: str, *,
                             registry_revision: str | None = None) -> AllocationSummary:
        self._guard(result_id)
        self._representation("FACE_FIELD")
        return _summary(True)

    def load_allocation_comparison(self, experiment_id: str, *, representation_type: str | None = None,
                                   registry_revision: str | None = None) -> AllocationComparison:
        if self.mode == "source":
            raise OSError("mock comparison source unreadable")
        if self.mode == "missing":
            raise KeyError(experiment_id)
        cell = self._representation(representation_type or "CELL_FIELD")
        entry_result = _result(f"mock.{experiment_id}.allocation", experiment_id=experiment_id,
                               config_id="Acoustic", semantic_id="Gate_cell_Pi_at_integrated", face=cell)
        entry = AllocationComparisonEntry.model_validate({
            "result_id": f"mock.{experiment_id}.allocation", "config_id": "Acoustic",
            "representation_type": "CELL_FIELD", "wire_representation": "CELL_FIELD",
            "array_ref": _array_ref(f"mock.{experiment_id}.allocation", "cells", [2, 2]),
            "summary": {"availability": "AVAILABLE", "value": _summary(cell)}})
        return AllocationComparison.model_validate({
            "comparison_id": f"mock.{experiment_id}.allocation-comparison",
            "experiment_id": experiment_id,
            "representation_type": representation_type or "CELL_FIELD",
            "shared_extent": [{"availability": "MISSING", "error": {
                "domain": "SCIENTIFIC", "code": "MISSING_SCIENTIFIC_ASSET",
                "message": "Test-only missing extent",
                "target": {"resource_type": "extent", "identity": _na("Mock extent")},
                "retryable": False, "details": [], "evidence_refs": ["mock.evidence.allocation"]}}],
            "colour_scale": "SHARED_COMPARISON_SCALE", "entries": [entry],
            "measure": _measure(cell), "evidence_refs": ["mock.evidence.allocation"]})
