import type {
  FacilityChangesResponse,
  FacilityDetailResponse,
  FacilityEvidenceResponse,
  FacilityListResponse,
  FacilitySourcesResponse,
  PublicRecordTemplateResponse,
} from "./types.js";

export class AquaStatDesktopClient {
  constructor(private readonly baseUrl: string) {}

  private async request<T>(path: string): Promise<T> {
    const response = await fetch(new URL(path, this.baseUrl));
    if (!response.ok) {
      let message = `AquaStat request failed: ${response.status} ${response.statusText}`;
      if (response.status === 402) {
        try {
          const payload = (await response.json()) as {
            error?: { message?: string; checkoutUrl?: string };
          };
          const checkoutUrl = payload.error?.checkoutUrl;
          message = payload.error?.message ?? message;
          if (checkoutUrl) {
            window.open(checkoutUrl, "_blank", "noopener");
          }
        } catch {
          // Keep the fallback message when the response body is not JSON.
        }
      }
      throw new Error(message);
    }
    return (await response.json()) as T;
  }

  fetchFacility(facilityId: string): Promise<FacilityDetailResponse> {
    return this.request<FacilityDetailResponse>(`/api/v1/facilities/${facilityId}`);
  }

  fetchFacilities(): Promise<FacilityListResponse> {
    return this.request<FacilityListResponse>("/api/v1/facilities?limit=20");
  }

  fetchFacilityEvidence(facilityId: string): Promise<FacilityEvidenceResponse> {
    return this.request<FacilityEvidenceResponse>(`/api/v1/facilities/${facilityId}/evidence`);
  }

  fetchFacilitySources(facilityId: string): Promise<FacilitySourcesResponse> {
    return this.request<FacilitySourcesResponse>(`/api/v1/facilities/${facilityId}/sources`);
  }

  fetchFacilityHistory(facilityId: string): Promise<FacilityChangesResponse> {
    return this.request<FacilityChangesResponse>(`/api/v1/facilities/${facilityId}/history`);
  }

  fetchPublicRecordTemplates(facilityId: string): Promise<PublicRecordTemplateResponse> {
    return this.request<PublicRecordTemplateResponse>(
      `/api/v1/facilities/${facilityId}/public-records/templates`,
    );
  }
}
