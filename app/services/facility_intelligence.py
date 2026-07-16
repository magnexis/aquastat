from __future__ import annotations

import ipaddress
import uuid
from collections.abc import Iterable
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, status

from app.core.config import settings
from app.db.models import CoolingType
from app.repository import get_region
from app.services.phase2_model import estimate_realtime_water_metrics
from app.services.risk import classify_water_stress
from app.services.telemetry import get_cached_or_baseline_snapshot
from app.services.water_accounting import classify_water_figure

DATASET_VERSIONS = {
    "facilityRegistry": "2026.07.1",
    "organizationRegistry": "2026.07.1",
    "sourceRegistry": "2026.07.1",
    "gridWaterIntensity": "2026.1",
    "waterStress": "2025.2",
    "climateProfiles": "1.1.2",
}

SOURCE_RELIABILITY = {
    "water-permit": {"score": 94, "tier": "Tier 1", "explanation": "Primary regulatory permit with facility-specific infrastructure details."},
    "utility-filing": {"score": 92, "tier": "Tier 1", "explanation": "Utility interconnection material with dated capacity context."},
    "planning-application": {"score": 86, "tier": "Tier 2", "explanation": "Planning material with project scope, but not necessarily operational."},
    "company-sustainability-report": {"score": 80, "tier": "Tier 2", "explanation": "Operator-published disclosure with partial measurement detail."},
    "news-report": {"score": 62, "tier": "Tier 3", "explanation": "Secondary reporting that can help with context but may compress scope."},
    "facility-directory": {"score": 45, "tier": "Tier 4", "explanation": "Directory-style listing with limited verification and temporal detail."},
    "user-submitted-source": {"score": 25, "tier": "Tier 5", "explanation": "User-supplied content requiring human review before trust."},
}

GRID_WATER_INTENSITY = {
    "US-PJM": 1.12,
    "IE": 0.62,
    "US-NW-PACW": 0.88,
}

ORGANIZATIONS = [
    {
        "id": "org_syn_cloud",
        "name": "Synthetic Cloud Operator",
        "legal_name": "Synthetic Cloud Operator LLC",
        "aliases": ["SCO"],
        "organization_type": "cloud-provider",
        "country": "US",
        "website": "https://example.com/synthetic-cloud",
        "facility_ids": ["fac_syn_ashburn", "fac_syn_dublin"],
        "relationships": [{"type": "operates", "target": "Synthetic Hyperscale Campus A"}],
        "warnings": ["Synthetic organization fixture for Phase 3 development and testing."],
    },
    {
        "id": "org_syn_colo",
        "name": "Synthetic Colo Group",
        "legal_name": "Synthetic Colo Group plc",
        "aliases": ["SCG"],
        "organization_type": "colocation-provider",
        "country": "IE",
        "website": "https://example.com/synthetic-colo",
        "facility_ids": ["fac_syn_colo_b"],
        "relationships": [{"type": "operates", "target": "Synthetic Colocation Facility B"}],
        "warnings": ["Synthetic organization fixture for Phase 3 development and testing."],
    },
]

SOURCES = [
    {
        "id": "src_syn_plan_ashburn",
        "title": "Synthetic Hyperscale Campus A planning application",
        "publisher": "Synthetic County Planning Office",
        "source_type": "planning-application",
        "url": "https://example.com/docs/synthetic-campus-a-planning.pdf",
        "document_type": "pdf",
        "publication_date": "2025-04-12",
        "retrieved_at": "2026-07-15T12:00:00Z",
        "license": "public-record-demo",
        "jurisdiction": "US-VA",
        "language": "en",
        "access_status": "public",
        "parser_version": "phase3-demo-1.0",
        "ingestion_status": "reviewed",
        "review_status": "approved",
        "notes": "Synthetic planning fixture modeled after common capacity and cooling disclosures.",
    },
    {
        "id": "src_syn_water_ashburn",
        "title": "Synthetic Campus A reclaimed water permit",
        "publisher": "Synthetic Regional Water Authority",
        "source_type": "water-permit",
        "url": "https://example.com/docs/synthetic-campus-a-water-permit.pdf",
        "document_type": "pdf",
        "publication_date": "2026-01-08",
        "retrieved_at": "2026-07-15T12:10:00Z",
        "license": "public-record-demo",
        "jurisdiction": "US-VA",
        "language": "en",
        "access_status": "public",
        "parser_version": "phase3-demo-1.0",
        "ingestion_status": "reviewed",
        "review_status": "approved",
        "notes": "Synthetic permit fixture describing reclaimed-water use.",
        "origin_chain_id": "chain_water_permit_ashburn",
    },
    {
        "id": "src_syn_sust_dublin",
        "title": "Synthetic Cloud Operator 2025 sustainability report",
        "publisher": "Synthetic Cloud Operator",
        "source_type": "company-sustainability-report",
        "url": "https://example.com/reports/synthetic-cloud-2025.pdf",
        "document_type": "pdf",
        "publication_date": "2026-03-20",
        "retrieved_at": "2026-07-15T12:15:00Z",
        "license": "company-demo",
        "jurisdiction": "IE",
        "language": "en",
        "access_status": "public",
        "parser_version": "phase3-demo-1.0",
        "ingestion_status": "reviewed",
        "review_status": "approved",
        "notes": "Synthetic sustainability fixture with campus-level PUE and water context.",
        "origin_chain_id": "chain_sust_report_dublin",
    },
    {
        "id": "src_syn_utility_dublin",
        "title": "Synthetic Dublin interconnection filing",
        "publisher": "Synthetic Grid Utility",
        "source_type": "utility-filing",
        "url": "https://example.com/utility/synthetic-dublin-interconnection.pdf",
        "document_type": "pdf",
        "publication_date": "2025-11-01",
        "retrieved_at": "2026-07-15T12:18:00Z",
        "license": "public-record-demo",
        "jurisdiction": "IE",
        "language": "en",
        "access_status": "public",
        "parser_version": "phase3-demo-1.0",
        "ingestion_status": "reviewed",
        "review_status": "approved",
        "notes": "Synthetic utility fixture with capacity allocation context.",
        "origin_chain_id": "chain_utility_dublin",
    },
]

