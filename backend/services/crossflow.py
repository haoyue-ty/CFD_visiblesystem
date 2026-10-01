"""Backend composite of typed child results under frozen 05/06 §12/13."""
from backend.core.errors import DomainError, system_error
from backend.models import ErrorBody, Metric, MetricCollection, known, unresolved
from backend.models.crossflow import CrossFlowComparison, CrossFlowSide
from backend.models.cylinder import AllocationResult
from backend.registry import cylinder_registry as R
from backend.registry.case8_source_constants import CONFIG_ORDER
from backend.registry.case8_semantics import FIELD_SEMANTICS
from backend.services.cylinder_resources import EVIDENCE_IDS

COMPOSITE_EVIDENCE_IDS = EVIDENCE_IDS | {"ev.case8.D_u.allocation"} | {
    f"ev.case8.{config}.{suffix}" for config in CONFIG_ORDER
    for suffix in ("entropy", "metrics", *(f"snapshot.{i}" for i in range(1, 7)),
                   *(f"snapshot.{i}.{field}" for i in range(1, 7) for field in FIELD_SEMANTICS))}


def _refs(value):
    payload = value.model_dump(mode="python") if hasattr(value, "model_dump") else value
    found = set()
    def visit(node):
        if hasattr(node, "model_dump"):
            node = node.model_dump(mode="python")
        if isinstance(node, dict):
            # Legacy Case8 config/domain metadata also puts SourceAsset IDs in
            # evidence_refs. They remain intact on children; the composite's
            # navigable evidence list contains only registered EvidenceRecords.
            found.update(ref for ref in node.get("evidence_refs", []) if ref in COMPOSITE_EVIDENCE_IDS)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(payload)
    return sorted(found)


def _rule(left, right, reason):
    return {"left_definition_id": left, "right_definition_id": right,
            "status": "DESCRIPTIVE_ONLY", "reason": reason,
            "mapping_ref": unresolved("No scientific mapping is declared", "NOT_APPLICABLE")}


RULES = [
    _rule("Case8_face_window_fraction", "def.cylinder_front_band_fraction",
          "Case8 FACE_FIELD localization uses native x/y-face measures in a fixed Cartesian window; Cylinder uses a fixed A_u radial +/-0.16 band only within its anchor angular span. These fractions describe different regions and denominators."),
    _rule("case8_front_high_k_energy", "def.cylinder_front_HF_RMS",
          "Case8 high-k is normalized Fourier energy above its seeded mode; Cylinder HF-RMS is a quadratic-detrended three-point high-pass normalized by local radial spacing. Units, signals and detectors differ."),
    _rule("case8_width", "def.cylinder_front_mean_width",
          "Case8 Cartesian front width and Cylinder radial pressure W10-90 use different geometry and detectors. Cylinder B/D readings approach the detector floor; small ratios do not resolve an ordering."),
    _rule("E_at_cumulative", "def.Cylinder_E_at_cumulative",
          "Case8 retains its own native-face budget boundary scope; Cylinder is INTERIOR_ONLY and excludes wall and far-field flux. Time horizons [0,0.08] and [0,2] and model units differ. No implicit normalization or shared budget scale is declared."),
]


