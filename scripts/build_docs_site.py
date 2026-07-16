from __future__ import annotations

import html
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
OPENAPI_DIR = ROOT / "openapi"
SITE_DIR = ROOT / "site"

DOC_LINKS = [
    ("Implementation Audit", "docs/implementation-audit.md"),
    ("Railway Deployment", "docs/deployment-railway.md"),
    ("Authentication", "docs/authentication.md"),
    ("Rate Limits", "docs/rate-limits.md"),
    ("Errors", "docs/errors.md"),
    ("Data Sources", "docs/data-sources.md"),
    ("Distribution", "docs/distribution.md"),
    ("RapidAPI Listing", "docs/rapidapi-listing.md"),
]


def _copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def build_index() -> str:
    cards = "\n".join(
        f'<li><a href="{href}">{html.escape(label)}</a></li>'
        for label, href in DOC_LINKS
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AquaStat Documentation</title>
  <style>
    :root {{
      --bg: #f5f8f8;
      --panel: #ffffff;
      --ink: #16333a;
      --muted: #5d7276;
      --line: #d8e2e1;
      --accent: #0f766e;
      --accent-soft: #dff2ef;
      --code: #0f172a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "IBM Plex Sans", sans-serif;
      background: linear-gradient(180deg, #eef5f4 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 48px 20px 72px;
      display: grid;
      gap: 24px;
    }}
    .hero, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 24px;
      box-shadow: 0 8px 30px rgba(15, 23, 42, 0.04);
    }}
    .hero {{
      display: grid;
      gap: 12px;
      background:
        radial-gradient(circle at top right, rgba(15, 118, 110, 0.12), transparent 28%),
        var(--panel);
    }}
    h1, h2 {{ margin: 0; }}
    p {{ margin: 0; line-height: 1.6; color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      background: #fbfdfd;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
    a:hover {{ text-decoration: underline; }}
    code {{
      font-family: "Cascadia Code", "Consolas", monospace;
      background: #ecf5f4;
      padding: 0.15rem 0.35rem;
      border-radius: 6px;
      color: var(--code);
    }}
    ul {{
      margin: 0;
      padding-left: 1.1rem;
      color: var(--muted);
      display: grid;
      gap: 0.5rem;
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>AquaStat Documentation</h1>
      <p>AquaStat is a developer-facing API for estimating direct and indirect data-center water impact, preserving provenance, confidence, and evidence classifications in every modeled response.</p>
      <p>Primary API docs live on the backend at <code>/docs</code>. This static site mirrors the operational guides, ships the OpenAPI files for client imports, and gives GitHub-hosted projects a stable documentation surface without a separate marketing site.</p>
    </section>

    <section class="grid">
      <article class="card">
        <h2>Quick Links</h2>
        <ul>
          <li><a href="./openapi.json">Download OpenAPI JSON</a></li>
          <li><a href="./openapi.yaml">Download OpenAPI YAML</a></li>
          <li><a href="./docs/deployment-railway.md">Railway deployment guide</a></li>
          <li><a href="./docs/authentication.md">Authentication guide</a></li>
        </ul>
      </article>
      <article class="card">
        <h2>Developer Setup</h2>
        <ul>
          <li><code>pip install -e .[dev]</code></li>
          <li><code>python scripts/generate_openapi.py</code></li>
          <li><code>python scripts/build_docs_site.py</code></li>
          <li><code>uvicorn app.main:app --host 0.0.0.0 --port 8080</code></li>
        </ul>
      </article>
      <article class="card">
        <h2>What This Site Covers</h2>
        <ul>
          <li>API auth, errors, and rate limits</li>
          <li>Deployment to Railway and self-hosted targets</li>
          <li>Data-source attribution and scientific caveats</li>
          <li>Distribution guidance for GitHub, Postman, and API marketplaces</li>
        </ul>
      </article>
    </section>

    <section class="panel">
      <h2>Repository Guides</h2>
      <ul>
        {cards}
      </ul>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "docs").mkdir(parents=True, exist_ok=True)

    for src in DOCS_DIR.glob("*.md"):
        _copy_file(src, SITE_DIR / "docs" / src.name)

    for src in OPENAPI_DIR.glob("openapi.*"):
        _copy_file(src, SITE_DIR / src.name)

    if (ROOT / "README.md").exists():
        _copy_file(ROOT / "README.md", SITE_DIR / "README.md")

    metadata = {
        "generatedFrom": "scripts/build_docs_site.py",
        "openapi": ["openapi.json", "openapi.yaml"],
        "docs": [href for _, href in DOC_LINKS],
    }
    (SITE_DIR / "site-manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (SITE_DIR / "index.html").write_text(build_index(), encoding="utf-8")


if __name__ == "__main__":
    main()
