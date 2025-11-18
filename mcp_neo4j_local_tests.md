# MCP Neo4j Server – Local Validation Notes

## Environment
- Repo: `neo4j-contrib/mcp-neo4j`, subdir `servers/mcp-neo4j-cypher`
- Virtual env: `.venv` (CPython 3.12.7) created via `uv venv`
- Installed editable package + dev deps (`pip install -e '.[dev]'`)

## Fixes Applied
1. **Schema sample config**
   - CLI flag (`--sample`) and env var parsing now supports both `schema_sample_size` & legacy `sample` inputs.
   - Invalid env values no longer default to `1000`; they remain `None` (matching test expectations).
   - Unit test corrected to assert `schema_sample_size` instead of typo `config["sa"]`.

## Tests Executed
- `PYTHONPATH=src uv run pytest tests/unit`
  - Result: **53 passed** (no failures).
  - Warning: `pytest_asyncio` default loop scope deprecation (upstream issue, harmless for now).
- Integration tests (`./test.sh`) were not executed because they rely on Docker/Testcontainers; will re-run once Cloud Run images are built in an environment with Docker.

## Next Steps
- Build container (`gcloud builds submit`) and deploy MCP server to Cloud Run per PRD.
- After Cloud Run deploy, run integration tests against the deployed service (Cypher read/write, vector query) via Codex MCP client.
