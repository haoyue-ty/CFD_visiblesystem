"""Case8 file projections only. Never import or execute the frozen Solver."""
import base64
import csv
import json
import re
import shutil
import struct
from xml.etree import ElementTree as ET

import numpy as np

from backend.postprocess.case8 import FIELD_DEFINITIONS, cell_axes, primitive_fields, read
from backend.solver_runtime.artifacts import sha256, target


def csv_value(value):
    if value is None:
        return "NA"
    if isinstance(value, float):
        return repr(value)  # Round-trips the source binary64; no display rounding.
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    return str(value)


def diagnostic_definition(name):
    known = {
        "step": "Zero-based accepted-step index (not snapshot index); dimensionless",
        "time_start": "Start of accepted interval; model time",
        "time_end": "End of accepted interval; model time",
        "dt": "Accepted interval length; model time",
    }
    if name in known:
        return known[name]
    if re.fullmatch(r"dotE_(bg|aa|at|total)_s[012]", name):
        return "Native-face entropy rate at SSP-RK3 stage U_n/U_1/U_2 (s0/s1/s2); model entropy / model time"
    if re.fullmatch(r"deltaE_(bg|aa|at|total)", name):
        return "Accepted-step entropy increment dt * sum_s w_s * dotE_channel_s; model entropy"
    if re.fullmatch(r"E_(bg|aa|at|total)", name):
        return "Cumulative accepted-step entropy integral through time_end; model entropy"
    if "additivity" in name:
        scale = "relative (dimensionless)" if "rel_error" in name else "absolute (model entropy / model time)"
        return f"Source channel-additivity {scale} residual at the named SSP-RK3 stage; preserved without renormalization"
    if re.fullmatch(r"J_max_s[012]", name):
        return "Maximum frozen-flux jump_scale J over unique native faces at the named SSP-RK3 stage; source model scale, no SI calibration"
    if re.fullmatch(r"pt_z_norm2_max_s[012]", name):
        return "Maximum ||P_T z||^2 over unique native faces at the named SSP-RK3 stage; z=T^T*(w_right-w_left), w=entropy variables; source model scale"
    if name.startswith("pi_") or "pi_" in name:
        return "Source instantaneous face diagnostic; preserved under its original name, never converted to cumulative E"
    return "Additional source diagnostic; original name and value preserved verbatim, no unit inferred (see effective Solver config)"


