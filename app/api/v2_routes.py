from datetime import UTC, datetime

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.repository import get_region, list_regions
from app.schemas import (
    BenchmarkEntry,
    BenchmarkResponse,
    EstimateDataCenter,
    EstimateResponse,
    FootprintResponse,
    GeoJsonFeature,
    RouteWorkloadRequest,
    RouteWorkloadResponse,
    RoutingMatrixEntry,
    StressMapProperties,
    StressMapResponse,
    WaterMetrics,
    WeatherSnapshot,
)
from app.services.footprint import estimate_monthly_footprint
from app.services.phase2_model import estimate_realtime_water_metrics, project_route_metrics
from app.services.risk import classify_water_stress
from app.services.telemetry import get_cached_or_baseline_snapshot
from app.services.thermodynamics import (
    calculate_dynamic_wue,
    calculate_water_consumption_lph,
    calculate_wet_bulb_temperature_c,
)


router = APIRouter()


@router.get("/estimate", response_model=EstimateResponse)
async def get_estimate_v2(
    provider: str = Query(..., min_length=1),
    region: str = Query(..., min_length=1),
    load_mw: float | None = Query(default=None, gt=0),
) -> EstimateResponse:
    datacenter = await get_region(provider, region)
    if datacenter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data center region profile not supported.")

    snapshot = await get_cached_or_baseline_snapshot(datacenter)
    active_load = load_mw if load_mw is not None else datacenter["max_it_capacity_mw"] * 0.5
    wet_bulb = calculate_wet_bulb_temperature_c(snapshot.dry_bulb_temp_c, snapshot.relative_humidity_pct)
    wue = calculate_dynamic_wue(datacenter["base_wue"], wet_bulb, datacenter["cooling_type"])
    liters_per_hour = calculate_water_consumption_lph(active_load, wue)
    gallons_per_hour = liters_per_hour * settings.gallons_per_liter
    households = gallons_per_hour / (settings.baseline_household_gallons_per_day / 24.0)

    return EstimateResponse(
        datacenter=EstimateDataCenter(
            id=datacenter["id"],
            provider=datacenter["provider"],
            region_slug=datacenter["region_slug"],
            cooling_type=datacenter["cooling_type"],
        ),
        timestamp=datetime.fromisoformat(snapshot.timestamp.replace("Z", "+00:00")),
        weather_snapshot=WeatherSnapshot(
            dry_bulb_temp_c=round(snapshot.dry_bulb_temp_c, 1),
            relative_humidity_pct=round(snapshot.relative_humidity_pct, 1),
            calculated_wet_bulb_temp_c=round(wet_bulb, 1),
            source=snapshot.source,
            quality="modeled" if "baseline" in snapshot.source else "cached",
        ),
        water_metrics=WaterMetrics(
            estimated_it_load_mw=round(active_load, 1),
            calculated_instant_wue=round(wue, 2),
            water_consumption_liters_per_hour=round(liters_per_hour, 1),
            water_consumption_gallons_per_hour=round(gallons_per_hour, 1),
            equivalent_household_daily_water_usage=round(households, 1),
        ),
    )


@router.get("/stress-map", response_model=StressMapResponse)
async def get_stress_map() -> StressMapResponse:
    features: list[GeoJsonFeature] = []
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
        tier, _ = classify_water_stress(datacenter.get("water_stress_score"))
        features.append(
            GeoJsonFeature(
                geometry={
                    "type": "Point",
                    "coordinates": [datacenter["longitude"], datacenter["latitude"]],
                },
                properties=StressMapProperties(
                    provider=datacenter["provider"],
                    region_slug=datacenter["region_slug"],
                    weighted_impact_score=round(float(metrics["weighted_impact"]), 1),
                    true_green_index=round(float(metrics["true_green_index"]), 3),
                    water_stress_score=round(float(datacenter.get("water_stress_score") or 1.0), 2),
                    water_stress_tier=tier,
                    current_carbon_intensity_g_per_kwh=round(snapshot.carbon_intensity_g_per_kwh, 1),
                    estimated_it_load_mw=round(float(metrics["estimated_it_load_mw"]), 2),
                ),
            )
        )

    return StressMapResponse(features=features)