SOURCE_CONNECTORS = [
    {
        "source_id": "connector_public_permits_va",
        "publisher": "Synthetic County Planning Office",
        "source_type": "planning-application",
        "jurisdiction": "US-VA",
        "access_method": "configured-html",
        "refresh_cadence": "weekly",
        "parser_version": "phase-final-1.0",
        "terms": "Public-record access only; no authenticated or private-network retrieval.",
        "last_successful_fetch": "2026-07-15T12:00:00Z",
        "last_failure": None,
        "checksum_policy": "document-content-hash",
        "archival_policy": "store metadata and excerpts only",
    },
    {
        "source_id": "connector_utility_filings_ie",
        "publisher": "Synthetic Grid Utility",
        "source_type": "utility-filing",
        "jurisdiction": "IE",
        "access_method": "configured-pdf-portal",
        "refresh_cadence": "daily",
        "parser_version": "phase-final-1.0",
        "terms": "Public utility filings only; respect portal rate limits and attribution terms.",
        "last_successful_fetch": "2026-07-15T12:18:00Z",
        "last_failure": None,
        "checksum_policy": "document-content-hash",
        "archival_policy": "store metadata, citations, and structured claims",
    },
]

FACILITIES = [
    {
        "id": "fac_syn_ashburn",
        "slug": "synthetic-hyperscale-campus-a",
        "name": "Synthetic Hyperscale Campus A",
        "aliases": ["Campus A", "Synthetic Ashburn Campus"],
        "operator_id": "org_syn_cloud",
        "owner_id": "org_syn_cloud",
        "facility_type": "hyperscale",
        "operational_status": "operational",
        "country": "US",
        "state_or_province": "Virginia",
        "municipality": "Ashburn",
        "address": "1000 Synthetic Loop",
        "latitude": 39.0438,
        "longitude": -77.4874,
        "campus_name": "Synthetic Hyperscale Campus",
        "announced_it_load_mw": 96.0,
        "estimated_it_load_mw": 84.0,
        "pue": 1.23,
        "wue_liters_per_kwh": 1.72,
        "cooling_systems": ["direct-evaporative", "cooling-tower"],
        "water_sources": [
            {"type": "municipal-reclaimed", "percent": 70.0, "status": "reported"},
            {"type": "municipal-potable", "percent": 30.0, "status": "reported"},
        ],
        "electricity_grid_region": "US-PJM",
        "utility_providers": ["Synthetic Regional Water Authority", "Synthetic Grid Utility"],
        "reported_data_year": 2025,
        "verification_status": "partially-verified",
        "record_status": "published",
        "confidence_score": 82,
        "synthetic": True,
        "production_eligible": False,
        "region_profile_key": ("aws", "us-east-1"),
        "coverage": {
            "location": "verified",
            "capacity": "source-linked",
            "cooling_system": "source-linked",
            "pue": "documented",
            "wue": "estimated",
            "water_use": "estimated",
        },
        "verification_notes": [
            "Facility record is synthetic and intended only for development and testing.",
            "Capacity and cooling values are modeled after public planning-style disclosures.",
        ],
        "warnings": ["SYNTHETIC_DEVELOPMENT_FIXTURE", "WUE_ESTIMATED"],
    },
    {
        "id": "fac_syn_dublin",
        "slug": "synthetic-dublin-cloud-campus",
        "name": "Synthetic Dublin Cloud Campus",
        "aliases": ["Synthetic Dublin Campus"],
        "operator_id": "org_syn_cloud",
        "owner_id": "org_syn_cloud",
        "facility_type": "cloud-region",
        "operational_status": "operational",
        "country": "IE",
        "state_or_province": "Leinster",
        "municipality": "Dublin",
        "address": "25 Synthetic Quay",
        "latitude": 53.3498,
        "longitude": -6.2603,
        "campus_name": "Synthetic Europe Campus",
        "announced_it_load_mw": 72.0,
        "estimated_it_load_mw": 65.0,
        "pue": 1.17,
        "wue_liters_per_kwh": 1.38,
        "cooling_systems": ["adiabatic", "air-cooled"],
        "water_sources": [{"type": "municipal-potable", "percent": 100.0, "status": "documented"}],
        "electricity_grid_region": "IE",
        "utility_providers": ["Synthetic Grid Utility"],
        "reported_data_year": 2025,
        "verification_status": "source-linked",
        "record_status": "published",
        "confidence_score": 76,
        "synthetic": True,
        "production_eligible": False,
        "region_profile_key": ("aws", "eu-west-1"),
        "coverage": {
            "location": "verified",
            "capacity": "source-linked",
            "cooling_system": "documented",
            "pue": "documented",
            "wue": "estimated",
            "water_use": "estimated",
        },
        "verification_notes": [
            "Synthetic sustainability and utility fixtures provide the primary provenance.",
            "No facility-specific measured water consumption is stored in this record.",
        ],
        "warnings": ["SYNTHETIC_DEVELOPMENT_FIXTURE", "FACILITY_WATER_USE_UNAVAILABLE"],
    },
    {
        "id": "fac_syn_colo_b",
        "slug": "synthetic-colocation-facility-b",
        "name": "Synthetic Colocation Facility B",
        "aliases": ["Facility B"],
        "operator_id": "org_syn_colo",
        "owner_id": "org_syn_colo",
        "facility_type": "colocation",
        "operational_status": "under-construction",
        "country": "US",
        "state_or_province": "Oregon",
        "municipality": "Hillsboro",
        "address": "800 Example Parkway",
        "latitude": 45.5152,
        "longitude": -122.6784,
        "campus_name": "Synthetic Northwest Campus",
        "announced_it_load_mw": 40.0,
        "estimated_it_load_mw": 34.0,
        "pue": 1.2,
        "wue_liters_per_kwh": 0.92,
        "cooling_systems": ["closed-loop-liquid", "air-cooled"],
        "water_sources": [{"type": "municipal-potable", "percent": 100.0, "status": "planned"}],
        "electricity_grid_region": "US-NW-PACW",
        "utility_providers": ["Synthetic Northwest Utility"],
        "reported_data_year": 2026,
        "verification_status": "identified",
        "record_status": "published",
        "confidence_score": 61,
        "synthetic": True,
        "production_eligible": False,
        "region_profile_key": ("azure", "us-west-2"),
        "coverage": {
            "location": "source-linked",
            "capacity": "documented",
            "cooling_system": "estimated",
            "pue": "estimated",
            "wue": "estimated",
            "water_use": "estimated",
        },
        "verification_notes": [
            "Project remains under construction; planned values are kept separate from operational measurements.",
        ],
        "warnings": ["SYNTHETIC_DEVELOPMENT_FIXTURE", "PLANNED_CAPACITY_ONLY", "LOW_CONFIDENCE_ESTIMATE"],
    },
]

