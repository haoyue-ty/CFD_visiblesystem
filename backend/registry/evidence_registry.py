"""One finite evidence registry over accepted scientific metadata and Phase1 history.

The normalized metadata catalog contains scientific headers, never values. Mode
and rank templates expand only identities; no arrays or numerical work occurs.
Inventory rows outside the accepted selection are HISTORY regardless of their
old verification label. Explore continues to reference the original IDs.
"""
import json
from copy import deepcopy
from pathlib import Path

from backend.models import known, unresolved
from backend.registry import spectral_registry as S
from backend.services.spectral_resources import PREFIX, SELECTORS

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_REVISION = "evidence-registry-v1"
DATA_REVISION = "accepted-phase5-10-evidence-v1"


def verification(status, identity, basis):
    return {"status": status, "basis": [basis],
            "verified_at": unresolved("No authoritative scientific verification event timestamp"),
            "observation_at": unresolved("No persisted observation event timestamp"), "evidence_refs": [identity]}


def metadata_record(identity, experiment, assets, *, status, basis, limitations=(), method_hash=None):
    return {"schema_version": "1.0.0", "evidence_id": identity,
        "result_ids": [], "result_contexts": [], "experiment_id": experiment,
        "config_id": unresolved("No numerical configuration", "NOT_APPLICABLE"),
        "config": unresolved("No numerical configuration", "NOT_APPLICABLE"), "definitions": [], "masks": [],
        "method_name": known("cross_mode_ec_unified_v1") if method_hash else unresolved("No confirmed method identity"),
        "method_hash": known(method_hash) if method_hash else unresolved("No confirmed method hash"),
        "recorded_source_hash": unresolved("No singular method source selected"),
        "current_source_hash": unresolved("Observe method source on demand"),
        "source_observations": [], "source_assets": assets,
        "data_hash": unresolved("No authoritative numerical data hash"),
        "freeze_reference": unresolved("No numerical freeze binding", "NOT_APPLICABLE"), "processing": [],
        "verification": verification(status, identity, basis), "limitations": list(limitations),
        "source_drift": unresolved("Observe all dependencies before asserting no drift"),
        "created_at": unresolved("No scientific creation event timestamp"),
        "verified_at": unresolved("No scientific verification event timestamp"),
        "related_evidence_refs": [], "superseded_by": unresolved("No successor recorded", "NOT_APPLICABLE")}


