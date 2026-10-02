"""Flask-independent ClosureService scientific core (frozen CLO01..05).

No application activation or API paths are introduced in Window 1.
"""
from pydantic import BaseModel

from backend.adapters.entropy_closure import EntropyClosureAdapterProtocol
from backend.core.errors import DomainError, system_error
from backend.models.closure import ClosureHistory, ClosureRunRegistry, EntropyClosureRun, RefinementSummary
from backend.models.evidence import EvidenceRecord, ResultProvenance
from backend.models import CapabilityList, ConfigList, Experiment, known
from backend.registry import closure_registry as R


class ClosureService:
    def __init__(self, adapter: EntropyClosureAdapterProtocol | None):
        self.adapter = adapter

    def _call(self, method, model: type[BaseModel], *args, **kwargs):
        if self.adapter is None:
            raise system_error("FEATURE_NOT_ENABLED", "Closure scientific adapter is not enabled", status=503, retryable=True)
        try:
            value = getattr(self.adapter, method)(*args, **kwargs)
            return model.model_validate(value.model_dump(mode="python") if isinstance(value, BaseModel) else value)
        except DomainError:
            raise
        except FileNotFoundError:
            raise system_error("MISSING_SCIENTIFIC_ASSET", "Registered closure scientific source is absent", status=404, availability="MISSING") from None
        except OSError:
            raise system_error("SOURCE_READ_ERROR", "Saved closure scientific source could not be read") from None
        except (ValueError, TypeError, KeyError, AssertionError, IndexError):
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Closure scientific result failed canonical validation") from None

    def list_runs(self) -> ClosureRunRegistry:
        registry = self._call("list_runs", ClosureRunRegistry)
        if tuple(run.run_id for run in registry.runs) != R.RUN_IDS:
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Closure registry must contain the exact five frozen runs")
        return registry

    def load_run(self, run_id: str) -> EntropyClosureRun:
        R.require_run(run_id)
        run = self._call("load_run", EntropyClosureRun, run_id)
        self._identity(run.run_id == run_id)
        return run

    def load_stage_history(self, run_id: str, *, series=None, offset=0, limit=2000) -> ClosureHistory:
        R.require_run(run_id)
        history = self._call("load_stage_history", ClosureHistory, run_id, series=series, offset=offset, limit=limit)
        self._identity(history.run_id == run_id and history.granularity == "PER_STAGE")
        return history

    def load_step_history(self, run_id: str, *, series=None, offset=0, limit=2000) -> ClosureHistory:
        R.require_run(run_id)
        history = self._call("load_step_history", ClosureHistory, run_id, series=series, offset=offset, limit=limit)
        self._identity(history.run_id == run_id and history.granularity == "PER_STEP")
        return history

    def load_refinement(self) -> RefinementSummary:
        summary = self._call("load_refinement", RefinementSummary)
        self._identity(summary.comparison_id == R.COMPARISON_ID and summary.run_ids == list(R.RUN_IDS[:4]))
        return summary

    def list_configs(self) -> ConfigList:
        return ConfigList(experiment_id="entropy-closure", items=[run.config for run in self.list_runs().runs])

    @staticmethod
    def _capabilities(registry) -> CapabilityList:
        items = []
        for task in ("overview", "semi-discrete", "fully-discrete", "evidence", "flow", "allocation", "spectrum"):
            status = "MISSING" if task == "flow" else "UNSUPPORTED" if task in ("allocation", "spectrum") else "SUPPORTED"
            supported = status == "SUPPORTED"
            refs_by_run, evidence = {}, []
            for run in registry.runs:
                refs = []
                if task in ("overview", "evidence"):
                    refs = [slot.root.value.result.result_id for slot in run.terminal_summary]
                    evidence.extend(run.evidence_refs)
                elif task == "semi-discrete":
                    refs = run.stage_series_refs
                    evidence.append(R.evidence_id(run.run_id, "stage"))
                elif task == "fully-discrete":
                    refs = list(run.step_series_refs)
                    evidence.append(R.evidence_id(run.run_id, "step"))
                    if run.run_id in R.RUN_IDS[:4]:
                        refs.append(R.result_id(run.run_id, "refinement", "R_total"))
                        evidence.append(R.REFINEMENT_EVIDENCE)
                refs_by_run[run.run_id] = refs
            reason = ("Saved frozen scalar diagnostics for the exact five-run selection" if supported else
                      "No saved spatial trajectory" if task == "flow" else "No frozen Closure capability for this task")
            items.append({
                "id": f"cap.entropy-closure.{task}", "experiment_id": "entropy-closure", "task": task,
                "status": status, "available_for_configs": list(R.RUN_IDS) if supported else [],
                "config_support": [{"config_id": run, "status": status, "reason": reason, "result_refs": refs}
                                   for run, refs in refs_by_run.items()],
                "controls": [{"name": "run", "kind": "ENUM", "allowed_values": list(R.RUN_IDS),
                              "combination_registry_ref": known(R.REGISTRY_REVISION)}] if supported else [],
                "tab_policy": {"tab_id": task, "visible_for_family": supported,
                               "disabled_for_configs": [] if supported else list(R.RUN_IDS),
                               "unsupported_deep_link_behavior": "EXPLAIN"},
                "result_refs": [ref for refs in refs_by_run.values() for ref in refs],
                "limitations": R.LIMITATIONS, "evidence_refs": list(dict.fromkeys(evidence)),
            })
        return CapabilityList.model_validate({"experiment_id": "entropy-closure", "items": items})

    def describe_capabilities(self) -> CapabilityList:
        return self._capabilities(self.list_runs())

    def describe_experiment(self) -> Experiment:
        registry = self.list_runs()
        return Experiment.model_validate({
            "schema_version": "1.0.0", "id": "entropy-closure", "name": "Entropy Closure",
            "scientific_family": "ENTROPY_CLOSURE",
            "description": "Frozen periodic Case7 semi-discrete closure and fully-discrete temporal diagnostics; existing D_u refinement.",
            "capabilities": self._capabilities(registry).items, "available_configs": [run.config for run in registry.runs],
            "status": "AVAILABLE", "delivery_status": "IMPLEMENTED", "limitations": R.LIMITATIONS,
            "evidence_refs": [ev for run in registry.runs for ev in run.evidence_refs] + [R.REFINEMENT_EVIDENCE],
            "related_experiment_ids": [],
        })

    @staticmethod
    def _identity(condition):
        if not condition:
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Closure adapter returned a different scientific selection")

    def load_evidence(self, evidence_id: str) -> EvidenceRecord:
        return self._call("load_evidence", EvidenceRecord, evidence_id)

    def load_provenance(self, result_id: str) -> ResultProvenance:
        return self._call("load_provenance", ResultProvenance, result_id)