FACILITY_EVIDENCE: dict[str, list[dict[str, Any]]] = {
    "fac_syn_ashburn": [
        {
            "field": "announcedItLoadMw",
            "value": 96.0,
            "unit": "megawatts",
            "evidence_class": "Level B",
            "figure_type": "official-reported",
            "reporting_boundary": "campus",
            "source_id": "src_syn_plan_ashburn",
            "source_type": "planning-application",
            "source_date": "2025-04-12",
            "extraction_method": "manual",
            "verification_status": "source-linked",
            "confidence": 0.91,
            "value_status": "documented",
            "independent_chain_id": "chain_plan_ashburn",
            "notes": "Planning application describes critical IT capacity for the first two phases.",
        },
        {
            "field": "coolingSystems",
            "value": "direct-evaporative",
            "unit": None,
            "evidence_class": "Level B",
            "figure_type": "official-reported",
            "reporting_boundary": "campus",
            "source_id": "src_syn_plan_ashburn",
            "source_type": "planning-application",
            "source_date": "2025-04-12",
            "extraction_method": "manual",
            "verification_status": "source-linked",
            "confidence": 0.86,
            "value_status": "documented",
            "independent_chain_id": "chain_plan_ashburn",
            "notes": "Cooling narrative references evaporative assist with towers.",
        },
        {
            "field": "annualDirectWaterLiters",
            "value": 180000000.0,
            "unit": "liters/year",
            "evidence_class": "Level B",
            "figure_type": "official-permitted-maximum",
            "reporting_boundary": "campus",
            "source_id": "src_syn_water_ashburn",
            "source_type": "water-permit",
            "source_date": "2026-01-08",
            "extraction_method": "manual",
            "verification_status": "source-linked",
            "confidence": 0.73,
            "value_status": "reported",
            "independent_chain_id": "chain_water_permit_ashburn",
            "notes": "Permit maximum for annual direct water use at full approved operation, not a metered actual.",
        },
        {
            "field": "waterSources",
            "value": "municipal-reclaimed",
            "unit": "percent",
            "evidence_class": "Level B",
            "figure_type": "official-reported",
            "reporting_boundary": "campus",
            "source_id": "src_syn_water_ashburn",
            "source_type": "water-permit",
            "source_date": "2026-01-08",
            "extraction_method": "manual",
            "verification_status": "verified",
            "confidence": 0.94,
            "value_status": "reported",
            "independent_chain_id": "chain_water_permit_ashburn",
            "notes": "Permit allocates reclaimed water as the primary non-potable source.",
        },
    ],
    "fac_syn_dublin": [
        {
            "field": "pue",
            "value": 1.17,
            "unit": "ratio",
            "evidence_class": "Level B",
            "figure_type": "official-reported",
            "reporting_boundary": "campus",
            "source_id": "src_syn_sust_dublin",
            "source_type": "company-sustainability-report",
            "source_date": "2026-03-20",
            "extraction_method": "parsed",
            "verification_status": "source-linked",
            "confidence": 0.82,
            "value_status": "parsed",
            "independent_chain_id": "chain_sust_report_dublin",
            "notes": "Campus-level PUE extracted from the synthetic sustainability appendix.",
        },
        {
            "field": "announcedItLoadMw",
            "value": 72.0,
            "unit": "megawatts",
            "evidence_class": "Level B",
            "figure_type": "official-reported",
            "reporting_boundary": "campus",
            "source_id": "src_syn_utility_dublin",
            "source_type": "utility-filing",
            "source_date": "2025-11-01",
            "extraction_method": "manual",
            "verification_status": "source-linked",
            "confidence": 0.89,
            "value_status": "documented",
            "independent_chain_id": "chain_utility_dublin",
            "notes": "Interconnection filing records the latest operationally allocated load.",
        },
        {
            "field": "annualDirectWaterLiters",
            "value": 42000000.0,
            "unit": "liters/year",
            "evidence_class": "Level D",
            "figure_type": "derived",
            "reporting_boundary": "campus",
            "source_id": "src_syn_sust_dublin",
            "source_type": "company-sustainability-report",
            "source_date": "2026-03-20",
            "extraction_method": "manual",
            "verification_status": "partially-verified",
            "confidence": 0.68,
            "value_status": "derived",
            "independent_chain_id": "chain_sust_report_dublin",
            "notes": "Derived from disclosed campus WUE and reported IT-energy assumptions rather than direct water metering.",
        },
    ],
    "fac_syn_colo_b": [
        {
            "field": "announcedItLoadMw",
            "value": 40.0,
            "unit": "megawatts",
            "evidence_class": "Level B",
            "figure_type": "official-projected",
            "reporting_boundary": "campus",
            "source_id": "src_syn_plan_ashburn",
            "source_type": "planning-application",
            "source_date": "2025-04-12",
            "extraction_method": "manual",
            "verification_status": "identified",
            "confidence": 0.58,
            "value_status": "documented",
            "independent_chain_id": "chain_plan_ashburn",
            "notes": "Synthetic fixture representing a planned capacity disclosure rather than operations.",
        }
    ],
}

