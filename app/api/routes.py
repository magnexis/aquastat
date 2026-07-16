from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings
from app.repository import get_region, list_regions
from app.schemas import DataCenterSummary, EstimateDataCenter, EstimateResponse, WaterMetrics, WeatherSnapshot
from app.services.thermodynamics import (
    calculate_dynamic_wue,
    calculate_water_consumption_lph,
    calculate_wet_bulb_temperature_c,
)
from app.services.weather import WeatherServiceError, fetch_current_weather


router = APIRouter()


@router.get("/regions", response_model=list[DataCenterSummary])
async def get_regions() -> list[DataCenterSummary]:
    regions = await list_regions()
    return [DataCenterSummary.model_validate(region) for region in regions]


@router.get("/estimate", response_model=EstimateResponse)
async def get_estimate(
    provider: str = Query(..., min_length=1),
    region: str = Query(..., min_length=1),
    load_mw: float | None = Query(default=None, gt=0),
) -> EstimateResponse:
    datacenter = await get_region(provider, region)
    if datacenter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found")

    estimated_it_load_mw = load_mw if load_mw is not None else datacenter["max_it_capacity_mw"] * 0.5

    try:
        weather = await fetch_current_weather(datacenter["latitude"], datacenter["longitude"])
    except WeatherServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weather service unavailable",
        ) from exc

    wet_bulb_temp_c = calculate_wet_bulb_temperature_c(
        weather["dry_bulb_temp_c"],
        weather["relative_humidity_pct"],
    )
    instant_wue = calculate_dynamic_wue(datacenter["base_wue"], wet_bulb_temp_c, datacenter["cooling_type"])
    water_lph = calculate_water_consumption_lph(estimated_it_load_mw, instant_wue)
    water_gph = water_lph * settings.gallons_per_liter
    household_equivalent = (water_gph * 24.0) / settings.baseline_household_gallons_per_day

    timestamp = datetime.fromisoformat(str(weather["timestamp"]).replace("Z", "+00:00"))
    return EstimateResponse(
        datacenter=EstimateDataCenter(
            id=datacenter["id"],
            provider=datacenter["provider"],
            region_slug=datacenter["region_slug"],
            cooling_type=datacenter["cooling_type"],
        ),
        timestamp=timestamp,
        weather_snapshot=WeatherSnapshot(
            dry_bulb_temp_c=round(weather["dry_bulb_temp_c"], 1),
            relative_humidity_pct=round(weather["relative_humidity_pct"], 1),
            calculated_wet_bulb_temp_c=round(wet_bulb_temp_c, 1),
            source=str(weather.get("source", "unknown")),
            quality=str(weather.get("quality", "modeled")),
        ),
        water_metrics=WaterMetrics(
            estimated_it_load_mw=round(estimated_it_load_mw, 1),
            calculated_instant_wue=round(instant_wue, 2),
            water_consumption_liters_per_hour=round(water_lph, 1),
            water_consumption_gallons_per_hour=round(water_gph, 1),
            equivalent_household_daily_water_usage=round(household_equivalent, 1),
        ),
    )