class ComparisonService:
    def __init__(self, case8, cylinder, allocation):
        self.case8, self.cylinder, self.allocation = case8, cylinder, allocation

    @staticmethod
    def _slot(loader):
        try:
            value = loader()
            if isinstance(value, MetricCollection):
                issues = []
                for child in value.items:
                    if child.root.availability == "PARTIAL":
                        issues.extend(child.root.issues)
                    elif child.root.availability != "AVAILABLE":
                        issues.append(child.root.error)
                if issues:
                    return {"availability": "PARTIAL", "value": value, "issues": issues}
            return {"availability": "AVAILABLE", "value": value}
        except DomainError as error:
            # Only child data failures are localized. Invalid requests/identities
            # are validated before any child read, and must never become HTTP 200.
            if error.availability not in ("MISSING", "UNSUPPORTED", "ERROR"):
                raise
            return {"availability": error.availability, "error": error.body}

    @staticmethod
    def _budget(service, config, experiment):
        """Expose recorded terminal cumulative values as typed metrics, unchanged.

        This is a DTO projection, not a sum or derived cross-flow calculation.
        Result identities, definitions, units, scopes and provenance stay intact.
        """
        items = []
        for channel in ("bg", "aa", "at"):
            identity = f"E_{channel}_cumulative"
            header = service.load_scalar_series(config, identity, limit=1)
            series = service.load_scalar_series(config, identity,
                offset=header.total_point_count - 1, limit=1)
            if len(series.points) != 1:
                raise system_error("CANONICAL_SCHEMA_MISMATCH", "Recorded terminal budget point is absent")
            metric = Metric(result=series.result, metric_id=series.series_id,
                value=series.points[0].value, definition_id=series.definition_id,
                detector=unresolved("Saved cumulative scalar; no spatial detector", "NOT_APPLICABLE"),
                time_scope=series.result.time, display_label=series.label,
                resolution_limit=unresolved("No numerical uncertainty was recorded"))
            items.append({"availability": "AVAILABLE", "value": metric})
        return MetricCollection(experiment_id=experiment, config_id=config,
                                items=items, evidence_refs=sorted({r for s in items for r in _refs(s["value"])}))

    def _side(self, service, config, experiment):
        configs = service.list_configs()
        selected = next(c for c in configs.items if c.id == config)
        snapshots = self._slot(lambda: service.list_snapshots(config))
        history = self._slot(lambda: service.load_entropy_history(config, limit=1))
        budget = self._slot(lambda: self._budget(service, config, experiment))
        metrics = self._slot(lambda: service.load_metrics(config))
        issues = []
        limits = []
        if experiment == "case8":
            if config == "D_u":
                allocation = self._slot(lambda: AllocationResult.model_validate(
                    self.allocation.load_allocation_metadata("case8.D_u.allocation").model_dump(mode="python")))
            else:
                error = system_error("MISSING_SCIENTIFIC_ASSET", "No saved cumulative native-face allocation for this Case8 configuration",
                    status=404, availability="MISSING", resource_type="allocation", identity=known(f"case8.{config}.allocation"),
                    evidence_refs=[f"ev.case8.{config}.entropy"])
                allocation = {"availability": "MISSING", "error": error.body}
            error = system_error("UNSUPPORTED_COMBINATION", "Case8 has no Cylinder front-band analysis task",
                status=422, availability="UNSUPPORTED", resource_type="front_band", identity=known(f"case8.{config}"),
                evidence_refs=[f"ev.case8.{config}.entropy"])
            band = {"availability": "UNSUPPORTED", "error": error.body}
        else:
            allocation = self._slot(lambda: service.load_sectors(config))
            band = self._slot(lambda: service.load_front_band(config))
            # The selected frozen source has no cumulative 2D result. This
            # limitation survives even when another independent child fails.
            issues.append(ErrorBody.model_validate(R.MANIFEST["missing_cumulative_2d"]["ResourceSlot"]["error"]))
            limits.append(R.NO_MAP)
        for slot in (snapshots, history, budget, metrics, allocation, band):
            if slot["availability"] == "PARTIAL":
                issues.extend(slot["issues"])
            elif slot["availability"] != "AVAILABLE":
                issues.append(slot["error"])
        # Child limitations remain on the originals and are also discoverable on
        # the composite, including diagnostic origin and detector floor.
        children = [snapshots, history, budget, metrics, allocation, band]
        def collect_limits(node):
            if hasattr(node, "model_dump"):
                node = node.model_dump(mode="python")
            if isinstance(node, dict):
                limits.extend(node.get("limitations", []))
                for child in node.values():
                    collect_limits(child)
            elif isinstance(node, list):
                for child in node:
                    collect_limits(child)
        collect_limits(children)
        side = CrossFlowSide.model_validate({"experiment_id": experiment, "config_id": config, "protocol": selected.protocol,
            "budget": budget, "metrics": metrics, "allocation": allocation, "front_band": band,
            "snapshot_refs": [s.snapshot_id for s in snapshots["value"].items] if snapshots["availability"] == "AVAILABLE" else [],
            "history_refs": [s.result.result_id for s in history["value"].series] if history["availability"] == "AVAILABLE" else [],
            "evidence_refs": sorted(set(_refs(selected)) | set(_refs(children)) | set(_refs(issues)))})
        return side, issues, limits

    def load_comparison(self, case8_config="D_u", cylinder_config="D_u"):
        if case8_config not in CONFIG_ORDER:
            raise system_error("UNKNOWN_CONFIG", "Unknown Case8 configuration identity", status=404,
                               availability="MISSING", resource_type="case8_config",
                               details=[{"field": "case8_config", "issue": "Not registered", "allowed_values": list(CONFIG_ORDER)}])
        R.require_config(cylinder_config)
        left, left_issues, left_limits = self._side(self.case8, case8_config, "case8")
        right, right_issues, right_limits = self._side(self.cylinder, cylinder_config, "cylinder")
        limits = {l.id if hasattr(l, "id") else l["id"]: l for l in left_limits + right_limits}
        limits["lim.crossflow.definitions"] = {"id": "lim.crossflow.definitions", "code": "DESCRIPTIVE_CROSS_FLOW_ONLY",
            "description": "Independent protocols, grids, masks, detector definitions, budget scopes and time horizons are preserved. No unified ranking or undeclared mapping.",
            "affected_refs": left.snapshot_refs + right.snapshot_refs, "severity": "WARNING"}
        comparison = CrossFlowComparison(comparison_id=f"case8-cylinder.{case8_config}.{cylinder_config}",
            left=left, right=right, comparability=RULES, ranking_policy="NO_UNIFIED_RANKING",
            limitations=list(limits.values()), evidence_refs=sorted(set(left.evidence_refs + right.evidence_refs)))
        return comparison, left_issues + right_issues
