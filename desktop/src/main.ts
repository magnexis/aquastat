import { AquaStatDesktopClient } from "./api.js";
import type {
  FacilityChangesResponse,
  FacilityDetailResponse,
  FacilityEvidenceResponse,
  FacilityListResponse,
  FacilitySourcesResponse,
  FieldEvidence,
  PublicRecordTemplateResponse,
} from "./types.js";

const DEFAULT_BASE_URL = "http://127.0.0.1:8080";
const fallbackFacilityId = "fac_syn_ashburn";

type DesktopBundle = {
  detail: FacilityDetailResponse;
  evidence: FacilityEvidenceResponse;
  sources: FacilitySourcesResponse;
  history: FacilityChangesResponse;
  templates: PublicRecordTemplateResponse;
};

type AppState = {
  baseUrl: string;
  client: AquaStatDesktopClient;
  facilities: FacilityListResponse["items"];
  selectedFacilityId: string;
  activeTab: "overview" | "evidence" | "sources" | "history" | "records";
  loadingList: boolean;
  loadingDetail: boolean;
  error: string | null;
  bundle: DesktopBundle | null;
};

const state: AppState = {
  baseUrl: DEFAULT_BASE_URL,
  client: new AquaStatDesktopClient(DEFAULT_BASE_URL),
  facilities: [],
  selectedFacilityId: fallbackFacilityId,
  activeTab: "overview",
  loadingList: true,
  loadingDetail: true,
  error: null,
  bundle: null,
};

