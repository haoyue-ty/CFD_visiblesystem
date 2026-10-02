"""Bridge accepted Gate/Spectral metadata to existing REG01–04 operations.

Only software metadata is composed; configs are the existing Evidence catalog
objects. No scientific values, hashes, fits or sources are generated here.
"""
from backend.models import CapabilityList, ConfigList, Experiment, ExperimentConfig


class WorkspaceMetadata:
    def __init__(self, identity, catalog):
        self.identity = identity
        configs = {}
        refs = []
        for key, fact in catalog["configs"].items():
            if fact["state"] == "KNOWN" and fact["value"]["experiment_id"] == identity:
                config = ExperimentConfig.model_validate(fact["value"])
                if config.id not in configs:
                    refs.append(key)
                configs.setdefault(config.id, config)
        self.configs = list(configs.values())
        self.evidence_refs = refs
        if not self.configs:
            raise ValueError("Delivered workspace requires existing canonical configurations")

    def list_configs(self):
        return ConfigList(experiment_id=self.identity, items=self.configs)

    def describe_capabilities(self):
        tasks = {"gate": ("allocation",), "spectrum": ("spectrum", "modes", "validation"),
                 "modal-validation": ("validation",)}[self.identity]
        ids = [c.id for c in self.configs]
        refs = self.evidence_refs
        items = [{"id": f"cap.{self.identity}.{tab}", "experiment_id": self.identity,
            "task": tab.upper(), "status": "SUPPORTED", "available_for_configs": ids,
            "config_support": [{"config_id": id, "status": "SUPPORTED",
                "reason": "Existing recorded workspace selection; resource failures remain explicit", "result_refs": []} for id in ids],
            "controls": [], "tab_policy": {"tab_id": tab, "visible_for_family": True,
                "disabled_for_configs": [], "unsupported_deep_link_behavior": "EXPLAIN"},
            "result_refs": [], "limitations": [], "evidence_refs": refs} for tab in ("overview", *tasks, "evidence")]
        return CapabilityList(experiment_id=self.identity, items=items)

    def describe_experiment(self):
        names = {"gate": "Gate Ablation", "spectrum": "Spectrum", "modal-validation": "Modal Validation"}
        descriptions = {"gate": "Three frozen static cumulative cell maps; approximately matched budgets do not imply the same allocation.",
            "spectrum": "Four recorded q_at configurations; complete ell 0…16 range, saved modes and modal validation. Serialized matrices MISSING.",
            "modal-validation": "24 recorded runs with 33 projected-amplitude points each; no spatial CFD movie or saved linear amplitude history."}
        return Experiment(schema_version="1.0.0", id=self.identity, name=names[self.identity],
            scientific_family=self.identity, description=descriptions[self.identity],
            capabilities=self.describe_capabilities().items, available_configs=self.configs,
            status="AVAILABLE", delivery_status="IMPLEMENTED", limitations=[],
            evidence_refs=self.evidence_refs,
            related_experiment_ids=["modal-validation"] if self.identity == "spectrum" else [])