FACILITY_CONTRADICTIONS: dict[str, list[dict[str, Any]]] = {
    "fac_syn_ashburn": [
        {
            "field": "annualDirectWaterLiters",
            "value": 95000000.0,
            "unit": "liters/year",
            "evidence_class": "Level C",
            "figure_type": "corroborated-observational",
            "reporting_boundary": "phase-1-building",
            "source_id": "src_syn_plan_ashburn",
            "source_type": "planning-application",
            "source_date": "2025-04-12",
            "extraction_method": "manual",
            "verification_status": "conflicting",
            "confidence": 0.42,
            "value_status": "documented",
            "independent_chain_id": "chain_plan_ashburn",
            "notes": "Earlier planning-stage narrative appears to describe one building rather than the full campus.",
        }
    ]
}

FACILITY_HISTORY = {
    "fac_syn_ashburn": [
        {
            "changed_at": "2026-01-08",
            "field": "waterSources",
            "previous_value": "municipal-potable only",
            "new_value": "70% municipal-reclaimed, 30% municipal-potable",
            "status": "approved",
            "source_id": "src_syn_water_ashburn",
            "summary": "Reclaimed-water permit evidence added to the facility record.",
        }
    ],
    "fac_syn_dublin": [
        {
            "changed_at": "2026-03-20",
            "field": "pue",
            "previous_value": None,
            "new_value": 1.17,
            "status": "approved",
            "source_id": "src_syn_sust_dublin",
            "summary": "Synthetic sustainability report provided campus PUE context.",
        }
    ],
    "fac_syn_colo_b": [
        {
            "changed_at": "2026-06-01",
            "field": "operationalStatus",
            "previous_value": "announced",
            "new_value": "under-construction",
            "status": "approved",
            "source_id": "src_syn_plan_ashburn",
            "summary": "Project status advanced from announcement to construction in the synthetic fixture.",
        }
    ],
}

CANDIDATE_FACTS = [
    {
        "id": "cand_syn_1",
        "entity_type": "facility",
        "entity_id": "fac_syn_ashburn",
        "field": "annualDirectWaterLiters",
        "raw_value": "180 million liters per year",
        "normalized_value": "180000000",
        "unit": "liters/year",
        "source_id": "src_syn_water_ashburn",
        "extraction_method": "parsed",
        "confidence": 0.61,
        "status": "needs-review",
        "review_notes": "Permit language may refer to allocation ceiling rather than measured consumption.",
    },
    {
        "id": "cand_syn_2",
        "entity_type": "facility",
        "entity_id": "fac_syn_dublin",
        "field": "wueLitersPerKwh",
        "raw_value": "1.38",
        "normalized_value": "1.38",
        "unit": "L/kWh",
        "source_id": "src_syn_sust_dublin",
        "extraction_method": "manual",
        "confidence": 0.74,
        "status": "pending",
        "review_notes": None,
    },
]

CORRECTIONS: list[dict[str, Any]] = []
INGESTION_JOBS: list[dict[str, Any]] = []


def _source_with_reliability(source: dict[str, Any]) -> dict[str, Any]:
    decorated = deepcopy(source)
    reliability = SOURCE_RELIABILITY.get(
        source["source_type"],
        {"score": 35, "tier": "Tier 5", "explanation": "Unknown source type requiring manual review."},
    )
    decorated["reliability"] = reliability
    return decorated


def _find_operator_name(operator_id: str | None) -> str:
    for organization in ORGANIZATIONS:
        if organization["id"] == operator_id:
            return str(organization["name"])
    return "Unknown operator"


def _build_source_summary(facility: dict[str, Any]) -> dict[str, Any]:
    source_ids = {item["source_id"] for item in FACILITY_EVIDENCE.get(facility["id"], [])}
    source_records = [_source_with_reliability(source) for source in SOURCES if source["id"] in source_ids]
    if not source_records:
        return {"total_sources": 0, "primary_sources": 0, "independent_chains": 0, "latest_source_date": "unknown"}
    latest = max(item["publication_date"] for item in source_records)
    primary = sum(1 for item in source_records if item["reliability"]["score"] >= 80)
    independent_chains = len({item.get("origin_chain_id") or item["id"] for item in source_records})
    return {
        "total_sources": len(source_records),
        "primary_sources": primary,
        "independent_chains": independent_chains,
        "latest_source_date": latest,
    }


def _select_primary_water_figure(facility_id: str) -> dict[str, Any] | None:
    candidates = [
        item for item in FACILITY_EVIDENCE.get(facility_id, [])
        if item["field"] in {"annualDirectWaterLiters", "directWaterLiters", "waterWithdrawalLiters"}
    ]
    if not candidates:
        return None
    rank = {
        "Level A": 0,
        "Level B": 1,
        "Level C": 2,
        "Level D": 3,
        "Level E": 4,
        "Level F": 5,
        "Level U": 6,
    }
    candidates.sort(key=lambda item: (rank.get(item["evidence_class"], 99), -float(item["confidence"])))
    return candidates[0]


def _quality_label(score: int) -> str:
    if score >= 85:
        return "very-high"
    if score >= 70:
        return "high"
    if score >= 55:
        return "moderate"
    if score >= 35:
        return "low"
    return "very-low"


