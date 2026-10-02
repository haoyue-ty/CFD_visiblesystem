"""Guarded read-only hash observation, independent of numerical decoding.

Only backend-registered relative origins resolve. No path is accepted from an
HTTP caller. Missing, unreadable or baseline-free dependencies remain unknown
for drift; a positively detected mismatch wins over every unknown observation.
"""
import hashlib
from pathlib import Path, PureWindowsPath

from backend.models import known, unresolved


def aggregate_drift(facts):
    facts = list(facts)
    if any(f.get("state") == "KNOWN" and f["value"] is True for f in facts):
        return known(True)
    if facts and all(f.get("state") == "KNOWN" and f["value"] is False for f in facts):
        return known(False)
    return unresolved("At least one dependency has no conclusive recorded/current comparison")


class EvidenceSourceObserver:
    def __init__(self, scientific_root, software_root, *, roots=None):
        self.scientific_root = Path(scientific_root).resolve()
        self.software_root = Path(software_root).resolve()
        self.roots = roots or {}

    def observe(self, asset, cache=None):
        cache = cache if cache is not None else {}
        origin = asset["relative_origin"]
        current = unresolved("Registered origin has no available raw source", "MISSING")
        if origin["state"] == "KNOWN":
            relative = origin["value"].replace("\\", "/")
            root = self.software_root if asset["source_id"] == "shockpath-content" else self.roots.get(asset["asset_id"], self.scientific_root)
            root = Path(root).resolve()
            path = (root / relative).resolve()
            # Includes symlink/junction escapes, UNC/drive paths and traversal.
            if PureWindowsPath(relative).is_absolute() or PureWindowsPath(relative).drive or not path.is_relative_to(root):
                current = unresolved("Registered source locator is outside its guarded root")
            elif path in cache:
                current = cache[path]
            else:
                try:
                    before = path.stat()
                    with path.open("rb") as stream:
                        digest = hashlib.file_digest(stream, "sha256").hexdigest()
                    after = path.stat()
                    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                        current = unresolved("Source changed during hash observation")
                    else:
                        current = known(digest)
                except FileNotFoundError:
                    current = unresolved("Registered raw source is missing", "MISSING")
                except OSError:
                    current = unresolved("Registered raw source could not be observed")
                cache[path] = current
        recorded = asset["recorded_data_hash"]
        drift = known(recorded["value"] != current["value"]) if recorded["state"] == current["state"] == "KNOWN" else unresolved("Recorded or current source hash is unavailable")
        asset["current_data_hash"], asset["data_drift"] = current, drift
        asset["verification"]["observation_at"] = unresolved("Read-only hash observation; no persisted event timestamp")
        if asset["verification"]["status"] not in ("MISSING", "LEGACY", "SUPERSEDED", "NOT_APPLICABLE"):
            if current["state"] == "MISSING":
                asset["verification"]["status"] = "MISSING"
            elif drift == known(True) or drift["state"] == "UNKNOWN":
                asset["verification"]["status"] = "PARTIAL"
        return asset
