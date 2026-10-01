"""Pinned identities and scientific definitions for the selected J2C formal v2.

The Window 0 source map is copied as metadata, never as numeric source data.
Only saved files under this selection may supply results. Fig15 is excluded.
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.core.errors import system_error, unsupported_combination
from backend.models.core import known, unresolved

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data/cylinder/source_manifest.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
SCIENTIFIC_ROOT = "D:/Paper/passage6"
REGISTRY_REVISION = "cylinder-registry-v1"
DATA_REVISION = "cylinder-j2c-formal-v2"
BASE = "jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2"
CONFIGS = ("A_u", "B_u", "D_u")
STEPS = (0, 2439, 4878, 7318, 9757)
FAMILIES = {"radial_interior": (31, 128), "angular_interior": (32, 128)}
FIELDS = ("pi_bg", "pi_aa", "pi_at", "pi_total", "J", "pt_z_norm2")
GEOMETRY = ("face_measure", "unit_normal_x", "unit_normal_y", "x_face", "y_face", "r_face", "theta_face")
ASSETS = {a["path"]: a for a in MANIFEST["assets"]}
MASK_ID = "mask.cylinder.fixed-front-band"
NO_MAP = MANIFEST["missing_cumulative_2d"]["ScientificLimitation"]
NA = unresolved("Does not apply to this result", "NOT_APPLICABLE")


def require_config(config_id):
    if config_id == "C_u":
        raise unsupported_combination("Cylinder C_u is outside the verified configuration set",
            resource_type="config", identity=known("C_u"))
    if config_id not in CONFIGS:
        raise system_error("UNKNOWN_CONFIG", "Cylinder configuration is not registered", status=404,
                           availability="MISSING", resource_type="config")
    return config_id


def run_path(config_id, filename):
    require_config(config_id)
    return f"{BASE}/runs/cylinder_{config_id}/{filename}"


def unit(quantity, label=None, dimensionless=False):
    return {"id": f"unit.cylinder.{quantity}", "system": "DIMENSIONLESS" if dimensionless else "MODEL",
            "quantity": quantity, "label": label or f"model {quantity}",
            "si_mapping": unresolved("SI conversion not established for model units", "NOT_APPLICABLE" if dimensionless else "UNKNOWN")}


ANGLE = unit("angle", "radian", True)
LENGTH = unit("length")
FRACTION = unit("fraction", "1", True)
ENTROPY = unit("integrated_entropy", "model integrated entropy")
RATE = unit("integrated_entropy_rate", "model integrated entropy rate")
FIELD_UNITS = {**{f"pi_{c}": unit("entropy_production_density") for c in ("bg", "aa", "at", "total")},
               "J": unit("J", "1", True), "pt_z_norm2": unit("transverse_opportunity_norm_squared")}
FIELD_DEFINITIONS = {
    "pi_bg": "0.5*z.T*Dhat_bg*z, equivalently 0.5*Delta_w.T*D_w_bg*Delta_w",
    "pi_aa": "0.5*q_aa*J*norm(P_A*z)**2; P_A=diag(1,1,0,0)",
    "pi_at": "0.5*q_at*J*norm(P_T*z)**2; P_T=diag(0,0,1,0)",
    "pi_total": "pi_bg+pi_aa+pi_at, equivalently 0.5*Delta_w.T*D_w_total*Delta_w",
    "J": "Saved production jump_scale=(1+m)*chi_hat; dimensionless activation, not an entropy budget",
    "pt_z_norm2": "norm(P_T*z)**2 with z=T.T*Delta_w and P_T=diag(0,0,1,0); transverse opportunity, not entropy production",
}


def verification(evidence_id):
    return {"status": "VERIFIED_NOT_FROZEN", "basis": [
        "J2C_V2_STATUS primary_budget_scope=INTERIOR_ONLY and gate=PASS",
        "Pinned Window 0 hashes and upstream result_hashes.csv match; saved physical reproduction is BITWISE"],
        "verified_at": unresolved("Upstream scientific verification date is not established"),
        "observation_at": unresolved("File observation is not a scientific verification event"),
        "evidence_refs": [evidence_id]}


def scope(definition_id, mask_refs=()):
    return {"id": "cylinder.interior-only", "description": "Primary Cylinder budget uses both native interior face families only",
            "boundary_scope": known("INTERIOR_ONLY; excludes wall and far-field boundary entropy flux"),
            "spatial_domain_ref": unresolved("Result may span both interior native face families", "NOT_APPLICABLE"),
            "mask_refs": list(mask_refs), "definition_refs": [definition_id]}


def time(sampling, accumulation="NONE", *, physical_time=None, step=None, snapshot=None, stage=None, interval=None):
    return {"sampling": sampling, "accumulation": accumulation,
            "physical_time": known(physical_time) if physical_time is not None else NA,
            "interval": known(interval) if interval is not None else NA,
            "step_index": known(step) if step is not None else NA,
            "stage_index": known(stage) if stage is not None else NA,
            "snapshot_index": known(snapshot) if snapshot is not None else NA,
            "index_convention": "Snapshots 1..5 at completed steps 0/2439/4878/7318/9757; history source step 0..9756 maps to canonical completed endpoint 1..9757; stage s0/s1/s2 is not an endpoint rate or exact stage-state time"}


TRAJECTORY = time("STATIC", "TRAJECTORY_INTEGRATED", interval={"start": 0.0, "end": 2.0})
TERMINAL = time("TERMINAL", physical_time=2.0, step=9757)
MEASURE = {"id": "cylinder.interior-sector-sum", "description": "Native interior-face measured SSP-RK3 cumulative statistics; weights already included",
           "integral_rule": "sum(channel_at)=E_at_int; dt*(rate_s0/6+rate_s1/6+2*rate_s2/3)",
           "measure_parameters": [], "includes_time_weights": True, "includes_spatial_measure": True}

# (frozen semantic id, saved physical_metrics key, exact source definition, unit)
METRICS = {
    "cylinder_centerline_width": ("centerline_width", "Upstream centerline radial pressure W10-90: strongest local p50 segment anchor, nearest ordered p90 <= p50 <= p10; width=p10-p90", LENGTH),
    "cylinder_front_mean_width": ("frontal_mean_width", "Mean radial pressure W10-90 over the eight nearest mesh rays in the upstream +/-12 degree sector; same ordered local p50 detector", LENGTH),
    "cylinder_front_RMS": ("front_rms", "Population standard deviation of the eight saved p50 front radii: sqrt(mean((r-mean(r))**2)); not the quadratic-detrended HF statistic", LENGTH),
    "cylinder_front_HF_RMS": ("front_hf_rms", "Unwrap eight upstream ray angles; quadratic fit to front radii; residual h; RMS of (h[i]-.5*(h[i-1]+h[i+1]))/local_radial_spacing[i] for six interior rays; values <=128*float64 eps are set to zero by source", unit("local_radial_cells", "local radial cell spacing", True)),
    "cylinder_high_angular_energy": ("front_high_mode_energy", "Unnormalized rfft of the quadratic-detrended eight-ray front residual; sum(abs(modes[k>=max(2,ray_count//4)])**2)/ray_count**2", unit("length_squared", "model length squared")),
    "cylinder_centerline_standoff": ("centerline_standoff", "Centerline local p50 crossing radius minus cylinder inner radius .5", LENGTH),
    "cylinder_front_standoff": ("front_standoff", "Mean of eight p50 ray radii minus cylinder inner radius .5", LENGTH),
    "cylinder_front_width_median": ("front_width_median", "Median of the eight radial ordered p10-p90 widths", LENGTH),
    "cylinder_front_width_std": ("front_width_std", "Population standard deviation of the eight radial ordered p10-p90 widths", LENGTH),
    "cylinder_front_width_min": ("front_width_min", "Minimum of the eight radial ordered p10-p90 widths", LENGTH),
    "cylinder_front_width_max": ("front_width_max", "Maximum of the eight radial ordered p10-p90 widths", LENGTH),
    "cylinder_front_mismatch_absolute": ("front_mismatch_absolute", "max(abs(front_radii-front_radii[::-1])) over the saved eight-ray detector", LENGTH),
    "cylinder_symmetry_absolute": ("symmetry_absolute_metric", "max(abs(state-reflected_state))/max(max(abs(state)),1); reverse angular index and flip y momentum", FRACTION),
    "cylinder_rho_min": ("rho_min", "Minimum saved terminal conservative density on all O-grid cells", unit("density")),
    "cylinder_p_min": ("p_min", "Minimum ideal-gas pressure of terminal state on all O-grid cells", unit("pressure")),
}


def detector(evidence_id, metric_id=None):
    if metric_id in ("cylinder_rho_min", "cylinder_p_min", "cylinder_symmetry_absolute"):
        return {"id": f"detector.{metric_id}", "name": "Saved terminal O-grid state statistic",
            "definition": METRICS[metric_id][1] + "; source cylinder_b2_4_production.py _row and cylinder.py upper_lower_symmetry_error",
            "parameters": [{"name": "gamma", "value": known(1.4)}] if metric_id == "cylinder_p_min" else [],
            "evidence_refs": [evidence_id]}
    return {"id": "detector.cylinder.local-bow-front", "name": "Frozen local radial bow-front detector",
        "definition": "solver/diagnostics/cylinder.py local_bow_shock_crossing and bow_shock_front_diagnostics; solver/experiments/cylinder_b2_4_production.py _row; no browser recomputation",
        "parameters": [{"name": "ray_count", "value": known(8.0)}, {"name": "sector_half_angle_degrees", "value": known(12.0)},
                       {"name": "thresholds", "value": known("p10/p50/p90")}, {"name": "nominal_dr_context_only", "value": known(7.5/32)}],
        "evidence_refs": [evidence_id]}


def floor_limit(config_id, result_id):
    return {"id": f"lim.cylinder.{config_id}.detector-floor", "code": "DETECTOR_LIMITED_SHARPNESS_READING",
        "description": "B/D radial widths lie at the detector floor relative to nominal dr=(8-.5)/32; nominal dr is resolution context, not an error bar or uncertainty. Width ratios do not establish arbitrarily resolved sharpening.",
        "affected_refs": [result_id], "severity": "WARNING"}
