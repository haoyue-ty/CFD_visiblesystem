"""Case8 canonical semantic registry.

Preserves the original scientific names, definitions, detectors, time scopes and
units declared in ``docs/05_DATA_SCHEMA.md`` section 8.1. Definitions are never
renamed or unified; a metric that is not stored is reported as MISSING rather
than synthesised.
"""
from __future__ import annotations

from typing import Final

from backend.models.core import known, unresolved

# --------------------------------------------------------------------------
# Units (MODEL system; no established SI mapping -> si_mapping UNKNOWN)
# --------------------------------------------------------------------------
UNIT_MODEL_LENGTH: Final[dict] = {
    "id": "model_length",
    "system": "MODEL",
    "quantity": "length",
    "label": "model length",
    "si_mapping": unresolved("No established SI mapping"),
}
UNIT_MODEL_DENSITY: Final[dict] = {
    "id": "model_density",
    "system": "MODEL",
    "quantity": "density",
    "label": "model density",
    "si_mapping": unresolved("No established SI mapping"),
}
UNIT_MODEL_PRESSURE: Final[dict] = {
    "id": "model_pressure",
    "system": "MODEL",
    "quantity": "pressure",
    "label": "model pressure",
    "si_mapping": unresolved("No established SI mapping"),
}
UNIT_MODEL_ENTROPY: Final[dict] = {
    "id": "model_integrated_entropy",
    "system": "MODEL",
    "quantity": "integrated entropy",
    "label": "model integrated entropy",
    "si_mapping": unresolved("No established SI mapping"),
}
UNIT_MODEL_ENERGY: Final[dict] = {
    "id": "model_energy",
    "system": "MODEL",
    "quantity": "energy",
    "label": "model energy",
    "si_mapping": unresolved("No established SI mapping"),
}
UNIT_FRACTION: Final[dict] = {
    "id": "dimensionless_fraction",
    "system": "DIMENSIONLESS",
    "quantity": "fraction",
    "label": "dimensionless fraction",
    "si_mapping": unresolved("Dimensionless quantity", "NOT_APPLICABLE"),
}
UNIT_CATEGORICAL: Final[dict] = {
    "id": "categorical",
    "system": "UNKNOWN",
    "quantity": "gate category",
    "label": "category",
    "si_mapping": unresolved("Categorical parameter", "NOT_APPLICABLE"),
}
UNIT_DIMENSIONLESS: Final[dict] = {
    "id": "dimensionless",
    "system": "DIMENSIONLESS",
    "quantity": "coefficient",
    "label": "dimensionless",
    "si_mapping": unresolved("Dimensionless coefficient", "NOT_APPLICABLE"),
}
UNIT_CFL: Final[dict] = {
    "id": "dimensionless_cfl",
    "system": "DIMENSIONLESS",
    "quantity": "CFL",
    "label": "dimensionless",
    "si_mapping": unresolved("Dimensionless ratio", "NOT_APPLICABLE"),
}

# --------------------------------------------------------------------------
# Stored flow fields (present as members of every Case8 checkpoint)
# --------------------------------------------------------------------------
STORED_FLOW_FIELDS: Final[tuple[str, ...]] = ("density", "pressure", "front")

FIELD_SEMANTICS: Final[dict[str, dict]] = {
    "density": {
        "field_id": "density",
        "label": "Density (model units)",
        "semantic_id": "density",
        "location_type": "CARTESIAN_CELL",
        "axes": ("y", "x"),
        "shape": (32, 128),
        "unit": UNIT_MODEL_DENSITY,
        "definition": "Saved primitive density member on the recorded Cartesian grid",
        "time_rule": "Recorded accepted-step endpoint; six snapshots only",
        "spatial_rule": "Cell-centered [y,x], 32x128",
    },
    "pressure": {
        "field_id": "pressure",
        "label": "Pressure (model units)",
        "semantic_id": "pressure",
        "location_type": "CARTESIAN_CELL",
        "axes": ("y", "x"),
        "shape": (32, 128),
        "unit": UNIT_MODEL_PRESSURE,
        "definition": "Saved primitive pressure member on the recorded Cartesian grid",
        "time_rule": "Recorded accepted-step endpoint; six snapshots only",
        "spatial_rule": "Cell-centered [y,x], 32x128",
    },
    "front": {
        "field_id": "front",
        "label": "Shock front position (model length)",
        "semantic_id": "front",
        "location_type": "CARTESIAN_ROW",
        "axes": ("y",),
        "shape": (32,),
        "unit": UNIT_MODEL_LENGTH,
        "definition": "Saved per-row shock front x-position member",
        "time_rule": "Recorded accepted-step endpoint; six snapshots only",
        "spatial_rule": "Row profile [y], 32",
    },
}