class Case8Exporter:
    def __init__(self, root, stage, result, budget):
        self.root, self.stage, self.result, self.budget = root, stage, result, budget
        self.config = result.config.normalized_config
        self.sources = {}

    def write_text(self, name, value, sources):
        self.budget.check(extra=len(value.encode("utf-8")))
        path = target(self.stage, name)
        path.write_text(value, encoding="utf-8", newline="\n")
        self.sources[name] = sources
        self.budget.check()
        return path

    def write_json(self, name, value, sources):
        return self.write_text(name, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                                              allow_nan=False) + "\n", sources)

    def copy(self, relative, destination):
        source = target(self.root, relative)
        self.budget.check(extra=source.stat().st_size)
        output = target(self.stage, destination)
        shutil.copyfile(source, output)  # No hard link can mutate an original NPZ.
        if sha256(source) != sha256(output):
            raise ValueError("Export copy differs from source")
        self.sources[destination] = [relative]
        self.budget.check()
        return output

    def diagnostics(self):
        rows = [json.loads(line) for line in target(self.root, "diagnostics/history.jsonl").read_text(encoding="utf-8").splitlines()]
        if len(rows) != self.result.runtime.accepted_steps or rows != self.result.entropy.rows:
            raise ValueError("Export history differs from verified result")
        # Union across every row, preserving all source columns and absence.
        columns = list(dict.fromkeys(key for row in rows for key in row))
        entropy_columns = [key for key in columns if key in ("step", "time_start", "time_end", "dt")
                           or re.fullmatch(r"(?:dotE_(?:bg|aa|at|total)_s[012]|deltaE_(?:bg|aa|at|total)|E_(?:bg|aa|at|total))", key)]
        for name, names in (("history", columns), ("entropy_budget", entropy_columns)):
            path = target(self.stage, f"diagnostics/{name}.csv")
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=names)
                writer.writeheader()
                for row in rows:
                    writer.writerow({key: csv_value(row.get(key)) for key in names})
                    self.budget.check()
            self.sources[f"diagnostics/{name}.csv"] = ["diagnostics/history.jsonl"]
        self.write_json("diagnostics/physical_metrics.json", {
            "run_id": self.result.identity.run_id, "source_result_hash": self.result.result_hash,
            "metrics": [m.model_dump(mode="json") for m in self.result.metrics],
            "entropy_totals": self.result.entropy.totals,
        }, ["scientific_result.json", "result.json", "diagnostics/history.jsonl"])
        definitions = "\n".join(f"| `{name}` | {diagnostic_definition(name)} |" for name in columns)
        self.write_text("diagnostics/README.md", "# Diagnostics\n\n"
            "UTF-8 CSV (with BOM for spreadsheet readers). history.csv retains the union of ALL source JSONL columns.\n"
            "entropy_budget.csv is an additional entropy projection; history.csv remains complete.\n"
            "Missing keys and null values are NA, never zero. Float values use round-trip precision.\n"
            "SSP-RK3 weights: 1/6, 1/6, 2/3. Channels: bg (baseline), aa (acoustic addition), at (transverse addition), total.\n\n"
            "| Source column | Meaning |\n| --- | --- |\n" + definitions + "\n",
            ["diagnostics/history.jsonl", "effective_solver_config.json"])

    def npz_descriptions(self, paths):
        lines = ["| File | Array | Actual shape | Axis / meaning |", "| --- | --- | --- | --- |"]
        for relative in paths:
            with np.load(target(self.root, relative), allow_pickle=False) as data:
                for key in data.files:
                    array = data[key]
                    if key in ("state", "conservative_state"):
                        meaning = "(y_cell, x_cell, conservative component); [density, density*velocity_x, density*velocity_y, total energy density]"
                    elif key == "primitive":
                        meaning = "(y_cell, x_cell, primitive component); [density, velocity_x, velocity_y, pressure], original Solver conversion"
                    elif key in ("density", "pressure"):
                        meaning = f"(y_cell, x_cell); {FIELD_DEFINITIONS[key][1]}; final Solver diagnostic field"
                    elif key == "x":
                        meaning = "Actual x cell-center coordinates; model length (1D x or source broadcast y,x mesh)"
                    elif key == "y":
                        meaning = "Actual y cell-center coordinates; model length (1D y or source broadcast y,x mesh)"
                    elif key.startswith("x_faces_"):
                        meaning = "(y_cell, x_face), including both x boundaries; " + self.face_definition(relative, key[8:])
                    elif key.startswith("y_faces_"):
                        meaning = "(y_face, x_cell); periodic y seam counted once; " + self.face_definition(relative, key[8:])
                    elif key == "front":
                        meaning = "(y_cell); row-local p50 crossing anchored to intended Case8 front; model x length; NaN when detector unavailable"
                    elif key == "width":
                        meaning = "(y_cell); row-local x90-x10 around the anchored p50 crossing; model length; NaN when unavailable"
                    elif key == "front_displacement":
                        meaning = "(y_cell); front minus mean of finite front rows; model length; missing rows remain NaN"
                    elif key.endswith("_modes"):
                        meaning = "(rfft_mode); integer Fourier mode number, 0 through ny/2; dimensionless"
                    elif key.endswith(("_amplitude", "_energy")):
                        signal = "front_displacement" if key.startswith("front_") else "row mean over ALL x cells of velocity_y * 1(|x-initial_front(y)|<=0.08)"
                        quantity = "abs(rfft(signal)/ny)" if key.endswith("_amplitude") else "abs(rfft(signal)/ny)^2, no extra factor two"
                        units = "model length" if key.startswith("front_") else "model velocity"
                        if key.endswith("_energy"):
                            units += " squared (modal squared amplitude, not total physical energy)"
                        meaning = f"(rfft_mode); {quantity}; signal={signal}; {units}. Original source spectrum replaces NaN signal rows by zero; missing-front HF remains unavailable in scientific_result"
                    elif key in ("step", "accepted_steps"):
                        meaning = "Scalar accepted-step count / snapshot step (dimensionless)"
                    elif key == "time":
                        meaning = "Scalar actual recorded model time"
                    else:
                        meaning = "Original Solver diagnostic array; shape preserved, no new physical interpretation"
                    lines.append(f"| `{relative}` | `{key}` | `{array.shape}` | {meaning} |")
        return "\n".join(lines)

    @staticmethod
    def face_definition(relative, key):
        if key.startswith("pi_"):
            channel = key[3:]
            if relative.startswith("derived/"):
                return f"cumulative A_{channel}(face)=sum_accepted_steps dt*sum_s w_s*Pi_{channel}(U_s,face); model entropy / face measure, not instantaneous Pi"
            return f"instantaneous Pi_{channel}=0.5*Delta_w^T*D_w,{channel}*Delta_w; model entropy / model time / face measure, no time weight applied"
        if key == "J":
            return "frozen flux jump_scale J; source activation observable / model scale, no SI calibration"
        if key == "pt_z_norm2":
            return "||P_T z||^2, z=T^T*(w_right-w_left), w=entropy variables; original transverse-channel activation observable / model scale"
        return "original native face diagnostic " + key + "; no inferred unit"

    def raw(self):
        paths = ["config.json", "effective_solver_config.json", "provenance.json", "result.json",
                 "initial_state.npz", "final_state.npz", "snapshots/index.json", "diagnostics/history.jsonl"]
        paths += [f"snapshots/{s.snapshot_id}.npz" for s in self.result.snapshots]
        recorded = {r["path"] for r in read(self.root, "provenance.json")["outputs"]}
        paths += [p for p in ("derived/physical_fields.npz", "derived/cumulative_faces.npz") if p in recorded]
        for relative in paths:
            self.copy(relative, "raw/" + relative)
        if target(self.root, "scientific_result.json").exists():
            self.copy("scientific_result.json", "raw/scientific_result.json")
        else:
            # Legacy result projection is identical to the existing result API.
            self.write_json("raw/scientific_result.json", self.result.model_dump(mode="json"),
                            ["config.json", "effective_solver_config.json", "result.json", "provenance.json", "diagnostics/history.jsonl"])
        self.diagnostics()
        grid = self.config.grid
        readme = f"""# ShockPath raw CFD data

Run ID: {self.result.identity.run_id}
Case: {self.config.case_id}; method: {self.config.method.method_id}; first-order finite volume / SSP-RK3.
Actual grid: nx={grid.nx}, ny={grid.ny}; x={grid.domain.x}, y={grid.domain.y}; gamma={self.config.physics.gamma!r}.
Result hash: {self.result.result_hash}
Method hash: {self.result.provenance.method_sha256}
Data source: verified, completed V2 independent-worker Run. Every NPZ is a byte-for-byte copy.

## Units and time

All dimensional variables are MODEL units without SI calibration. Density: model density;
pressure / total energy density: model pressure; velocity / speed: model velocity;
momentum density: model density * model velocity; Mach: dimensionless.
Coordinates: model length; time: model time. Initial state is at t=0. Final state is at
t={self.result.runtime.final_time!r}. Snapshot time and step are copied from each actual NPZ,
also listed in raw/snapshots/index.json; no resimulation or interpolation.
Cell fields have (ny,nx) order, x fastest in C order. Native face arrays are NOT cell data;
instantaneous snapshot Pi and cumulative derived face allocations are different quantities.
Pi has model entropy / model time / face measure; cumulative face allocation has model entropy / face measure.
Spatial scalar integrals use dy*sum(x_faces)+dx*sum(y_faces); periodic y seam occurs once.

## NPZ arrays (actual storage, no reshaping)

{self.npz_descriptions([p for p in paths if p.endswith('.npz')])}

## Diagnostics

See diagnostics/README.md for EVERY history.csv column. NA denotes missing values.
The original JSONL is also included; entropy_budget.csv does not replace history.csv.
physical_metrics.json retains unavailable/null detector outputs and their reasons.
Scientific limitations: {json.dumps(self.result.limitations, ensure_ascii=False)}
Existing provenance and method hashes describe original science; export manifests describe copies only.
"""
        self.write_text("raw/README.md", readme, ["config.json", "provenance.json", "snapshots/index.json"])
        return ["NPZ", "JSON", "CSV"]

    def visualization(self):
        cell_axes(self.root, self.config)  # Verify actual centers against domain edges.
        nx, ny = self.config.grid.nx, self.config.grid.ny
        x0, x1 = self.config.grid.domain.x
        y0, y1 = self.config.grid.domain.y
        dx, dy = (x1 - x0) / nx, (y1 - y0) / ny
        dz = min(dx, dy)
        extent = f"0 {nx} 0 {ny} 0 1"  # One real layer of cells, two z point planes.
        collection = ET.Element("VTKFile", type="Collection", version="0.1", byte_order="LittleEndian")
        series = ET.SubElement(collection, "Collection")
        previous = -float("inf")
        if not self.result.snapshots:
            raise ValueError("Completed result has no real snapshots")
        for index, snapshot in enumerate(self.result.snapshots):
            if snapshot.time <= previous or not re.fullmatch(r"step_[0-9]{6}", snapshot.snapshot_id):
                raise ValueError("Snapshot identities/times are not ordered")
            previous = snapshot.time
            relative = f"snapshots/{snapshot.snapshot_id}.npz"
            with np.load(target(self.root, relative), allow_pickle=False) as data:
                state = data["state"]
                if (state.shape != (ny, nx, 4) or int(data["step"]) != snapshot.step
                        or float(data["time"]) != snapshot.time):
                    raise ValueError("Snapshot metadata mismatch")
                fields = primitive_fields(state, self.config.physics.gamma)
                fields.update(momentum_density_x=state[..., 1], momentum_density_y=state[..., 2],
                              total_energy_density=state[..., 3])
                vtk = ET.Element("VTKFile", type="ImageData", version="1.0", byte_order="LittleEndian", header_type="UInt64")
                image = ET.SubElement(vtk, "ImageData", WholeExtent=extent,
                    Origin=f"{x0!r} {y0!r} {-dz/2!r}", Spacing=f"{dx!r} {dy!r} {dz!r}")
                meta = ET.SubElement(image, "FieldData")
                ET.SubElement(meta, "DataArray", type="Float64", Name="TimeValue", NumberOfTuples="1", format="ascii").text = repr(snapshot.time)
                piece = ET.SubElement(image, "Piece", Extent=extent)
                ET.SubElement(piece, "PointData")
                cells = ET.SubElement(piece, "CellData", Scalars="density")
                for name, array in fields.items():
                    # VTK tuple index = x + nx*y + nx*ny*z. Float64 binary is lossless.
                    values = np.asarray(array, dtype="<f8").tobytes(order="C")
                    ET.SubElement(cells, "DataArray", type="Float64", Name=name, NumberOfComponents="1", format="binary").text = base64.b64encode(struct.pack("<Q", len(values)) + values).decode("ascii")
                filename = f"field_{index:06d}.vti"
                self.write_text("visualization/" + filename, ET.tostring(vtk, encoding="unicode", xml_declaration=True) + "\n",
                                [relative, "initial_state.npz", "effective_solver_config.json"])
                ET.SubElement(series, "DataSet", timestep=repr(snapshot.time), group="", part="0", file=filename)
        self.write_text("visualization/timeseries.pvd", ET.tostring(collection, encoding="unicode", xml_declaration=True) + "\n",
                        ["snapshots/index.json", *[f"snapshots/{s.snapshot_id}.npz" for s in self.result.snapshots]])
        definitions = "\n".join(f"- {name}: {unit}; {definition}" for name, (_, unit, definition) in FIELD_DEFINITIONS.items())
        self.write_text("visualization/README.md", f"""# ShockPath Case8 VTK / PVD

Run: {self.result.identity.run_id}; verified result: {self.result.result_hash}.
Open timeseries.pvd in ParaView; every DataSet is one actually recorded snapshot.
nx={nx}, ny={ny}; domain x=[{x0},{x1}], y=[{y0},{y1}]; dx={dx!r}, dy={dy!r}.
ImageData point extent {extent}; {nx*ny} CellData tuples; NO PointData fields.
Origin is the x/y lower DOMAIN EDGE, not the first cell center. x fastest, then y;
tuple index x+nx*y. Source shape (ny,nx), without transpose or vertical flip.
Z is a display-only single extruded layer of thickness {dz!r}, centered on z=0;
it does not add a simulated physical dimension. Units are model units, not SI.
Binary little-endian Float64, UInt64 length header; no lossy display rounding.
gamma={self.config.physics.gamma!r}; primitive conversion uses backend/postprocess/case8.py.

{definitions}
- momentum_density_x/y: model density * model velocity; original U[...,1/2].
- total_energy_density: model pressure / model energy density; original U[...,3].

Limits: only stored times are available; no temporal interpolation or new CFD values.
""", ["config.json", "initial_state.npz", "effective_solver_config.json"])
        return ["VTI", "PVD"]
