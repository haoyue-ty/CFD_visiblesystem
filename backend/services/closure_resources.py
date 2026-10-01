"""Finite Closure Evidence/provenance ownership; no spatial or array capability."""
from backend.registry import closure_registry as R


EVIDENCE_IDS = frozenset(R.evidence_id(run, group) for run in R.RUN_IDS for group in ("run", "stage", "step")) | {R.REFINEMENT_EVIDENCE}
RESULT_IDS = frozenset(
    R.result_id(run, group, field)
    for run in R.RUN_IDS
    for group, fields in (("run", R.TERMINAL_FIELDS), ("stage", R.STAGE_SERIES), ("step", R.STEP_SERIES))
    for field in fields
) | frozenset(
    R.result_id(run, "refinement", field)
    for index, run in enumerate(R.RUN_IDS[:4])
    for field in ("R_total", "dt_eff", *(('refinement_slope',) if index == 0 else ()),
                  *((f"pairwise_slope_to_{R.RUN_IDS[index + 1]}",) if index < 3 else ()))
)


class ClosureResources:
    registry_revision = R.REGISTRY_REVISION

    def __init__(self, service):
        self.service = service

    def owns_result(self, identity):
        return identity in RESULT_IDS

    def owns_evidence(self, identity):
        return identity in EVIDENCE_IDS

    def load_evidence(self, evidence_id):
        return self.service.load_evidence(evidence_id)

    def load_provenance(self, result_id):
        return self.service.load_provenance(result_id)