def _build_data_quality(facility: dict[str, Any]) -> dict[str, Any]:
    score = 20
    reasons: list[str] = []
    if facility.get("latitude") is not None and facility.get("longitude") is not None:
        score += 15
        reasons.append("Facility location is recorded with coordinates.")
    if facility.get("operator_id"):
        score += 10
        reasons.append("Operator relationship is present.")
    if facility.get("announced_it_load_mw") is not None:
        score += 15
        reasons.append("Facility-specific capacity is documented.")
    if facility.get("pue") is not None:
        score += 10
        reasons.append("PUE context is available.")
    if facility.get("cooling_systems"):
        score += 10
        reasons.append("Cooling-system information is available.")
    if FACILITY_EVIDENCE.get(facility["id"]):
        score += 10
        reasons.append("Field-level provenance is attached.")
    summary = _build_source_summary(facility)
    if summary["primary_sources"] >= 2:
        score += 10
        reasons.append("Multiple higher-reliability sources support the record.")
    if facility["operational_status"] == "operational":
        score += 5
        reasons.append("Operational status is current rather than purely planned.")
    if facility["synthetic"]:
        reasons.append("Record is synthetic and not production-eligible.")
        score = min(score, facility["confidence_score"])
    score = min(score, 100)
    return {"score": score, "label": _quality_label(score), "reasons": reasons}


def _facility_summary(facility: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": facility["id"],
        "slug": facility["slug"],
        "name": facility["name"],
        "operator": _find_operator_name(facility.get("operator_id")),
        "facility_type": facility["facility_type"],
        "operational_status": facility["operational_status"],
        "country": facility["country"],
        "state_or_province": facility.get("state_or_province"),
        "municipality": facility.get("municipality"),
        "latitude": facility.get("latitude"),
        "longitude": facility.get("longitude"),
        "estimated_it_load_mw": facility.get("estimated_it_load_mw"),
        "announced_it_load_mw": facility.get("announced_it_load_mw"),
        "cooling_systems": facility.get("cooling_systems", []),
        "electricity_grid_region": facility.get("electricity_grid_region"),
        "verification_status": facility["verification_status"],
        "synthetic": facility["synthetic"],
        "production_eligible": facility["production_eligible"],
        "data_quality": _build_data_quality(facility),
        "coverage": facility["coverage"],
        "source_summary": _build_source_summary(facility),
        "warnings": facility.get("warnings", []),
    }


def list_facilities(filters: dict[str, Any], cursor: str | None = None, limit: int = 20) -> dict[str, Any]:
    query = str(filters.get("query") or "").strip().lower()
    operator = str(filters.get("operator") or "").strip().lower()
    country = str(filters.get("country") or "").strip().lower()
    state = str(filters.get("state") or "").strip().lower()
    facility_type = str(filters.get("facility_type") or "").strip().lower()
    operational_status = str(filters.get("operational_status") or "").strip().lower()

    filtered = []
    for facility in FACILITIES:
        haystack = " ".join(
            [
                facility["name"],
                facility["slug"],
                " ".join(facility.get("aliases", [])),
                _find_operator_name(facility.get("operator_id")),
                str(facility.get("municipality") or ""),
                str(facility.get("state_or_province") or ""),
                str(facility.get("country") or ""),
            ]
        ).lower()
        if query and query not in haystack:
            continue
        if operator and operator not in _find_operator_name(facility.get("operator_id")).lower():
            continue
        if country and country != str(facility.get("country") or "").lower():
            continue
        if state and state != str(facility.get("state_or_province") or "").lower():
            continue
        if facility_type and facility_type != str(facility.get("facility_type") or "").lower():
            continue
        if operational_status and operational_status != str(facility.get("operational_status") or "").lower():
            continue
        filtered.append(facility)

    start = int(cursor or "0")
    page = filtered[start : start + limit]
    next_cursor = str(start + limit) if start + limit < len(filtered) else None
    return {
        "items": [_facility_summary(item) for item in page],
        "next_cursor": next_cursor,
        "total": len(filtered),
    }


def get_facility_by_id(facility_id: str) -> dict[str, Any] | None:
    for facility in FACILITIES:
        if facility["id"] == facility_id:
            return facility
    return None


def get_facility_by_slug(slug: str) -> dict[str, Any] | None:
    for facility in FACILITIES:
        if facility["slug"] == slug:
            return facility
    return None


def get_facility_detail(facility_id: str) -> dict[str, Any]:
    facility = get_facility_by_id(facility_id)
    if facility is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
    return {
        "facility": _facility_summary(facility),
        "aliases": facility.get("aliases", []),
        "owner": _find_operator_name(facility.get("owner_id")),
        "campus_name": facility.get("campus_name"),
        "primary_water_figure": _select_primary_water_figure(facility_id),
        "contradictory_claims": FACILITY_CONTRADICTIONS.get(facility_id, []),
        "water_sources": facility.get("water_sources", []),
        "utility_providers": facility.get("utility_providers", []),
        "reported_data_year": facility.get("reported_data_year"),
        "confidence_score": facility.get("confidence_score", 0),
        "record_status": facility.get("record_status", "published"),
        "verification_notes": facility.get("verification_notes", []),
    }


