"""Spectral extension protocol only: no file access or concrete adapter.

Implementers resolve exact registered identities at one pinned revision through
the registry, preserve verification and separate method/data hashes, and return
typed ResourceSlot failures. API/service code must use this boundary and may not
open files. No paths, free q, arbitrary time, formula or NPZ member inputs exist.
"""
from typing import Protocol, runtime_checkable

from backend.models.core import ResourceSlot
from backend.models.spectral import (ComplexProjection, Eigenmode,
                                     EigenRepresentation, EigenSide,
                                     GrowthValidation, SpectrumDataset,
                                     SpectralPoints)


@runtime_checkable
class SpectralAdapterProtocol(Protocol):
    def list_spectral_datasets(self, *, registry_revision: str | None = None) -> list[SpectrumDataset]: ...

    def describe_spectrum(self, dataset_id: str, *, registry_revision: str | None = None) -> ResourceSlot[SpectrumDataset]: ...

    def load_spectral_points(self, dataset_id: str, *, registry_revision: str | None = None) -> ResourceSlot[SpectralPoints]: ...

    def load_eigenmode(self, dataset_id: str, mode_index: int, *, side: EigenSide = "RIGHT",
                       rank: int = 0, representation: EigenRepresentation = "COMPLEX_VECTOR",
                       projection: ComplexProjection = "COMPLEX", field_component: str = "stored_vector",
                       registry_revision: str | None = None) -> ResourceSlot[Eigenmode]: ...

    def load_growth_validation(self, run_id: str, *, registry_revision: str | None = None) -> ResourceSlot[GrowthValidation]: ...