@router.post("/route-workload", response_model=RouteWorkloadResponse)
async def route_workload(request: Request, payload: RouteWorkloadRequest) -> RouteWorkloadResponse:
    routing_rows: list[tuple[str, dict, dict]] = []
    for region_key in payload.candidate_regions:
        provider, _, region_slug = region_key.partition(":")
        datacenter = await get_region(provider, region_slug)
        if datacenter is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Region not found: {region_key}")

        snapshot = await get_cached_or_baseline_snapshot(datacenter)
        metrics = project_route_metrics(
            payload.compute_demand_mwh,
            payload.job_duration_hours,
            datacenter["base_wue"],
            datacenter["cooling_type"],
            datacenter.get("water_stress_score"),
            snapshot,
        )
        routing_rows.append((region_key.lower(), datacenter, {"snapshot": snapshot, "metrics": metrics}))

    ordered = sorted(
        routing_rows,
        key=lambda item: (
            float(item[2]["metrics"]["water_stress_adjusted_impact_score"]),
            float(item[2]["metrics"]["projected_carbon_g"]),
        ),
    )
    optimal_region, _, optimal_bundle = ordered[0]
    optimal_metrics = optimal_bundle["metrics"]
    optimal_snapshot = optimal_bundle["snapshot"]

    matrix = [
        RoutingMatrixEntry(
            region=region_key,
            projected_water_liters=round(float(bundle["metrics"]["projected_water_liters"]), 1),
            projected_carbon_g=round(float(bundle["metrics"]["projected_carbon_g"]), 1),
            water_stress_adjusted_impact_score=round(
                float(bundle["metrics"]["water_stress_adjusted_impact_score"]),
                1,
            ),
        )
        for region_key, _, bundle in ordered
    ]

    comparison_bits: list[str] = []
    if len(ordered) > 1:
        runner_up = ordered[1]
        runner_metrics = runner_up[2]["metrics"]
        runner_snapshot = runner_up[2]["snapshot"]
        water_delta = 100.0 * (
            1.0
            - float(optimal_metrics["projected_water_liters"]) / float(runner_metrics["projected_water_liters"])
        )
        comparison_bits.append(
            f"{optimal_region} currently benefits from lower ambient wet-bulb temperatures "
            f"({float(optimal_metrics['wet_bulb_temp_c']):.1f}C vs {float(runner_metrics['wet_bulb_temp_c']):.1f}C)"
        )
        comparison_bits.append(f"yielding a {max(water_delta, 0.0):.0f}% reduction in local water evaporation")
        comparison_bits.append(
            f"grid carbon intensity is {optimal_snapshot.carbon_intensity_g_per_kwh:.0f} g/kWh "
            f"vs {runner_snapshot.carbon_intensity_g_per_kwh:.0f} g/kWh"
        )

    explanation = ". ".join(comparison_bits) if comparison_bits else (
        f"{optimal_region} has the lowest combined water-stress-adjusted impact and carbon output right now"
    )

    return RouteWorkloadResponse(
        optimal_region=optimal_region,
        explanation=explanation,
        routing_matrix=matrix,
    )


@router.get("/benchmark", response_model=BenchmarkResponse)
async def get_benchmark() -> BenchmarkResponse:
    rankings: list[BenchmarkEntry] = []
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
        rankings.append(
            BenchmarkEntry(
                region=f"{datacenter['provider'].lower()}:{datacenter['region_slug'].lower()}",
                provider=datacenter["provider"],
                pue=round(float(datacenter["pue"]), 2),
                instant_wue=round(float(metrics["instant_wue"]), 3),
                stress_adjusted_wue=round(float(metrics["stress_adjusted_wue"]), 3),
                true_green_index=round(float(metrics["true_green_index"]), 3),
                carbon_intensity_g_per_kwh=round(snapshot.carbon_intensity_g_per_kwh, 1),
                weighted_impact_score=round(float(metrics["weighted_impact"]), 1),
                water_stress_tier=str(metrics["water_stress_tier"]),
            )
        )

    rankings.sort(key=lambda item: (item.true_green_index, item.weighted_impact_score, item.carbon_intensity_g_per_kwh))
    return BenchmarkResponse(generated_at=datetime.now(UTC), rankings=rankings)


