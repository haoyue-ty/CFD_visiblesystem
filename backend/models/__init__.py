"""Single canonical import surface for the Case8 slice and its dependencies."""
from .core import *
from .context import *
from .experiments import *
from .results import *

# Resolve the spatial/array reference cycle before importing evidence DTOs.
for _model in (AxisDescriptor, SpatialDomain):
    _model.model_rebuild(_types_namespace={"ArrayRef": ArrayRef})

from .evidence import *
from .transport import *
from .allocation import (AllocationArrayResponse, AllocationComparison,
                         AllocationComparisonEntry, AllocationMetadata,
                         AllocationRepresentation, AllocationResult,
                         AllocationSummary, CellAllocation, FaceAllocation,
                         MeasureDefinition, WIRE_REPRESENTATION)
from .spectral_api import (EigenmodeView, GrowthErrorView, GrowthRatesView,
                           GrowthValidationView, SpectralHeader,
                           SpectralNormalizationView, SpectralPointView,
                           SpectrumCurveView, SpectrumDatasetView,
                           ValidationRunListView, ValidationRunView,
                           project_curve, project_dataset, project_eigenmode,
                           project_point, project_validation,
                           project_validation_runs)

CORE_MODELS = (
    UnitSpec, ScientificLimitation, Verification, ProvenanceRef, ScientificResult,
    ErrorBody, ProjectInfo, ExperimentRef, Experiment, ExperimentConfig,
    ExperimentCapability, ConfigCapability, ControlSpec, ProtocolSpec, GridSpec,
    FieldSnapshot, FieldDescriptor, SnapshotIndex, ArrayDescriptor, ArrayRef,
    ScientificArray, ScalarPoint, ScalarSeries, EntropyHistory, SnapshotAlignment,
    Metric, MetricCollection, DetectorSpec, EvidenceRecord, EvidenceIndexItem,
    ResultProvenance, SourceAsset, SourceObservation, FreezeReference,
    ProcessingRecord, ScopeSpec, TimeSpec, SpatialDomain, ScientificDefinition,
    Fact[Number], HashFact, ResourceSlot[Metric], ApiEnvelope[ProjectInfo],
    AllocationResult, AllocationSummary, AllocationMetadata,
    AllocationArrayResponse, AllocationComparison, AllocationComparisonEntry,
    # Phase 7B Window 2 spectral public DTOs; Window 3 adds the run selector list.
    SpectrumDatasetView, SpectrumCurveView, SpectralPointView, EigenmodeView,
    GrowthValidationView, ValidationRunListView, ValidationRunView,
)
