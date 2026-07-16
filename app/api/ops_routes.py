from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.errors import health_payload
from app.ops_schemas import (
    AuditEventListResponse,
    ControlCenterOverviewResponse,
    HealthReadyResponse,
    ManagedApiKeyActionResponse,
    ManagedApiKeyCreateRequest,
    ManagedApiKeyCreateResponse,
    ManagedApiKeyListResponse,
    ModelRegistryResponse,
    RequestLogResponse,
    VersionResponse,
)
from app.schemas import HealthResponse
from app.security import require_admin_api_key
from app.services.ops_center import (
    build_overview_payload,
    get_version_payload,
    list_audit_events,
    list_models,
    list_request_activity,
    managed_key_store,
    record_audit_event,
)


router = APIRouter()


@router.get("/health/live", response_model=HealthReadyResponse, tags=["meta"])
async def get_liveness() -> HealthReadyResponse:
    return HealthReadyResponse.model_validate(health_payload("aquastat-api", settings.app_version))


@router.get("/health/ready", response_model=HealthReadyResponse, tags=["meta"])
async def get_readiness() -> HealthReadyResponse:
    return HealthReadyResponse.model_validate(health_payload("aquastat-api", settings.app_version))


@router.get("/version", response_model=VersionResponse, tags=["meta"])
async def get_version() -> VersionResponse:
    return VersionResponse.model_validate(get_version_payload())


@router.get("/api/v1/control-center/overview", response_model=ControlCenterOverviewResponse, tags=["control-center"])
async def get_control_center_overview() -> ControlCenterOverviewResponse:
    return ControlCenterOverviewResponse.model_validate(await build_overview_payload())


@router.get("/api/v1/control-center/requests", response_model=RequestLogResponse, tags=["control-center"])
async def get_request_log(_: str = Depends(require_admin_api_key)) -> RequestLogResponse:
    return RequestLogResponse.model_validate(await list_request_activity())


@router.get("/api/v1/control-center/models", response_model=ModelRegistryResponse, tags=["control-center"])
async def get_models() -> ModelRegistryResponse:
    return ModelRegistryResponse.model_validate(list_models())


@router.get("/api/v1/control-center/api-keys", response_model=ManagedApiKeyListResponse, tags=["control-center"])
async def list_managed_keys(_: str = Depends(require_admin_api_key)) -> ManagedApiKeyListResponse:
    return ManagedApiKeyListResponse.model_validate(await managed_key_store.list())


@router.post("/api/v1/control-center/api-keys", response_model=ManagedApiKeyCreateResponse, tags=["control-center"])
async def create_managed_key(
    payload: ManagedApiKeyCreateRequest,
    request: Request,
    _: str = Depends(require_admin_api_key),
) -> ManagedApiKeyCreateResponse:
    created = await managed_key_store.create(payload.model_dump())
    await record_audit_event(
        actor="admin",
        action="api_key.created",
        target=created["record"]["id"],
        result="success",
        request_id=getattr(request.state, "request_id", None),
        client_ip=getattr(request.client, "host", None) if request.client else None,
        metadata_json={"environment": created["record"]["environment"], "scopes": created["record"]["scopes"]},
    )
    return ManagedApiKeyCreateResponse.model_validate(created)


@router.post(
    "/api/v1/control-center/api-keys/{key_id}/revoke",
    response_model=ManagedApiKeyActionResponse,
    tags=["control-center"],
)
async def revoke_managed_key(
    key_id: str,
    request: Request,
    _: str = Depends(require_admin_api_key),
) -> ManagedApiKeyActionResponse:
    record = await managed_key_store.set_status(key_id, "revoked")
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Managed key not found")
    await record_audit_event(
        actor="admin",
        action="api_key.revoked",
        target=key_id,
        result="success",
        request_id=getattr(request.state, "request_id", None),
        client_ip=getattr(request.client, "host", None) if request.client else None,
        metadata_json={"status": "revoked"},
    )
    return ManagedApiKeyActionResponse(id=key_id, status="revoked", message="API key revoked.")


@router.post(
    "/api/v1/control-center/api-keys/{key_id}/disable",
    response_model=ManagedApiKeyActionResponse,
    tags=["control-center"],
)
async def disable_managed_key(
    key_id: str,
    request: Request,
    _: str = Depends(require_admin_api_key),
) -> ManagedApiKeyActionResponse:
    record = await managed_key_store.set_status(key_id, "disabled")
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Managed key not found")
    await record_audit_event(
        actor="admin",
        action="api_key.disabled",
        target=key_id,
        result="success",
        request_id=getattr(request.state, "request_id", None),
        client_ip=getattr(request.client, "host", None) if request.client else None,
        metadata_json={"status": "disabled"},
    )
    return ManagedApiKeyActionResponse(id=key_id, status="disabled", message="API key disabled.")


