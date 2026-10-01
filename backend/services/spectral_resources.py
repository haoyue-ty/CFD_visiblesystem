"""Contract-preserving array/evidence integration over the frozen adapter.

Only exact registry identities resolve. Evidence maps already-observed canonical
configuration/assets; this module never opens sources or computes scientific data.
"""
from backend.core.errors import missing_asset, missing_resource
from backend.models import EvidenceRecord, ResultProvenance, known, unresolved
from backend.registry import spectral_registry as R


def _selectors():
    result = {dataset: ("dataset", dataset) for dataset in R.DATASETS}
    for dataset in R.DATASETS:
        for mode in range(17):
            result[R.record_id(dataset, mode)] = ("point", dataset, mode)
            for rank in range(32):
                for side in ("LEFT", "RIGHT"):
                    result[R.eigenmode_id(dataset, mode, side, rank)] = (
                        "eigenmode", dataset, mode, side, rank, "COMPLEX_VECTOR", "stored_vector")
                for component in ("density", "u", "v", "pressure"):
                    result[R.eigenmode_id(dataset, mode, "RIGHT", rank, "PRIMITIVE_PROFILE", component)] = (
                        "eigenmode", dataset, mode, "RIGHT", rank, "PRIMITIVE_PROFILE", component)
    result.update({f"{run}.history": ("validation", run) for run in R.RUNS})
    return result


SELECTORS = _selectors()
PREFIX = "evidence.spectral."


def bind_evidence(view):
    """Bind navigable records while retaining the adapter's source_asset_ids."""
    if view.result.result_id not in SELECTORS:
        return view  # Test-only adapter namespaces keep their own evidence.
    payload = view.model_dump(mode="python")
    def bind(header):
        ref = PREFIX + header["result"]["result_id"]
        header["provenance"]["evidence_refs"] = [ref]
        header["result"]["provenance"]["evidence_refs"] = [ref]
        if "evidence_refs" in header:
            header["evidence_refs"] = [ref]
    bind(payload)
    for point in payload.get("points", []):
        bind(point)
    return type(view).model_validate(payload)


