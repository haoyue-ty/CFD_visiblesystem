"""Flask-independent AllocationService interface plus its DI dispatch wrapper.

Phase 6A froze the Protocol only. Window 3 adds `AllocationServiceImpl`, a thin
Flask-independent seam that adapts an optional `AllocationAdapterProtocol` to the
HTTP layer and maps adapter failures onto the three typed allocation errors:

* MISSING_ASSET            -> 404 a recognized identity whose saved asset is absent
* UNSUPPORTED_REPRESENTATION -> 422 the requested representation is not renderable
* SOURCE_ERROR             -> 500 the controlled source could not be read faithfully

The wrapper never opens a path, never guesses face/cell, and revalidates every
canonical model so an adapter cannot bypass the frozen validators.
"""
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from backend.adapters.allocation import AllocationAdapterProtocol, AllocationDescription
from backend.core.errors import (missing_asset, source_error, system_error,
                                 unsupported_representation)
from backend.models.allocation import (AllocationArrayResponse, AllocationComparison,
                                       AllocationComparisonEntry, AllocationMetadata,
                                       AllocationResult, AllocationSummary)
from backend.models.evidence import MaskSpec
from backend.models.results import ArrayRef, ScientificArray


@runtime_checkable
class AllocationService(AllocationAdapterProtocol, Protocol):
    """Shared interface for Case8 D_u and the three Gate variants."""


class AllocationServiceImpl:
    """Concrete dispatch for the four allocation endpoints.

    A missing adapter is a delivery gap (503 FEATURE_NOT_ENABLED), not a scientific
    failure: the capability is advertised only once a loader is wired in.
    """

    def __init__(self, adapter: AllocationAdapterProtocol | None):
        self.adapter = adapter

    def _call(self, method: str, model: type[BaseModel], *args, **kwargs):
        value = self._call_raw(method, *args, **kwargs)
        payload = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
        return model.model_validate(payload)

    def _call_raw(self, method: str, *args, **kwargs):
        """Invoke the adapter and map its failures onto the typed allocation errors."""
        if self.adapter is None:
            raise system_error("FEATURE_NOT_ENABLED", "Allocation adapter has not been delivered",
                               status=503, retryable=True)
        handler = getattr(self.adapter, method, None)
        if handler is None:
            raise system_error("FEATURE_NOT_ENABLED",
                               "Allocation adapter does not implement this capability",
                               status=503, retryable=True)
        try:
            return handler(*args, **kwargs)
        except KeyError:
            raise missing_asset("Requested allocation identity is not registered",
                                resource_type="allocation",
                                identity=None) from None
        except NotImplementedError:
            raise unsupported_representation(
                "Requested allocation representation is not implemented by this adapter",
                resource_type="allocation", identity=None) from None
        except (FileNotFoundError, OSError):
            raise source_error("Recorded allocation source could not be read", retryable=False) from None

    # --- AllocationService interface -------------------------------------------

    def describe_allocation(self, experiment_id: str, config_id: str, *,
                            registry_revision: str | None = None) -> AllocationDescription:
        return self._call("describe_allocation", AllocationDescription,
                          experiment_id, config_id, registry_revision=registry_revision)

    def load_allocation_metadata(self, result_id: str, *,
                                 registry_revision: str | None = None) -> AllocationResult:
        return self._call("load_allocation_metadata", AllocationResult, result_id,
                          registry_revision=registry_revision)

    def load_allocation_array(self, result_id: str, array_id: str, *,
                              registry_revision: str | None = None) -> ScientificArray:
        return self._call("load_allocation_array", ScientificArray, result_id, array_id,
                          registry_revision=registry_revision)

    def load_mask(self, mask_id: str, *,
                  registry_revision: str | None = None) -> MaskSpec:
        return self._call("load_mask", MaskSpec, mask_id, registry_revision=registry_revision)

    def load_summary_metrics(self, result_id: str, *,
                             registry_revision: str | None = None) -> AllocationSummary:
        return self._call("load_summary_metrics", AllocationSummary, result_id,
                          registry_revision=registry_revision)

    # --- HTTP-facing projections -----------------------------------------------

    def describe_capability(self, result_id: str, *,
                            registry_revision: str | None = None) -> AllocationMetadata:
        """Registered identity metadata; never loads arrays."""
        return self._call("load_allocation_metadata_view", AllocationMetadata, result_id,
                          registry_revision=registry_revision)

    def load_comparison(self, experiment_id: str, *,
                        representation_type: str | None = None,
                        registry_revision: str | None = None) -> AllocationComparison:
        """Multi-variant comparison; the adapter owns variant discovery and extent."""
        return self._call("load_allocation_comparison", AllocationComparison, experiment_id,
                          representation_type=representation_type,
                          registry_revision=registry_revision)

    def load_array_view(self, result_id: str, array_id: str, *,
                        registry_revision: str | None = None) -> AllocationArrayResponse:
        """HTTP shape for one allocation array.

        The frozen ``AllocationService.load_allocation_array`` returns a bare
        ``ScientificArray`` and carries no representation header. The HTTP layer must
        always advertise ``representation_type``, so an allocation adapter that can
        speak the richer DTO returns ``AllocationArrayResponse`` directly; a bare
        ``ScientificArray`` is upgraded using the registered metadata identity.
        """
        raw = self._call_raw("load_allocation_array", result_id, array_id,
                             registry_revision=registry_revision)
        if isinstance(raw, AllocationArrayResponse):
            return AllocationArrayResponse.model_validate(raw.model_dump(mode="python"))
        scientific = ScientificArray.model_validate(
            raw.model_dump(mode="python") if isinstance(raw, BaseModel) else raw)
        metadata = self.describe_capability(scientific.result.result_id,
                                            registry_revision=registry_revision)
        return AllocationArrayResponse(
            result=scientific.result,
            representation_type=metadata.representation_type,
            field_id=scientific.descriptor.array_id,
            array_ref=ArrayRef(result_id=scientific.result.result_id, descriptor=scientific.descriptor),
            values=list(scientific.values),
        )