@router.post("/footprint", response_model=FootprintResponse)
async def upload_footprint_csv(file: UploadFile = File(...)) -> FootprintResponse:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV uploads are supported")
    try:
        payload = await estimate_monthly_footprint(await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FootprintResponse.model_validate(payload)


@router.get("/footprint-calculator", response_class=HTMLResponse)
async def footprint_calculator_ui() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AquaStat Water-Score Calculator</title>
  <style>
    :root {
      --bg: linear-gradient(135deg, #e4f7f4 0%, #f5efe2 100%);
      --ink: #15343a;
      --panel: rgba(255,255,255,0.82);
      --accent: #0f766e;
      --accent-2: #c97b2f;
      --border: rgba(21,52,58,0.12);
    }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background: var(--bg);
      min-height: 100vh;
    }
    .wrap {
      max-width: 920px;
      margin: 0 auto;
      padding: 48px 20px 72px;
    }
    .hero {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 32px;
      box-shadow: 0 18px 60px rgba(21,52,58,0.08);
      backdrop-filter: blur(10px);
    }
    h1 { margin: 0 0 12px; font-size: clamp(2.2rem, 6vw, 4.6rem); line-height: 0.96; }
    p { font-size: 1.05rem; line-height: 1.6; }
    .upload {
      display: grid;
      gap: 14px;
      margin-top: 28px;
    }
    input, button {
      font: inherit;
    }
    input[type=file] {
      padding: 14px;
      border: 1px dashed var(--border);
      border-radius: 14px;
      background: rgba(255,255,255,0.75);
    }
    button {
      width: fit-content;
      padding: 14px 20px;
      border: 0;
      border-radius: 999px;
      background: var(--accent);
      color: white;
      cursor: pointer;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 28px;
    }
    .card, .table-wrap {
      background: rgba(255,255,255,0.78);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
    }
    .label {
      font-size: 0.85rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: rgba(21,52,58,0.7);
    }
    .value {
      margin-top: 8px;
      font-size: 1.8rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }
    th, td {
      text-align: left;
      padding: 10px 6px;
      border-bottom: 1px solid rgba(21,52,58,0.1);
    }
    #status { margin-top: 14px; color: var(--accent-2); }
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>Measure Your Water-Score</h1>
      <p>Upload an AWS, GCP, or Azure monthly billing CSV and AquaStat will estimate your compute-linked water footprint, translate it into Olympic swimming pools, and point you toward a cleaner region.</p>
      <form class="upload" id="upload-form">
        <input id="csv-file" type="file" accept=".csv" required>
        <button type="submit">Estimate Footprint</button>
      </form>
      <div id="status"></div>
      <div class="cards" id="summary"></div>
      <div class="table-wrap" id="breakdown-wrap" hidden>
        <table>
          <thead>
            <tr><th>Line Item</th><th>Region</th><th>MWh</th><th>Water Liters</th></tr>
          </thead>
          <tbody id="breakdown"></tbody>
        </table>
      </div>
    </section>
  </main>
  <script>
    const form = document.getElementById("upload-form");
    const fileInput = document.getElementById("csv-file");
    const statusEl = document.getElementById("status");
    const summaryEl = document.getElementById("summary");
    const breakdownWrap = document.getElementById("breakdown-wrap");
    const breakdownEl = document.getElementById("breakdown");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const file = fileInput.files[0];
      if (!file) return;
      statusEl.textContent = "Crunching billing data into water and carbon signals...";
      summaryEl.innerHTML = "";
      breakdownEl.innerHTML = "";
      breakdownWrap.hidden = true;

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/v2/footprint", { method: "POST", body: formData });
      const payload = await response.json();
      if (!response.ok) {
        statusEl.textContent = payload.detail || "Upload failed";
        return;
      }

      statusEl.textContent = "Estimate ready.";
      const summary = payload.summary;
      const cards = [
        ["Provider", summary.provider_detected],
        ["Compute MWh", summary.estimated_compute_mwh],
        ["Water Liters", summary.estimated_water_liters],
        ["Olympic Pools", summary.olympic_pools],
        ["Best Region", summary.recommended_region],
        ["Best TGI", summary.true_green_index],
      ];
      summaryEl.innerHTML = cards.map(([label, value]) =>
        `<article class="card"><div class="label">${label}</div><div class="value">${value}</div></article>`
      ).join("");

      breakdownEl.innerHTML = payload.breakdown.map((row) =>
        `<tr><td>${row.line_item}</td><td>${row.region}</td><td>${row.estimated_mwh}</td><td>${row.estimated_water_liters}</td></tr>`
      ).join("");
      breakdownWrap.hidden = payload.breakdown.length === 0;
    });
  </script>
</body>
</html>
        """
    )