class SpectralResources:
    def __init__(self, service):
        self.service = service

    def owns_result(self, identity):
        return identity in SELECTORS

    def owns_evidence(self, identity):
        return identity.startswith(PREFIX) and identity[len(PREFIX):] in SELECTORS

    def load_array(self, result_id, array_id):
        slot = self.service._require_adapter("load_array")(result_id, array_id)
        if slot.root.availability == "UNSUPPORTED":
            raise missing_resource("INVALID_RESULT_ID", "Array/result combination is not registered",
                                   resource_type="array", identity=unresolved("Unknown array selector"))
        value, _ = self.service._unwrap(slot, missing=missing_asset,
                                       resource_type="array", identity=known(result_id))
        payload = value.model_dump(mode="python")
        payload["result"]["provenance"]["evidence_refs"] = [PREFIX + result_id]
        return type(value).model_validate(payload)

    def _internal(self, result_id):
        kind, *selection = SELECTORS[result_id]
        dataset = selection[0]
        if kind == "dataset":
            slot = self.service._slot("describe_spectrum", dataset)
        elif kind == "point":
            slot = self.service._slot("load_spectral_points", dataset)
        elif kind == "validation":
            slot = self.service._slot("load_growth_validation", dataset)
        else:
            dataset, mode, side, rank, representation, component = selection
            slot = self.service._slot("load_eigenmode", dataset, mode, side=side, rank=rank,
                                      representation=representation, field_component=component,
                                      projection="COMPLEX" if representation == "COMPLEX_VECTOR" else "AMPLITUDE")
        value, _ = self.service._unwrap(slot, missing=missing_asset,
                                       resource_type="result", identity=known(result_id))
        return value.points[selection[1]] if kind == "point" else value

    def load_evidence(self, evidence_id):
        if not self.owns_evidence(evidence_id):
            raise missing_resource("UNKNOWN_EVIDENCE_ID", "Evidence identity is not registered",
                                   resource_type="evidence", identity=unresolved("Unknown evidence"))
        result_id = evidence_id[len(PREFIX):]
        value = self._internal(result_id)
        context = value.result.model_dump(mode="python")
        context["provenance"]["evidence_refs"] = [evidence_id]
        config = value.evidence.configuration
        assets = value.evidence.source_assets
        method = next(a for a in assets if a.asset_id == R.ASSETS[
            "production_source/solver/fluxes/cross_mode_ec_unified_v1.py"][0])
        manifest = next(a for a in assets if a.asset_id == R.ASSETS["SHA256_MANIFEST.json"][0])
        primary_name = "spectrum/eigenvalues.npz"
        if hasattr(value, "run_id"):
            primary_name = R.RUNS[value.run_id][3]
        elif hasattr(value, "side"):
            primary_name = (f"spectrum/{value.side.lower()}_eigenvectors.npz"
                            if value.representation == "COMPLEX_VECTOR" else
                            "spectrum/leading_primitive_amplitude_profiles.npz")
        primary = next(a for a in assets if a.source_display == primary_name)
        unknown = unresolved("Not recorded in the frozen metadata")
        limits = [{"id": "lim.spectral.selective-response", "code": "SELECTIVE_MODAL_RESPONSE",
                   "description": "Positive entropy production does not imply uniform modal damping; "
                                  "only recorded modes on this common Mach6 base are supported.",
                   "severity": "INFO", "affected_refs": [result_id]}]
        if hasattr(value, "run_id"):
            limits.append({"id": "lim.spectral.missing-linear-history", "code": "MISSING_LINEAR_HISTORY",
                           "description": "Linear/RK3 amplitude histories were not saved; recorded rates and CFD history are retained.",
                           "severity": "INFO", "affected_refs": [result_id]})
        if hasattr(value, "normalization"):
            limits.append({"id": "lim.spectral.unknown-normalization", "code": "UNKNOWN_NORMALIZATION",
                           "description": "Raw normalization and phase conventions are unknown; saved vectors are preserved verbatim.",
                           "severity": "INFO", "affected_refs": [result_id]})
        return EvidenceRecord.model_validate({
            "schema_version": "1.0.0", "evidence_id": evidence_id,
            "result_ids": [result_id], "result_contexts": [context],
            "experiment_id": known(value.experiment_id), "config_id": known(value.configuration_id),
            "config": known(config.model_dump(mode="python")), "definitions": [],
            "masks": [mask.model_dump(mode="python")] if (mask := getattr(value, "mask", getattr(value, "mask_reference", None))) else [],
            "method_name": config.protocol.method_name, "method_hash": config.protocol.method_hash,
            "recorded_source_hash": method.recorded_data_hash, "current_source_hash": method.current_data_hash,
            "source_assets": assets, "source_observations": [{
                "asset_id": a.asset_id, "recorded_hash": a.recorded_data_hash,
                "current_hash": a.current_data_hash, "drift": a.data_drift,
                "observation_at": value.verification.observation_at} for a in assets],
            "data_hash": primary.recorded_data_hash,
            "freeze_reference": known({"freeze_id": "freeze.linear-perturbation.common-mach6",
                "manifest_asset_id": manifest.asset_id, "recorded_at": unknown,
                "hash": manifest.recorded_data_hash.model_dump(mode="python")}),
            "processing": [], "verification": value.verification, "limitations": limits,
            "source_drift": value.provenance.source_drift, "created_at": unknown,
            "verified_at": value.verification.verified_at,
            "related_evidence_refs": [], "superseded_by": unresolved("No successor recorded", "NOT_APPLICABLE"),
        })

    def load_provenance(self, result_id):
        evidence = self.load_evidence(PREFIX + result_id)
        return ResultProvenance(result_id=result_id, provenance=evidence.result_contexts[0].provenance,
                                evidence_records=[evidence])


class ResultResourceRouter:
    """Keep Case8 and Allocation delivery intact; route registered spectral IDs."""
    def __init__(self, case8, spectral, project):
        self.case8, self.spectral, self.project = case8, spectral, project

    def revision_for(self, identity):
        return R.REGISTRY_REVISION if (self.spectral.owns_result(identity) or
                                      self.spectral.owns_evidence(identity)) else self.project.registry_revision

    def load_array(self, result_id, array_id):
        selected = self.spectral if self.spectral.owns_result(result_id) else self.case8
        return selected.load_array(result_id, array_id)

    def load_evidence(self, evidence_id):
        selected = self.spectral if self.spectral.owns_evidence(evidence_id) else self.case8
        return selected.load_evidence(evidence_id)

    def load_provenance(self, result_id):
        selected = self.spectral if self.spectral.owns_result(result_id) else self.case8
        return selected.load_provenance(result_id)