@router.get("/api/v1/control-center/audit-logs", response_model=AuditEventListResponse, tags=["control-center"])
async def get_audit_logs(_: str = Depends(require_admin_api_key)) -> AuditEventListResponse:
    return AuditEventListResponse.model_validate(await list_audit_events())


CONTROL_CENTER_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AquaStat Control Center</title>
  <style>
    :root {
      --bg: #f4f7f7;
      --panel: #ffffff;
      --ink: #14343a;
      --muted: #5f7478;
      --line: #d8e2e1;
      --accent: #0f766e;
      --accent-soft: #dff2ef;
      --warn: #9a6700;
      --focus: #1d4ed8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "IBM Plex Sans", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    .layout {
      display: grid;
      grid-template-columns: 240px 1fr;
      min-height: 100vh;
    }
    nav {
      border-right: 1px solid var(--line);
      background: #eef4f3;
      padding: 24px 18px;
      position: sticky;
      top: 0;
      height: 100vh;
    }
    nav h1 {
      margin: 0 0 12px;
      font-size: 1.25rem;
    }
    nav p {
      margin: 0 0 20px;
      color: var(--muted);
      line-height: 1.5;
      font-size: 0.95rem;
    }
    nav a {
      display: block;
      text-decoration: none;
      color: var(--ink);
      padding: 10px 12px;
      border-radius: 10px;
      margin-bottom: 4px;
    }
    nav a:hover, nav a:focus-visible {
      background: var(--accent-soft);
      outline: 2px solid transparent;
    }
    main {
      padding: 28px;
      display: grid;
      gap: 22px;
    }
    .toolbar, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
    }
    .toolbar {
      display: grid;
      gap: 12px;
    }
    .toolbar-row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }
    label { font-weight: 600; }
    input, select, textarea, button {
      font: inherit;
    }
    input, select, textarea {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      width: 100%;
      background: #fff;
    }
    button {
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      background: var(--accent);
      color: #fff;
      cursor: pointer;
    }
    button.secondary {
      background: #d8e9e7;
      color: var(--ink);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 14px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: #fbfdfd;
    }
    .metric .label { color: var(--muted); font-size: 0.9rem; }
    .metric .value { font-size: 1.6rem; margin-top: 8px; }
    .panel h2 { margin-top: 0; }
    .two {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 18px;
    }
    pre, code {
      font-family: "Cascadia Code", "Consolas", monospace;
    }
    pre {
      white-space: pre-wrap;
      background: #0f172a;
      color: #e2e8f0;
      padding: 14px;
      border-radius: 12px;
      overflow: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      font-size: 0.95rem;
    }
    .status {
      color: var(--warn);
      font-size: 0.95rem;
    }
    .bars { display: grid; gap: 10px; }
    .bar-row { display: grid; gap: 6px; }
    .bar {
      height: 12px;
      border-radius: 999px;
      background: #e7eeee;
      overflow: hidden;
    }
    .bar > span {
      display: block;
      height: 100%;
      background: var(--accent);
    }
    @media (max-width: 960px) {
      .layout { grid-template-columns: 1fr; }
      nav { position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }
      .two { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="layout">
    <nav aria-label="Control center navigation">
      <h1>AquaStat Control Center</h1>
      <p>A focused workspace for calculations, facilities, API access, request diagnostics, and platform operations.</p>
      <a href="#overview">Overview</a>
      <a href="#calculate">Calculate</a>
      <a href="#facilities">Facilities</a>
      <a href="#api-keys">API Keys</a>
      <a href="#requests">Requests</a>
      <a href="#models">Models</a>
      <a href="#documentation">Documentation</a>
    </nav>
    <main>
      <section class="toolbar" id="overview">
        <div class="toolbar-row">
          <div style="min-width:260px; flex:1;">
            <label for="adminKey">Admin API Key</label>
            <input id="adminKey" type="password" placeholder="aq_live_..." aria-describedby="adminHelp">
          </div>
          <div style="min-width:220px;">
            <label for="rangeSelect">Overview range</label>
            <select id="rangeSelect">
              <option>last 24 hours</option>
              <option>last 7 days</option>
              <option>last 30 days</option>
              <option>current billing period</option>
            </select>
          </div>
          <div style="align-self:end;">
            <button id="refreshOverview">Refresh overview</button>
          </div>
        </div>
        <div id="adminHelp" class="status">Admin-only data such as request history and key management requires a configured admin API key. The UI never stores it beyond the current browser session.</div>
      </section>

      <section class="panel">
        <h2>Overview Dashboard</h2>
        <div class="grid" id="metricsGrid"></div>
      </section>

      <section class="two">
        <section class="panel">
          <h2>Usage by Endpoint</h2>
          <div class="bars" id="endpointBars"></div>
        </section>
        <section class="panel">
          <h2>Confidence Distribution</h2>
          <div class="bars" id="confidenceBars"></div>
        </section>
      </section>

      <section class="panel" id="calculate">
        <h2>Interactive Calculation Workspace</h2>
        <div class="grid">
          <div>
            <label for="provider">Provider</label>
            <select id="provider">
              <option value="aws">AWS</option>
              <option value="gcp">GCP</option>
              <option value="azure">Azure</option>
            </select>
          </div>
          <div>
            <label for="region">Region</label>
            <input id="region" value="us-east-1">
          </div>
          <div>
            <label for="loadMw">IT load (MW)</label>
            <input id="loadMw" type="number" value="12.5" step="0.1" min="0.1">
          </div>
        </div>
        <div class="toolbar-row" style="margin-top:14px;">
          <button id="runEstimate">Run estimate</button>
          <button id="copyCurl" class="secondary">Copy as cURL</button>
          <button id="copyPython" class="secondary">Copy as Python</button>
        </div>
        <pre id="estimateOutput">Run an AquaStat estimate to inspect the response, assumptions, and units.</pre>
      </section>

      <section class="two">
        <section class="panel" id="facilities">
          <h2>Facilities</h2>
          <button id="loadFacilities">Load facilities</button>
          <table>
            <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Quality</th></tr></thead>
            <tbody id="facilitiesBody"></tbody>
          </table>
        </section>
        <section class="panel" id="models">
          <h2>Model Registry</h2>
          <button id="loadModels">Load models</button>
          <pre id="modelsOutput">Load the active AquaStat model registry.</pre>
        </section>
      </section>

      <section class="two">
        <section class="panel" id="api-keys">
          <h2>API Key Lifecycle</h2>
          <div class="grid">
            <div>
              <label for="keyName">Key name</label>
              <input id="keyName" value="Control Center Demo Key">
            </div>
            <div>
              <label for="keyEnv">Environment</label>
              <select id="keyEnv">
                <option value="development">development</option>
                <option value="testing">testing</option>
                <option value="staging">staging</option>
                <option value="production">production</option>
              </select>
            </div>
          </div>
          <div class="toolbar-row" style="margin-top:14px;">
            <button id="createKey">Generate key</button>
            <button id="listKeys" class="secondary">List keys</button>
          </div>
          <pre id="keysOutput">Managed API keys are stored as hashes server-side and the raw key is shown only once on creation.</pre>
        </section>

        <section class="panel" id="requests">
          <h2>Request Explorer</h2>
          <button id="loadRequests">Load request history</button>
          <pre id="requestsOutput">Recent requests will appear here with request IDs, paths, status codes, and durations.</pre>
        </section>
      </section>

      <section class="panel" id="documentation">
        <h2>Documentation and Versioning</h2>
        <p>Interactive API documentation remains available at <code>/docs</code>. AquaStat also exposes <code>/openapi.json</code>, <code>/version</code>, <code>/health</code>, <code>/health/live</code>, and <code>/health/ready</code> for deployment and incident workflows.</p>
        <p>Managed API keys now enforce declared scopes such as <code>calculations:read</code>, <code>calculations:write</code>, <code>facilities:read</code>, <code>facilities:write</code>, and <code>usage:read</code>. Environment-level operator keys still retain full access.</p>
      </section>
    </main>
  </div>
  <script>
    const adminKeyInput = document.getElementById("adminKey");
    const metricsGrid = document.getElementById("metricsGrid");
    const endpointBars = document.getElementById("endpointBars");
    const confidenceBars = document.getElementById("confidenceBars");
    const estimateOutput = document.getElementById("estimateOutput");
    const facilitiesBody = document.getElementById("facilitiesBody");
    const keysOutput = document.getElementById("keysOutput");
    const requestsOutput = document.getElementById("requestsOutput");
    const modelsOutput = document.getElementById("modelsOutput");

    function headers(adminOnly = false) {
      const headers = { "Content-Type": "application/json" };
      if (adminOnly && adminKeyInput.value) {
        headers["X-API-Key"] = adminKeyInput.value;
      }
      return headers;
    }

    function renderBars(container, items) {
      container.innerHTML = "";
      const max = Math.max(...items.map((item) => item.value), 1);
      items.forEach((item) => {
        const row = document.createElement("div");
        row.className = "bar-row";
        row.innerHTML = `<div>${item.label} <strong>${item.value}</strong></div><div class="bar"><span style="width:${(item.value / max) * 100}%"></span></div>`;
        container.appendChild(row);
      });
    }

    async function loadOverview() {
      const response = await fetch("/api/v1/control-center/overview");
      const payload = await response.json();
      metricsGrid.innerHTML = payload.metrics.map((metric) =>
        `<article class="metric"><div class="label">${metric.label}</div><div class="value">${metric.value}${metric.unit ? " " + metric.unit : ""}</div></article>`
      ).join("");
      renderBars(endpointBars, payload.endpoint_usage);
      renderBars(confidenceBars, payload.confidence_distribution);
    }

    async function runEstimate() {
      const provider = document.getElementById("provider").value;
      const region = document.getElementById("region").value;
      const loadMw = document.getElementById("loadMw").value;
      const response = await fetch(`/api/v1/estimate?provider=${encodeURIComponent(provider)}&region=${encodeURIComponent(region)}&load_mw=${encodeURIComponent(loadMw)}`, { headers: headers(false) });
      const payload = await response.json();
      estimateOutput.textContent = JSON.stringify(payload, null, 2);
    }

    async function loadFacilities() {
      const response = await fetch("/api/v1/facilities");
      const payload = await response.json();
      facilitiesBody.innerHTML = payload.items.map((item) =>
        `<tr><td>${item.name}</td><td>${item.facility_type}</td><td>${item.operational_status}</td><td>${item.data_quality.label} (${item.data_quality.score})</td></tr>`
      ).join("");
    }

    async function loadRequests() {
      const response = await fetch("/api/v1/control-center/requests", { headers: headers(true) });
      const payload = await response.json();
      requestsOutput.textContent = JSON.stringify(payload, null, 2);
    }

    async function loadModels() {
      const response = await fetch("/api/v1/control-center/models");
      const payload = await response.json();
      modelsOutput.textContent = JSON.stringify(payload, null, 2);
    }

    async function createKey() {
      const response = await fetch("/api/v1/control-center/api-keys", {
        method: "POST",
        headers: headers(true),
        body: JSON.stringify({
          name: document.getElementById("keyName").value,
          description: "Generated from the AquaStat Control Center",
          environment: document.getElementById("keyEnv").value,
          scopes: ["calculations:read", "calculations:write", "facilities:read", "usage:read"],
          allowed_endpoints: ["/api/v1/estimate", "/api/v1/facilities"],
          allowed_origins: [],
          allowed_ips: [],
          usage_limit: 10000
        })
      });
      const payload = await response.json();
      keysOutput.textContent = JSON.stringify(payload, null, 2);
    }

    async function listKeys() {
      const response = await fetch("/api/v1/control-center/api-keys", { headers: headers(true) });
      const payload = await response.json();
      keysOutput.textContent = JSON.stringify(payload, null, 2);
    }

    function copySnippet(kind) {
      const provider = document.getElementById("provider").value;
      const region = document.getElementById("region").value;
      const loadMw = document.getElementById("loadMw").value;
      const key = adminKeyInput.value || "aq_live_your_key";
      const baseUrl = window.location.origin === "null" ? "https://aquastat-api.onrender.com" : window.location.origin;
      const curl = `curl -sS "${baseUrl}/api/v1/estimate?provider=${provider}&region=${region}&load_mw=${loadMw}" -H "X-API-Key: ${key}"`;
      const python = `import httpx\\nresponse = httpx.get("${baseUrl}/api/v1/estimate", params={"provider": "${provider}", "region": "${region}", "load_mw": ${loadMw}}, headers={"X-API-Key": "${key}"})\\nprint(response.json())`;
      navigator.clipboard.writeText(kind === "curl" ? curl : python);
    }

    document.getElementById("refreshOverview").addEventListener("click", loadOverview);
    document.getElementById("runEstimate").addEventListener("click", runEstimate);
    document.getElementById("loadFacilities").addEventListener("click", loadFacilities);
    document.getElementById("loadRequests").addEventListener("click", loadRequests);
    document.getElementById("loadModels").addEventListener("click", loadModels);
    document.getElementById("createKey").addEventListener("click", createKey);
    document.getElementById("listKeys").addEventListener("click", listKeys);
    document.getElementById("copyCurl").addEventListener("click", () => copySnippet("curl"));
    document.getElementById("copyPython").addEventListener("click", () => copySnippet("python"));

    loadOverview();
    loadModels();
  </script>
</body>
</html>
"""


@router.get("/control-center", response_class=HTMLResponse, tags=["control-center"])
@router.get("/overview", response_class=HTMLResponse, tags=["control-center"])
@router.get("/calculate", response_class=HTMLResponse, tags=["control-center"])
@router.get("/facilities", response_class=HTMLResponse, tags=["control-center"])
@router.get("/api-keys", response_class=HTMLResponse, tags=["control-center"])
@router.get("/requests", response_class=HTMLResponse, tags=["control-center"])
@router.get("/documentation", response_class=HTMLResponse, tags=["control-center"])
async def control_center_shell() -> HTMLResponse:
    return HTMLResponse(CONTROL_CENTER_HTML)
