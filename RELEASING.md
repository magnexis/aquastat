# Releasing AquaStat

This repository is prepared for build-oriented releases without automatic package publication.

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

## What it does not publish automatically

- npm
- PyPI
- Docker Hub
- cloud hosting

This keeps external publication credential-gated and deliberate.

## Recommended release flow

1. Run CI on the release branch.
2. Update changelog and version references.
3. Create a tag such as `v1.0.0`.
4. Push the tag.
5. Review the generated GitHub workflow artifacts.
6. If desired, attach or publish built packages manually using your registry credentials.
