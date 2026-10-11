"""Bounded, run-scoped export caches with cross-process atomic publication."""
from contextlib import contextmanager, ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import time
from uuid import uuid4
import zipfile

import numpy as np

from backend.models.v2.export import ExportMetadata, RunExports
from backend.postprocess.case8 import cell_axes, primitive_fields, read
from backend.services.v2.case8_exports import Case8Exporter
from backend.services.v2.experiments import ExperimentError
from backend.services.v2.pdf_export import PDFUnavailable, pdf_capability, render_pdf
from backend.services.v2.reports import ReportService
from backend.services.v2.results import ScientificResultService
from backend.solver_runtime.artifacts import sha256, target, utc_now, write_json
from backend.solver_runtime.processes import process_identity
from backend.solver_runtime.run_store import file_lock

EXPORTER_VERSION = "case8.exports.b1.0"
KINDS = ("raw", "visualization", "report")
BUNDLES = {"raw": "raw_data.zip", "visualization": "flow_field.zip", "report": "experiment_report.zip"}
FORMATS = {".npz": "NPZ", ".json": "JSON", ".jsonl": "JSONL", ".csv": "CSV", ".md": "Markdown",
           ".vti": "VTI", ".pvd": "PVD", ".html": "HTML", ".pdf": "PDF", ".zip": "ZIP"}
SAFE_FILE = re.compile(r"^(?:raw/(?:config.json|effective_solver_config.json|provenance.json|result.json|scientific_result.json|initial_state.npz|final_state.npz|README.md|export_manifest.json|snapshots/(?:index.json|step_[0-9]{6}.npz)|diagnostics/history.jsonl|derived/(?:physical_fields.npz|cumulative_faces.npz))|diagnostics/(?:history.csv|entropy_budget.csv|physical_metrics.json|README.md)|visualization/(?:field_[0-9]{6}.vti|timeseries.pvd|README.md|export_manifest.json)|reports/(?:report.html|report.pdf|README.md|export_manifest.json)|bundles/(?:raw_data.zip|flow_field.zip|experiment_report.zip))$")


def cache_bytes(root):
    if root.is_symlink() or (hasattr(root, "is_junction") and root.is_junction()):
        raise ValueError("Linked export root")
    if not root.exists():
        return 0
    total = 0
    for path in root.rglob("*"):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("Linked export cache")
        try:
            if path.is_file():
                total += path.stat().st_size
        except FileNotFoundError:
            continue
    return total


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(",", ":")).encode()).hexdigest()


class ExportBudget:
    def __init__(self, root, settings):
        self.root, self.settings, self.started = root, settings, time.monotonic()

    def remaining(self):
        return max(.1, self.settings.max_export_seconds - (time.monotonic() - self.started))

    def check(self, *, extra=0):
        if time.monotonic() - self.started > self.settings.max_export_seconds:
            raise ExperimentError("EXPORT_TIMEOUT", "导出生成超过时长限制，请重试。", 503, retryable=True)
        if cache_bytes(self.root) + extra > self.settings.max_export_cache_bytes:
            raise ExperimentError("EXPORT_CACHE_LIMIT", "导出缓存超过独立容量上限，请联系管理员调整导出容量。", 413)
        if extra and shutil.disk_usage(self.root).free < extra + 1048576:
            raise ExperimentError("EXPORT_STORAGE_UNAVAILABLE", "导出磁盘空间不足。", 503, retryable=True)


