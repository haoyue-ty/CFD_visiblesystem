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
)