def get_facility_evidence(facility_id: str) -> dict[str, Any]:
    if get_facility_by_id(facility_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
    return {"facility_id": facility_id, "evidence": FACILITY_EVIDENCE.get(facility_id, [])}


def get_facility_sources(facility_id: str) -> dict[str, Any]:
    if get_facility_by_id(facility_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
    source_ids = {item["source_id"] for item in FACILITY_EVIDENCE.get(facility_id, [])}
    return {
        "facility_id": facility_id,
        "sources": [_source_with_reliability(source) for source in SOURCES if source["id"] in source_ids],
    }


def get_facility_history(facility_id: str) -> dict[str, Any]:
    if get_facility_by_id(facility_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
    return {"facility_id": facility_id, "changes": FACILITY_HISTORY.get(facility_id, [])}


def get_source(source_id: str) -> dict[str, Any]:
    for source in SOURCES:
        if source["id"] == source_id:
            return _source_with_reliability(source)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")


def list_source_connectors() -> dict[str, Any]:
    return {"items": SOURCE_CONNECTORS, "total": len(SOURCE_CONNECTORS)}


def list_organizations() -> dict[str, Any]:
    items = [
        {
            "id": org["id"],
            "name": org["name"],
            "legal_name": org.get("legal_name"),
            "organization_type": org["organization_type"],
            "country": org["country"],
            "website": org.get("website"),
            "facility_ids": org.get("facility_ids", []),
        }
        for org in ORGANIZATIONS
    ]
    return {"items": items, "total": len(items)}


def get_organization(organization_id: str) -> dict[str, Any]:
    for org in ORGANIZATIONS:
        if org["id"] == organization_id:
            return {
                "organization": {
                    "id": org["id"],
                    "name": org["name"],
                    "legal_name": org.get("legal_name"),
                    "organization_type": org["organization_type"],
                    "country": org["country"],
                    "website": org.get("website"),
                    "facility_ids": org.get("facility_ids", []),
                },
                "aliases": org.get("aliases", []),
                "relationships": org.get("relationships", []),
                "warnings": org.get("warnings", []),
            }
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")


def get_organization_facilities(organization_id: str) -> dict[str, Any]:
    organization = get_organization(organization_id)
    facility_ids = set(organization["organization"]["facility_ids"])
    return {
        "items": [_facility_summary(facility) for facility in FACILITIES if facility["id"] in facility_ids],
        "next_cursor": None,
        "total": len(facility_ids),
    }


def get_public_record_templates(facility_id: str) -> dict[str, Any]:
    facility = get_facility_by_id(facility_id)
    if facility is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")

    jurisdiction = f"{facility.get('country', 'unknown')}-{facility.get('state_or_province', 'unknown')}"
    holders = [
        {
            "authority": f"{facility.get('municipality', 'Local')} Water Utility",
            "jurisdiction": jurisdiction,
            "record_types": [
                "monthly aggregate water consumption",
                "water and sewer billing records",
                "meter reading summaries",
            ],
            "rationale": "The local utility is the most likely holder of lawful billing and service-capacity records.",
        },
        {
            "authority": f"{facility.get('municipality', 'Local')} Planning Department",
            "jurisdiction": jurisdiction,
            "record_types": [
                "planning applications",
                "development agreements",
                "water-main upgrade studies",
            ],
            "rationale": "Planning materials often distinguish projected maximum demand from operating demand.",
        },
    ]

    templates = [
        {
            "facility_id": facility_id,
            "authority": holders[0]["authority"],
            "subject": f"Public-record request for aggregate water records for {facility['name']}",
            "summary": "Request only institution-level utility records relevant to facility-scale water use.",
            "requested_records": holders[0]["record_types"],
            "body": (
                f"Please provide non-personal, facility-level records for {facility['name']} located at "
                f"{facility.get('address', 'the identified facility address')}, including monthly aggregate "
                "water consumption, water and sewer billing summaries, and meter-reading summaries for the most "
                "recent complete reporting year. If exact meter exports are exempt, please provide any releasable "
                "aggregate summaries or billing records that show monthly volumes, service account type, and the "
                "covered period."
            ),
            "legal_notes": [
                "Do not request personal customer details or private credentials.",
                "Ask for aggregate, institution-level records only.",
                "Clarify whether provided figures represent withdrawal, billed consumption, or another boundary.",
            ],
        },
        {
            "facility_id": facility_id,
            "authority": holders[1]["authority"],
            "subject": f"Public-record request for planning and infrastructure records for {facility['name']}",
            "summary": "Request planning and utility-capacity materials that can distinguish projected from actual use.",
            "requested_records": holders[1]["record_types"],
            "body": (
                f"Please provide planning, zoning, infrastructure, and development records for {facility['name']} "
                "that discuss water demand, wastewater demand, reclaimed-water service, or utility-capacity studies. "
                "Please include documents that distinguish requested, allocated, permitted, projected, peak, average, "
                "or actual water use."
            ),
            "legal_notes": [
                "A planning projection should not be treated as actual operational use.",
                "Retain the reporting period and facility boundary from each document.",
            ],
        },
    ]

    return {"facility_id": facility_id, "known_holders": holders, "templates": templates}


def _to_cooling_type(cooling_systems: Iterable[str], fallback: CoolingType) -> CoolingType:
    joined = " ".join(cooling_systems).lower()
    if "direct-evaporative" in joined or "cooling-tower" in joined:
        return CoolingType.DIRECT_EVAPORATIVE
    if "air-cooled" in joined or "closed-loop" in joined or "liquid" in joined:
        return CoolingType.CLOSED_LOOP
    if "adiabatic" in joined:
        return CoolingType.ADIABATIC_HYBRID
    return fallback


def _estimate_confidence(facility: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    quality = _build_data_quality(facility)
    score = max(20, quality["score"] - (12 if "PLANNED_CAPACITY_ONLY" in warnings else 0) - (8 if "WUE_ESTIMATED" in warnings else 0))
    if facility["synthetic"]:
        score = min(score, 79)
    reasons = [
        "Estimate uses approved facility-record values where available.",
        "Missing facility-specific measurements widen the uncertainty range.",
    ]
    if "PLANNED_CAPACITY_ONLY" in warnings:
        reasons.append("Capacity is planned rather than measured operational load.")
    if "WUE_ESTIMATED" in warnings:
        reasons.append("WUE is estimated from cooling profile and weather context.")
    return {"score": score, "label": _quality_label(score), "reasons": reasons}


async def estimate_facility(facility_id: str) -> dict[str, Any]:
    facility = get_facility_by_id(facility_id)
    if facility is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")

    provider, region = facility["region_profile_key"]
    region_profile = await get_region(provider, region)
    if region_profile is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Region profile unavailable")
    snapshot = await get_cached_or_baseline_snapshot(region_profile)

    max_capacity = float(facility.get("announced_it_load_mw") or facility.get("estimated_it_load_mw") or region_profile["max_it_capacity_mw"])
    pue = float(facility.get("pue") or region_profile["pue"])
    base_wue = float(facility.get("wue_liters_per_kwh") or region_profile["base_wue"])
    cooling_type = _to_cooling_type(facility.get("cooling_systems", []), region_profile["cooling_type"])
    metrics = estimate_realtime_water_metrics(
        max_capacity,
        pue,
        base_wue,
        cooling_type,
        region_profile.get("water_stress_score"),
        snapshot,
    )

    direct_expected = round(float(metrics["water_lph"]), 1)
    indirect_factor = GRID_WATER_INTENSITY.get(str(facility.get("electricity_grid_region") or region_profile.get("grid_zone_id") or "US-PJM"), 1.0)
    indirect_expected = round(float(metrics["estimated_it_load_mw"]) * 1000.0 * pue * indirect_factor, 1)
    total_expected = round(direct_expected + indirect_expected, 1)

    uncertainty = 0.2 if facility["operational_status"] == "operational" else 0.35
    if facility["synthetic"]:
        uncertainty += 0.05
    direct_low = round(direct_expected * (1.0 - uncertainty), 1)
    direct_high = round(direct_expected * (1.0 + uncertainty), 1)
    indirect_low = round(indirect_expected * (1.0 - uncertainty), 1)
    indirect_high = round(indirect_expected * (1.0 + uncertainty), 1)
    total_low = round(direct_low + indirect_low, 1)
    total_high = round(direct_high + indirect_high, 1)

    warnings = list(dict.fromkeys(facility.get("warnings", [])))
    if facility["operational_status"] != "operational" and "PLANNED_CAPACITY_ONLY" not in warnings:
        warnings.append("PLANNED_CAPACITY_ONLY")

    confidence = _estimate_confidence(facility, warnings)
    data_quality = _build_data_quality(facility)
    evidence = FACILITY_EVIDENCE.get(facility_id, [])
    primary_water_figure = _select_primary_water_figure(facility_id)
    result_classification = classify_water_figure(
        evidence_class="Level E",
        is_projected=facility["operational_status"] != "operational",
    )
    input_selection = [
        {
            "field": "announcedItLoadMw",
            "selected_value": max_capacity,
            "status": "documented" if facility.get("announced_it_load_mw") is not None else "estimated",
            "source_id": evidence[0]["source_id"] if evidence else None,
            "alternatives": [str(facility.get("estimated_it_load_mw"))] if facility.get("estimated_it_load_mw") else [],
        },
        {
            "field": "pue",
            "selected_value": pue,
            "status": "documented" if facility.get("pue") is not None else "estimated",
            "source_id": next((item["source_id"] for item in evidence if item["field"] == "pue"), None),
            "alternatives": [],
        },
        {
            "field": "coolingSystems",
            "selected_value": ", ".join(facility.get("cooling_systems", [])),
            "status": facility["coverage"]["cooling_system"],
            "source_id": next((item["source_id"] for item in evidence if item["field"] == "coolingSystems"), None),
            "alternatives": [],
        },
    ]
    assumptions = [
        {
            "field": "weatherSnapshot",
            "value": snapshot.source,
            "unit": None,
            "status": "cached" if "baseline" not in snapshot.source else "estimated",
            "reason": "Facility estimates reuse the Phase 2 telemetry snapshot for regional weather and carbon context.",
            "source_id": None,
        },
        {
            "field": "gridWaterIntensity",
            "value": indirect_factor,
            "unit": "L/kWh",
            "status": "documented",
            "reason": "Indirect water uses the regional grid-water-intensity dataset for the facility grid region.",
            "source_id": None,
        },
    ]
    methodology = (
        "Facility estimation selects the strongest approved facility-record values, preserves source-linked fields, "
        "fills remaining gaps with the Phase 2 thermodynamic model, and widens uncertainty when the record is planned, synthetic, or missing measured water data. "
        "Official, derived, corroborated, and modeled figures remain distinct rather than being collapsed into one undifferentiated number."
    )
    return {
        "facility_record": _facility_summary(facility),
        "primary_water_figure": primary_water_figure,
        "input_selection": input_selection,
        "source_evidence": evidence,
        "direct_water": {
            "low_liters_per_hour": direct_low,
            "expected_liters_per_hour": direct_expected,
            "high_liters_per_hour": direct_high,
        },
        "indirect_water": {
            "low_liters_per_hour": indirect_low,
            "expected_liters_per_hour": indirect_expected,
            "high_liters_per_hour": indirect_high,
        },
        "total_water": {
            "low_liters_per_hour": total_low,
            "expected_liters_per_hour": total_expected,
            "high_liters_per_hour": total_high,
        },
        "projections": {
            "daily_liters": round(total_expected * 24.0, 1),
            "monthly_liters": round(total_expected * 24.0 * 30.0, 1),
            "annual_liters": round(total_expected * 24.0 * 365.0, 1),
        },
        "confidence": confidence,
        "data_quality": data_quality,
        "assumptions": assumptions,
        "warnings": warnings,
        "result_classification": result_classification,
        "methodology": methodology,
        "model_versions": {
            "application_version": settings.app_version,
            "model_version": "2.0.0",
            "facility_profile_version": "1.1.2",
            "dataset_versions": DATASET_VERSIONS,
        },
    }


async def estimate_facility_batch(facility_ids: list[str]) -> dict[str, Any]:
    results = []
    model_versions: dict[str, Any] | None = None
    for facility_id in facility_ids:
        try:
            estimate = await estimate_facility(facility_id)
            model_versions = estimate["model_versions"]
            results.append({"facility_id": facility_id, "status": "ok", "estimate": estimate, "error": None})
        except HTTPException as exc:
            results.append({"facility_id": facility_id, "status": "error", "estimate": None, "error": str(exc.detail)})
    return {"results": results, "model_versions": model_versions or {
        "application_version": settings.app_version,
        "model_version": "2.0.0",
        "facility_profile_version": "1.1.2",
        "dataset_versions": DATASET_VERSIONS,
    }}


async def compare_facilities(facility_ids: list[str]) -> dict[str, Any]:
    rows = []
    for facility_id in facility_ids:
        facility = get_facility_by_id(facility_id)
        if facility is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Facility not found: {facility_id}")
        estimate = await estimate_facility(facility_id)
        tier, _ = classify_water_stress((await get_region(*facility["region_profile_key"])).get("water_stress_score"))  # type: ignore[union-attr]
        rows.append(
            {
                "facility_id": facility_id,
                "facility_name": facility["name"],
                "direct_water_lph": estimate["direct_water"]["expected_liters_per_hour"],
                "indirect_water_lph": estimate["indirect_water"]["expected_liters_per_hour"],
                "total_water_lph": estimate["total_water"]["expected_liters_per_hour"],
                "data_quality_score": estimate["data_quality"]["score"],
                "estimate_confidence_score": estimate["confidence"]["score"],
                "cooling_systems": facility["cooling_systems"],
                "water_stress_category": tier,
            }
        )
    rows.sort(key=lambda item: (item["total_water_lph"], -item["estimate_confidence_score"]))
    explanation = (
        f"{rows[0]['facility_name']} currently ranks best because it combines the lowest expected hourly water footprint "
        f"with stronger estimate confidence than the noisier alternatives."
    )
    return {"rankings": rows, "explanation": explanation}


async def export_facilities(facility_ids: list[str]) -> dict[str, Any]:
    items = []
    for facility_id in facility_ids:
        items.append(
            {
                "facility": get_facility_detail(facility_id),
                "estimate": await estimate_facility(facility_id),
                "warnings": get_facility_by_id(facility_id).get("warnings", []) if get_facility_by_id(facility_id) else [],
                "retrieved_at": datetime.now(UTC),
            }
        )
    return {"items": items}


def create_correction(payload: dict[str, Any]) -> dict[str, Any]:
    if get_facility_by_id(payload["facility_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
    correction = {
        "correction_id": f"cor_{uuid.uuid4().hex[:12]}",
        "status": "pending-review",
        "message": "Correction received and queued for review.",
        **payload,
    }
    CORRECTIONS.append(correction)
    return {
        "correction_id": correction["correction_id"],
        "status": correction["status"],
        "message": correction["message"],
    }


def list_review_items() -> dict[str, Any]:
    items = list(CANDIDATE_FACTS)
    for correction in CORRECTIONS:
        items.append(
            {
                "id": correction["correction_id"],
                "entity_type": "facility-correction",
                "entity_id": correction["facility_id"],
                "field": correction["field"],
                "raw_value": correction["proposed_value"],
                "normalized_value": correction["proposed_value"],
                "unit": None,
                "source_id": "user-submitted-source",
                "extraction_method": "user-submitted",
                "confidence": 0.2,
                "status": correction["status"],
                "review_notes": correction.get("notes"),
            }
        )
    return {"items": items, "total": len(items)}


def get_review_item(candidate_id: str) -> dict[str, Any]:
    for item in list_review_items()["items"]:
        if item["id"] == candidate_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found")


def decide_review_item(candidate_id: str, approved: bool) -> dict[str, Any]:
    status_value = "accepted" if approved else "rejected"
    for item in CANDIDATE_FACTS:
        if item["id"] == candidate_id:
            item["status"] = status_value
            return {
                "candidate_id": candidate_id,
                "status": status_value,
                "message": f"Candidate fact {status_value}.",
            }
    for correction in CORRECTIONS:
        if correction["correction_id"] == candidate_id:
            correction["status"] = status_value
            return {
                "candidate_id": candidate_id,
                "status": status_value,
                "message": f"Correction {status_value}.",
            }
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found")


def _validate_safe_url(source_url: str) -> None:
    parsed = urlparse(source_url)
    if parsed.scheme != "https":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only https source URLs are allowed.")
    hostname = parsed.hostname or ""
    if hostname in {"localhost", "127.0.0.1"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Private or local source URLs are not allowed.")
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None
    if ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Private or local source URLs are not allowed.")


def create_ingestion_job(payload: dict[str, Any]) -> dict[str, Any]:
    _validate_safe_url(payload["source_url"])
    duplicate = any(source["url"] == payload["source_url"] for source in SOURCES)
    job = {
        "job_id": f"job_{uuid.uuid4().hex[:12]}",
        "status": "completed" if payload.get("dry_run", True) else "queued",
        "source_url": payload["source_url"],
        "source_type": payload["source_type"],
        "dry_run": payload.get("dry_run", True),
        "summary": "Dry-run ingestion validated the source metadata without fetching external content."
        if payload.get("dry_run", True)
        else "Source ingestion job accepted and queued for later processing.",
        "sources_processed": 0 if duplicate else 1,
        "candidate_facts_created": 0,
        "errors": ["SOURCE_ALREADY_REGISTERED"] if duplicate else [],
    }
    INGESTION_JOBS.append(job)
    return job


def get_ingestion_job(job_id: str) -> dict[str, Any]:
    for job in INGESTION_JOBS:
        if job["job_id"] == job_id:
            return job
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found")


def cancel_ingestion_job(job_id: str) -> dict[str, Any]:
    job = get_ingestion_job(job_id)
    if job["status"] in {"completed", "failed", "cancelled"}:
        return job
    job["status"] = "cancelled"
    job["summary"] = "Ingestion job cancelled before processing."
    return job
