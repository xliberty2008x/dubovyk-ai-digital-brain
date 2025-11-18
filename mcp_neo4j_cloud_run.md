# MCP Neo4j Server – Cloud Run Deployment

## Service Details
- **Project:** `famous-segment-470211-b5`
- **Service name:** `mcp-neo4j-cypher`
- **Region:** `us-central1`
- **URL:** `https://mcp-neo4j-cypher-858161250402.us-central1.run.app/api/mcp/`
- **Container image:** `gcr.io/famous-segment-470211-b5/mcp-neo4j-cypher:latest`
- **Runtime env vars:** `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `NEO4J_TRANSPORT=http`, `NEO4J_MCP_SERVER_PATH=/api/mcp/`, allowed hosts/origins `*`, host `0.0.0.0`, port `8080`.

## Deployment Steps
```bash
cd mcp-neo4j/servers/mcp-neo4j-cypher
# Build container
gcloud builds submit --tag gcr.io/famous-segment-470211-b5/mcp-neo4j-cypher:latest
# Deploy service
gcloud run deploy mcp-neo4j-cypher \
  --image gcr.io/famous-segment-470211-b5/mcp-neo4j-cypher:latest \
  --region us-central1 \
  --platform managed \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars \
    NEO4J_URI=neo4j+s://1a1e5411.databases.neo4j.io,\
    NEO4J_USERNAME=neo4j,\
    NEO4J_PASSWORD=<redacted>,\
    NEO4J_DATABASE=neo4j,\
    NEO4J_TRANSPORT=http,\
    NEO4J_MCP_SERVER_PATH=/api/mcp/,\
    NEO4J_MCP_SERVER_ALLOWED_HOSTS=*,\
    NEO4J_MCP_SERVER_ALLOW_ORIGINS=*,\
    NEO4J_MCP_SERVER_HOST=0.0.0.0,\
    NEO4J_MCP_SERVER_PORT=8080
```

## Verification
- `npx -y mcp-remote <URL> list-tools` → successful handshake.
- `codex exec --skip-git-repo-check --sandbox read-only 'Use mcp-neo4j/read_neo4j_cypher …'` returned `[{"id":"1719"}, {"id":"1720"}, {"id":"259"}]` from Aura DB.
- Codex CLI `/mcp` now lists `mcp-neo4j` alongside GitHub/Playwright.

## Next Steps
- Use `read_neo4j_cypher` for search/hybrid RAG, `write_neo4j_cypher` for ingestion, `get_neo4j_schema` for validation.
- Consider adding a dedicated vector-search helper (wrapper around `db.index.vector.queryNodes`) if needed.
