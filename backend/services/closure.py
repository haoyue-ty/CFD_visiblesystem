"""Flask-independent ClosureService scientific core (frozen CLO01..05).

No application activation or API paths are introduced in Window 1.
"""
from pydantic import BaseModel

from backend.adapters.entropy_closure import EntropyClosureAdapterProtocol
from backend.core.errors import DomainError, system_error
from backend.models.closure import ClosureHistory, ClosureRunRegistry, EntropyClosureRun, RefinementSummary
from backend.models.evidence import EvidenceRecord, ResultProvenance
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

    @staticmethod
    def _identity(condition):
        if not condition:
            raise system_error("CANONICAL_SCHEMA_MISMATCH", "Closure adapter returned a different scientific selection")

    def load_evidence(self, evidence_id: str) -> EvidenceRecord:
        return self._call("load_evidence", EvidenceRecord, evidence_id)

    def load_provenance(self, result_id: str) -> ResultProvenance:
        return self._call("load_provenance", ResultProvenance, result_id)
