# Releasing AquaStat

This repository is prepared for build-oriented releases and conditional package publication.

## Versioning

Use semantic version tags such as `v1.0.0`.

Update:

- `CHANGELOG.md`
- package versions in `pyproject.toml`, `js-sdk/package.json`, and `desktop/package.json` when applicable

## Release workflow

The release workflow lives at `.github/workflows/release.yml`.

It can be triggered by:

- `workflow_dispatch`
- pushing a Git tag that matches `v*`

## What it builds

- Python SDK distribution files
- JavaScript SDK distribution files
- desktop TypeScript build artifacts
- OpenAPI JSON and YAML
- static documentation artifact

## Conditional publication

The release workflow can publish automatically when registry credentials are configured:

- `PYPI_API_TOKEN` for `aquastat-sdk` on PyPI
- `NPM_TOKEN` for `@aquastat/sdk` on npm

If those secrets are missing, the workflow still builds release artifacts and attaches the OpenAPI files to the GitHub release without failing.

## Recommended release flow

1. Run CI on the release branch.
2. Update changelog and version references.
3. Create a tag such as `v1.0.0`.
4. Push the tag.
5. Review the generated GitHub workflow artifacts.
6. If `PYPI_API_TOKEN` and/or `NPM_TOKEN` are configured in GitHub Actions secrets, the tag-triggered release workflow will publish the matching SDK packages automatically.
7. Otherwise, publish manually using the built artifacts in the GitHub release or workflow outputs.