class EvidenceRegistry:
    def __init__(self):
        self.catalog = json.loads((ROOT / "data/evidence/canonical_metadata.json").read_text(encoding="utf-8"))
        self.inventory = json.loads((ROOT / "data/data_asset_inventory.json").read_text(encoding="utf-8"))["assets"]
        self.assets = deepcopy(self.catalog["assets"])
        self.entries = {identity: (identity, None) for identity in self.catalog["records"]}
        self.extra = {}
        self.sections = {identity: "CURRENT" for identity in self.entries}
        self.sections["ev.missing.cylinder-cumulative2d"] = "GAPS"
        self.result_evidence = {}
        for identity, raw in self.catalog["records"].items():
            for rid in raw["result_ids"]:
                self.result_evidence.setdefault(rid, []).append(identity)
        # All saved legal eigenmodes and Fourier records, without copying evidence.
        for rid, selector in SELECTORS.items():
            kind, dataset, *selection = selector
            identity = PREFIX + rid
            if kind == "validation":
                continue
            template_kind = kind
            if kind == "eigenmode":
                _, side, _, representation, component = selection
                template_kind = side if representation == "COMPLEX_VECTOR" else component
            template = self.catalog["spectral_templates"][f"{dataset}.{template_kind}"]
            self.entries[identity] = (template, rid)
            self.sections[identity] = "CURRENT"
            self.result_evidence[rid] = [identity]
        self._inventory_assets()
        self._add_basis()
        self._history_and_gaps()
        self._comparisons()
        self.asset_evidence = {}
        for identity in self.entries:
            _, asset_ids = self.index_metadata(identity)
            for asset_id in asset_ids:
                # A bounded explanatory ref, not every 13k mode using a common asset.
                self.asset_evidence.setdefault(asset_id, identity)

    def _inventory_assets(self):
        for row in self.inventory:
            identity = row["asset_id"]
            if identity in self.assets:
                continue
            missing = row["status"] == "MISSING"
            sha = row["sha256"]
            limits = [{"id": f"lim.{identity}.{i}", "code": "INVENTORY_LIMITATION", "description": text,
                       "severity": "WARNING", "affected_refs": [identity]} for i, text in enumerate(row["limitations"])]
            relative = row["relative_source_path"]
            self.assets[identity] = {"asset_id": identity, "source_id": "scientific-root-v1",
                "source_display": relative if not missing else row.get("semantic_meaning", identity),
                "relative_origin": unresolved("Authoritative raw source unavailable", "MISSING") if missing else known(relative),
                "role": "MISSING_REFERENCE" if missing else "METHOD" if row["data_format"].upper() == "PY" else "DATA",
                "format": row["data_format"], "recorded_data_hash": known(sha) if len(sha) == 64 else unresolved("No recorded asset hash", "MISSING" if missing else "UNKNOWN"),
                "current_data_hash": unresolved("Observe selected asset on demand"), "data_drift": unresolved("No current observation"),
                "verification": verification(row["status"], f"ev.inventory.{identity}", "Recorded Phase1 inventory status; no promotion to current numerical certification"),
                "canonical_selected": False, "limitations": limits}
        # Correct a historical DTO bug: protocol-lock bytes are not method-code bytes.
        protocol = self.assets["asset_8d15c3f16f95"]
        row = next(r for r in self.inventory if r["asset_id"] == protocol["asset_id"])
        protocol["recorded_data_hash"] = known(row["sha256"])
        protocol["role"] = "CONFIG"

    def _register(self, raw, section):
        identity = raw["evidence_id"]
        self.extra[identity] = raw
        self.entries[identity] = (identity, None)
        self.sections[identity] = section

    def _add_basis(self):
        method_row = next(r for r in self.inventory if r["relative_source_path"] == "solver/fluxes/cross_mode_ec_unified_v1.py")
        self.method_asset = method_row["asset_id"]
        self.assets[self.method_asset]["canonical_selected"] = True
        self.assets[self.method_asset]["source_display"] = method_row["relative_source_path"]
        self.assets[self.method_asset]["verification"]["evidence_refs"] = ["ev.method.unified-v1"]
        self._register(metadata_record("ev.method.unified-v1", unresolved("Shared implementation basis", "NOT_APPLICABLE"),
            [self.assets[self.method_asset]], status="FROZEN_VERIFIED", basis="Accepted unified method implementation identity; not a CFD numerical result", method_hash=S.METHOD_HASH), "CURRENT")
        content_assets = []
        manifest = json.loads((ROOT / "config/content/freeze_manifest.json").read_text(encoding="utf-8"))
        for name in ("mechanism.json", "scenes.json"):
            identity = "asset.content." + name.removesuffix(".json")
            self.assets[identity] = {"asset_id": identity, "source_id": "shockpath-content", "source_display": "Frozen schematic/content basis: " + name,
                "relative_origin": known("config/content/" + name), "role": "METHOD", "format": "JSON",
                "recorded_data_hash": known(manifest["sha256"][name]), "current_data_hash": unresolved("Observe on demand"),
                "data_drift": unresolved("Observe on demand"), "verification": verification("VERIFIED_NOT_FROZEN", "ev.mechanism.theory-implementation", "Frozen Phase10 schematic content; no CFD numerical claim"),
                "canonical_selected": True, "limitations": []}
            content_assets.append(self.assets[identity])
        limits = [{"id": "lim.mechanism.schematic-evidence", "code": "SCHEMATIC", "description": "Theory and implementation basis for STRICT_1D/WEAKLY_2D pathway explanation. No numeric Near1D scan or CFD result is represented.", "severity": "INFO", "affected_refs": ["mechanism.acoustic-pathways.v1"]}]
        self._register(metadata_record("ev.mechanism.theory-implementation", known("mechanism"),
            content_assets + [self.assets[self.method_asset]], status="VERIFIED_NOT_FROZEN", basis="Phase10 accepted SCHEMATIC mechanism and unified method implementation basis", limitations=limits, method_hash=S.METHOD_HASH), "CURRENT")
        self.result_evidence["mechanism.acoustic-pathways.v1"] = ["ev.mechanism.theory-implementation"]

    def _history_and_gaps(self):
        selected_paths = {a["relative_origin"].get("value") for a in self.catalog["assets"].values()}
        for row in self.inventory:
            identity = row["asset_id"]
            if row["relative_source_path"] in selected_paths or identity == self.method_asset:
                continue
            section = "GAPS" if row["status"] == "MISSING" else "HISTORY"
            # The already established Cylinder gap has one record and one identity.
            if identity == "missing_cylinder_trajectory_spatial_pi_at":
                continue
            family = {"Case8_Mach6": "case8", "Case8_external": "case8", "Case8_Gate_Ablation": "gate",
                      "Common_Mach6_Zero_Residual_Discrete_Shock": "spectrum", "Mach3_Cylinder": "cylinder",
                      "Cylinder_external": "cylinder", "Case7_Isentropic_Vortex": "entropy-closure",
                      "Near1D_Mach6": "mechanism", "Near1D_Mach6_epsilon_scan_UNVERIFIED": "mechanism"}.get(row["case"])
            raw = metadata_record(f"ev.inventory.{identity}", known(family) if family else unresolved("Historical/absent asset experiment has no canonical current binding"),
                [self.assets[identity]], status=row["status"], basis="Phase1 registered asset; outside accepted current Phase5–10 numerical selection", limitations=self.assets[identity]["limitations"])
            if len(row["method_hash"]) == 64:
                raw["method_hash"] = known(row["method_hash"])
            if row["method"] != "UNKNOWN":
                raw["method_name"] = known(row["method"])
            raw["data_hash"] = self.assets[identity]["recorded_data_hash"] if self.assets[identity]["role"] == "DATA" else unresolved("No scientific data hash for this asset role", "MISSING" if section == "GAPS" else "UNKNOWN")
            self._register(raw, section)
        for identity, experiment, code, text, status in (
            ("ev.gap.closure-spatial-trajectory", "entropy-closure", "MISSING", "Closure spatial trajectory was not saved", "MISSING"),
            ("ev.gap.case8-cylinder-front-band", "case8", "UNSUPPORTED", "Case8 has no Cylinder front-band task", "NOT_APPLICABLE"),
            ("ev.gap.modal-linear-history", "modal-validation", "MISSING", "Fig13 linear/RK3 amplitude histories were not saved", "MISSING"),
        ):
            limit = {"id": "lim." + identity, "code": code, "description": text, "severity": "WARNING", "affected_refs": []}
            self._register(metadata_record(identity, known(experiment), [], status=status, basis=text, limitations=[limit]), "GAPS")

    def _comparisons(self):
        for case in ("A_u", "B_u", "C_u", "D_u"):
            for cylinder in ("A_u", "B_u", "D_u"):
                refs = [f"ev.case8.{case}.{g}" for g in ("entropy", "metrics")]
                if case == "D_u":
                    refs.append("ev.case8.D_u.allocation")
                refs += [f"ev.cylinder.{cylinder}.{g}" for g in ("protocol", "snapshots", "history", "sectors", "front-band", "metrics")]
                refs += ["ev.missing.cylinder-cumulative2d"]
                self.result_evidence[f"case8-cylinder.{case}.{cylinder}"] = refs
        for rid in ("gate.comparison.min", "gate.comparison.max"):
            self.result_evidence[rid] = [f"ev.gate.{c}.allocation" for c in ("Acoustic", "Pressure", "Ungated")]

    def record(self, identity):
        if identity in self.extra:
            return deepcopy(self.extra[identity])
        template, rid = self.entries[identity]
        raw = deepcopy(self.catalog["records"][template])
        raw["source_assets"] = [deepcopy(self.assets[a]) for a in raw.pop("asset_refs")]
        raw["config"] = deepcopy(self.catalog["configs"][raw.pop("config_ref")])
        raw["result_contexts"] = [deepcopy(self.catalog["contexts"][r]) for r in raw.pop("context_refs")]
        if rid is not None:
            old = raw["result_ids"][0]
            def replace(node):
                if isinstance(node, str):
                    return node.replace(PREFIX + old, PREFIX + rid).replace(old, rid)
                if isinstance(node, dict):
                    return {key: replace(value) for key, value in node.items()}
                if isinstance(node, list):
                    return [replace(item) for item in node]
                return node
            raw = replace(raw)
        raw["evidence_id"] = identity
        # Every Case8/Gate allocation includes the actual method, separately from data.
        if identity.startswith(("ev.case8.", "ev.gate.")):
            ids = {a["asset_id"] for a in raw["source_assets"]}
            if self.method_asset not in ids:
                raw["source_assets"].append(deepcopy(self.assets[self.method_asset]))
            raw["related_evidence_refs"] = ["ev.method.unified-v1"]
        return raw

    def index_metadata(self, identity):
        """Small index projection; do not expand full contexts to list records."""
        template, rid = self.entries[identity]
        raw = self.extra.get(identity) or self.catalog["records"][template]
        asset_ids = raw.get("asset_refs", [a["asset_id"] for a in raw.get("source_assets", [])])
        if identity.startswith(("ev.case8.", "ev.gate.")):
            asset_ids = list(dict.fromkeys([*asset_ids, self.method_asset]))
        return {"evidence_id": identity, "result_ids": [rid] if rid else raw["result_ids"],
                "experiment_id": raw["experiment_id"], "title": identity,
                "verification": raw["verification"], "limitations": raw["limitations"]}, asset_ids
