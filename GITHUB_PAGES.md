# GitHub Pages

AquaStat can publish a lightweight static documentation site directly from this repository without introducing a separate frontend stack.

## What gets published

- `site/index.html`
- `site/openapi.json`
- `site/openapi.yaml`
- mirrored operational docs from `docs/`
- `site/README.md`

## Build locally

```bash
python scripts/generate_openapi.py
python scripts/build_docs_site.py
```

Open `site/index.html` locally or serve the directory with any static file server.

## GitHub Actions workflow

The Pages deployment workflow lives at `.github/workflows/docs.yml`.

It:

1. installs Python dependencies
2. generates OpenAPI JSON and YAML
3. builds the static Pages artifact
4. validates the output contains `openapi.json` and `openapi.yaml`
5. uploads and deploys the Pages site

## Manual activation steps

1. Push the repository to GitHub.
2. Open `Settings -> Pages`.
3. Ensure GitHub Pages is configured to use GitHub Actions.
4. Run the `Docs` workflow or push to `main`.

## Resulting URLs

- `https://USERNAME.github.io/REPOSITORY/`
- `https://USERNAME.github.io/REPOSITORY/openapi.json`
- `https://USERNAME.github.io/REPOSITORY/openapi.yaml`

Replace `USERNAME` and `REPOSITORY` with the actual GitHub repository path.
