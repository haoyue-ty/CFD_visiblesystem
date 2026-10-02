"""Lightweight frozen content registry for CONTENT01–03.

Every call yields independently owned validated metadata. Numerical resources
remain in their existing registries, adapters and APIs.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from backend.models.content import MechanismContent, MechanismState, QatState, SceneList, ScenePreset
from backend.models.core import fact_value
from backend.registry.content_bindings import (DU_CROSS_FLOW, GATE_COMPARISON,
    ResourceBinding, resolve_evidence, resolve_target)

CONTENT_ROOT = Path(__file__).resolve().parents[2] / "config" / "content"
BASE_COMMIT = "5d6ceb4bb64e15a5db51ecc77b297add5c9c39e3"
CONTENT_VERSION = "1.0.1"
TITLES = (
    "How much dissipation?", "What triggers it? Where does it act?",
    "Trigger ≠ Output", "Same budget ≠ Same allocation",
    "Positive entropy ≠ Uniform modal damping",
    "Same pathway ≠ Same macroscopic response", "Real solver / frozen evidence / hash",
)
VIEWS = ("ENTROPY", "MECHANISM", "MECHANISM", "ALLOCATION", "SPECTRUM", "CROSS_FLOW", "EVIDENCE")
TARGET_CONFIGS = {
    1: (("case8", "B_u"), ("case8", "D_u")), 2: (), 3: (),
    4: (("gate", "Acoustic"), ("gate", "Pressure"), ("gate", "Ungated")),
    5: (("spectrum", "spectrum.q-0.000"), ("spectrum", "spectrum.q-0.396")),
    6: (("case8", "D_u"), ("cylinder", "D_u")), 7: (),
}
# Only selectors/overlays backed by this fixed story. No arbitrary parameters.
CONTROL_VALUES = {
    1: {"config": ("B_u", "D_u")},
    2: {"node": ("acoustic-information", "acoustic-gate", "normal-output", "tangential-output")},
    3: {"state": ("STRICT_1D", "WEAKLY_2D"), "q_at": ("OFF", "ENABLED")},
    4: {"gate": ("Acoustic", "Pressure", "Ungated")},
    5: {"q_at": ("0", "0.396"), "mode_index": tuple(str(mode) for mode in range(17))},
    6: {},
    7: {"evidence_id": ("ev.case8.D_u.entropy", "ev.case8.D_u.allocation",
         "ev.gate.Acoustic.allocation", "evidence.spectral.spectrum.q-0.396", "ev.cylinder.D_u.sectors")},
}


def _read_frozen(name: str) -> bytes:
    manifest = json.loads((CONTENT_ROOT / "freeze_manifest.json").read_text(encoding="utf-8"))
    if (manifest["base_commit"] != BASE_COMMIT or manifest["status"] != "FROZEN"
            or manifest["content_registry_version"] != CONTENT_VERSION):
        raise ValueError("Content freeze baseline/status mismatch")
    payload = (CONTENT_ROOT / name).read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest["sha256"][name]:
        raise ValueError(f"Frozen content bytes changed: {name}")
    return payload


def load_mechanism() -> MechanismContent:
    mechanism, _ = load_foundation()
    return mechanism


def load_scenes() -> SceneList:
    _, scenes = load_foundation()
    return scenes


def load_foundation() -> tuple[MechanismContent, SceneList]:
    mechanism = MechanismContent.model_validate_json(_read_frozen("mechanism.json"))
    scenes = SceneList.model_validate_json(_read_frozen("scenes.json"))
    validate_foundation(mechanism, scenes)
    return mechanism, scenes


def get_scene(scene_id: int) -> ScenePreset:
    if type(scene_id) is not int or scene_id not in range(1, 8):
        raise KeyError(scene_id)
    return load_scenes().items[scene_id - 1]


def scene_requests(scene_id: int) -> tuple[ResourceBinding, ...]:
    scene = get_scene(scene_id)
    if scene_id == 4:
        return (GATE_COMPARISON,)
    if scene_id == 6:
        return (DU_CROSS_FLOW,)
    if scene.view_kind == "EVIDENCE":
        return tuple(resolve_evidence(ref) for ref in scene.evidence_refs)
    return tuple(binding for target in scene.targets for binding in resolve_target(target))


def validate_foundation(mechanism: MechanismContent, scenes: SceneList) -> None:
    """Fail closed on scientific graph, target, control and evidence drift."""
    pairs = {(e.from_node, e.to_node) for e in mechanism.edges}
    required = {("interface-state", "background-psd"), ("interface-state", "acoustic-information"),
        ("acoustic-information", "acoustic-gate"), ("acoustic-gate", "q-aa"),
        ("q-aa", "normal-output"), ("acoustic-gate", "q-at"), ("q-at", "tangential-output"),
        ("interface-state", "tangential-content"), ("tangential-content", "tangential-output"),
        ("background-psd", "combiner"), ("normal-output", "combiner"),
        ("tangential-output", "combiner"), ("combiner", "entropy-variable-mapping")}
    if pairs != required:
        raise ValueError("Frozen trigger/output graph changed; delta_t must not enter the gate")
    if "NO_AUTHORITATIVE_NEAR1D_RAW_SCAN" not in {lim.code for lim in mechanism.limitations}:
        raise ValueError("Near-1D raw numerical evidence gap must be explicit")
    for ref in mechanism.evidence_refs:
        resolve_evidence(ref)
    for scene, title, view in zip(scenes.items, TITLES, VIEWS, strict=True):
        if scene.title != title or scene.view_kind != view:
            raise ValueError("Frozen scene title/view mismatch")
        configs = tuple((target.experiment_id, fact_value(target.config_id)) for target in scene.targets)
        if configs != TARGET_CONFIGS[scene.scene_id]:
            raise ValueError("Scene scientific configurations must match the frozen story")
        if scene.scene_id == 1:
            for target in scene.targets:
                config = fact_value(target.config_id)
                expected = [f"case8.{config}.E_{channel}_cumulative" for channel in ("bg", "aa", "at")]
                if target.result_ids != expected:
                    raise ValueError("Scene 1 must retain all three real pathway budget histories")
        if scene.scene_id == 6:
            if (scene.targets[0].result_ids != ["case8.D_u.allocation"]
                    or scene.targets[1].result_ids != ["cylinder.D_u.sectors", "cylinder.D_u.front-band"]):
                raise ValueError("Scene 6 must retain both original allocation representations")
            if not {"DESCRIPTIVE_ONLY", "NO_UNIFIED_RANKING"} <= {lim.code for lim in scene.limitations}:
                raise ValueError("Cross-flow comparability and ranking boundaries are required")
        controls = {control.name: tuple(control.allowed_values) for control in scene.allowed_controls}
        if len(controls) != len(scene.allowed_controls) or controls != CONTROL_VALUES[scene.scene_id]:
            raise ValueError("Unsupported or missing scene controls")
        for control in scene.allowed_controls:
            expected_kind = "RECORDED_INDEX" if control.name == "mode_index" else "ENUM"
            if control.kind != expected_kind:
                raise ValueError("Control kind must match its supported discrete selector")
            expected_registry = {
                "config": "case8.configs", "node": mechanism.content_id,
                "state": mechanism.content_id, "q_at": (mechanism.content_id if scene.scene_id == 3 else "spectrum.common-mach6"),
                "gate": "gate.configs", "mode_index": "spectrum.common-mach6", "evidence_id": "explore.evidence",
            }[control.name]
            if fact_value(control.combination_registry_ref) != expected_registry:
                raise ValueError("Control registry reference mismatch")
        for target in scene.targets:
            resolve_target(target)
        for ref in scene.evidence_refs:
            resolve_evidence(ref)


@dataclass(frozen=True)
class MechanismStateExplanation:
    """Qualitative state labels only; these are not sampled J/output values."""
    state: MechanismState
    q_at: QatState
    acoustic_trigger: str
    tangential_receiving_content: str
    tangential_output: str
    reason: str


def explain_mechanism_state(state: MechanismState, q_at: QatState) -> MechanismStateExplanation:
    if state not in ("STRICT_1D", "WEAKLY_2D") or q_at not in ("OFF", "ENABLED"):
        raise ValueError("Only the two schematic states and OFF/ENABLED are supported")
    content = "VANISHES" if state == "STRICT_1D" else "MAY_BE_NONZERO"
    if q_at == "OFF":
        output, reason = "VANISHES", "q_at pathway is disabled; acoustic trigger may still exist."
    elif state == "STRICT_1D":
        output, reason = "VANISHES", "Tangential jump is zero; output vanishes because tangential receiving content vanishes, not because the gate is inactive."
    else:
        output, reason = "CONDITIONALLY_ACTIVE", "Same/similar acoustic trigger can act on nonzero tangential content; actual dissipative amplitude still depends on tangential receiving content."
    return MechanismStateExplanation(state, q_at, "MAY_BE_NONZERO", content, output, reason)
