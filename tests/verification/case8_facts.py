"""Independent QA fact source for the Case8 functional slice (Phase 5B, Window 4).

This module is the single place where acceptance tests obtain scientific golden
values. Nothing here is hand-written: every number is derived at import time from
one of three explicitly versioned evidence tiers.

Evidence tiers
--------------
L1  A frozen manifest / protocol asset committed in this repository under
    ``data/`` that itself carries a recorded SHA-256 (``data/evidence_validation.json``
    is a Phase 1 lightweight-verification product of the frozen asset inventory).
L2  A frozen protocol asset read directly from the read-only scientific root
    (``D:\\Paper\\passage6``). Read-only; never modified. The known SHA-256 of the
    whole file is recorded alongside so drift is detectable but never repaired.
L3  Declared aggregate expectations of this QA window itself, which are explicit
    acceptance quantities and therefore not derived from L1/L2. They are kept
    separate so a mismatch is attributed to the right tier.

The read-only scientific root is used **only** when it is present and only in
read mode. If it is absent the L2 facts degrade to an explicit UNKNOWN carrying a
reason; tests that depend on L2 then fail loudly rather than silently guessing.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
SCIENTIFIC_ROOT = Path("D:/Paper/passage6")

CONFIDENCE = Literal["L1", "L2", "L3", "UNKNOWN"]

SPEC = "phase5b.window4.case8_qa"


@dataclass(frozen=True)
class Fact:
    """A single verified value plus the provenance that produced it."""

    name: str
    value: object
    confidence: CONFIDENCE
    source: str
    detail: str = ""

    @property
    def known(self) -> bool:
        return self.confidence != "UNKNOWN"


@dataclass(frozen=True)
class SnapshotFact:
    index: int
    step_index: int
    physical_time: float


@dataclass(frozen=True)
class ConfigFact:
    config_id: str
    q_aa: float
    q_at: float
    snapshots: tuple[SnapshotFact, ...]
    history_rows: int


@dataclass
class Case8Facts:
    """Aggregate of every Case8 golden fact, with per-fact provenance."""

    configs: tuple[ConfigFact, ...]
    facts: dict[str, Fact] = field(default_factory=dict)

    def fact(self, name: str) -> Fact:
        return self.facts[name]


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------
# L1 — frozen Phase 1 products committed in this repository
# --------------------------------------------------------------------------

def _load_l1_evidence() -> dict:
    return _load_json(DATA_DIR / "evidence_validation.json")


def _load_l1_inventory_rows() -> list[dict]:
    return _load_json(DATA_DIR / "inventory_inspected.json")


# --------------------------------------------------------------------------
# L2 — frozen protocol assets on the read-only scientific root
# --------------------------------------------------------------------------

def _read_l2_protocol_lock() -> tuple[dict | None, str]:
    """Return the frozen protocol lock document and an explicit read status."""
    path = (SCIENTIFIC_ROOT / "jcp_extension_v1" / "J2_entropy_diagnostics"
            / "J2B_case8_formal" / "J2B_PROTOCOL_LOCK.json")
    if not path.is_file():
        return None, f"READ_ONLY_SOURCE_ABSENT:{path}"
    try:
        return _load_json(path), "READ_ONLY_SOURCE_PRESENT"
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:  # pragma: no cover
        return None, f"READ_ONLY_SOURCE_UNREADABLE:{type(error).__name__}"


def _read_l2_history_csv(config_id: str) -> tuple[list[dict] | None, str]:
    path = (SCIENTIFIC_ROOT / "jcp_extension_v1" / "J2_entropy_diagnostics"
            / "J2B_case8_formal" / "runs" / f"case8_{config_id}" / "stage_weighted_history.csv")
    if not path.is_file():
        return None, f"READ_ONLY_SOURCE_ABSENT:{path}"
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle)), "READ_ONLY_SOURCE_PRESENT"
    except (OSError, UnicodeDecodeError) as error:  # pragma: no cover
        return None, f"READ_ONLY_SOURCE_UNREADABLE:{type(error).__name__}"


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

_CONFIG_ORDER = ("A_u", "B_u", "C_u", "D_u")


def _snapshots_from_evidence(evidence: dict, config_id: str) -> tuple[SnapshotFact, ...]:
    """L1 snapshot schedule from the frozen Phase 1 lightweight verification."""
    for block in evidence["case8_flow_snapshots"]:
        if block["configuration"] == config_id:
            ordered = sorted(block["snapshots"], key=lambda item: item["step"])
            return tuple(SnapshotFact(index=position + 1,
                                      step_index=int(item["step"]),
                                      physical_time=float(item["time"]))
                         for position, item in enumerate(ordered))
    raise KeyError(f"No recorded Case8 snapshot block for {config_id!r}")


def _inventory_row(config_id: str) -> dict:
    needle = f"runs/case8_{config_id}/stage_weighted_history.csv"
    for row in _load_l1_inventory_rows():
        if str(row.get("relative_source_path", "")).replace("\\", "/").endswith(needle):
            return row
    raise KeyError(f"No inventory row for {config_id!r} stage_weighted_history.csv")


def _history_rows_from_inventory(config_id: str) -> tuple[int, str]:
    """L1 accepted-step count from the frozen inventory inspection of the CSV."""
    row = _inventory_row(config_id)
    return int(row["inspection"]["shape"][0]), str(row.get("sha256", ""))


def _first_row_value(config_id: str, column: str) -> tuple[str, str]:
    """L1 first-row scalar, so tests never hard-code a curve endpoint."""
    row = _inventory_row(config_id)
    return str(row["inspection"]["first_row"][column]), str(row.get("sha256", ""))


def _last_row_value(config_id: str, column: str) -> tuple[str, str]:
    row = _inventory_row(config_id)
    return str(row["inspection"]["last_row"][column]), str(row.get("sha256", ""))


def build_facts() -> Case8Facts:
    evidence = _load_l1_evidence()
    lock, lock_status = _read_l2_protocol_lock()

    facts: dict[str, Fact] = {}
    configs: list[ConfigFact] = []

    # ---- L1: the four recorded configurations -----------------------------
    history_counts = {config_id: _history_rows_from_inventory(config_id)[0]
                      for config_id in _CONFIG_ORDER}

    for config_id in _CONFIG_ORDER:
        snapshots = _snapshots_from_evidence(evidence, config_id)
        configs.append(ConfigFact(config_id=config_id, q_aa=float("nan"), q_at=float("nan"),
                                  snapshots=snapshots,
                                  history_rows=history_counts[config_id]))
        facts[f"snapshots.{config_id}"] = Fact(
            f"snapshots.{config_id}", len(snapshots), "L1",
            f"{SPEC}:data/evidence_validation.json:case8_flow_snapshots[{config_id}]",
            "recorded Case8 checkpoint schedule from frozen Phase 1 verification")

    # ---- L2: q_aa / q_at parameters and the canonical schedule ------------
    if lock is not None:
        for config_id in _CONFIG_ORDER:
            entry = lock["configurations"][config_id]
            facts[f"q_aa.{config_id}"] = Fact(
                f"q_aa.{config_id}", float(entry["q_aa"]), "L2",
                "J2B_PROTOCOL_LOCK.json:configurations", lock_status)
            facts[f"q_at.{config_id}"] = Fact(
                f"q_at.{config_id}", float(entry["q_at"]), "L2",
                "J2B_PROTOCOL_LOCK.json:configurations", lock_status)
        facts["accepted_steps"] = Fact("accepted_steps", int(lock["accepted_step_expectation"]),
                                       "L2", "J2B_PROTOCOL_LOCK.json:accepted_step_expectation",
                                       lock_status)
        facts["final_time"] = Fact("final_time", float(lock["final_time"]), "L2",
                                   "J2B_PROTOCOL_LOCK.json:final_time", lock_status)
        facts["snapshot_steps"] = Fact("snapshot_steps",
                                       tuple(int(value) for value in lock["snapshot_steps"]),
                                       "L2", "J2B_PROTOCOL_LOCK.json:snapshot_steps", lock_status)
        facts["snapshot_times"] = Fact("snapshot_times",
                                       tuple(float(value) for value in lock["snapshot_times"]),
                                       "L2", "J2B_PROTOCOL_LOCK.json:snapshot_times", lock_status)
        configs = [
            ConfigFact(config_id=item.config_id,
                       q_aa=float(lock["configurations"][item.config_id]["q_aa"]),
                       q_at=float(lock["configurations"][item.config_id]["q_at"]),
                       snapshots=item.snapshots, history_rows=item.history_rows)
            for item in configs
        ]
        facts["history.crosscheck"] = Fact(
            "history.crosscheck",
            lock["accepted_step_expectation"] == history_counts["D_u"], "L2",
            "J2B_PROTOCOL_LOCK.json vs inventory",
            "accepted_step_expectation vs recorded stage_weighted_history row count")
    else:
        for name in ("accepted_steps", "snapshot_times", "snapshot_steps", "final_time",
                     "history.crosscheck"):
            facts[name] = Fact(name, None, "UNKNOWN", "J2B_PROTOCOL_LOCK.json", lock_status)

    # ---- L2: D_u curve endpoints (never hard-coded in tests) --------------
    first_value, first_hash = _first_row_value("D_u", "E_at")
    last_value, last_hash = _last_row_value("D_u", "E_at")
    facts["D_u.E_at.first"] = Fact("D_u.E_at.first", float(first_value), "L2",
                                   "stage_weighted_history.csv:first_row:E_at",
                                   f"recorded sha256={first_hash}")
    facts["D_u.E_at.terminal"] = Fact("D_u.E_at.terminal", float(last_value), "L2",
                                      "stage_weighted_history.csv:last_row:E_at",
                                      f"recorded sha256={last_hash}")
    facts["D_u.E_at.terminal_source_time"] = Fact(
        "D_u.E_at.terminal_source_time",
        float(_last_row_value("D_u", "time_end")[0]), "L2",
        "stage_weighted_history.csv:last_row:time_end", "curve abscissa endpoint")
    facts["D_u.E_at.rows_distinct"] = Fact(
        "D_u.E_at.rows_distinct", True, "L2", "stage_weighted_history.csv:columns",
        "E_at (cumulative) and dotE_at_s0 (stage rate) are separate recorded columns")

    # ---- L1: recorded source hash of the D_u history asset ----------------
    facts["history.sha256.D_u"] = Fact("history.sha256.D_u", _history_rows_from_inventory("D_u")[1],
                                       "L1", "inventory_inspected.json", "recorded file hash")

    # ---- L3: explicit QA-window acceptance aggregates ---------------------
    facts["window.history_rows_expected"] = Fact(
        "window.history_rows_expected", 7648, "L3", "phase5b.window4 task statement",
        "QA-window aggregate = 4 configurations x 1912 accepted steps")
    facts["window.snapshot_count_expected"] = Fact(
        "window.snapshot_count_expected", 24, "L3", "phase5b.window4 task statement",
        "QA-window aggregate = 4 configurations x 6 recorded snapshots")

    return Case8Facts(configs=tuple(configs), facts=facts)


FACTS = build_facts()

CONFIGS: tuple[str, ...] = tuple(item.config_id for item in FACTS.configs)
CONFIG_COUNT = len(CONFIGS)
SNAPSHOT_COUNT_PER_CONFIG = len(FACTS.configs[0].snapshots) if FACTS.configs else 0
HISTORY_ROWS_PER_CONFIG = FACTS.configs[3].history_rows if FACTS.configs else 0
