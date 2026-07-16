from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_BASE_URL = "https://aquastat-api.onrender.com"


class CliError(Exception):
    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class CliContext:
    base_url: str
    api_key: str | None
    json_mode: bool

    def headers(self) -> dict[str, str]:
        headers = {"User-Agent": "aquastat-cli/1.1.0"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aquastat",
        description="AquaStat command-line interface for water-aware infrastructure analysis.",
    )
    parser.add_argument("--base-url", default=os.getenv("AQUASTAT_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=os.getenv("AQUASTAT_API_KEY"))
    parser.add_argument("--json", action="store_true", help="Output raw JSON.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show service status and documentation endpoints.")
    subparsers.add_parser("info", help="Show public API metadata.")
    subparsers.add_parser("regions", help="List supported regions.")

    estimate = subparsers.add_parser("estimate", help="Estimate water impact for a provider region.")
    estimate.add_argument("--provider", required=True)
    estimate.add_argument("--region", required=True)
    estimate.add_argument("--load-mw", type=float)

    facilities = subparsers.add_parser("facilities", help="List facility intelligence records.")
    facilities.add_argument("--query")
    facilities.add_argument("--operator")
    facilities.add_argument("--country")
    facilities.add_argument("--limit", type=int, default=10)

    facility = subparsers.add_parser("facility", help="Inspect a single facility record.")
    facility.add_argument("facility_id")

    route = subparsers.add_parser("route-workload", help="Compare candidate regions for a workload.")
    route.add_argument("--job-duration-hours", required=True, type=float)
    route.add_argument("--compute-demand-mwh", required=True, type=float)
    route.add_argument("--candidate-region", dest="candidate_regions", action="append", required=True)

    return parser


def render_title(title: str, subtitle: str | None = None) -> str:
    lines = [f"AquaStat :: {title}"]
    if subtitle:
        lines.append(subtitle)
    lines.append("-" * max(len(lines[0]), 28))
    return "\n".join(lines)


def format_table(rows: list[tuple[str, str]]) -> str:
    width = max(len(label) for label, _ in rows) if rows else 0
    return "\n".join(f"{label.ljust(width)}  {value}" for label, value in rows)


def dump_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=False)


def request_json(ctx: CliContext, method: str, path: str, *, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None) -> Any:
    url = f"{ctx.base_url.rstrip('/')}{path}"
    try:
        with httpx.Client(timeout=15.0, headers=ctx.headers()) as client:
            response = client.request(method, url, params=params, json=json_body)
    except httpx.HTTPError as exc:
        raise CliError(f"Request failed: {exc}", exit_code=2) from exc

    if response.status_code >= 400:
        try:
            payload = response.json()
            error = payload.get("error", {})
            message = error.get("message") or response.text
            code = error.get("code") or f"HTTP_{response.status_code}"
        except ValueError:
            message = response.text
            code = f"HTTP_{response.status_code}"
        raise CliError(f"{code}: {message}", exit_code=4 if response.status_code == 402 else 3)

    try:
        return response.json()
    except ValueError as exc:
        raise CliError("Server returned a non-JSON response.", exit_code=2) from exc


def handle_status(ctx: CliContext) -> str:
    payload = request_json(ctx, "GET", "/api/v1/status")
    if ctx.json_mode:
        return dump_json(payload)
    return "\n".join(
        [
            render_title("Status", "Current AquaStat service metadata"),
            format_table(
                [
                    ("Service", payload.get("name", "AquaStat API")),
                    ("Version", payload.get("version", "unknown")),
                    ("Docs", payload.get("documentation", "/docs")),
                    ("OpenAPI", payload.get("openapi", "/openapi.json")),
                    ("Health", payload.get("health", "/health")),
                ]
            ),
        ]
    )


def handle_info(ctx: CliContext) -> str:
    payload = request_json(ctx, "GET", "/api/v1/info")
    if ctx.json_mode:
        return dump_json(payload)
    return "\n".join(
        [
            render_title("Info", payload.get("description", "Public AquaStat metadata")),
            format_table(
                [
                    ("Name", payload.get("name", "AquaStat API")),
                    ("Version", payload.get("version", "unknown")),
                    ("Docs", payload.get("documentation", "/docs")),
                    ("OpenAPI", payload.get("openapi", "/openapi.json")),
                    ("Health", payload.get("health", "/health")),
                ]
            ),
        ]
    )


def handle_regions(ctx: CliContext) -> str:
    payload = request_json(ctx, "GET", "/api/v1/regions")
    if ctx.json_mode:
        return dump_json(payload)
    lines = [render_title("Regions", f"{len(payload)} supported data-center regions")]
    for item in payload:
        lines.append(f"- {item['provider']} :: {item['region_slug']} :: {item['name']}")
    return "\n".join(lines)


def handle_estimate(ctx: CliContext, args: argparse.Namespace) -> str:
    payload = request_json(
        ctx,
        "GET",
        "/api/v1/estimate",
        params={"provider": args.provider, "region": args.region, "load_mw": args.load_mw},
    )
    if ctx.json_mode:
        return dump_json(payload)
    metrics = payload["water_metrics"]
    weather = payload["weather_snapshot"]
    datacenter = payload["datacenter"]
    return "\n".join(
        [
            render_title("Estimate", f"{datacenter['provider']} :: {datacenter['region_slug']}"),
            format_table(
                [
                    ("Cooling", datacenter["cooling_type"]),
                    ("Wet bulb", f"{weather['calculated_wet_bulb_temp_c']} C"),
                    ("Humidity", f"{weather['relative_humidity_pct']} %"),
                    ("IT load", f"{metrics['estimated_it_load_mw']} MW"),
                    ("Instant WUE", str(metrics["calculated_instant_wue"])),
                    ("Water / hour", f"{metrics['water_consumption_liters_per_hour']} L"),
                    ("Gallons / hour", f"{metrics['water_consumption_gallons_per_hour']} gal"),
                    ("Homes / day", str(metrics["equivalent_household_daily_water_usage"])),
                ]
            ),
        ]
    )


def handle_facilities(ctx: CliContext, args: argparse.Namespace) -> str:
    payload = request_json(
        ctx,
        "GET",
        "/api/v1/facilities",
        params={
            "query": args.query,
            "operator": args.operator,
            "country": args.country,
            "limit": args.limit,
        },
    )
    if ctx.json_mode:
        return dump_json(payload)
    items = payload.get("items", [])
    lines = [render_title("Facilities", f"{payload.get('total', len(items))} records available")]
    for item in items:
        lines.append(
            f"- {item['name']} :: {item['operator']} :: {item['country']} :: quality {item['data_quality']['score']}"
        )
    return "\n".join(lines)


def handle_facility(ctx: CliContext, args: argparse.Namespace) -> str:
    payload = request_json(ctx, "GET", f"/api/v1/facilities/{args.facility_id}")
    if ctx.json_mode:
        return dump_json(payload)
    facility = payload["facility"]
    primary = payload.get("primary_water_figure")
    return "\n".join(
        [
            render_title("Facility", facility["name"]),
            format_table(
                [
                    ("Operator", facility["operator"]),
                    ("Type", facility["facility_type"]),
                    ("Status", facility["operational_status"]),
                    ("Country", facility["country"]),
                    ("Grid", facility.get("electricity_grid_region") or "unknown"),
                    ("Cooling", ", ".join(facility["cooling_systems"])),
                    ("Data quality", f"{facility['data_quality']['score']} ({facility['data_quality']['label']})"),
                    ("Primary figure", primary["field"] if primary else "none"),
                    ("Primary value", formatValue_cli(primary["value"], primary.get("unit")) if primary else "n/a"),
                    ("Contradictions", str(len(payload.get("contradictory_claims", [])))),
                ]
            ),
        ]
    )


def handle_route(ctx: CliContext, args: argparse.Namespace) -> str:
    payload = request_json(
        ctx,
        "POST",
        "/api/v1/route-workload",
        json_body={
            "job_duration_hours": args.job_duration_hours,
            "compute_demand_mwh": args.compute_demand_mwh,
            "candidate_regions": args.candidate_regions,
        },
    )
    if ctx.json_mode:
        return dump_json(payload)
    lines = [
        render_title("Route Workload", f"Optimal region: {payload['optimal_region']}"),
        payload["explanation"],
        "",
        "Routing matrix:",
    ]
    for row in payload["routing_matrix"]:
        lines.append(
            f"- {row['region']} :: water {row['projected_water_liters']} L :: carbon {row['projected_carbon_g']} g :: score {row['water_stress_adjusted_impact_score']}"
        )
    return "\n".join(lines)


def formatValue_cli(value: Any, unit: str | None) -> str:
    if value is None:
        return "unknown"
    return f"{value}{f' {unit}' if unit else ''}"


def dispatch(ctx: CliContext, args: argparse.Namespace) -> str:
    if args.command == "status":
        return handle_status(ctx)
    if args.command == "info":
        return handle_info(ctx)
    if args.command == "regions":
        return handle_regions(ctx)
    if args.command == "estimate":
        return handle_estimate(ctx, args)
    if args.command == "facilities":
        return handle_facilities(ctx, args)
    if args.command == "facility":
        return handle_facility(ctx, args)
    if args.command == "route-workload":
        return handle_route(ctx, args)
    raise CliError(f"Unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ctx = CliContext(base_url=args.base_url, api_key=args.api_key, json_mode=args.json)
    try:
        output = dispatch(ctx, args)
    except CliError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exc.exit_code
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
