import type { FacilityDetailResponse, PublicRecordTemplateResponse } from "./types.js";

export class AquaStatDesktopClient {
  constructor(private readonly baseUrl: string) {}

  private async request<T>(path: string): Promise<T> {
    const response = await fetch(new URL(path, this.baseUrl));
    if (!response.ok) {
      throw new Error(`AquaStat request failed: ${response.status} ${response.statusText}`);
    }
    return (await response.json()) as T;
  }

  fetchFacility(facilityId: string): Promise<FacilityDetailResponse> {
    return this.request<FacilityDetailResponse>(`/api/v1/facilities/${facilityId}`);
  }

  fetchPublicRecordTemplates(facilityId: string): Promise<PublicRecordTemplateResponse> {
    return this.request<PublicRecordTemplateResponse>(
      `/api/v1/facilities/${facilityId}/public-records/templates`,
    );
  }
}
