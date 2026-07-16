from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.api.v2_routes import (
    get_benchmark,
    get_stress_map,
    route_workload,
    upload_footprint_csv,
    footprint_calculator_ui,
)
from app.schemas import BenchmarkResponse, FootprintResponse, RouteWorkloadRequest, RouteWorkloadResponse, StressMapResponse


router = APIRouter()


@router.get("/benchmark", response_model=BenchmarkResponse, tags=["analytics"])
async def get_benchmark_v1() -> BenchmarkResponse:
    return await get_benchmark()


@router.get("/stress-map", response_model=StressMapResponse, tags=["analytics"])
async def get_stress_map_v1() -> StressMapResponse:
    return await get_stress_map()


@router.post("/route-workload", response_model=RouteWorkloadResponse, tags=["analytics"])
async def route_workload_v1(request: Request, payload: RouteWorkloadRequest) -> RouteWorkloadResponse:
    return await route_workload(request, payload)


@router.post("/footprint", response_model=FootprintResponse, tags=["analytics"])
async def upload_footprint_csv_v1(file: UploadFile = File(...)) -> FootprintResponse:
    return await upload_footprint_csv(file)


@router.get("/footprint-calculator", response_class=HTMLResponse, tags=["analytics"])
async def footprint_calculator_ui_v1() -> HTMLResponse:
    return await footprint_calculator_ui()
