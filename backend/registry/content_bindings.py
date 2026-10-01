"""Resolve content references to existing Phase8 resources and operations.

This module returns request metadata only. It never loads arrays, integrates
budgets, constructs a spectrum, or calls a numerical service.
"""
from dataclasses import dataclass
from urllib.parse import urlencode

from backend.models.content import ScientificTarget
from backend.models.core import fact_value
from backend.registry import case8_allocation as A
from backend.registry import case8_registry as C
from backend.registry import case8_semantics as S
from backend.registry import gate_registry as G
from backend.registry import spectral_registry as R
from backend.services.cylinder_resources import EVIDENCE_IDS as CYLINDER_EVIDENCE
from backend.services.cylinder_resources import RESULT_IDS as CYLINDER_RESULTS
from backend.services.spectral_resources import PREFIX, SELECTORS


@dataclass(frozen=True)
class ResourceBinding:
    operation_id: str
    path: str
    query: tuple[tuple[str, str], ...] = ()

    @property
    def url(self) -> str:
        return self.path + ("?" + urlencode(self.query) if self.query else "")


def resolve_target(target: ScientificTarget) -> tuple[ResourceBinding, ...]:
    config = fact_value(target.config_id)
    if config is None:
        raise ValueError("Real scientific targets require an explicit registered configuration")
    bindings = []
    for result in target.result_ids:
        if target.experiment_id == "case8" and config in C.config_ids():
            prefix = f"case8.{config}."
            series = result.removeprefix(prefix)
            if result.startswith(prefix) and series in S.HISTORY_SERIES:
                bindings.append(ResourceBinding("C805", f"/api/v1/experiments/case8/configs/{config}/scalar-series/{series}"))
            elif config == "D_u" and result == A.RESULT_ID:
                bindings.append(ResourceBinding("ALLOC01", f"/api/v1/allocations/{result}/metadata"))
            else:
                raise ValueError(f"Unregistered Case8 content target: {result}")
        elif target.experiment_id == "gate" and config in G.gate_ids():
            if result != G.allocation_registry()[config]["result_id"]:
                raise ValueError(f"Unregistered Gate content target: {result}")
            bindings.append(ResourceBinding("ALLOC01", f"/api/v1/allocations/{result}/metadata"))
        elif target.experiment_id == "spectrum" and config in R.DATASETS:
            if result != config or result not in SELECTORS:
                raise ValueError(f"Unregistered spectral content target: {result}")
            bindings.append(ResourceBinding("SPEC02", f"/api/v1/spectra/{config}/points"))
        elif target.experiment_id == "cylinder" and config in ("A_u", "B_u", "D_u"):
            base = f"cylinder.{config}"
            if result not in CYLINDER_RESULTS:
                raise ValueError(f"Unregistered Cylinder content target: {result}")
            if result == f"{base}.sectors":
                suffix, operation = "allocation/sectors", "CYL07"
            elif result == f"{base}.front-band":
                suffix, operation = "allocation/front-band", "CYL08"
            else:
                raise ValueError(f"Unsupported Cylinder scene target: {result}")
            bindings.append(ResourceBinding(operation, f"/api/v1/experiments/cylinder/configs/{config}/{suffix}"))
        else:
            raise ValueError(f"Unregistered experiment/configuration: {target.experiment_id}/{config}")
    return tuple(bindings)


def resolve_evidence(identity: str) -> ResourceBinding:
    case8 = {f"ev.case8.{config}.entropy" for config in C.config_ids()}
    gate = {f"ev.gate.{config}.allocation" for config in G.gate_ids()}
    spectral = identity.startswith(PREFIX) and identity[len(PREFIX):] in SELECTORS
    if identity not in case8 | gate | CYLINDER_EVIDENCE | {A.EVIDENCE_ID} and not spectral:
        raise ValueError(f"Unregistered content evidence: {identity}")
    return ResourceBinding("EVI02", f"/api/v1/evidence/{identity}")


GATE_COMPARISON = ResourceBinding("ALLOC04", "/api/v1/allocations/comparison",
                                (("experiment_id", "gate"), ("representation_type", "CELL_FIELD")))
DU_CROSS_FLOW = ResourceBinding("CMP01", "/api/v1/comparisons/case8-cylinder",
                              (("case8_config", "D_u"), ("cylinder_config", "D_u")))