function injectStyles(): void {
  const style = document.createElement("style");
  style.textContent = `
    :root {
      color-scheme: light;
      --bg-top: #eff8f8;
      --bg-bottom: #e2f0ef;
      --panel: rgba(255, 255, 255, 0.88);
      --panel-strong: rgba(255, 255, 255, 0.96);
      --panel-alt: #f3faf9;
      --text: #123038;
      --muted: #617d84;
      --line: rgba(15, 91, 99, 0.14);
      --brand: #0d8b8f;
      --brand-deep: #0a5f67;
      --brand-soft: #dff2f1;
      --accent: #f5a524;
      --danger: #b64242;
      --warning: #a56318;
      --shadow: 0 18px 60px rgba(13, 55, 62, 0.14);
      font-family: "Segoe UI", "IBM Plex Sans", system-ui, sans-serif;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(13, 139, 143, 0.16), transparent 28%),
        radial-gradient(circle at bottom right, rgba(245, 165, 36, 0.12), transparent 24%),
        linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 100%);
    }

    button, input, textarea {
      font: inherit;
    }

    .app-shell {
      max-width: 1440px;
      margin: 0 auto;
      padding: 28px;
      display: grid;
      gap: 20px;
    }

    .glass,
    .sidebar,
    .workspace-panel,
    .hero-card {
      backdrop-filter: blur(18px);
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }

    .hero-card {
      border-radius: 30px;
      padding: 28px;
      overflow: hidden;
      position: relative;
    }

    .hero-card::after {
      content: "";
      position: absolute;
      inset: auto -80px -120px auto;
      width: 320px;
      height: 320px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(13, 139, 143, 0.20) 0%, transparent 70%);
      pointer-events: none;
    }

    .hero-top {
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: flex-start;
      margin-bottom: 22px;
    }

    .hero-kicker {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 7px 12px;
      background: rgba(13, 139, 143, 0.10);
      color: var(--brand-deep);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-size: 12px;
      font-weight: 800;
      margin-bottom: 14px;
    }

    .hero-card h1 {
      margin: 0 0 10px;
      font-size: 38px;
      line-height: 1.05;
      max-width: 14ch;
    }

    .hero-card p {
      margin: 0;
      max-width: 68ch;
      color: var(--muted);
      line-height: 1.6;
    }

    .status-stack {
      display: grid;
      gap: 10px;
      min-width: 260px;
    }

    .status-pill {
      display: inline-flex;
      justify-content: center;
      align-items: center;
      padding: 12px 16px;
      border-radius: 18px;
      background: var(--panel-strong);
      border: 1px solid var(--line);
      font-weight: 700;
      color: var(--brand-deep);
    }

    .hero-metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }

    .metric-card {
      border-radius: 22px;
      padding: 18px;
      background: var(--panel-strong);
      border: 1px solid var(--line);
    }

    .metric-card .label {
      color: var(--muted);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 8px;
    }

    .metric-card .value {
      font-size: 28px;
      font-weight: 800;
      line-height: 1.1;
    }

    .layout {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 20px;
      min-height: 760px;
    }

    .sidebar {
      border-radius: 28px;
      padding: 20px;
      display: grid;
      gap: 16px;
      align-content: start;
    }

    .sidebar h2,
    .workspace-panel h2,
    .workspace-panel h3 {
      margin: 0;
    }

    .sidebar-intro {
      color: var(--muted);
      line-height: 1.5;
      margin: 0;
      font-size: 14px;
    }

    .base-url-box,
    .search-box {
      display: grid;
      gap: 8px;
    }

    .field-label {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
      font-weight: 700;
    }

    .row {
      display: flex;
      gap: 10px;
    }

    .text-input,
    .search-input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      background: rgba(255, 255, 255, 0.92);
      color: var(--text);
    }

    .button {
      border: 0;
      border-radius: 14px;
      padding: 12px 16px;
      background: linear-gradient(135deg, var(--brand) 0%, var(--brand-deep) 100%);
      color: white;
      font-weight: 700;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 120ms ease;
      box-shadow: 0 10px 22px rgba(13, 139, 143, 0.24);
    }

    .button.secondary {
      background: var(--panel-strong);
      color: var(--brand-deep);
      border: 1px solid var(--line);
      box-shadow: none;
    }

    .button:hover {
      transform: translateY(-1px);
    }

    .facility-list {
      display: grid;
      gap: 10px;
      max-height: 520px;
      overflow: auto;
      padding-right: 4px;
    }

    .facility-button {
      text-align: left;
      border: 1px solid transparent;
      border-radius: 18px;
      padding: 14px;
      background: rgba(255, 255, 255, 0.72);
      cursor: pointer;
      transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
    }

    .facility-button:hover {
      transform: translateX(1px);
      border-color: rgba(13, 139, 143, 0.26);
    }

    .facility-button.active {
      background: linear-gradient(180deg, rgba(13, 139, 143, 0.12), rgba(13, 139, 143, 0.04));
      border-color: rgba(13, 139, 143, 0.34);
    }

    .facility-name {
      font-weight: 700;
      margin-bottom: 6px;
    }

    .facility-meta {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }

    .workspace {
      display: grid;
      gap: 20px;
      align-content: start;
    }

    .workspace-panel {
      border-radius: 28px;
      padding: 22px;
    }

    .tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }

    .tab {
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.82);
      border-radius: 999px;
      padding: 10px 14px;
      font-weight: 700;
      color: var(--brand-deep);
      cursor: pointer;
    }

    .tab.active {
      background: linear-gradient(135deg, var(--brand) 0%, var(--brand-deep) 100%);
      color: #fff;
      border-color: transparent;
    }

    .content-grid {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 18px;
    }

    .stack {
      display: grid;
      gap: 16px;
    }

    .card {
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
      background: var(--panel-strong);
    }

    .card h3 {
      margin-bottom: 6px;
      font-size: 20px;
    }

    .card p {
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
    }

    .value-xl {
      font-size: 40px;
      font-weight: 800;
      line-height: 1.05;
      margin: 14px 0 8px;
    }

    .badge-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 6px 10px;
      background: var(--brand-soft);
      color: var(--brand-deep);
      font-size: 12px;
      font-weight: 800;
    }

    .badge.warn {
      background: #fff2df;
      color: var(--warning);
    }

    .badge.danger {
      background: #fdeaea;
      color: var(--danger);
    }

    .badge.dark {
      background: rgba(18, 48, 56, 0.1);
      color: var(--text);
    }

    .meta-grid {
      display: grid;
      grid-template-columns: 150px 1fr;
      gap: 10px 14px;
      margin-top: 16px;
    }

    .meta-grid dt {
      margin: 0;
      color: var(--muted);
      font-weight: 700;
    }

    .meta-grid dd {
      margin: 0;
      font-weight: 600;
    }

    .table-list,
    .timeline-list,
    .source-list,
    .template-list,
    .claim-list {
      display: grid;
      gap: 12px;
    }

    .evidence-row,
    .timeline-item,
    .source-item,
    .template-item,
    .claim-item {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      background: rgba(255, 255, 255, 0.92);
    }

    .section-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 14px;
    }

    .eyebrow {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-size: 12px;
      font-weight: 800;
    }

    .muted {
      color: var(--muted);
    }

    .empty,
    .loading,
    .error-box {
      border: 1px dashed var(--line);
      border-radius: 24px;
      padding: 28px;
      text-align: center;
      background: rgba(255, 255, 255, 0.6);
      color: var(--muted);
    }

    .error-box {
      color: var(--danger);
      border-color: rgba(182, 66, 66, 0.25);
      background: rgba(253, 234, 234, 0.72);
    }

    .mini-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .mini-stat {
      border-radius: 18px;
      padding: 14px;
      background: var(--panel-alt);
      border: 1px solid var(--line);
    }

    .mini-stat .k {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 6px;
    }

    .mini-stat .v {
      font-size: 22px;
      font-weight: 800;
    }

    pre.template-body {
      white-space: pre-wrap;
      word-break: break-word;
      background: #f5fbfa;
      border-radius: 16px;
      border: 1px solid var(--line);
      padding: 14px;
      margin: 12px 0 0;
      color: #27434a;
      font-family: "Cascadia Code", "Consolas", monospace;
      font-size: 13px;
      line-height: 1.5;
    }

    a.inline-link {
      color: var(--brand-deep);
      text-decoration: none;
      font-weight: 700;
    }

    a.inline-link:hover {
      text-decoration: underline;
    }

    @media (max-width: 1180px) {
      .layout,
      .content-grid {
        grid-template-columns: 1fr;
      }

      .hero-top {
        flex-direction: column;
      }

      .hero-metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 720px) {
      .app-shell { padding: 16px; }
      .hero-card h1 { font-size: 30px; }
      .hero-metrics,
      .mini-grid { grid-template-columns: 1fr; }
      .meta-grid { grid-template-columns: 1fr; }
      .row { flex-direction: column; }
    }
  `;
  document.head.append(style);
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatValue(value: string | number | boolean | null, unit?: string | null): string {
  if (value === null || value === "") {
    return "Unknown";
  }
  return `${String(value)}${unit ? ` ${unit}` : ""}`;
}

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function summaryCards(detail: FacilityDetailResponse, templates: PublicRecordTemplateResponse): string {
  return `
    <div class="hero-metrics">
      <article class="metric-card">
        <div class="label">Data Quality</div>
        <div class="value">${detail.facility.data_quality.score.toFixed(2)}</div>
      </article>
      <article class="metric-card">
        <div class="label">Confidence</div>
        <div class="value">${detail.confidence_score}</div>
      </article>
      <article class="metric-card">
        <div class="label">Known Holders</div>
        <div class="value">${templates.known_holders.length}</div>
      </article>
      <article class="metric-card">
        <div class="label">Contradictions</div>
        <div class="value">${detail.contradictory_claims.length}</div>
      </article>
    </div>
  `;
}

function renderOverview(detail: FacilityDetailResponse, templates: PublicRecordTemplateResponse): string {
  const primary = detail.primary_water_figure;
  const warnings = detail.facility.warnings.length
    ? detail.facility.warnings.map((warning) => `<span class="badge warn">${escapeHtml(warning)}</span>`).join("")
    : '<span class="badge">No active facility warnings</span>';
  const waterSources = detail.water_sources.length
    ? detail.water_sources
        .map(
          (source) =>
            `<span class="badge dark">${escapeHtml(source.type)}${source.percent !== null ? ` ${source.percent}%` : ""}</span>`,
        )
        .join("")
    : '<span class="badge dark">No water source breakdown</span>';

  return `
    <div class="content-grid">
      <div class="stack">
        <section class="card">
          <div class="section-title">
            <div>
              <div class="eyebrow">Primary water figure</div>
              <h3>${primary ? escapeHtml(primary.field) : "No promoted primary figure"}</h3>
            </div>
            ${primary ? `<span class="badge">${escapeHtml(primary.evidence_class)}</span>` : ""}
          </div>
          <p>${primary ? escapeHtml(primary.notes ?? "AquaStat selected this figure as the current best-supported operational reference.") : "This facility exists in the registry but does not yet have a single promoted primary figure."}</p>
          ${
            primary
              ? `
            <div class="value-xl">${escapeHtml(formatValue(primary.value, primary.unit))}</div>
            <div class="badge-row">
              <span class="badge">${escapeHtml(primary.figure_type)}</span>
              <span class="badge">${escapeHtml(primary.reporting_boundary)}</span>
              <span class="badge dark">${escapeHtml(primary.value_status)}</span>
              <span class="badge dark">${pct(primary.confidence)} confidence</span>
            </div>
            <dl class="meta-grid">
              <dt>Source</dt>
              <dd>${escapeHtml(primary.source_id)}</dd>
              <dt>Source type</dt>
              <dd>${escapeHtml(primary.source_type)}</dd>
              <dt>Source date</dt>
              <dd>${escapeHtml(primary.source_date)}</dd>
              <dt>Verification</dt>
              <dd>${escapeHtml(primary.verification_status)}</dd>
              <dt>Extraction</dt>
              <dd>${escapeHtml(primary.extraction_method)}</dd>
              <dt>Independent chain</dt>
              <dd>${escapeHtml(primary.independent_chain_id ?? "Not assigned")}</dd>
            </dl>
          `
              : ""
          }
        </section>

        <section class="card">
          <div class="section-title">
            <div>
              <div class="eyebrow">Coverage and provenance</div>
              <h3>Record quality and operational coverage</h3>
            </div>
          </div>
          <div class="mini-grid">
            <article class="mini-stat"><div class="k">Location</div><div class="v">${escapeHtml(detail.facility.coverage.location)}</div></article>
            <article class="mini-stat"><div class="k">Capacity</div><div class="v">${escapeHtml(detail.facility.coverage.capacity)}</div></article>
            <article class="mini-stat"><div class="k">Cooling system</div><div class="v">${escapeHtml(detail.facility.coverage.cooling_system)}</div></article>
            <article class="mini-stat"><div class="k">Water use</div><div class="v">${escapeHtml(detail.facility.coverage.water_use)}</div></article>
          </div>
          <div class="badge-row" style="margin-top: 16px;">
            ${warnings}
          </div>
        </section>
      </div>

      <div class="stack">
        <section class="card">
          <div class="section-title">
            <div>
              <div class="eyebrow">Facility profile</div>
              <h3>${escapeHtml(detail.facility.name)}</h3>
            </div>
            <span class="badge dark">${escapeHtml(detail.record_status)}</span>
          </div>
          <dl class="meta-grid">
            <dt>Operator</dt>
            <dd>${escapeHtml(detail.facility.operator)}</dd>
            <dt>Facility type</dt>
            <dd>${escapeHtml(detail.facility.facility_type)}</dd>
            <dt>Operational status</dt>
            <dd>${escapeHtml(detail.facility.operational_status)}</dd>
            <dt>Country</dt>
            <dd>${escapeHtml(detail.facility.country)}</dd>
            <dt>Municipality</dt>
            <dd>${escapeHtml(detail.facility.municipality ?? "Unknown")}</dd>
            <dt>Campus</dt>
            <dd>${escapeHtml(detail.campus_name ?? "Unknown")}</dd>
            <dt>Owner</dt>
            <dd>${escapeHtml(detail.owner ?? "Unknown")}</dd>
            <dt>Grid region</dt>
            <dd>${escapeHtml(detail.facility.electricity_grid_region ?? "Unknown")}</dd>
            <dt>Cooling systems</dt>
            <dd>${escapeHtml(detail.facility.cooling_systems.join(", ") || "Unknown")}</dd>
            <dt>Water sources</dt>
            <dd><div class="badge-row">${waterSources}</div></dd>
          </dl>
        </section>

        <section class="card">
          <div class="section-title">
            <div>
              <div class="eyebrow">Public record readiness</div>
              <h3>Known holders and follow-up</h3>
            </div>
          </div>
          <div class="mini-grid">
            <article class="mini-stat"><div class="k">Sources</div><div class="v">${detail.facility.source_summary.total_sources}</div></article>
            <article class="mini-stat"><div class="k">Primary sources</div><div class="v">${detail.facility.source_summary.primary_sources}</div></article>
            <article class="mini-stat"><div class="k">Independent chains</div><div class="v">${detail.facility.source_summary.independent_chains}</div></article>
            <article class="mini-stat"><div class="k">Latest source</div><div class="v">${escapeHtml(formatDate(detail.facility.source_summary.latest_source_date))}</div></article>
          </div>
          <div class="badge-row" style="margin-top: 16px;">
            ${
              templates.known_holders
                .slice(0, 4)
                .map((holder) => `<span class="badge">${escapeHtml(holder.authority)}</span>`)
                .join("") || '<span class="badge dark">No holders available</span>'
            }
          </div>
        </section>
      </div>
    </div>
  `;
}

function renderEvidenceTab(evidence: FacilityEvidenceResponse): string {
  if (evidence.evidence.length === 0) {
    return '<div class="empty">No evidence rows are currently attached to this facility.</div>';
  }

  return `
    <div class="table-list">
      ${evidence.evidence
        .map(
          (item) => `
            <article class="evidence-row">
              <div class="section-title">
                <div>
                  <div class="eyebrow">${escapeHtml(item.field)}</div>
                  <h3>${escapeHtml(formatValue(item.value, item.unit))}</h3>
                </div>
                <span class="badge">${escapeHtml(item.evidence_class)}</span>
              </div>
              <p>${escapeHtml(item.notes ?? "No inline note provided for this evidence record.")}</p>
              <div class="badge-row">
                <span class="badge">${escapeHtml(item.figure_type)}</span>
                <span class="badge">${escapeHtml(item.reporting_boundary)}</span>
                <span class="badge dark">${escapeHtml(item.source_type)}</span>
                <span class="badge dark">${pct(item.confidence)} confidence</span>
              </div>
              <dl class="meta-grid">
                <dt>Source ID</dt>
                <dd>${escapeHtml(item.source_id)}</dd>
                <dt>Source date</dt>
                <dd>${escapeHtml(item.source_date)}</dd>
                <dt>Verification</dt>
                <dd>${escapeHtml(item.verification_status)}</dd>
                <dt>Status</dt>
                <dd>${escapeHtml(item.value_status)}</dd>
              </dl>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderSourcesTab(sources: FacilitySourcesResponse): string {
  if (sources.sources.length === 0) {
    return '<div class="empty">No source records are currently attached to this facility.</div>';
  }

  return `
    <div class="source-list">
      ${sources.sources
        .map(
          (source) => `
            <article class="source-item">
              <div class="section-title">
                <div>
                  <div class="eyebrow">${escapeHtml(source.publisher)}</div>
                  <h3>${escapeHtml(source.title)}</h3>
                </div>
                <span class="badge">${escapeHtml(source.reliability.tier)}</span>
              </div>
              <p>${escapeHtml(source.notes ?? source.reliability.explanation)}</p>
              <div class="badge-row">
                <span class="badge">${escapeHtml(source.document_type)}</span>
                <span class="badge dark">${escapeHtml(source.source_type)}</span>
                <span class="badge dark">${escapeHtml(source.review_status)}</span>
                <span class="badge dark">Reliability ${source.reliability.score}</span>
              </div>
              <dl class="meta-grid">
                <dt>Publication date</dt>
                <dd>${escapeHtml(formatDate(source.publication_date))}</dd>
                <dt>Retrieved</dt>
                <dd>${escapeHtml(formatDate(source.retrieved_at))}</dd>
                <dt>Jurisdiction</dt>
                <dd>${escapeHtml(source.jurisdiction ?? "Unknown")}</dd>
                <dt>Access</dt>
                <dd>${escapeHtml(source.access_status)}</dd>
              </dl>
              <div class="badge-row">
                <a class="inline-link" href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">Open source record</a>
              </div>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderHistoryTab(history: FacilityChangesResponse): string {
  if (history.changes.length === 0) {
    return '<div class="empty">No change history entries are currently available for this facility.</div>';
  }

  return `
    <div class="timeline-list">
      ${history.changes
        .map(
          (entry) => `
            <article class="timeline-item">
              <div class="section-title">
                <div>
                  <div class="eyebrow">${escapeHtml(formatDate(entry.changed_at))}</div>
                  <h3>${escapeHtml(entry.field)}</h3>
                </div>
                <span class="badge dark">${escapeHtml(entry.status)}</span>
              </div>
              <p>${escapeHtml(entry.summary)}</p>
              <dl class="meta-grid">
                <dt>Previous</dt>
                <dd>${escapeHtml(entry.previous_value === null ? "Unknown" : String(entry.previous_value))}</dd>
                <dt>New</dt>
                <dd>${escapeHtml(entry.new_value === null ? "Unknown" : String(entry.new_value))}</dd>
                <dt>Source</dt>
                <dd>${escapeHtml(entry.source_id ?? "Unknown")}</dd>
              </dl>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderRecordsTab(templates: PublicRecordTemplateResponse): string {
  if (templates.templates.length === 0) {
    return '<div class="empty">No public-record templates are currently available for this facility.</div>';
  }

  return `
    <div class="template-list">
      ${templates.templates
        .map(
          (template) => `
            <article class="template-item">
              <div class="section-title">
                <div>
                  <div class="eyebrow">${escapeHtml(template.authority)}</div>
                  <h3>${escapeHtml(template.subject)}</h3>
                </div>
                <span class="badge">${template.requested_records.length} record asks</span>
              </div>
              <p>${escapeHtml(template.summary)}</p>
              <div class="badge-row">
                ${template.requested_records.map((record) => `<span class="badge dark">${escapeHtml(record)}</span>`).join("")}
              </div>
              <pre class="template-body">${escapeHtml(template.body)}</pre>
              <div class="badge-row">
                ${template.legal_notes.map((note) => `<span class="badge warn">${escapeHtml(note)}</span>`).join("")}
              </div>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderClaims(claims: FieldEvidence[]): string {
  if (claims.length === 0) {
    return '<div class="empty">No contradictory claims are currently attached to this facility.</div>';
  }

  return `
    <div class="claim-list">
      ${claims
        .map(
          (claim) => `
            <article class="claim-item">
              <div class="section-title">
                <div>
                  <div class="eyebrow">${escapeHtml(claim.field)}</div>
                  <h3>${escapeHtml(formatValue(claim.value, claim.unit))}</h3>
                </div>
                <span class="badge danger">${escapeHtml(claim.evidence_class)}</span>
              </div>
              <p>${escapeHtml(claim.notes ?? "Conflicting claim kept visible for analyst review.")}</p>
              <div class="badge-row">
                <span class="badge warn">${escapeHtml(claim.figure_type)}</span>
                <span class="badge dark">${escapeHtml(claim.reporting_boundary)}</span>
                <span class="badge dark">${escapeHtml(claim.source_id)}</span>
              </div>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderWorkspace(): string {
  if (state.error) {
    return `<div class="error-box">${escapeHtml(state.error)}</div>`;
  }

  if (state.loadingDetail || !state.bundle) {
    return '<div class="loading">Loading facility intelligence, evidence, and source history...</div>';
  }

  const { detail, evidence, sources, history, templates } = state.bundle;
  const activeTab = state.activeTab;
  const tabContent =
    activeTab === "overview"
      ? renderOverview(detail, templates)
      : activeTab === "evidence"
        ? renderEvidenceTab(evidence)
        : activeTab === "sources"
          ? renderSourcesTab(sources)
          : activeTab === "history"
            ? renderHistoryTab(history)
            : renderRecordsTab(templates);

  return `
    <section class="hero-card">
      <div class="hero-top">
        <div>
          <div class="hero-kicker">AquaStat Desktop Analyst Shell</div>
          <h1>${escapeHtml(detail.facility.name)}</h1>
          <p>
            Browse facility intelligence, evidence lineage, contradiction signals, and public-record request templates
            from one local-first workspace that talks directly to the AquaStat API.
          </p>
        </div>
        <div class="status-stack">
          <div class="status-pill">${escapeHtml(detail.facility.operator)} · ${escapeHtml(detail.facility.country)}</div>
          <div class="status-pill">${escapeHtml(detail.facility.verification_status)} · ${escapeHtml(detail.record_status)}</div>
        </div>
      </div>
      ${summaryCards(detail, templates)}
    </section>

    <section class="workspace-panel">
      <div class="section-title">
        <div>
          <div class="eyebrow">Investigation workspace</div>
          <h2>Facility intelligence panels</h2>
        </div>
        <span class="muted">Current facility: ${escapeHtml(detail.facility.slug)}</span>
      </div>
      <div class="tabs">
        ${([
          ["overview", "Overview"],
          ["evidence", `Evidence (${evidence.evidence.length})`],
          ["sources", `Sources (${sources.sources.length})`],
          ["history", `History (${history.changes.length})`],
          ["records", `Public Records (${templates.templates.length})`],
        ] as const)
          .map(
            ([id, label]) =>
              `<button class="tab ${activeTab === id ? "active" : ""}" data-tab="${id}">${escapeHtml(label)}</button>`,
          )
          .join("")}
      </div>
    </section>

    <section class="workspace-panel">
      ${tabContent}
    </section>

    <section class="workspace-panel">
      <div class="section-title">
        <div>
          <div class="eyebrow">Contradiction review</div>
          <h2>Competing claims kept visible</h2>
        </div>
      </div>
      ${renderClaims(detail.contradictory_claims)}
    </section>
  `;
}

function renderSidebar(): string {
  const facilities = state.facilities;
  const selected = state.selectedFacilityId;

  return `
    <aside class="sidebar">
      <div>
        <div class="eyebrow">Connection</div>
        <h2>Desktop control surface</h2>
        <p class="sidebar-intro">
          Point this shell at a local or hosted AquaStat API, then browse facility records without a separate web frontend.
        </p>
      </div>

      <label class="base-url-box">
        <span class="field-label">API base URL</span>
        <div class="row">
          <input id="baseUrlInput" class="text-input" value="${escapeHtml(state.baseUrl)}" spellcheck="false">
          <button id="connectButton" class="button">Connect</button>
        </div>
      </label>

      <label class="search-box">
        <span class="field-label">Facility search</span>
        <input id="facilitySearch" class="search-input" placeholder="Filter by name, operator, country, or slug">
      </label>

      <div class="row">
        <button id="refreshButton" class="button secondary">Refresh Data</button>
      </div>

      <div>
        <div class="field-label">Facilities</div>
      </div>

      <div id="facilityList" class="facility-list">
        ${
          state.loadingList
            ? '<div class="loading">Loading facilities...</div>'
            : facilities.length === 0
              ? '<div class="empty">No facilities returned from this API endpoint.</div>'
              : facilities
                  .map(
                    (facility) => `
                      <button class="facility-button ${selected === facility.id ? "active" : ""}" data-facility-id="${escapeHtml(facility.id)}">
                        <div class="facility-name">${escapeHtml(facility.name)}</div>
                        <div class="facility-meta">${escapeHtml(facility.operator)} · ${escapeHtml(facility.country)} · ${escapeHtml(facility.slug)}</div>
                        <div class="badge-row">
                          <span class="badge">${escapeHtml(facility.data_quality.label)}</span>
                          <span class="badge dark">${escapeHtml(facility.operational_status)}</span>
                        </div>
                      </button>
                    `,
                  )
                  .join("")
        }
      </div>
    </aside>
  `;
}

function mountShell(): HTMLElement {
  const root = document.createElement("main");
  root.className = "app-shell";
  root.innerHTML = `
    <div class="layout">
      <div id="sidebarMount"></div>
      <div class="workspace" id="workspaceMount"></div>
    </div>
  `;
  document.body.append(root);
  return root;
}

function getWorkspaceElement(): HTMLElement {
  const element = document.getElementById("workspaceMount");
  if (!element) {
    throw new Error("workspaceMount element not found");
  }
  return element;
}

function getSidebarElement(): HTMLElement {
  const element = document.getElementById("sidebarMount");
  if (!element) {
    throw new Error("sidebarMount element not found");
  }
  return element;
}

function renderSidebarIntoDom(): void {
  getSidebarElement().innerHTML = renderSidebar();
  bindSidebarEvents();
}

function renderWorkspaceIntoDom(): void {
  getWorkspaceElement().innerHTML = renderWorkspace();
  bindWorkspaceEvents();
}

function filteredFacilities(query: string): AppState["facilities"] {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return state.facilities;
  }
  return state.facilities.filter((facility) =>
    [facility.name, facility.operator, facility.country, facility.slug].some((value) =>
      value.toLowerCase().includes(needle),
    ),
  );
}

function applySearchFilter(): void {
  const input = document.getElementById("facilitySearch") as HTMLInputElement | null;
  const list = document.getElementById("facilityList");
  if (!input || !list) {
    return;
  }
  const facilities = filteredFacilities(input.value);
  list.innerHTML =
    facilities.length === 0
      ? '<div class="empty">No facilities match this filter.</div>'
      : facilities
          .map(
            (facility) => `
              <button class="facility-button ${state.selectedFacilityId === facility.id ? "active" : ""}" data-facility-id="${escapeHtml(facility.id)}">
                <div class="facility-name">${escapeHtml(facility.name)}</div>
                <div class="facility-meta">${escapeHtml(facility.operator)} · ${escapeHtml(facility.country)} · ${escapeHtml(facility.slug)}</div>
                <div class="badge-row">
                  <span class="badge">${escapeHtml(facility.data_quality.label)}</span>
                  <span class="badge dark">${escapeHtml(facility.operational_status)}</span>
                </div>
              </button>
            `,
          )
          .join("");
  list.querySelectorAll<HTMLButtonElement>("[data-facility-id]").forEach((button) => {
    button.addEventListener("click", () => {
      void selectFacility(button.dataset.facilityId ?? fallbackFacilityId);
    });
  });
}

function bindSidebarEvents(): void {
  const connectButton = document.getElementById("connectButton");
  const refreshButton = document.getElementById("refreshButton");
  const baseUrlInput = document.getElementById("baseUrlInput") as HTMLInputElement | null;
  const searchInput = document.getElementById("facilitySearch") as HTMLInputElement | null;

  connectButton?.addEventListener("click", () => {
    const nextBaseUrl = baseUrlInput?.value.trim() || DEFAULT_BASE_URL;
    void reconnect(nextBaseUrl);
  });

  refreshButton?.addEventListener("click", () => {
    void loadFacilitiesAndSelection();
  });

  searchInput?.addEventListener("input", applySearchFilter);

  document.querySelectorAll<HTMLButtonElement>("[data-facility-id]").forEach((button) => {
    button.addEventListener("click", () => {
      void selectFacility(button.dataset.facilityId ?? fallbackFacilityId);
    });
  });
}

function bindWorkspaceEvents(): void {
  document.querySelectorAll<HTMLButtonElement>("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      const tab = button.dataset.tab as AppState["activeTab"] | undefined;
      if (!tab) {
        return;
      }
      state.activeTab = tab;
      renderWorkspaceIntoDom();
    });
  });
}

async function reconnect(baseUrl: string): Promise<void> {
  state.baseUrl = baseUrl;
  state.client = new AquaStatDesktopClient(baseUrl);
  state.error = null;
  state.loadingList = true;
  state.loadingDetail = true;
  renderSidebarIntoDom();
  renderWorkspaceIntoDom();
  await loadFacilitiesAndSelection();
}

async function loadFacilitiesAndSelection(): Promise<void> {
  try {
    state.loadingList = true;
    renderSidebarIntoDom();
    const facilities = await state.client.fetchFacilities();
    state.facilities = facilities.items;
    state.loadingList = false;
    if (!state.facilities.some((facility) => facility.id === state.selectedFacilityId)) {
      state.selectedFacilityId = state.facilities[0]?.id ?? fallbackFacilityId;
    }
    renderSidebarIntoDom();
    await loadFacilityBundle(state.selectedFacilityId);
  } catch (error) {
    state.loadingList = false;
    state.error = error instanceof Error ? error.message : "Unable to load facility list";
    state.facilities = [];
    renderSidebarIntoDom();
    renderWorkspaceIntoDom();
  }
}

async function selectFacility(facilityId: string): Promise<void> {
  state.selectedFacilityId = facilityId;
  renderSidebarIntoDom();
  await loadFacilityBundle(facilityId);
}

async function loadFacilityBundle(facilityId: string): Promise<void> {
  try {
    state.loadingDetail = true;
    state.error = null;
    renderWorkspaceIntoDom();
    const [detail, evidence, sources, history, templates] = await Promise.all([
      state.client.fetchFacility(facilityId),
      state.client.fetchFacilityEvidence(facilityId),
      state.client.fetchFacilitySources(facilityId),
      state.client.fetchFacilityHistory(facilityId),
      state.client.fetchPublicRecordTemplates(facilityId),
    ]);
    state.bundle = { detail, evidence, sources, history, templates };
  } catch (error) {
    state.bundle = null;
    state.error = error instanceof Error ? error.message : "Unable to load facility detail";
  } finally {
    state.loadingDetail = false;
    renderWorkspaceIntoDom();
  }
}

async function run(): Promise<void> {
  injectStyles();
  mountShell();
  renderSidebarIntoDom();
  renderWorkspaceIntoDom();
  await loadFacilitiesAndSelection();
}

void run();
