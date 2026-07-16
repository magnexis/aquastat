export class AquaStatClient {
  constructor({ apiKey = null, apiUrl = "https://aquastat-api.onrender.com/api/v1", fetchImpl = globalThis.fetch } = {}) {
    this.apiKey = apiKey;
    this.apiUrl = apiUrl.replace(/\/$/, "");
    this.fetchImpl = fetchImpl;
  }

  headers() {
    const headers = { "User-Agent": "aquastat-sdk-js/1.1.0" };
    if (this.apiKey) headers["X-API-Key"] = this.apiKey;
    return headers;
  }

  async estimate(provider, region, loadMw) {
    const url = new URL(`${this.apiUrl}/estimate`);
    url.searchParams.set("provider", provider);
    url.searchParams.set("region", region);
    if (loadMw !== undefined) url.searchParams.set("load_mw", String(loadMw));
    const response = await this.fetchImpl(url, { headers: this.headers() });
    if (!response.ok) throw new Error(`AquaStat estimate failed: ${response.status}`);
    return response.json();
  }

  async routeWorkload(payload) {
    const response = await this.fetchImpl(`${this.apiUrl}/route-workload`, {
      method: "POST",
      headers: { ...this.headers(), "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error(`AquaStat route-workload failed: ${response.status}`);
    return response.json();
  }
}
