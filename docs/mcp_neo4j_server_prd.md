# MCP Neo4j Server PRD

## Objective
Provide a managed MCP (Model Context Protocol) server that exposes Neo4j capabilities (Cypher queries, vector search, schema introspection) to Codex/n8n agents. Server must be customizable locally, deployed to Google Cloud Run, and registered with Codex for day-to-day use.

## Scope
1. **Local Development**
   - Clone https://github.com/neo4j-contrib/mcp-neo4j (focus on `servers/mcp-neo4j-cypher`).
   - Add `.env` support aligned with our existing Neo4j creds (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`).
   - Implement/verify tools:
     - `runCypher` – execute arbitrary Cypher with parameter binding.
     - `vectorSearch` – wrap `db.index.vector.queryNodes` for dedupe agent.
     - Optional helpers (`listTopics`, `listEntities`) for metadata validation.
   - Add a CLI smoke test (`npm run test:local`) that hits the MCP endpoint locally and checks response shape.

2. **Cloud Deployment (GCP)**
   - Containerize via provided Dockerfile; build with Cloud Build (`gcloud builds submit`).
   - Deploy to Cloud Run (`gcloud run deploy mcp-neo4j-cypher --source . --region us-central1 --platform managed --port 8080`).
   - Inject secrets via `--set-secrets` (Neo4j URI/user/password stored in Secret Manager).
   - Enforce HTTPS, enable Cloud Logging, and configure concurrency/autoscaling (default OK for v1).

3. **Codex Integration + Testing**
   - Register the MCP server in Codex (`mcp_server_n8n.json`) pointing to the Cloud Run URL.
   - Document usage in `.skills/n8n_skill` (examples: `mcp neo4j runCypher "MATCH ..."`).
   - End-to-end tests: issue Cypher + vector queries through Codex, ensure error handling surfaces cleanly.

## Deliverables
- Customized MCP server repo (branch or fork) with env support + optional tools.
- Cloud Run deployment script/commands + live service URL.
- Codex configuration referencing the MCP Neo4j server.
- Documentation updates (AGENTS.md entry + this PRD) describing setup/maintenance.

## Risks & Assumptions
- Aura credentials remain stable; rotating secrets requires redeploy.
- If private access is required, Cloud Run IAM or VPC connectors must be configured in phase 2.
- Cold starts may add latency; adjust min instances later if needed.