# Members that exist in the source checkpoint NPZ but are deliberately NOT
# exposed as first-slice fields (kept for capability reporting only).
OTHER_CHECKPOINT_MEMBERS: Final[tuple[str, ...]] = (
    "conservative_state", "primitive", "width", "front_displacement",
    "front_modes", "front_amplitude", "front_energy",
    "transverse_modes", "transverse_amplitude", "transverse_energy",
    "step", "time",
)

# --------------------------------------------------------------------------
# Entropy history series (source columns, preserved names)
# --------------------------------------------------------------------------
# aggregation distinguishes cumulative vs step increment vs stage aggregate.
HISTORY_SERIES: Final[dict[str, dict]] = {
    "E_bg_cumulative": {
        "series_id": "E_bg_cumulative", "source_column": "E_bg",
        "definition_id": "E_bg_cumulative", "label": "E_bg cumulative",
        "aggregation": "CUMULATIVE", "unit": UNIT_MODEL_ENTROPY,
    },
    "E_aa_cumulative": {
        "series_id": "E_aa_cumulative", "source_column": "E_aa",
        "definition_id": "E_aa_cumulative", "label": "E_aa cumulative",
        "aggregation": "CUMULATIVE", "unit": UNIT_MODEL_ENTROPY,
    },
    "E_at_cumulative": {
        "series_id": "E_at_cumulative", "source_column": "E_at",
        "definition_id": "E_at_cumulative", "label": "E_at cumulative",
        "aggregation": "CUMULATIVE", "unit": UNIT_MODEL_ENTROPY,
    },
    "E_bg_step": {
        "series_id": "E_bg_step", "source_column": "deltaE_bg",
        "definition_id": "E_bg_step", "label": "E_bg step increment",
        "aggregation": "STEP_INCREMENT", "unit": UNIT_MODEL_ENTROPY,
    },
    "E_aa_step": {
        "series_id": "E_aa_step", "source_column": "deltaE_aa",
        "definition_id": "E_aa_step", "label": "E_aa step increment",
        "aggregation": "STEP_INCREMENT", "unit": UNIT_MODEL_ENTROPY,
    },
    "E_at_step": {
        "series_id": "E_at_step", "source_column": "deltaE_at",
        "definition_id": "E_at_step", "label": "E_at step increment",
        "aggregation": "STEP_INCREMENT", "unit": UNIT_MODEL_ENTROPY,
    },
}

# Stage-aggregate columns exist but are retained as stage aggregate refs only.
STAGE_AGGREGATE_COLUMNS: Final[tuple[str, ...]] = (
    "dotE_bg_s0", "dotE_bg_s1", "dotE_bg_s2",
    "dotE_aa_s0", "dotE_aa_s1", "dotE_aa_s2",
    "dotE_at_s0", "dotE_at_s1", "dotE_at_s2",
)

