export interface EstimateResponse {
  datacenter: {
    id: string;
    provider: string;
    region_slug: string;
    cooling_type: string;
  };
  timestamp: string;
  weather_snapshot: {
    dry_bulb_temp_c: number;
    relative_humidity_pct: number;
    calculated_wet_bulb_temp_c: number;
  };
  water_metrics: {
    estimated_it_load_mw: number;
    calculated_instant_wue: number;
    water_consumption_liters_per_hour: number;
    water_consumption_gallons_per_hour: number;
    equivalent_household_daily_water_usage: number;
  };
}

export interface RouteWorkloadRequest {
  job_duration_hours: number;
  compute_demand_mwh: number;
  candidate_regions: string[];
}

export interface RouteWorkloadResponse {
  optimal_region: string;
  explanation: string;
  routing_matrix: Array<{
    region: string;
    projected_water_liters: number;
    projected_carbon_g: number;
    water_stress_adjusted_impact_score: number;
  }>;
}

export class AquaStatClient {
  constructor(options?: { apiKey?: string | null; apiUrl?: string; fetchImpl?: typeof fetch });
  estimate(provider: string, region: string, loadMw?: number): Promise<EstimateResponse>;
  routeWorkload(payload: RouteWorkloadRequest): Promise<RouteWorkloadResponse>;
}
