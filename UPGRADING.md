# Upgrading

Before upgrading AquaStat:

1. review `CHANGELOG.md`
2. regenerate OpenAPI if route contracts changed
3. verify environment variables, especially admin key hashes
4. run the full test suite
5. validate health and version endpoints after restart