# --------------------------------------------------------------------------
# Scientific definitions (bound to section 8.1 semantics)
# --------------------------------------------------------------------------
DEFINITIONS: Final[dict[str, dict]] = {
    "E_bg_cumulative": {
        "id": "E_bg_cumulative", "semantic_id": "E_bg_cumulative",
        "title": "Background entropy, cumulative",
        "definition": "Accepted-step cumulative background entropy column E_bg",
        "time_rule": "PER_STEP accumulated to accepted-step endpoint",
        "spatial_rule": "Fixed boundary/face scope; not a spatial field",
        "unit": UNIT_MODEL_ENTROPY, "mask_refs": [], "detector": unresolved("Direct integrated budget column", "NOT_APPLICABLE"),
    },
    "E_aa_cumulative": {
        "id": "E_aa_cumulative", "semantic_id": "E_aa_cumulative",
        "title": "q_aa channel entropy, cumulative",
        "definition": "Accepted-step cumulative q_aa channel entropy column E_aa",
        "time_rule": "PER_STEP accumulated to accepted-step endpoint",
        "spatial_rule": "Fixed boundary/face scope; not a spatial field",
        "unit": UNIT_MODEL_ENTROPY, "mask_refs": [], "detector": unresolved("Direct integrated budget column", "NOT_APPLICABLE"),
    },
    "E_at_cumulative": {
        "id": "E_at_cumulative", "semantic_id": "E_at_cumulative",
        "title": "q_at channel entropy, cumulative",
        "definition": "Accepted-step cumulative q_at channel entropy column E_at",
        "time_rule": "PER_STEP accumulated to accepted-step endpoint",
        "spatial_rule": "Fixed boundary/face scope; not a spatial field",
        "unit": UNIT_MODEL_ENTROPY, "mask_refs": [], "detector": unresolved("Direct integrated budget column", "NOT_APPLICABLE"),
    },
    "E_bg_step": {
        "id": "E_bg_step", "semantic_id": "E_bg_step",
        "title": "Background entropy, step increment",
        "definition": "Per-step RK-weighted background entropy increment deltaE_bg",
        "time_rule": "PER_STEP increment (not the cumulative curve itself)",
        "spatial_rule": "Fixed boundary/face scope; not a spatial field",
        "unit": UNIT_MODEL_ENTROPY, "mask_refs": [], "detector": unresolved("Derived step increment column", "NOT_APPLICABLE"),
    },
    "E_aa_step": {
        "id": "E_aa_step", "semantic_id": "E_aa_step",
        "title": "q_aa channel entropy, step increment",
        "definition": "Per-step RK-weighted q_aa entropy increment deltaE_aa",
        "time_rule": "PER_STEP increment (not the cumulative curve itself)",
        "spatial_rule": "Fixed boundary/face scope; not a spatial field",
        "unit": UNIT_MODEL_ENTROPY, "mask_refs": [], "detector": unresolved("Derived step increment column", "NOT_APPLICABLE"),
    },
    "E_at_step": {
        "id": "E_at_step", "semantic_id": "E_at_step",
        "title": "q_at channel entropy, step increment",
        "definition": "Per-step RK-weighted q_at entropy increment deltaE_at",
        "time_rule": "PER_STEP increment (not the cumulative curve itself)",
        "spatial_rule": "Fixed boundary/face scope; not a spatial field",
        "unit": UNIT_MODEL_ENTROPY, "mask_refs": [], "detector": unresolved("Derived step increment column", "NOT_APPLICABLE"),
    },
    "case8_front_RMS": {
        "id": "case8_front_RMS", "semantic_id": "case8_front_RMS",
        "title": "Front displacement RMS",
        "definition": "p50 front displacement about its mean, RMS (model length)",
        "time_rule": "Recorded accepted-step endpoint snapshot",
        "spatial_rule": "Over the 32-row front displacement profile",
        "unit": UNIT_MODEL_LENGTH, "mask_refs": [],
        "detector": {"id": "det.case8.front_rms", "name": "front_rms",
                     "definition": "RMS of the front displacement profile about its row-mean",
                     "parameters": [{"name": "rows", "value": known(32.0)}], "evidence_refs": []},
    },
    "case8_width": {
        "id": "case8_width", "semantic_id": "case8_width",
        "title": "Shock width",
        "definition": "Row p10-p90 crossing distance detector width (model length)",
        "time_rule": "Recorded accepted-step endpoint snapshot",
        "spatial_rule": "Per-row detector on the shock profile",
        "unit": UNIT_MODEL_LENGTH, "mask_refs": [],
        "detector": {"id": "det.case8.width", "name": "width",
                     "definition": "Row-wise p10-p90 crossing-distance width",
                     "parameters": [{"name": "percentile_low", "value": known(10.0)},
                                    {"name": "percentile_high", "value": known(90.0)}], "evidence_refs": []},
    },
    "case8_front_high_k_energy": {
        "id": "case8_front_high_k_energy", "semantic_id": "case8_front_high_k_energy",
        "title": "Front high-wavenumber energy",
        "definition": "Energy in front spectral modes with k > seeded mode 4",
        "time_rule": "Recorded accepted-step endpoint snapshot",
        "spatial_rule": "Over stored front spectral mode energies",
        "unit": UNIT_MODEL_ENERGY, "mask_refs": [],
        "detector": {"id": "det.case8.hf", "name": "front_high_k_energy",
                     "definition": "Sum of front mode energies above the seed cutoff k>4",
                     "parameters": [{"name": "seed_mode", "value": known(4.0)}], "evidence_refs": []},
    },
}
