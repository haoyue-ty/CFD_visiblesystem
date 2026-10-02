"""Read-only entropy closure scientific adapter. No scientific code is imported.

Every selected asset is observed before use, including cache hits. Parsing and
arithmetic audit operate only on saved CSV/JSON; they do not recompute an experiment.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from io import StringIO
from pathlib import Path
from typing import Protocol, runtime_checkable

from backend.core.errors import system_error
from backend.models.closure import ClosureHistory, ClosureRunRegistry, EntropyClosureRun, RefinementSummary
from backend.models.core import known, unresolved
from backend.models.evidence import EvidenceRecord, ResultProvenance
from backend.models.experiments import ExperimentConfig
from backend.models.results import Metric, ScalarSeries, ScientificDefinition, ScientificResult
from backend.registry import closure_registry as R


@runtime_checkable
class EntropyClosureAdapterProtocol(Protocol):
    def list_runs(self) -> ClosureRunRegistry: ...
    def load_run(self, run_id: str) -> EntropyClosureRun: ...
    def load_stage_history(self, run_id: str, *, series=None, offset=0, limit=2000) -> ClosureHistory: ...
    def load_step_history(self, run_id: str, *, series=None, offset=0, limit=2000) -> ClosureHistory: ...
    def load_refinement(self) -> RefinementSummary: ...
    def load_evidence(self, evidence_id: str) -> EvidenceRecord: ...
    def load_provenance(self, result_id: str) -> ResultProvenance: ...


def _mismatch(message):
    return system_error("CANONICAL_SCHEMA_MISMATCH", message, resource_type="closure")


class EntropyClosureAdapter:
    def __init__(self, scientific_root: str | Path = R.SCIENTIFIC_ROOT):
        self._root = Path(scientific_root).resolve()
        self._observations: dict[str, str] = {}
        self._cache: dict[str, tuple[tuple[str, ...], list[dict], list[dict], dict]] = {}
        self._results: dict[str, ScientificResult] = {}
        self._definitions: dict[tuple[str, str], ScientificDefinition] = {}
        self._sources: dict[str, set[str]] = {}

    @property
    def registry_revision(self):
        return R.REGISTRY_REVISION

    @property
    def data_revision(self):
        return R.DATA_REVISION

    def _read(self, relative):
        if relative not in R.ASSETS:
            raise system_error("UNKNOWN_ASSET_ID", "Unregistered closure source asset", status=404, availability="MISSING")
        path = (self._root / relative).resolve()
        if not path.is_relative_to(self._root):
            raise system_error("SOURCE_READ_ERROR", "Registered closure asset escapes the configured source root")
        try:
            before = path.stat()
            raw = path.read_bytes()
            after = path.stat()
        except FileNotFoundError:
            raise system_error("MISSING_SCIENTIFIC_ASSET", "Registered closure scientific asset is absent",
                status=404, availability="MISSING", resource_type="source_asset",
                identity=known(R.ASSETS[relative]["asset_id"])) from None
        except OSError:
            raise system_error("SOURCE_READ_ERROR", "Saved closure source could not be read") from None
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise system_error("SOURCE_CHANGED_DURING_READ", "Closure source changed during observation", status=409)
        digest = hashlib.sha256(raw).hexdigest()
        self._observations[relative] = digest
        # Current imported code drift is distinct from frozen result data drift.
        # Frozen driver/config/observer definitions remain hard-bound to freeze.
        if relative not in R.IMPORTED_METHODS and digest != R.ASSETS[relative]["sha256"]:
            raise system_error("SOURCE_DATA_DRIFT", "Closure source bytes differ from the frozen binding", status=409,
                resource_type="source_asset", identity=known(R.ASSETS[relative]["asset_id"]))
        return raw

    def _json(self, relative):
        try:
            return json.loads(self._read(relative))
        except (ValueError, UnicodeError):
            raise _mismatch("Saved closure JSON cannot be decoded") from None

    @staticmethod
    def _csv(raw, columns, *, strings=(), integers=()):
        try:
            reader = csv.DictReader(StringIO(raw.decode("utf-8")))
            if not reader.fieldnames or any(column not in reader.fieldnames for column in columns):
                raise system_error("MISSING_SCIENTIFIC_ASSET", "Required scientific CSV column is absent; no zero-fill",
                    status=404, availability="MISSING", resource_type="closure_history")
            if tuple(reader.fieldnames) != tuple(columns):
                raise _mismatch("Closure CSV columns differ from the frozen schema")
            rows = []
            for row in reader:
                if None in row or any(value is None or value == "" for value in row.values()):
                    raise _mismatch("Incomplete closure CSV row")
                parsed = {}
                for field, value in row.items():
                    parsed[field] = value if field in strings else int(value) if field in integers else float(value)
                    if field not in strings and not math.isfinite(parsed[field]):
                        raise _mismatch("Nonfinite closure CSV value")
                rows.append(parsed)
            return rows
        except (ValueError, UnicodeError, csv.Error):
            raise _mismatch("Closure CSV cannot be decoded faithfully") from None

    def _context(self):
        for path in R.COMMON:
            self._read(path)
        config = self._json(f"{R.BASE}/FREEZE/frozen_config.json")
        protocol = config["protocol"]
        expected = R.SOURCE_MAP["protocol"]
        if (protocol["protocol_identity"] != expected["identity"] or protocol["grid"] != [128, 128]
                or protocol["time_integrator"] != "SSP-RK3" or protocol["spatial_order"] != 1
                or protocol["requested_final_time"] != 10.0
                or config["stage_weights"] != expected["stage_weights"] or config["eps0"] != expected["eps0"]
                or config["source_hashes"][R.METHOD_PATH] != R.METHOD_HASH):
            raise _mismatch("Frozen closure protocol identity is inconsistent")
        manifest = self._json(f"{R.BASE}/FREEZE/FREEZE_MANIFEST.json")
        if manifest["freeze_status"] != "ENTROPY_BUDGET_CLOSURE_FREEZE_COMPLETE" or manifest["method_sha256"] != R.METHOD_HASH:
            raise _mismatch("Closure freeze authority is inconsistent")

    def _load(self, run_id):
        run = R.require_run(run_id)
        self._context()
        paths = (R.run_path(run_id, "stage_closure.csv"), R.run_path(run_id, "step_closure.csv"),
            R.run_path(run_id, "run_summary.json"), R.SUMMARY_PATH)
        blobs = [self._read(path) for path in paths]
        key = tuple(self._observations[path] for path in paths)
        cached = self._cache.get(run_id)
        if cached is not None and cached[0] == key:
            return cached[1:]
        stage = self._csv(blobs[0], R.STAGE_COLUMNS, integers=("step", "stage", "x_face_count", "y_face_count"))
        step = self._csv(blobs[1], R.STEP_COLUMNS, integers=("step",))
        summary = json.loads(blobs[2])
        columns = tuple(run["terminal_summary"])
        frozen_rows = self._csv(blobs[3], columns, strings=("config", "grid"), integers=("N_steps", "N_stages", "rejected_steps"))
        matching = [row for row in frozen_rows if row["config"] == run["config"] and row["CFL"] == run["CFL"]]
        if len(frozen_rows) != 5 or len(matching) != 1 or matching[0] != summary or summary != run["terminal_summary"]:
            raise _mismatch("Closure run summary differs from the frozen selection")
        if (summary["N_steps"] != run["steps"] or summary["N_stages"] != 3 * run["steps"]
                or summary["dt_eff"] != run["dt"] or summary["T"] != 10.0 or summary["rejected_steps"] != 0):
            raise _mismatch("Closure accepted-step protocol is inconsistent")
        self._verify(run, stage, step, summary)
        self._cache[run_id] = (key, stage, step, summary)
        return stage, step, summary

    @staticmethod
    def _verify(run, stage, step, summary):
        def check(condition, description):
            if not condition:
                raise _mismatch(description)

        n = run["steps"]
        check(len(step) == n and len(stage) == 3 * n, "Closure CSV counts differ from the frozen run")
        eps0 = R.SOURCE_MAP["protocol"]["eps0"]
        weights = R.SOURCE_MAP["protocol"]["stage_weights"]
        cumulative = {channel: 0.0 for channel in ("bg", "aa", "at")}
        previous_time, previous_entropy = 0.0, summary["S0"]
        for index, row in enumerate(step):
            check(row["step"] == index + 1, "Closure accepted-step sequence must be 1..N")
            check(row["dt"] == run["dt"] and row["time_n"] == previous_time and row["time_np1"] > row["time_n"], "Closure step interval or duration is inconsistent")
            check(row["S_n"] == previous_entropy and row["DeltaS"] == row["S_np1"] - row["S_n"], "Closure single-state entropy change is inconsistent")
            samples = stage[3 * index:3 * index + 3]
            for source_stage, item in enumerate(samples, 1):
                check(item["step"] == row["step"] and item["stage"] == source_stage, "Closure stage source order must be 1/2/3 per step")
                check(item["dt"] == row["dt"] and item["t_stage_or_step_time"] == row["time_n"], "Recorded closure stage clock must remain the containing step start")
                check(item["x_face_count"] == 16384 and item["y_face_count"] == 16384, "Closure unique periodic face counts are inconsistent")
                check(item["R_SD"] == item["G"] + item["D_total"], "R_SD must equal recorded G plus independent D_total")
                check(item["eps_SD"] == abs(item["R_SD"]) / (abs(item["G"]) + abs(item["D_total"]) + eps0), "Closure eps_SD normalization is inconsistent")
                check(item["R_decomp"] == item["D_total"] - sum(item[f"D_{c}"] for c in cumulative), "Closure channel decomposition differs from frozen source")
                check(all(item[f"D_{c}"] >= 0 for c in cumulative), "Closure channel production is negative")
                if run["config"] == "B_u":
                    check(item["D_at"] == 0.0, "B_u D_at must be recorded zero")
                for channel in (*cumulative, "total"):
                    check(row[f"D_{channel}_stage{source_stage}"] == item[f"D_{channel}"], "Step-embedded rates must match their real stage CSV rows")
            for channel in (*cumulative, "total"):
                column = f"E_{channel}_step" if channel != "total" else "E_total_independent_step"
                increment = row["dt"] * sum(weight * item[f"D_{channel}"] for weight, item in zip(weights, samples))
                check(row[column] == increment, "Recorded weighted step increment is inconsistent")
                if channel in cumulative:
                    cumulative[channel] += row[column]
            check(row["E_obs_step"] == sum(row[f"E_{c}_step"] for c in cumulative), "Closure observed step increment decomposition is inconsistent")
            check(row["R_time_step"] == row["DeltaS"] + row["E_obs_step"], "Recorded step temporal residual is inconsistent")
            check(row["R_time_cumulative"] == row["S_np1"] - summary["S0"] + sum(cumulative.values()), "Recorded cumulative temporal residual is inconsistent")
            previous_time, previous_entropy = row["time_np1"], row["S_np1"]
        check(previous_time == summary["T"] and previous_entropy == summary["ST"], "Closure terminal state/clock differs from frozen summary")
        check(step[-1]["R_time_cumulative"] == summary["R_total"], "Terminal recorded R(T) differs from frozen summary")
        check(all(cumulative[c] == summary[f"E_{c}_total"] for c in cumulative), "Recorded cumulative channel terminal totals differ from frozen summary")
        check(summary["DeltaS_total"] == summary["ST"] - summary["S0"] and summary["E_obs_total"] == sum(cumulative.values()), "Terminal entropy increment or observer total is inconsistent")
        check(summary["R_total"] == summary["DeltaS_total"] + summary["E_obs_total"], "Terminal fully-discrete diagnostic is inconsistent")
        check(summary["eps_time_total"] == abs(summary["R_total"]) / (abs(summary["DeltaS_total"]) + abs(summary["E_obs_total"]) + eps0), "Terminal temporal normalization is inconsistent")
        if run["config"] == "B_u":
            check(summary["E_at_total"] == 0.0, "B_u terminal tangential channel must be recorded zero")

    def _deps(self, run_id):
        return set(R.COMMON) | {R.run_path(run_id, name) for name in ("stage_closure.csv", "step_closure.csv", "run_summary.json")} | {R.SUMMARY_PATH}

    def _source_drift(self, deps):
        return any(self._observations[path] != R.ASSETS[path]["sha256"] for path in deps if path in R.IMPORTED_METHODS)

    def _header(self, run_id, group, field, *, deps=None, sampling=None):
        run = R.require_run(run_id)
        ev = R.REFINEMENT_EVIDENCE if group == "refinement" else R.evidence_id(run_id, group)
        deps = set(deps) if deps is not None else self._deps(run_id)
        definition = R.definition(field)
        sampling = sampling or {"stage": "PER_STAGE", "step": "PER_STEP", "run": "TERMINAL", "refinement": "TERMINAL"}[group]
        accumulation = definition["accumulation"]
        if sampling == "TERMINAL":
            clock = 0.0 if field == "S0" else run["T"]
            time = R.time(sampling, accumulation, physical_time=clock, step=0 if field == "S0" else run["steps"],
                interval={"start": 0.0, "end": clock}, rule=definition["time_rule"])
        else:
            time = R.time(sampling, accumulation, interval={"start": 0.0, "end": run["T"]})
        did = definition["definition_id"]
        rid = R.result_id(run_id, group, field)
        result = ScientificResult.model_validate({"schema_version": "1.0.0", "result_id": rid,
            "experiment_id": "entropy-closure", "config_id": run_id, "semantic_id": did,
            "data_origin": "FROZEN_PRODUCTION", "availability": "AVAILABLE", "time": time,
            "scope": {"id": "closure.periodic-case7", "description": R.DEFINITIONS["G"]["scope"],
                "boundary_scope": known(R.SOURCE_MAP["protocol"]["boundary_scope"]),
                "spatial_domain_ref": R.NA, "mask_refs": [], "definition_refs": [did]},
            "unit": R.UNITS[definition["unit_ref"]], "verification": R.verification(ev, (
                "All raw stage/step rows checked for counts, finite fields, index/clock conventions, channel formulas, weighted increments and terminal frozen-summary agreement",
                "Temporal residual is a fully-discrete diagnostic, not an exact identity")),
            "provenance": {"evidence_refs": [ev], "source_asset_ids": [R.ASSETS[path]["asset_id"] for path in sorted(deps)],
                "registry_revision": R.REGISTRY_REVISION, "data_revision": R.DATA_REVISION,
                "release_id": unresolved("No application closure release", "NOT_APPLICABLE"), "source_drift": known(self._source_drift(deps))},
            "limitations": R.LIMITATIONS})
        self._results[rid] = result
        self._sources.setdefault(ev, set()).update(deps)
        self._definitions[(ev, did)] = ScientificDefinition.model_validate({"id": did, "semantic_id": did,
            "title": field, "definition": definition["definition"],
            "time_rule": f"{sampling}; {accumulation}; {definition['time_rule']}; {time['index_convention']}",
            "spatial_rule": result.scope.description, "unit": result.unit, "mask_refs": [], "detector": R.NA,
            "evidence_refs": [ev], "limitations": R.LIMITATIONS})
        return result

    def _config(self, run_id):
        run = R.require_run(run_id)
        ev = R.evidence_id(run_id, "run")
        return ExperimentConfig.model_validate({"id": run_id, "experiment_id": "entropy-closure", "name": f"{run['config']} CFL {run['CFL']}",
            "parameters": [{"name": name, "value": known(float(run[name])), "unit": R.UNITS["dimensionless"]} for name in ("CFL", "q_aa", "q_at")],
            "protocol": {"method_name": known("cross_mode_ec_unified_v1; canonical periodic Case7 FV/independent observer"),
                "method_hash": known(R.METHOD_HASH), "grid": known({"coordinate_system": "CARTESIAN",
                    "dimensions": [{"axis": "x", "size": 128}, {"axis": "y", "size": 128}],
                    "extent": [{"axis": "x", "lower": 0.0, "upper": 10.0}, {"axis": "y", "lower": 0.0, "upper": 10.0}]}),
                "integrator": known("SSP-RK3"), "reconstruction": known("first-order finite volume"),
                "final_time": known(10.0), "boundary_scope": known(R.SOURCE_MAP["protocol"]["boundary_scope"]),
                "protocol_asset_refs": [R.ASSETS[path]["asset_id"] for path in R.COMMON]},
            "verification": R.verification(ev, ("Canonical CFL checked against frozen run metadata; directory suffix and inherited default CFL are not selectors",)),
            "limitations": R.LIMITATIONS, "evidence_refs": [ev]})

    def _metric(self, run_id, group, field, value, *, deps=None):
        header = self._header(run_id, group, field, deps=deps)
        return Metric(result=header, metric_id=field, value=known(float(value)), definition_id=R.definition(field)["definition_id"],
            detector=R.NA, time_scope=header.time, display_label=field, resolution_limit=unresolved("No established resolution/error bar"))

    def load_run(self, run_id):
        _, _, summary = self._load(run_id)
        run = R.require_run(run_id)
        return EntropyClosureRun(run_id=run_id, config=self._config(run_id),
            stage_point_count=run["stage_rows"], step_point_count=run["step_rows"],
            stage_series_refs=[R.result_id(run_id, "stage", field) for field in R.STAGE_SERIES],
            step_series_refs=[R.result_id(run_id, "step", field) for field in R.STEP_SERIES],
            terminal_summary=[{"availability": "AVAILABLE", "value": self._metric(run_id, "run", field, summary[field])} for field in R.TERMINAL_FIELDS],
            limitations=R.LIMITATIONS, evidence_refs=[R.evidence_id(run_id, "run")])

    def list_runs(self):
        return ClosureRunRegistry(experiment_id="entropy-closure", runs=[self.load_run(run_id) for run_id in R.RUN_IDS])

    def _history(self, run_id, group, *, series=None, offset=0, limit=2000):
        R.require_run(run_id)
        fields = R.STAGE_SERIES if group == "stage" else R.STEP_SERIES
        if series is not None and (not isinstance(series, (tuple, list)) or not series or len(set(series)) != len(series) or any(field not in fields for field in series)):
            raise system_error("INVALID_RESULT_ID", "Closure series selection is not registered for this granularity", status=404, availability="MISSING")
        if type(offset) is not int or type(limit) is not int or offset < 0 or limit < 1:
            raise system_error("INVALID_REQUEST", "History pagination requires nonnegative integer offset and positive integer limit", status=400)
        stage, step, _ = self._load(run_id)
        rows = stage if group == "stage" else step
        selected = tuple(series) if series is not None else fields
        output = []
        # Register every group header even for a page/subset so Evidence is stable.
        headers = {field: self._header(run_id, group, field) for field in fields}
        for field in selected:
            points = []
            definition = R.definition(field)
            embedded_stage = definition.get("source_stage_index") if group == "step" else None
            for ordinal in range(offset, min(len(rows), offset + limit)):
                row = rows[ordinal]
                endpoint = step[row["step"] - 1]
                source_stage = row["stage"] if group == "stage" else embedded_stage
                points.append({"point_index": ordinal, "step_index": known(row["step"]), "source_step_index": known(row["step"]),
                    "stage_index": known(source_stage - 1) if source_stage is not None else R.NA,
                    "source_stage_index": known(source_stage) if source_stage is not None else R.NA,
                    "physical_time": known(row["t_stage_or_step_time"] if group == "stage" else row["time_np1"]),
                    "interval": known({"start": endpoint["time_n"], "end": endpoint["time_np1"]}), "value": known(float(row[field]))})
            aggregation = "CUMULATIVE" if field == "R_time_cumulative" else "STEP_INCREMENT" if definition["accumulation"] in ("STEP_INCREMENT", "STAGE_WEIGHTED_INCREMENT") else "NONE"
            output.append(ScalarSeries(result=headers[field], series_id=field, label=field, total_point_count=len(rows), points=points,
                page={"offset": offset, "limit": limit, "returned_count": len(points), "total_count": len(rows), "has_more": offset + len(points) < len(rows)},
                aggregation=aggregation, source_column=field, definition_id=definition["definition_id"]))
        return ClosureHistory(run_id=run_id, granularity="PER_STAGE" if group == "stage" else "PER_STEP", series=output, evidence_refs=[R.evidence_id(run_id, group)])

    def load_stage_history(self, run_id, *, series=None, offset=0, limit=2000):
        return self._history(run_id, "stage", series=series, offset=offset, limit=limit)

    def load_step_history(self, run_id, *, series=None, offset=0, limit=2000):
        return self._history(run_id, "step", series=series, offset=offset, limit=limit)

    def load_refinement(self):
        run_ids = list(R.RUN_IDS[:4])
        loaded = {run_id: self._load(run_id) for run_id in run_ids}
        slopes = self._csv(self._read(R.SLOPES_PATH), tuple(R.SOURCE_MAP["refinement"]["pairwise_slopes"][0]))
        audit = self._json(R.AUDIT_PATH)
        if (slopes != R.SOURCE_MAP["refinement"]["pairwise_slopes"] or slopes != audit["pairwise_slopes"]
                or audit["global_slope"] != R.SOURCE_MAP["refinement"]["global_slope"]
                or audit["temporal_refinement_monotonic"] is not True or audit["floating_point_floor"] is not False):
            raise _mismatch("Frozen temporal refinement results are inconsistent")
        deps = set().union(*(self._deps(run_id) for run_id in run_ids)) | {R.SLOPES_PATH, R.AUDIT_PATH}
        metrics_by_run = []
        for index, run_id in enumerate(run_ids):
            _, step, summary = loaded[run_id]
            if index and abs(summary["R_total"]) >= abs(loaded[run_ids[index - 1]][2]["R_total"]):
                raise _mismatch("Frozen temporal terminal residual magnitudes must decrease monotonically")
            metrics = [self._metric(run_id, "refinement", "R_total", step[-1]["R_time_cumulative"], deps=deps),
                self._metric(run_id, "refinement", "dt_eff", summary["dt_eff"], deps=deps)]
            if index < 3:
                slope = slopes[index]
                fine = loaded[run_ids[index + 1]][2]
                if (slope["CFL_coarse"] != summary["CFL"] or slope["CFL_fine"] != fine["CFL"]
                        or slope["dt_eff_coarse"] != summary["dt_eff"] or slope["dt_eff_fine"] != fine["dt_eff"]
                        or slope["abs_R_coarse"] != abs(summary["R_total"]) or slope["abs_R_fine"] != abs(fine["R_total"])):
                    raise _mismatch("Frozen pairwise slope inputs do not bind the selected runs")
                metrics.append(self._metric(run_id, "refinement", f"pairwise_slope_to_{run_ids[index + 1]}", slope["slope"], deps=deps))
            metrics_by_run.append({"run_id": run_id, "metrics": [{"availability": "AVAILABLE", "value": metric} for metric in metrics]})
        return RefinementSummary(comparison_id=R.COMPARISON_ID, run_ids=run_ids, metrics_by_run=metrics_by_run,
            refinement_slope={"availability": "AVAILABLE", "value": self._metric(run_ids[0], "refinement", "refinement_slope", audit["global_slope"], deps=deps)},
            limitations=R.LIMITATIONS, evidence_refs=[R.REFINEMENT_EVIDENCE])

    def _materialize_group(self, evidence_id):
        if evidence_id == R.REFINEMENT_EVIDENCE:
            self.load_refinement()
            return None, "refinement"
        for run_id in R.RUN_IDS:
            for group in ("run", "stage", "step"):
                if evidence_id == R.evidence_id(run_id, group):
                    self.load_run(run_id)
                    if group != "run":
                        for field in R.STAGE_SERIES if group == "stage" else R.STEP_SERIES:
                            self._header(run_id, group, field)
                    return run_id, group
        raise system_error("UNKNOWN_EVIDENCE_ID", "Closure evidence identity is not registered", status=404, availability="MISSING")

    def load_evidence(self, evidence_id):
        run_id, group = self._materialize_group(evidence_id)
        deps = self._sources[evidence_id]
        for path in sorted(deps):
            self._read(path)
        source_drift = self._source_drift(deps)
        contexts = [header for _, header in sorted(self._results.items()) if evidence_id in header.provenance.evidence_refs]
        definitions = [definition for (ev, _), definition in sorted(self._definitions.items()) if ev == evidence_id]
        assets, observations = [], []
        for path in sorted(deps):
            asset = R.ASSETS[path]
            current = self._observations[path]
            drift = current != asset["sha256"]
            verification = R.verification(evidence_id, ("Current hash compared with recorded freeze/source-map hash",),
                "PARTIAL" if drift else asset["verification"])
            assets.append({"asset_id": asset["asset_id"], "source_id": "passage6", "source_display": "Frozen entropy closure scientific source",
                "relative_origin": known(path), "role": asset["role"], "format": Path(path).suffix.lstrip(".").upper(),
                "recorded_data_hash": known(asset["sha256"]), "current_data_hash": known(current), "data_drift": known(drift),
                "verification": verification, "canonical_selected": True, "limitations": R.LIMITATIONS})
            if path in R.IMPORTED_METHODS:
                observations.append({"asset_id": asset["asset_id"], "recorded_hash": known(asset["sha256"]), "current_hash": known(current),
                    "drift": known(drift), "observation_at": unresolved("No persisted observation event timestamp")})
        definition_ids = [definition.id for definition in definitions]
        inputs = [R.ASSETS[path]["asset_id"] for path in sorted(deps)]
        processing = [self._processing("closure.format-mapping-v1", "FORMAT_MAPPING",
            "Read real CSV columns with finite numeric values; preserve source accepted step 1..N and original clock; map source stage 1/2/3 to 0/1/2. Retain independent D_total, embedded rates and recorded R_time_cumulative. Audit frozen formulas only; no experiment rerun, no new fit, no generated channel cumulative history.", inputs, definition_ids, evidence_id),
            self._processing("closure.cfl-correction-v1", "METADATA_CORRECTION",
            "Canonical CFL from frozen run_summary and frozen temporal summary/protocol: Du_cfl_005/Bu_cfl_005 = .05, Du_cfl_0025 = .025. Inherited config default .1 is not a selector. Inventory and scientific sources remain unchanged.", inputs, definition_ids, evidence_id)]
        if group == "refinement":
            processing.append(self._processing("closure.frozen-slope-binding-v1", "FORMAT_MAPPING",
                "Bind existing frozen pairwise slopes and global log-log slope versus dt_eff to the four D_u runs and terminal recorded residuals. No refit; observed refinement remains a fully-discrete diagnostic.", inputs, definition_ids, evidence_id))
        freeze_path = f"{R.BASE}/FREEZE/FREEZE_MANIFEST.json"
        limitations = list(R.LIMITATIONS)
        if source_drift:
            limitations.append({"id": "lim.closure.source-drift", "code": "SOURCE_CODE_DRIFT", "description": "Current imported scientific code differs from frozen identity; frozen numeric bytes are unchanged and no scientific code was executed.", "affected_refs": [], "severity": "WARNING"})
        return EvidenceRecord.model_validate({"schema_version": "1.0.0", "evidence_id": evidence_id,
            "result_ids": [header.result_id for header in contexts], "result_contexts": contexts,
            "experiment_id": known("entropy-closure"), "config_id": known(run_id) if run_id else R.NA,
            "config": known(self._config(run_id)) if run_id else R.NA, "definitions": definitions, "masks": [],
            "method_name": known("cross_mode_ec_unified_v1; periodic first-order FV; independent observer; SSP-RK3"),
            "method_hash": known(R.METHOD_HASH), "recorded_source_hash": known(R.METHOD_HASH),
            "current_source_hash": known(self._observations[R.METHOD_PATH]), "source_observations": observations, "source_assets": assets,
            "data_hash": unresolved("No authoritative composite data hash recorded"), "freeze_reference": known({"freeze_id": "entropy-budget-closure-freeze-v1",
                "manifest_asset_id": R.ASSETS[freeze_path]["asset_id"], "recorded_at": unresolved("Freeze timestamp not recorded"), "hash": known(R.ASSETS[freeze_path]["sha256"])}),
            "processing": processing, "verification": R.verification(evidence_id, ("Saved CSV arithmetic audits and terminal frozen bindings; checksum list excludes its own hash by design",)),
            "limitations": limitations, "source_drift": known(source_drift), "created_at": unresolved("No evidence creation event in the frozen scientific record"),
            "verified_at": unresolved("Frozen scientific verification timestamp not recorded"), "related_evidence_refs": [],
            "superseded_by": unresolved("Current canonical closure selection", "NOT_APPLICABLE")})

    @staticmethod
    def _processing(identity, kind, description, inputs, definitions, ev):
        # Hash the actual adapter/registry implementation, not its description.
        digest = hashlib.sha256(Path(__file__).read_bytes() + Path(R.__file__).read_bytes()).hexdigest()
        return {"id": identity, "kind": kind, "description": description, "input_asset_ids": inputs,
            "definition_refs": definitions, "processing_hash": known(digest), "verification": R.verification(ev,
                ("Canonical format/metadata mapping validated by Window1 real-source regression; software processing is not an upstream scientific freeze",),
                status="VERIFIED_NOT_FROZEN")}

    def load_provenance(self, result_id):
        for run_id in R.RUN_IDS:
            for group, fields in (("run", R.TERMINAL_FIELDS), ("stage", R.STAGE_SERIES), ("step", R.STEP_SERIES)):
                if result_id in {R.result_id(run_id, group, field) for field in fields}:
                    evidence = self.load_evidence(R.evidence_id(run_id, group))
                    return ResultProvenance(result_id=result_id, provenance=self._results[result_id].provenance, evidence_records=[evidence])
        # Refinement IDs are also finite registry identities, materialized on demand.
        refinement_fields = [(run_id, field) for run_id in R.RUN_IDS[:4] for field in ("R_total", "dt_eff")]
        refinement_fields += [(R.RUN_IDS[0], "refinement_slope")]
        refinement_fields += [(R.RUN_IDS[i], f"pairwise_slope_to_{R.RUN_IDS[i + 1]}") for i in range(3)]
        if result_id in {R.result_id(run_id, "refinement", field) for run_id, field in refinement_fields}:
            evidence = self.load_evidence(R.REFINEMENT_EVIDENCE)
            return ResultProvenance(result_id=result_id, provenance=self._results[result_id].provenance, evidence_records=[evidence])
        raise system_error("INVALID_RESULT_ID", "Closure result identity is not registered", status=404, availability="MISSING")
