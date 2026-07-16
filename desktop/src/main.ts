import { AquaStatDesktopClient } from "./api.js";
import type { FieldEvidence, PublicRecordTemplateResponse } from "./types.js";

const client = new AquaStatDesktopClient("http://127.0.0.1:8080");
const facilityId = "fac_syn_ashburn";

function injectStyles(): void {
  const style = document.createElement("style");
  style.textContent = `
    :root {
      color-scheme: light;
      --bg: #f4fbfc;
      --panel: #ffffff;
      --panel-alt: #eef8f7;
      --border: #c9e3df;
      --text: #153037;
      --muted: #5d7c83;
      --brand: #0d8b8f;
      --brand-deep: #0c5f66;
      --warn: #b15e16;
      --danger: #b83f3f;
      --shadow: 0 18px 50px rgba(15, 68, 79, 0.12);
      font-family: "Segoe UI", Inter, system-ui, sans-serif;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(13, 139, 143, 0.18), transparent 30%),
        linear-gradient(180deg, #f7fcfc 0%, var(--bg) 100%);
      color: var(--text);
    }

    .shell {
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px;
    }

    .hero {
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-start;
      margin-bottom: 24px;
    }

    .hero-card,
    .panel {
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--border);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }

    .hero-card {
      flex: 1;
      padding: 28px;
    }

    .hero h1 {
      margin: 0 0 10px;
      font-size: 34px;
      line-height: 1.1;
    }

    .hero p {
      margin: 0;
      color: var(--muted);
      max-width: 62ch;
    }

    .status-chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 8px 12px;
      background: rgba(13, 139, 143, 0.1);
      color: var(--brand-deep);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      margin-bottom: 16px;
    }

    .summary-grid,
    .insight-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
      margin-top: 24px;
    }

    .stat {
      padding: 18px;
      background: var(--panel-alt);
      border-radius: 18px;
      border: 1px solid var(--border);
    }

    .stat-label {
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 10px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .stat-value {
      font-size: 28px;
      font-weight: 700;
    }

    .layout {
      display: grid;
      grid-template-columns: 1.35fr 0.95fr;
      gap: 20px;
    }

    .panel {
      padding: 24px;
    }

    .panel h2 {
      margin: 0 0 6px;
      font-size: 22px;
    }

    .panel-intro {
      margin: 0 0 18px;
      color: var(--muted);
      line-height: 1.5;
    }

    .evidence-card,
    .template-card,
    .claim-card {
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
      background: #fff;
      margin-bottom: 14px;
    }

    .badge-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 12px 0 0;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 700;
      background: #edf7f7;
      color: var(--brand-deep);
    }

    .badge.warn {
      background: #fff0df;
      color: var(--warn);
    }

    .badge.danger {
      background: #fdeaea;
      color: var(--danger);
    }

    dl.meta {
      display: grid;
      grid-template-columns: 160px 1fr;
      gap: 10px 14px;
      margin: 18px 0 0;
    }

    dt {
      color: var(--muted);
      font-weight: 600;
    }

    dd {
      margin: 0;
      font-weight: 600;
    }

    ul {
      margin: 10px 0 0;
      padding-left: 20px;
      color: var(--text);
    }

    li + li {
      margin-top: 6px;
    }

    .loading,
    .error {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 260px;
      border: 1px dashed var(--border);
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.7);
      color: var(--muted);
      font-size: 16px;
      text-align: center;
      padding: 20px;
    }

    .error {
      color: var(--danger);
      border-color: rgba(184, 63, 63, 0.3);
      background: rgba(253, 234, 234, 0.8);
    }

    @media (max-width: 980px) {
      .hero,
      .layout {
        grid-template-columns: 1fr;
        display: grid;
      }

      .summary-grid,
      .insight-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 640px) {
      .shell {
        padding: 18px;
      }

      .summary-grid,
      .insight-grid {
        grid-template-columns: 1fr;
      }

      dl.meta {
        grid-template-columns: 1fr;
      }
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

function renderEvidence(evidence: FieldEvidence | null): string {
  if (!evidence) {
    return `
      <div class="evidence-card">
        <h3>No primary water figure</h3>
        <p class="panel-intro">This facility record exists, but AquaStat has not promoted a single primary figure yet.</p>
      </div>
    `;
  }

  const value = evidence.value ?? "unknown";
  const unit = evidence.unit ? ` ${escapeHtml(evidence.unit)}` : "";
  return `
    <div class="evidence-card">
      <h3>${escapeHtml(evidence.field)}</h3>
      <div class="stat-value">${escapeHtml(String(value))}${unit}</div>
      <div class="badge-row">
        <span class="badge">${escapeHtml(evidence.evidence_class)}</span>
        <span class="badge">${escapeHtml(evidence.figure_type)}</span>
        <span class="badge">${escapeHtml(evidence.reporting_boundary)}</span>
      </div>
      <dl class="meta">
        <dt>Confidence</dt>
        <dd>${Math.round(evidence.confidence * 100)}%</dd>
        <dt>Status</dt>
        <dd>${escapeHtml(evidence.value_status)}</dd>
        <dt>Source</dt>
        <dd>${escapeHtml(evidence.source_id)}</dd>
      </dl>
      ${evidence.notes ? `<p class="panel-intro">${escapeHtml(evidence.notes)}</p>` : ""}
    </div>
  `;
}

function renderTemplateList(templates: PublicRecordTemplateResponse): string {
  return templates.templates
    .slice(0, 2)
    .map(
      (template) => `
        <article class="template-card">
          <h3>${escapeHtml(template.authority)}</h3>
          <p class="panel-intro">${escapeHtml(template.summary)}</p>
          <div class="badge-row">
            <span class="badge">${escapeHtml(template.facility_id)}</span>
            <span class="badge">${template.requested_records.length} requested records</span>
          </div>
          <ul>
            ${template.requested_records.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        </article>
      `,
    )
    .join("");
}

function renderClaims(claims: FieldEvidence[]): string {
  if (claims.length === 0) {
    return `
      <div class="claim-card">
        <strong>No contradictory claims detected.</strong>
      </div>
    `;
  }

  return claims
    .map(
      (claim) => `
        <article class="claim-card">
          <strong>${escapeHtml(claim.field)}</strong>
          <div class="badge-row">
            <span class="badge danger">${escapeHtml(claim.evidence_class)}</span>
            <span class="badge warn">${escapeHtml(claim.figure_type)}</span>
          </div>
          <p class="panel-intro">${escapeHtml(String(claim.value ?? "unknown"))}${claim.unit ? ` ${escapeHtml(claim.unit)}` : ""}</p>
        </article>
      `,
    )
    .join("");
}

async function run(): Promise<void> {
  injectStyles();

  const root = document.createElement("main");
  root.className = "shell";
  root.innerHTML = `<div class="loading">Loading AquaStat desktop facility intelligence...</div>`;
  document.body.append(root);

  try {
    const [facility, templates] = await Promise.all([
      client.fetchFacility(facilityId),
      client.fetchPublicRecordTemplates(facilityId),
    ]);

    root.innerHTML = `
      <section class="hero">
        <div class="hero-card">
          <div class="status-chip">Desktop Control Surface</div>
          <h1>${escapeHtml(facility.facility.name)}</h1>
          <p>
            Local-first AquaStat desktop workspace for reviewing facility evidence, contradiction risk,
            and public-record request pathways before a water figure is trusted or reused.
          </p>
          <div class="summary-grid">
            <article class="stat">
              <div class="stat-label">Operator</div>
              <div class="stat-value">${escapeHtml(facility.facility.operator)}</div>
            </article>
            <article class="stat">
              <div class="stat-label">Data Quality</div>
              <div class="stat-value">${facility.facility.data_quality.score.toFixed(2)}</div>
            </article>
            <article class="stat">
              <div class="stat-label">Evidence Class</div>
              <div class="stat-value">${escapeHtml(facility.primary_water_figure?.evidence_class ?? "Level U")}</div>
            </article>
            <article class="stat">
              <div class="stat-label">Contradictions</div>
              <div class="stat-value">${facility.contradictory_claims.length}</div>
            </article>
          </div>
        </div>
      </section>

      <section class="layout">
        <article class="panel">
          <h2>Primary Water Figure</h2>
          <p class="panel-intro">
            AquaStat promotes only one primary figure at a time and keeps conflicting claims visible.
          </p>
          ${renderEvidence(facility.primary_water_figure)}
          <div class="insight-grid">
            <article class="stat">
              <div class="stat-label">Facility Type</div>
              <div class="stat-value">${escapeHtml(facility.facility.facility_type)}</div>
            </article>
            <article class="stat">
              <div class="stat-label">Operational Status</div>
              <div class="stat-value">${escapeHtml(facility.facility.operational_status)}</div>
            </article>
            <article class="stat">
              <div class="stat-label">Country</div>
              <div class="stat-value">${escapeHtml(facility.facility.country)}</div>
            </article>
            <article class="stat">
              <div class="stat-label">Known Holders</div>
              <div class="stat-value">${templates.known_holders.length}</div>
            </article>
          </div>
        </article>

        <article class="panel">
          <h2>Public Record Retrieval</h2>
          <p class="panel-intro">
            Suggested authorities and ready-to-edit request templates for lawful follow-up.
          </p>
          ${renderTemplateList(templates)}
        </article>
      </section>

      <section class="layout" style="margin-top: 20px;">
        <article class="panel">
          <h2>Contradictory Claims</h2>
          <p class="panel-intro">
            Competing figures stay visible so reviewers can challenge green claims before publishing them.
          </p>
          ${renderClaims(facility.contradictory_claims)}
        </article>

        <article class="panel">
          <h2>Why This Desktop Shell Exists</h2>
          <p class="panel-intro">
            The desktop package is intentionally local-first. It gives analysts a typed surface for
            reviewing evidence, sources, and retrieval pathways without needing a separate web product.
          </p>
          <ul>
            <li>Strict TypeScript source with a typed AquaStat client.</li>
            <li>Facility detail and public-record workflows wired into real API endpoints.</li>
            <li>Small enough to evolve into Electron, Tauri, or a packaged internal desktop app.</li>
          </ul>
        </article>
      </section>
    `;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown desktop startup error";
    root.innerHTML = `
      <div class="error">
        AquaStat desktop could not load local data.<br><br>
        ${escapeHtml(message)}<br><br>
        Start the API locally at http://127.0.0.1:8080 and refresh the page.
      </div>
    `;
  }
}

void run();