class ExportService:
    def __init__(self, store, client=None):
        self.store = store
        self.science = ScientificResultService(store)
        self.reports = ReportService(store, client)
        self.exporter_sha256 = digest([sha256(Path(__file__)),
            *[sha256(Path(__file__).with_name(name)) for name in ("case8_exports.py", "pdf_export.py", "pdf_worker.py")]])

    def capabilities(self):
        _, reason = pdf_capability(self.store.settings)
        return {"raw": {"formats": ["NPZ", "JSON", "CSV"], "unavailable_formats": {}},
                "visualization": {"formats": ["VTI", "PVD"], "unavailable_formats": {}},
                "report": {"formats": ["HTML"] + ([] if reason else ["PDF"]),
                           "unavailable_formats": {"PDF": reason} if reason else {}, "retryable_formats": []}}

    def source(self, run_id):
        result = self.science.result(run_id)
        if result.config.normalized_config.case_id != "case8":
            raise ExperimentError("EXPORT_UNSUPPORTED_CASE", "本算例尚未登记标准导出器。", 422)
        root = self.store.directory(run_id)
        try:
            provenance = read(root, "provenance.json")
            rows = provenance["outputs"]
            recorded = {r["path"]: r for r in rows}
            if len(recorded) != len(rows):
                raise ValueError("Duplicate scientific output paths")
            required = ["config.json", "effective_solver_config.json", "result.json", "initial_state.npz",
                        "final_state.npz", "snapshots/index.json", "diagnostics/history.jsonl"]
            if any(not re.fullmatch(r"step_[0-9]{6}", s.snapshot_id) for s in result.snapshots):
                raise ValueError("Invalid snapshot identity")
            required += [f"snapshots/{s.snapshot_id}.npz" for s in result.snapshots]
            if target(root, "scientific_result.json").exists():
                required.append("scientific_result.json")
            for name in required:
                if (name not in recorded or sha256(target(root, name)) != recorded[name]["sha256"]
                        or target(root, name).stat().st_size != recorded[name]["size"]):
                    raise ValueError("Scientific export source not verified")
            config = result.config.normalized_config
            if not math.isclose(result.runtime.final_time, config.time.final_time, rel_tol=0, abs_tol=1e-14):
                raise ValueError("Requested interval is incomplete")
            summary = read(root, "result.json")
            if summary.get("full_requested_interval_completed") is False:
                raise ValueError("Partial Solver result")
            cell_axes(root, config)
            shape = (config.grid.ny, config.grid.nx, 4)
            with np.load(target(root, "initial_state.npz"), allow_pickle=False) as data:
                initial = data["state"]
                if initial.shape != shape:
                    raise ValueError("Initial state shape mismatch")
                primitive_fields(initial, config.physics.gamma)
            with np.load(target(root, "final_state.npz"), allow_pickle=False) as data:
                final = data["state"]
                if (final.shape != shape or float(data["time"]) != result.runtime.final_time
                        or int(data["accepted_steps"]) != result.runtime.accepted_steps):
                    raise ValueError("Final state shape/time mismatch")
                primitive_fields(final, config.physics.gamma)
            index = read(root, "snapshots/index.json")
            if len(index) != len(result.snapshots) or not index:
                raise ValueError("Snapshot count mismatch")
            previous = -float("inf")
            for row, snapshot in zip(index, result.snapshots):
                if (row["step"] != snapshot.step or row["time"] != snapshot.time
                        or row["cell_shape"] != list(shape) or snapshot.cell_shape != list(shape)
                        or snapshot.time <= previous or not 0 <= snapshot.time <= result.runtime.final_time):
                    raise ValueError("Snapshot index mismatch")
                previous = snapshot.time
                with np.load(target(root, f"snapshots/{snapshot.snapshot_id}.npz"), allow_pickle=False) as data:
                    state = data["state"]
                    if (state.shape != shape or float(data["time"]) != snapshot.time or int(data["step"]) != snapshot.step):
                        raise ValueError("Snapshot state mismatch")
                    primitive_fields(state, config.physics.gamma)
                    if snapshot.time == 0 and not np.array_equal(state, initial):
                        raise ValueError("Initial snapshot differs from initial state")
                    if snapshot.time == result.runtime.final_time and not np.array_equal(state, final):
                        raise ValueError("Final snapshot differs from final state")
            # This fingerprint uses recorded source identity, never current source code.
            identity = digest([result.result_hash, sha256(target(root, "provenance.json")),
                               [(p, recorded[p]["sha256"]) for p in required]])
            return root, result, identity
        except (ValueError, KeyError, OSError) as error:
            raise ExperimentError("RUN_OUTPUT_INVALID", "导出来源文件未通过原始科学清单校验。", 500) from error

    def empty_manifest(self, result, identity):
        return {"schema_version": "1.0", "run_id": result.identity.run_id, "source_result_hash": result.result_hash,
            "source_identity_sha256": identity, "exporter_version": EXPORTER_VERSION,
            "exporter_sha256": self.exporter_sha256, "generated_at": None,
            "formats": {"raw": [], "visualization": [], "report": []}, "exports": {}, "files": []}

    def manifest(self, root, result, identity):
        path = target(root, "exports/manifest.json")
        if not path.exists():
            return self.empty_manifest(result, identity)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if (value["run_id"] != result.identity.run_id or value["source_result_hash"] != result.result_hash
                    or value["source_identity_sha256"] != identity or value["exporter_sha256"] != self.exporter_sha256
                    or value["exporter_version"] != EXPORTER_VERSION):
                return self.empty_manifest(result, identity)
            if value["schema_version"] != "1.0" or not isinstance(value["files"], list):
                raise ValueError("Invalid manifest schema")
            names = set()
            for row in value["files"]:
                name = row["path"]
                if (not SAFE_FILE.fullmatch(name) or name in names or row["kind"] not in KINDS
                        or row["format"] != FORMATS[Path(name).suffix] or type(row["size"]) is not int or row["size"] <= 0
                        or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])):
                    raise ValueError("Invalid export inventory")
                names.add(name)
            for kind, entry in value["exports"].items():
                public = {k: v for k, v in entry.items() if k in ExportMetadata.model_fields}
                if kind not in KINDS or ExportMetadata.model_validate(public).kind != kind:
                    raise ValueError("Invalid export state")
            return value
        except (ValueError, KeyError, TypeError, OSError) as error:
            raise ExperimentError("EXPORT_OUTPUT_INVALID", "导出清单未通过校验，请重新生成导出。", 500) from error

    def cache_valid(self, root, manifest, kind, *, report_key=None, format="zip"):
        entry = manifest["exports"].get(kind, {})
        if entry.get("status") != "READY" or (kind == "report" and entry.get("report_id") != report_key):
            return False
        if format == "pdf" and "PDF" not in entry.get("formats", []):
            return False
        rows = [row for row in manifest["files"] if row["kind"] == kind]
        names = {r["path"] for r in rows}
        required = {
            "raw": {"raw/config.json", "raw/effective_solver_config.json", "raw/provenance.json", "raw/scientific_result.json",
                    "raw/initial_state.npz", "raw/final_state.npz", "diagnostics/history.csv", "diagnostics/entropy_budget.csv"},
            "visualization": {"visualization/timeseries.pvd", "visualization/field_000000.vti"},
            "report": {"reports/report.html"} | ({"reports/report.pdf"} if "PDF" in entry.get("formats", []) else set()),
        }[kind]
        bundle_name = f"bundles/{BUNDLES[kind]}"
        if not rows or not required.issubset(names) or bundle_name not in names:
            return False
        bundle = next(r for r in rows if r["path"] == bundle_name)
        if (entry.get("sha256") != bundle["sha256"] or entry.get("size_bytes") != bundle["size"]
                or entry.get("formats") != manifest["formats"].get(kind)):
            return False
        try:
            for row in rows:
                path = target(root, "exports/" + row["path"])
                if path.stat().st_size != row["size"] or sha256(path) != row["sha256"]:
                    return False
        except (ValueError, OSError):
            return False
        return True

    def public_metadata(self, root, manifest, kind, report_key=None):
        entry = manifest["exports"].get(kind, {"kind": kind, "status": "NOT_GENERATED"})
        # Internal scheduling fields do not cross the API boundary.
        metadata = ExportMetadata.model_validate({k: v for k, v in entry.items() if k in ExportMetadata.model_fields})
        if metadata.status == "GENERATING" and process_identity(entry.get("pid", -1)) != entry.get("process_identity"):
            return metadata.model_copy(update={"status": "FAILED", "reason": "导出进程已中断，请重试。", "error_code": "EXPORT_INTERRUPTED"})
        if metadata.status == "GENERATING":
            try:
                with file_lock(target(root, "exports/generate.lock"), blocking=False):
                    return metadata.model_copy(update={"status": "FAILED", "reason": "导出任务已中断，请重试。", "error_code": "EXPORT_INTERRUPTED"})
            except RuntimeError:
                pass
        if metadata.status == "READY" and not self.cache_valid(root, manifest, kind, report_key=report_key):
            return metadata.model_copy(update={"status": "FAILED", "download_urls": {}, "formats": [],
                "reason": "导出缓存失效，请重新生成。", "error_code": "EXPORT_OUTPUT_INVALID"})
        return metadata

    def status(self, run_id):
        record = self.store.get(run_id)
        capabilities = self.capabilities()
        if record.status != "COMPLETED":
            return RunExports(run_id=run_id, available=False, reason="仅成功完成并通过科学校验的运行可以导出；当前状态：" + record.status,
                source_result_hash=None, exporter_version=EXPORTER_VERSION, capabilities=capabilities,
                exports={k: ExportMetadata(kind=k) for k in KINDS})
        root, result, identity = self.source(run_id)
        manifest = self.manifest(root, result, identity)
        key, report_error = None, None
        if manifest["exports"].get("report", {}).get("status") == "READY":
            try:
                key = self.reports.inputs(run_id)[4]
            except ExperimentError as error:
                report_error = error
        entries = {k: self.public_metadata(root, manifest, k, key) for k in KINDS}
        if report_error:
            entries["report"] = ExportMetadata(kind="report", status="FAILED", error_code=report_error.code, reason=report_error.message)
        if entries["report"].unavailable_formats:
            capabilities["report"]["retryable_formats"] = [f for f in entries["report"].unavailable_formats if f in capabilities["report"]["formats"]]
            capabilities["report"]["unavailable_formats"].update(entries["report"].unavailable_formats)
            capabilities["report"]["formats"] = [f for f in capabilities["report"]["formats"] if f not in entries["report"].unavailable_formats]
        return RunExports(run_id=run_id, available=True, reason=None, source_result_hash=result.result_hash,
                          exporter_version=EXPORTER_VERSION, capabilities=capabilities, exports=entries)

    @contextmanager
    def generation_slot(self, run_id, export_root):
        """Global cross-process admission and conservative disk reservations."""
        settings = self.store.settings
        with ExitStack() as stack:
            for i in range(settings.max_concurrent_exports):
                try:
                    stack.enter_context(file_lock(target(self.store.control, f"export-slot-{i}.lock"), blocking=False))
                    break
                except RuntimeError:
                    continue
            else:
                raise ExperimentError("EXPORT_SERVICE_BUSY", "导出服务繁忙，请稍后重试。", 429, retryable=True)
            reservations_path = target(self.store.control, "export-reservations.json")
            def reservations():
                rows = json.loads(reservations_path.read_text(encoding="utf-8")) if reservations_path.exists() else {}
                return {k: v for k, v in rows.items() if process_identity(v["pid"]) == v["identity"]}
            with file_lock(target(self.store.control, "export-quota.lock")):
                reserved = reservations()
                total = 0
                runs_root = self.store.root / "runs"
                for directory in runs_root.iterdir():
                    if directory.is_dir() and directory.name not in reserved:
                        safe = self.store.directory(directory.name)
                        total += cache_bytes(safe / "exports")
                required = settings.max_export_cache_bytes
                if total + sum(r["bytes"] for r in reserved.values()) + required > settings.max_total_export_cache_bytes:
                    raise ExperimentError("EXPORT_CACHE_LIMIT", "导出总缓存容量不足，请联系管理员清理导出缓存或调整上限。", 413)
                reserved[run_id] = {"pid": os.getpid(), "identity": process_identity(os.getpid()), "bytes": required}
                write_json(self.store.control, "export-reservations.json", reserved)
            try:
                yield ExportBudget(export_root, settings)
            finally:
                with file_lock(target(self.store.control, "export-quota.lock")):
                    reserved = reservations()
                    reserved.pop(run_id, None)
                    write_json(self.store.control, "export-reservations.json", reserved)

    def file_record(self, stage, name, kind, sources, root, result):
        path = target(stage, name)
        source_rows = []
        for source in sources:
            actual = target(root, source)
            if actual.exists():
                source_rows.append({"path": source, "sha256": sha256(actual)})
            elif source == "scientific_result.json":
                source_rows.append({"path": source, "result_hash": result.result_hash, "projection": "verified result API (legacy Run)"})
            else:
                raise ValueError("Missing export source")
        return {"path": name, "kind": kind, "format": FORMATS[path.suffix], "size": path.stat().st_size,
                "sha256": sha256(path), "sources": source_rows}

    def report(self, exporter, run_id, format):
        metadata = self.reports.generate(run_id)
        relative = f"report/{metadata.report_id}.html"
        html_path = exporter.copy(relative, "reports/report.html")
        formats, unavailable = ["HTML"], {}
        browser, reason = pdf_capability(self.store.settings)
        if format != "html":
            if browser:
                output = target(exporter.stage, "reports/report.pdf")
                try:
                    render_pdf(html_path.read_text(encoding="utf-8"), output, browser,
                               timeout=min(45, exporter.budget.remaining()))
                    exporter.sources["reports/report.pdf"] = [relative]
                    formats.append("PDF")
                    exporter.budget.check()
                except PDFUnavailable as error:
                    output.unlink(missing_ok=True)
                    unavailable["PDF"] = str(error)
            else:
                unavailable["PDF"] = reason
        exporter.write_text("reports/README.md", f"# ShockPath experiment report\n\nRun: {run_id}\n"
            f"Result hash: {exporter.result.result_hash}\nReport ID: {metadata.report_id}\n"
            "report.html is copied from the existing verified ReportService; all SVG/data are embedded for offline use.\n"
            "PDF is an A4 print of the same HTML with Chinese fonts, no new analysis or provider call.\n"
            f"PDF status: {'AVAILABLE' if 'PDF' in formats else 'UNAVAILABLE'}\n"
            f"PDF reason: {unavailable.get('PDF', 'Not requested; HTML format selected' if format == 'html' else 'None')}\n",
            [relative, "scientific_result.json"])
        return formats, unavailable, metadata.report_id

    def generate(self, run_id, kind, format="zip"):
        if kind not in KINDS or format not in ("zip", "html", "pdf") or (kind != "report" and format != "zip"):
            raise ExperimentError("INVALID_REQUEST", "不支持的导出分类或格式。", 400)
        # Deny noncompleted or invalid science before creating any export files.
        self.store.get(run_id)
        root = self.store.directory(run_id)
        if self.store.get(run_id).status != "COMPLETED":
            raise ExperimentError("RUN_RESULT_NOT_READY", "运行尚未成功完成，导出不可用。", 409)
        lock = file_lock(target(root, "exports/generate.lock"), blocking=False)
        try:
            lock.__enter__()
        except RuntimeError:
            raise ExperimentError("EXPORT_BUSY", "本次运行的导出正在生成，请稍后重试。", 429, retryable=True) from None
        except ValueError:
            raise ExperimentError("EXPORT_OUTPUT_INVALID", "导出路径校验失败。", 500) from None
        stage = None
        try:
            root, result, identity = self.source(run_id)
            try:
                manifest = self.manifest(root, result, identity)
            except ExperimentError as error:
                if error.code != "EXPORT_OUTPUT_INVALID":
                    raise
                manifest = self.empty_manifest(result, identity)
            key = self.reports.inputs(run_id)[4] if kind == "report" else None
            if self.cache_valid(root, manifest, kind, report_key=key, format=format):
                return self.public_metadata(root, manifest, kind, key)
            if format == "pdf" and pdf_capability(self.store.settings)[1]:
                raise ExperimentError("PDF_UNAVAILABLE", pdf_capability(self.store.settings)[1], 503)
            # Remove only our abandoned export staging area, never any Solver file.
            staging = target(root, "exports/.staging/.owned").parent
            for abandoned in staging.iterdir():
                if abandoned.is_dir():
                    if abandoned.is_symlink() or (hasattr(abandoned, "is_junction") and abandoned.is_junction()):
                        raise ValueError("Linked staging directory")
                    shutil.rmtree(abandoned)
            with self.generation_slot(run_id, root / "exports") as budget:
                entry = {"kind": kind, "status": "GENERATING", "pid": os.getpid(), "process_identity": process_identity(os.getpid())}
                manifest["exports"][kind] = entry
                manifest["formats"][kind] = []
                write_json(root, "exports/manifest.json", manifest)
                stage = target(root, f"exports/.staging/{uuid4()}/.owned").parent
                exporter = Case8Exporter(root, stage, result, budget)
                unavailable = {}
                if kind == "raw":
                    formats = exporter.raw()
                elif kind == "visualization":
                    formats = exporter.visualization()
                else:
                    formats, unavailable, key = self.report(exporter, run_id, format)
                generated = utc_now()
                rows = [self.file_record(stage, name, kind, sources, root, result) for name, sources in exporter.sources.items()]
                prefix = {"raw": "raw", "visualization": "visualization", "report": "reports"}[kind]
                partial = {"schema_version": "1.0", "run_id": run_id, "source_result_hash": result.result_hash,
                    "exporter_version": EXPORTER_VERSION, "exporter_sha256": self.exporter_sha256,
                    "generated_at": generated, "formats": {kind: formats}, "unavailable_formats": unavailable, "files": rows}
                name = f"{prefix}/export_manifest.json"
                exporter.write_json(name, partial, ["scientific_result.json", "provenance.json"])
                rows.append(self.file_record(stage, name, kind, exporter.sources[name], root, result))
                bundle_name = f"bundles/{BUNDLES[kind]}"
                bundle = target(stage, bundle_name)
                # Reserve the worst-case stored size before compression, then stream.
                budget.check(extra=sum(r["size"] for r in rows) + 65536)
                with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5, allowZip64=True) as archive:
                    for row in rows:
                        name = row["path"]
                        archive_name = name.removeprefix("reports/") if kind == "report" else name
                        archive.write(target(stage, name), archive_name)
                        budget.check()
                    if kind == "raw":
                        archive.write(target(stage, "raw/README.md"), "README.md")
                budget.check()
                # Re-verify science after generation; no stale/tampered source is published.
                if self.source(run_id)[2] != identity:
                    raise ExperimentError("RUN_OUTPUT_INVALID", "生成期间科学来源发生变化，导出未发布。", 500)
                bundle_row = {"path": bundle_name, "kind": kind, "format": "ZIP", "size": bundle.stat().st_size,
                              "sha256": sha256(bundle), "sources": [{"path": r["path"], "sha256": r["sha256"], "layer": "exports"} for r in rows]}
                rows.append(bundle_row)
                urls = {"zip": f"/api/v2/runs/{run_id}/exports/{kind}/download"}
                if kind == "report":
                    urls.update({f.lower(): f"/api/v2/runs/{run_id}/exports/report/download?format={f.lower()}" for f in formats})
                ready = ExportMetadata(kind=kind, status="READY", formats=formats, generated_at=generated,
                    size_bytes=bundle_row["size"], sha256=bundle_row["sha256"], download_urls=urls, unavailable_formats=unavailable)
                # Per-file rename, bundle rename, then manifest commit. Downloads share the lock.
                for row in rows:
                    target(stage, row["path"]).replace(target(root, "exports/" + row["path"]))
                if kind == "report" and "PDF" not in formats:
                    target(root, "exports/reports/report.pdf").unlink(missing_ok=True)
                manifest["files"] = [r for r in manifest["files"] if r["kind"] != kind] + rows
                manifest["exports"][kind] = {**ready.model_dump(mode="json"), **({"report_id": key} if kind == "report" else {})}
                manifest["formats"][kind] = formats
                manifest["generated_at"] = generated
                write_json(root, "exports/manifest.json", manifest)
                if format == "pdf" and "PDF" not in formats:
                    raise ExperimentError("PDF_UNAVAILABLE", unavailable["PDF"], 503, retryable=True)
                return ready
        except Exception as error:
            code = error.code if isinstance(error, ExperimentError) else "EXPORT_GENERATION_FAILED"
            message = error.message if isinstance(error, ExperimentError) else "导出生成失败；原始科学结果与 HTML 报告仍可用，请重试。"
            if "manifest" in locals() and code != "PDF_UNAVAILABLE":
                manifest["exports"][kind] = ExportMetadata(kind=kind, status="FAILED", error_code=code, reason=message).model_dump(mode="json")
                manifest["formats"][kind] = []
                write_json(root, "exports/manifest.json", manifest)
            if isinstance(error, ExperimentError):
                raise
            raise ExperimentError(code, message, 500, retryable=True) from error
        finally:
            if stage and stage.exists():
                shutil.rmtree(stage)
            lock.__exit__(None, None, None)

    def download(self, run_id, kind, format="zip"):
        if kind not in KINDS or format not in ("zip", "html", "pdf") or (kind != "report" and format != "zip"):
            raise ExperimentError("INVALID_REQUEST", "不支持的下载格式。", 400)
        self.store.get(run_id)
        root = self.store.directory(run_id)
        if self.store.get(run_id).status != "COMPLETED":
            raise ExperimentError("RUN_RESULT_NOT_READY", "运行尚未完成，下载不可用。", 409)
        try:
            with file_lock(target(root, "exports/generate.lock"), blocking=False):
                root, result, identity = self.source(run_id)
                manifest = self.manifest(root, result, identity)
                key = self.reports.inputs(run_id)[4] if kind == "report" else None
                if not self.cache_valid(root, manifest, kind, report_key=key, format=format):
                    code = "PDF_UNAVAILABLE" if format == "pdf" and manifest["exports"].get(kind, {}).get("status") == "READY" else "EXPORT_NOT_READY"
                    raise ExperimentError(code, "导出文件尚未就绪或缓存校验失败，请重新生成。", 409)
                name = f"bundles/{BUNDLES[kind]}" if format == "zip" else f"reports/report.{format}"
                row = next(r for r in manifest["files"] if r["path"] == name and r["kind"] == kind)
                filename = f"ShockPath_{run_id}_{BUNDLES[kind]}" if format == "zip" else f"ShockPath_{run_id}_report.{format}"
                stream = target(root, "exports/" + name).open("rb")
                return stream, filename, row["size"], row["sha256"]
        except RuntimeError:
            raise ExperimentError("EXPORT_BUSY", "导出正在更新，请稍后重试下载。", 429, retryable=True) from None
        except (ValueError, OSError) as error:
            raise ExperimentError("EXPORT_OUTPUT_INVALID", "导出文件或路径校验失败。", 500) from error
