"""Exact Cylinder canonical ownership; never derive a scientific path from an ID."""
from backend.registry import cylinder_registry as R


def _result_ids():
    identities = set()
    for config in R.CONFIGS:
        base = f"cylinder.{config}"
        identities.update({f"{base}.protocol", f"{base}.sectors", f"{base}.sectors.geometry", f"{base}.front-band"})
        identities.update(f"{base}.metric.{m}" for m in (*R.METRICS, "E_at_int", "cylinder_front_band_fraction", "cylinder_outside_band_fraction"))
        identities.update(f"{base}.history.{s['series_id']}" for s in R.MANIFEST["runs"][config]["history_source"]["series"])
        for index in range(1, 6):
            snapshot = f"{base}.snapshot.{index}"
            identities.add(snapshot)
            identities.update(f"{snapshot}.{family}_{field}" for family in R.FAMILIES for field in R.FIELDS)
            identities.update(f"{snapshot}.geometry.{family}_{member}" for family in R.FAMILIES for member in R.GEOMETRY)
    return frozenset(identities)


RESULT_IDS = _result_ids()
EVIDENCE_IDS = frozenset(f"ev.cylinder.{c}.{group}" for c in R.CONFIGS
                        for group in ("protocol", "snapshots", "history", "sectors", "front-band", "metrics")) | {"ev.missing.cylinder-cumulative2d"}


class CylinderResources:
    registry_revision = R.REGISTRY_REVISION

    def __init__(self, service):
        self.service = service

    def owns_result(self, identity):
        return identity in RESULT_IDS

    def owns_evidence(self, identity):
        return identity in EVIDENCE_IDS

    def load_array(self, result_id, array_id):
        return self.service.load_array(result_id, array_id)

    def load_evidence(self, evidence_id):
        return self.service.load_evidence(evidence_id)

    def load_provenance(self, result_id):
        return self.service.load_provenance(result_id)
