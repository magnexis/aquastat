import csv
import io

from app.core.config import settings
from app.repository import get_region, list_regions
from app.services.phase2_model import estimate_realtime_water_metrics, project_route_metrics
from app.services.telemetry import get_cached_or_baseline_snapshot


OLYMPIC_POOL_LITERS = 2_500_000.0

SERVICE_MULTIPLIERS = {
    "ec2": 0.0005,
    "lambda": 0.0000002,
    "fargate": 0.00045,
    "ecs": 0.00045,
    "eks": 0.00055,
    "compute engine": 0.0005,
    "cloud run": 0.00018,
    "cloud functions": 0.0000002,
    "virtual machines": 0.0005,
    "app service": 0.00035,
    "container instances": 0.0003,
    "kubernetes service": 0.00055,
}

REGION_ALIASES = {
    "us east (n. virginia)": "aws:us-east-1",
    "eu (ireland)": "aws:eu-west-1",
    "europe-west1": "aws:eu-west-1",
    "europe-west2": "aws:eu-west-1",
    "frankfurt": "aws:eu-central-1",
    "europe-west3": "aws:eu-central-1",
    "singapore": "gcp:asia-southeast1",
    "asia-southeast1": "gcp:asia-southeast1",
    "oregon": "azure:us-west-2",
    "us-west-2": "azure:us-west-2",
    "west us 2": "azure:us-west-2",
}


def detect_provider(headers: list[str], text: str) -> str:
    joined = " ".join(headers).lower() + " " + text.lower()
    if "aws" in joined or "lineitem" in joined:
        return "AWS"
    if "gcp" in joined or "sku" in joined or "project.id" in joined:
        return "GCP"
    if "azure" in joined or "metercategory" in joined:
        return "Azure"
    return "Unknown"


def _get_usage_quantity(row: dict[str, str]) -> float:
    for key in (
        "UsageQuantity",
        "lineItem/UsageAmount",
        "usage amount",
        "Quantity",
        "quantity",
        "CostInBillingCurrency",
        "ConsumedQuantity",
    ):
        value = row.get(key)
        if value:
            try:
                return abs(float(value))
            except ValueError:
                continue
    return 0.0


def _get_service_name(row: dict[str, str]) -> str:
    for key in (
        "ProductName",
        "lineItem/ProductCode",
        "Service description",
        "MeterCategory",
        "service",
        "sku.description",
    ):
        value = row.get(key)
        if value:
            return value
    return "Unknown"


def _get_region_hint(row: dict[str, str]) -> str:
    for key in (
        "product/region",
        "lineItem/AvailabilityZone",
        "region",
        "Region",
        "ResourceLocation",
        "location",
    ):
        value = row.get(key)
        if value:
            return value
    return ""


def estimate_mwh_for_row(service_name: str, usage_quantity: float) -> float:
    service_lower = service_name.lower()
    for token, multiplier in SERVICE_MULTIPLIERS.items():
        if token in service_lower:
            return usage_quantity * multiplier
    return usage_quantity * 0.0002


def normalize_region_key(region_hint: str) -> str:
    hint = region_hint.strip().lower()
    if hint in REGION_ALIASES:
        return REGION_ALIASES[hint]
    if hint.startswith("us-east-1"):
        return "aws:us-east-1"
    if hint.startswith("eu-west-1"):
        return "aws:eu-west-1"
    if hint.startswith("eu-central-1"):
        return "aws:eu-central-1"
    if hint.startswith("asia-southeast1"):
        return "gcp:asia-southeast1"
    if hint.startswith("us-west-2"):
        return "azure:us-west-2"
    return "aws:us-east-1"


async def rank_greenest_region() -> tuple[str, float]:
    best_region = "aws:eu-west-1"
    best_tgi = float("inf")
    for datacenter in await list_regions():
        snapshot = await get_cached_or_baseline_snapshot(datacenter)
        metrics = estimate_realtime_water_metrics(
            datacenter["max_it_capacity_mw"],
            datacenter["pue"],
            datacenter["base_wue"],
            datacenter["cooling_type"],
            datacenter.get("water_stress_score"),
            snapshot,
        )
        if float(metrics["true_green_index"]) < best_tgi:
            best_tgi = float(metrics["true_green_index"])
            best_region = f"{datacenter['provider'].lower()}:{datacenter['region_slug'].lower()}"
    return best_region, best_tgi


async def estimate_monthly_footprint(csv_bytes: bytes) -> dict:
    text = csv_bytes.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV file is empty or missing headers")

    provider = detect_provider(reader.fieldnames or [], text)
    recommended_region, recommended_tgi = await rank_greenest_region()

    breakdown: list[dict] = []
    total_mwh = 0.0
    total_water_liters = 0.0

    for row in rows[:5000]:
        service_name = _get_service_name(row)
        usage_quantity = _get_usage_quantity(row)
        if usage_quantity <= 0:
            continue
        estimated_mwh = estimate_mwh_for_row(service_name, usage_quantity)
        region_key = normalize_region_key(_get_region_hint(row))
        provider_key, _, region_slug = region_key.partition(":")
        datacenter = await get_region(provider_key, region_slug)
        if datacenter is None:
            continue
        snapshot = await get_cached_or_baseline_snapshot(datacenter)
        route_metrics = project_route_metrics(
            estimated_mwh,
            max(estimated_mwh, 1.0),
            datacenter["base_wue"],
            datacenter["cooling_type"],
            datacenter.get("water_stress_score"),
            snapshot,
        )
        water_liters = float(route_metrics["projected_water_liters"])
        total_mwh += estimated_mwh
        total_water_liters += water_liters
        if len(breakdown) < 50:
            breakdown.append(
                {
                    "line_item": service_name,
                    "region": region_key,
                    "estimated_mwh": round(estimated_mwh, 4),
                    "estimated_water_liters": round(water_liters, 1),
                }
            )

    return {
        "summary": {
            "provider_detected": provider,
            "estimated_compute_mwh": round(total_mwh, 3),
            "estimated_water_liters": round(total_water_liters, 1),
            "estimated_water_gallons": round(total_water_liters * settings.gallons_per_liter, 1),
            "olympic_pools": round(total_water_liters / OLYMPIC_POOL_LITERS, 4),
            "recommended_region": recommended_region,
            "true_green_index": round(recommended_tgi, 3),
        },
        "breakdown": breakdown,
    }
