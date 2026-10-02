"""Reproducibility Center: one registry, four frozen public operations.

Evidence inspection never invokes a numerical reader. Recorded context metadata
remains inspectable after missing/drifting sources and cannot certify delivery.
"""
from copy import deepcopy

from backend.adapters.evidence_sources import EvidenceSourceObserver, aggregate_drift
from backend.core.errors import system_error
from backend.models import EvidenceRecord, EvidenceIndex, ResultProvenance, SourceAsset, known, unresolved
from backend.registry import evidence_registry as R


class EvidenceService:
    registry_revision = R.REGISTRY_REVISION
    data_revision = R.DATA_REVISION

    def __init__(self, scientific_root="D:/Paper/passage6", *, roots=None):
        self.registry = R.EvidenceRegistry()
        self.observer = EvidenceSourceObserver(scientific_root, R.ROOT, roots=roots)

    def owns_evidence(self, identity):
        return identity in self.registry.entries

    def owns_result(self, identity):
        return identity in self.registry.result_evidence

    def revision_for(self, identity):
        if self.owns_result(identity):
            refs = self.registry.result_evidence[identity]
            identity = refs[0]
        raw = self.registry.record(identity) if self.owns_evidence(identity) else None
        if raw and raw["result_contexts"]:
            return raw["result_contexts"][0]["provenance"]["registry_revision"]
        return self.registry_revision

    def load_asset(self, identity, *, cache=None):
        if identity not in self.registry.assets:
            raise system_error("UNKNOWN_ASSET_ID", "Source asset is not registered", status=404, availability="MISSING")
        raw = self.observer.observe(deepcopy(self.registry.assets[identity]), cache)
        raw["verification"]["evidence_refs"] = [self.registry.asset_evidence[identity]] if identity in self.registry.asset_evidence else []
        return SourceAsset.model_validate(raw)

    def load_evidence(self, identity, *, cache=None):
        if not self.owns_evidence(identity):
            raise system_error("UNKNOWN_EVIDENCE_ID", "Evidence identity is not registered", status=404, availability="MISSING")
        cache = cache if cache is not None else {}
        raw = self.registry.record(identity)
        assets = [self.observer.observe(a, cache) for a in raw["source_assets"]]
        for asset in assets:
            asset["verification"]["evidence_refs"] = [identity]
        drift = aggregate_drift(a["data_drift"] for a in assets)
        raw["source_observations"] = [{"asset_id": a["asset_id"], "recorded_hash": a["recorded_data_hash"],
            "current_hash": a["current_data_hash"], "drift": a["data_drift"],
            "observation_at": a["verification"]["observation_at"]} for a in assets]
        raw["source_drift"] = drift
        # Source-code identity is distinct from data and transport hashes.
        method = next((a for a in assets if a["role"] == "METHOD" and a["recorded_data_hash"] == raw["method_hash"] and raw["method_hash"]["state"] == "KNOWN"), None)
        raw["recorded_source_hash"] = method["recorded_data_hash"] if method else unresolved("No singular recorded implementation source hash")
        raw["current_source_hash"] = method["current_data_hash"] if method else unresolved("No singular implementation source observation")
        unhealthy = drift == known(True) or any(a["current_data_hash"]["state"] != "KNOWN" for a in assets)
        if unhealthy:
            limitation = {"id": "lim." + identity + ".source-observation", "code": "SOURCE_DEPENDENCY_UNCONFIRMED",
                "description": "Recorded evidence metadata remains readable. Source drift or unavailable dependencies prevent current reproduction certification; no numerical values are supplied by this endpoint.",
                "severity": "WARNING", "affected_refs": list(raw["result_ids"])}
            raw["limitations"].append(limitation)
            if raw["verification"]["status"] not in ("MISSING", "LEGACY", "SUPERSEDED", "NOT_APPLICABLE"):
                raw["verification"]["status"] = "PARTIAL"
            for context in raw["result_contexts"]:
                context["verification"]["status"] = "PARTIAL"
                context["limitations"].append(limitation)
        asset_ids = [a["asset_id"] for a in assets]
        for context in raw["result_contexts"]:
            context["provenance"]["source_drift"] = drift
            original_ids = context["provenance"]["source_asset_ids"]
            context["provenance"]["source_asset_ids"] = list(dict.fromkeys(original_ids + sorted(set(asset_ids) - set(original_ids))))
            # Contexts can be shared by a snapshot group and field detail.
            if not any(ref in self.registry.entries for ref in context["provenance"]["evidence_refs"]):
                context["provenance"]["evidence_refs"] = [identity]
        return EvidenceRecord.model_validate(raw)

    def list_evidence(self, query):
        # Filter before paging. Shared asset observations are deduplicated per
        # request; no numerical data or complete catalog is shipped to clients.
        identities = []
        cache, observed_assets, observed_items = {}, {}, {}

        def item_for(identity, descriptor, asset_ids):
            item = deepcopy(descriptor)
            for asset_id in asset_ids:
                if asset_id not in observed_assets:
                    observed_assets[asset_id] = self.observer.observe(deepcopy(self.registry.assets[asset_id]), cache)
            assets = [observed_assets[a] for a in asset_ids]
            item["source_drift"] = aggregate_drift(a["data_drift"] for a in assets)
            if item["verification"]["status"] not in ("MISSING", "LEGACY", "SUPERSEDED", "NOT_APPLICABLE") and (
                    item["source_drift"] == known(True) or any(a["current_data_hash"]["state"] != "KNOWN" for a in assets)):
                item["verification"]["status"] = "PARTIAL"
            item["verification"]["evidence_refs"] = [identity]
            return item

        for identity in sorted(self.registry.entries):
            section = self.registry.sections[identity]
            if query.section == "HISTORY" and section != "HISTORY" or query.section in ("CURRENT", "GAPS") and section == "HISTORY":
                continue
            descriptor, asset_ids = self.registry.index_metadata(identity)
            if query.experiment_id is not None and descriptor["experiment_id"] != known(query.experiment_id):
                continue
            if section == "CURRENT":
                # Newly absent/drifting numerical dependencies join GAPS;
                # EVI02 and EVI03 still retain recorded context for inspection.
                item = item_for(identity, descriptor, asset_ids)
                observed_items[identity] = item
                if any(observed_assets[a]["role"] != "METHOD" and (
                       observed_assets[a]["current_data_hash"]["state"] == "MISSING" or observed_assets[a]["data_drift"] == known(True)) for a in asset_ids):
                    section = "GAPS"
            if query.section != "ALL" and section != query.section:
                continue
            if query.status is not None:
                item = observed_items.get(identity) or item_for(identity, descriptor, asset_ids)
                if item["verification"]["status"] != query.status:
                    continue
                observed_items[identity] = item
            identities.append(identity)
        total = len(identities)
        items = []
        for identity in identities[query.offset:query.offset + query.limit]:
            descriptor, asset_ids = self.registry.index_metadata(identity)
            items.append(observed_items.get(identity) or item_for(identity, descriptor, asset_ids))
        return EvidenceIndex.model_validate({"items": items, "page": {"offset": query.offset, "limit": query.limit,
            "returned_count": len(items), "total_count": total, "has_more": query.offset + len(items) < total}})

    def load_provenance(self, identity):
        if not self.owns_result(identity):
            raise system_error("INVALID_RESULT_ID", "Result identity is not registered", status=404, availability="MISSING")
        refs = self.registry.result_evidence[identity]
        # Retain every direct evidence ref on the accepted scientific header.
        header = deepcopy(self.registry.catalog["contexts"].get(identity))
        if header:
            direct = header["provenance"]["evidence_refs"]
            refs = sorted(set(refs + [r for r in direct if self.owns_evidence(r)]))
        cache = {}
        records = [self.load_evidence(ref, cache=cache) for ref in refs]
        if header is None:
            header = next((c.model_dump(mode="python") for r in records for c in r.result_contexts if c.result_id == identity), None)
        provenance = deepcopy(header["provenance"]) if header else {
            "registry_revision": self.registry_revision, "data_revision": self.data_revision,
            "release_id": unresolved("No composite numerical release", "NOT_APPLICABLE")}
        asset_ids = {a.asset_id for r in records for a in r.source_assets}
        original_ids = provenance.get("source_asset_ids", [])
        provenance.update(evidence_refs=refs, source_asset_ids=list(dict.fromkeys(original_ids + sorted(asset_ids - set(original_ids)))),
                          source_drift=aggregate_drift(r.source_drift.model_dump(mode="python") for r in records))
        return ResultProvenance.model_validate({"result_id": identity, "provenance": provenance, "evidence_records": records})

    def guard_result(self, identity):
        """Numerical delivery must stop on a positively observed data drift."""
        if not self.owns_result(identity):
            return
        cache = {}
        for ref in self.registry.result_evidence[identity]:
            raw = self.registry.record(ref)
            for asset in raw["source_assets"]:
                if asset["role"] in ("DATA", "CONFIG", "MASK", "ANALYSIS", "FREEZE"):
                    observed = self.observer.observe(asset, cache)
                    if observed["data_drift"] == known(True):
                        raise system_error("SOURCE_DATA_DRIFT", "Recorded source dependency differs from the accepted hash", status=409,
                                           domain="SCIENTIFIC", evidence_refs=[ref])
