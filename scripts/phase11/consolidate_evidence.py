"""Extract canonical provenance metadata from accepted Phase5–10 readers.

Only EvidenceRecord headers/definitions are persisted, never numeric payloads.
The catalog is an explicit software registry, not a new scientific freeze.
Spectral mode/rank metadata shares templates because those selectors change
identity, not the saved source dependency set. Runtime reobserves all sources.
"""
import json
from pathlib import Path

from backend import create_app
from backend.models import EvidenceRecord, known, unresolved
from backend.registry import case8_source_constants as C, case8_semantics as S
from backend.registry import spectral_registry as R
from backend.services.closure_resources import EVIDENCE_IDS as CLOSURE
from backend.services.cylinder_resources import EVIDENCE_IDS as CYLINDER
from backend.services.spectral_resources import PREFIX

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data/evidence/canonical_metadata.json"


def main():
    app = create_app()
    resources = app.extensions["result_resources"]
    allocation = app.extensions["allocation_service"]
    records, assets, configs, contexts = {}, {}, {}, {}
    inventory = json.loads((ROOT / "data/data_asset_inventory.json").read_text(encoding="utf-8"))
    by_path = {a["relative_source_path"]: a for a in inventory["assets"]}

    def add(record):
        p = record.model_dump(mode="json")
        # Capture no transient observation as a persisted scientific event.
        def clear(node):
            if isinstance(node, dict):
                for key, value in list(node.items()):
                    if key == "observation_at":
                        node[key] = unresolved("Observed on demand; no persisted scientific observation event")
                    else:
                        clear(value)
            elif isinstance(node, list):
                for item in node:
                    clear(item)
        clear(p)
        p["source_observations"] = []
        p["source_drift"] = unresolved("Observe all registered dependencies before asserting no drift")
        for asset in p["source_assets"]:
            origin = asset["relative_origin"].get("value", "").replace("\\", "/")
            # Phase1 recorded inventory is a baseline, never a hash of today's bytes.
            baseline = by_path.get(origin)
            if baseline and asset["recorded_data_hash"]["state"] == "UNKNOWN" and baseline["sha256"] != "UNKNOWN":
                asset["recorded_data_hash"] = known(baseline["sha256"])
            asset["current_data_hash"] = unresolved("Runtime observation required")
            asset["data_drift"] = unresolved("Runtime comparison required")
            assets[asset["asset_id"]] = asset
        p["asset_refs"] = [a["asset_id"] for a in p.pop("source_assets")]
        # Composite data hashes have no authoritative upstream definition.
        if p["evidence_id"].startswith(("ev.cylinder.", "ev.entropy-closure.")):
            p["data_hash"] = unresolved("No authoritative composite data hash recorded")
        config = p.pop("config")
        config_key = p["evidence_id"]
        configs[config_key] = config
        p["config_ref"] = config_key
        for context in p.pop("result_contexts"):
            contexts[context["result_id"]] = context
        p["context_refs"] = list(p["result_ids"])
        records[p["evidence_id"]] = p

    for config in C.CONFIG_ORDER:
        for group in ("entropy", "metrics"):
            add(resources.load_evidence(f"ev.case8.{config}.{group}"))
        for index in range(1, 7):
            base = resources.load_evidence(f"ev.case8.{config}.snapshot.{index}")
            add(base)
            for field in S.FIELD_SEMANTICS:
                selected = next(r for r in base.result_contexts if r.result_id.endswith("." + field))
                p = base.model_dump(mode="python")
                p.update(evidence_id=f"ev.case8.{config}.snapshot.{index}.{field}",
                         result_ids=[selected.result_id], result_contexts=[selected])
                add(EvidenceRecord.model_validate(p))
        print("Case8 metadata:", config, flush=True)
    for identity in ("ev.case8.D_u.allocation", *(f"ev.gate.{c}.allocation" for c in ("Acoustic", "Pressure", "Ungated"))):
        add(allocation.load_evidence(identity))
    for identity in sorted(CYLINDER | CLOSURE):
        add(resources.load_evidence(identity))
        print("Metadata:", identity, flush=True)
    # Exhaustive spectrum selector coverage uses a small set of exact header templates.
    spectral_templates = {}
    for dataset in R.DATASETS:
        selected = {"dataset": dataset, "point": R.record_id(dataset, 0)}
        for side in ("LEFT", "RIGHT"):
            selected[side] = R.eigenmode_id(dataset, 0, side, 0)
        for component in ("density", "u", "v", "pressure"):
            selected[component] = R.eigenmode_id(dataset, 0, "RIGHT", 0, "PRIMITIVE_PROFILE", component)
        for kind, rid in selected.items():
            identity = PREFIX + rid
            add(resources.load_evidence(identity))
            spectral_templates[f"{dataset}.{kind}"] = identity
        print("Spectral metadata templates:", dataset, flush=True)
    for run in R.RUNS:
        add(resources.load_evidence(PREFIX + run + ".history"))
    # Complete Gate comparison provenance uses its existing min/max headers.
    comparison = allocation.load_comparison("gate", representation_type="CELL_FIELD")
    for slot in comparison.shared_extent:
        header = slot.root.value.result.model_dump(mode="json")
        contexts[header["result_id"]] = header
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"schema_version": "1.0.0", "accepted_base": "884bcd382f8d6fe67062e779ce37bbeeebe7816f",
        "records": records, "assets": assets, "configs": configs, "contexts": contexts,
        "spectral_templates": spectral_templates}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("Saved metadata only:", len(records), "templates/groups;", len(assets), "assets", flush=True)


if __name__ == "__main__":
    main()
