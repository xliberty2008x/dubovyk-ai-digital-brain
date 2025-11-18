# Agent Workbench

Refer to [PRD.md](./PRD.md) for the full specification. The snapshot below captures the **/init** state of the project so newcomers can see where each agent stands.

## /init Snapshot

| Agent | Purpose | State |
| --- | --- | --- |
| Ingestion Orchestrator | Main n8n workflow that sequences every downstream step from Telegram trigger to Neo4j writes. | In Progress |
| Classification Agent | Tags article topics, urgency, and routes follow-up actions. | Planned |
| Extraction Agent | Performs NER/relation extraction before persisting nodes/edges. | Planned |
| Embedding Agent | Chunks content, produces vectors, and stores embeddings in Neo4j. | In Progress |
| Deduplication Agent | Runs vector similarity search, creates `SIMILAR_TO` edges, alerts editors. | In Progress |
| Enrichment Agent | Pulls external signals (company info, GitHub links) and augments the graph. | Planned |
| Summarization/Digest Agent | Generates scheduled digests (weekly, topical). | Planned |
| Question-Answering Agent | Handles retrieval workflows for OpenAI news, VLM projects, etc. | Planned |
| Maintenance Agent | Re-scores similarity edges, recomputes centroids, audits schema health. | Planned |

Update this file as implementation progresses (e.g., `In Progress`, `Live`, `On Hold`) so the roster mirrors reality while PRD.md continues to host the detailed requirements.

## Skill Usage Rule

Before an agent starts any task, it must check the `.skills` registry to see whether a reusable skill exists for that task. If a relevant skill is found, invoke it; otherwise continue with the regular flow and log the gap for future skill creation.

## Knowledge Graph References

- [Graph Schema](knowledge_graph/GRAPH_SCHEMA.md) — nodes, properties, and relationships (`Article`, `Topic`, `Entity`, `Channel`, `SIMILAR_TO`, etc.).
- [Metadata Extraction Contract](knowledge_graph/METADATA_CONTRACT.md) — JSON fields LLMs must return (`title`, `summary`, canonical topics, entity types, CTA data).
- [Search & Retrieval Playbook](knowledge_graph/SEARCH_PLAYBOOK.md) — question templates (duplicate detection, topic/entity queries, CTA tracking) plus Cypher/vector approaches.
- [MCP Neo4j Server PRD](docs/mcp_neo4j_server_prd.md) — plan for customizing the MCP server, deploying it to GCP Cloud Run, and integrating it with Codex.
- [MCP Neo4j Local Tests](docs/mcp_neo4j_local_tests.md) — notes on local fixes and unit-test coverage before Cloud Run deployment.
- [MCP Neo4j Cloud Run](docs/mcp_neo4j_cloud_run.md) — live deployment details (Cloud Run URL, env vars, verification commands) confirming the MCP server is ready for Codex.

These docs define how we populate the graph so agents can answer requests like “Which posts mention finetuning this week?”, “Show duplicates for message 1720”, or “List CTAs pointing to wan.video”. Keep them in sync as the schema evolves.
