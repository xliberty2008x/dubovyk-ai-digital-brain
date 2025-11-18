# Agentic Knowledge Graph PRD

## 1. Context
n8n currently ingests Telegram articles and performs copywriting tasks. We want to extend this system with an agentic knowledge graph backend powered by Neo4j so that every new article is vectorized, contextualized, and becomes part of a living memory. Inspiration: [Agentic Knowledge Graph Construction with Neo4j](https://shilpathota.medium.com/agentic-knowledge-graph-construction-with-neo4j-aadda43b71d9).

## 2. Goals & Success Metrics
- **Holistic memory:** every Telegram article ingested once, linked to topics, entities, and prior knowledge.
- **Actionable agents:** orchestrated agents (running in n8n) can make routing decisions, triage duplicates, and answer editorial questions.
- **Question coverage:** system can reliably answer the defined queries (weekly digest, OpenAI news, VLM projects, image-edit models) within seconds.
- **Operator awareness:** editors get alerts when new articles duplicate or contradict recent posts.
- **Operational metrics:** ≥95% of articles processed automatically; duplicate detection precision ≥0.9; answer accuracy measured via spot checks.

### Non-Goals
- Replacing the existing copywriting flow entirely.
- Providing external-facing APIs beyond n8n workflow triggers (phase 1 is internal automation).

## 3. Users & User Needs
- **Content editors:** need curated digests, duplicate warnings, and quick references with Telegram links.
- **Automation agents (n8n):** need structured storage for memory and reasoning, plus hooks to store provenance.
- **Knowledge ops/maintainers:** need visibility into graph health, schema evolution, and ability to adjust agent behavior.

## 4. Key Questions the System Must Answer
1. Digest of articles from the past week.
2. Recent news about OpenAI.
3. Cool projects related to VLMs.
4. List (with Telegram links) of news about image-edit models.
5. Trending topics compared to last month.
6. Which creators/companies dominate multimodal AI coverage this week.
7. Highlight contradictions or updates to previous coverage on a topic.
8. What tasks or follow-ups remain open for a research drop.

## 5. High-Level Architecture
1. **Source:** Telegram channel → n8n trigger node.
2. **Pre-processing agent:** cleans text, extracts metadata, optionally chunks content.
3. **Embedding service:** OpenAI / Vertex / local model to produce vector per chunk and per article.
4. **Neo4j backend:**
   - Nodes: Article, Topic, Entity (Person/Org), Project, Event, Insight, Task.
   - Relationships: MENTIONS, DESCRIBES, SIMILAR_TO, REFUTES, FOLLOWS_UP, SOURCE_OF, HAS_TASK.
   - Vector indexes for `Article.embedding` (and optionally chunk embeddings).
5. **Agent swarm (n8n-hosted):** orchestrating nodes calling LLM functions for classification, extraction, dedup, question-answering, maintenance.
6. **Surfaces:** Telegram bot, dashboards, internal notifications.

```
Telegram → n8n Flow → {Classification Agent → Extraction Agent → Embedding Service} → Neo4j
                                                      ↓
                                          Dedup Agent / Alerting
                                                      ↓
                                           QA Agents & Summaries
```

## 6. Data Model Details
- **Article**: `id`, `title`, `body`, `telegram_message_id`, `telegram_url`, `published_at`, `source_channel`, `status`, `embedding`.
- **Topic**: `name`, `category`, `vector` (optional centroid), `created_at`.
- **Entity (Person/Org/Product)**: `name`, `type`, `aliases`, `created_at`.
- **Project**: `name`, `owner`, `description`, `launch_date`.
- **Event**: `name`, `date`, `location`, `summary`.
- **Task/Action**: `description`, `status`, `assignee`, `due_at`, `origin_article`.

**Relationships**
- `(:Article)-[:MENTIONS]->(:Entity)`
- `(:Article)-[:ABOUT]->(:Topic)`
- `(:Article)-[:SIMILAR_TO {score}]->(:Article)`
- `(:Article)-[:REFUTES|UPDATES]->(:Article)`
- `(:Article)-[:FEATURES]->(:Project)`
- `(:Article)-[:TRIGGERS]->(:Task)`
- `(:Task)-[:ASSIGNED_TO]->(:Entity)` (when entity is person/editor)

**Indexes & Constraints**
- Uniqueness on `Article.telegram_message_id`.
- Vector index: `CREATE VECTOR INDEX article_embedding IF NOT EXISTS FOR (a:Article) ON (a.embedding) OPTIONS {indexConfig: {vector.dimensions: 1536, vector.similarity_function: 'cosine'}}` (update dims per model).
- Text index on `Topic.name`, `Entity.name` for lexical filters.

## 7. Agent Responsibilities
1. **Ingestion Orchestrator** (n8n main flow): sequences the downstream agents.
2. **Classification Agent:** tags topics, categories, priority.
3. **Extraction Agent:** runs NER/relation extraction; writes nodes/edges to Neo4j.
4. **Embedding Agent:** chunks content, calls embedding API, stores vectors.
5. **Deduplication Agent:** queries Neo4j vector index, scores similarity, creates `SIMILAR_TO` edges, and notifies editors if `score > threshold` and article age < N days.
6. **Enrichment Agent:** attaches external data (company info, GitHub links) and updates nodes.
7. **Summarization/Digest Agent:** scheduled job to compile weekly digests using Neo4j queries + LLM summarizer.
8. **Question-Answering Agent:** takes prompts (e.g., "recent OpenAI news"), issues Cypher/vector hybrid queries, and formats responses with Telegram links.
9. **Maintenance Agent:** cleans stale nodes, recalculates topic centroids, audits schema changes.

## 8. Workflow Deep Dive
### 8.1 Article Ingestion
1. Trigger: n8n Telegram node receives message.
2. Normalize: strip formatting, store raw payload in storage (S3 or Supabase) for auditing.
3. Metadata agent infers language, sentiment, type (news, project, opinion).
4. Classification agent tags topics and determines if follow-up actions needed.
5. Embedding agent chunks (~500 tokens) & gets embeddings.
6. Neo4j write:
   - Create `Article` node with metadata + embedding.
   - Merge `Topic`, `Entity`, `Project` nodes.
   - Create relationships.
7. Dedup agent queries vector index (`CALL db.index.vector.queryNodes('article_embedding', 3, article.embedding)`), compares scores.
8. If duplicate found: mark `status='duplicate_flagged'`, send n8n notification with `similar_article.telegram_url`.
9. QA agent (if necessary) initiates follow-up tasks.

### 8.2 Answering Required Questions
- **Past Week Digest:** Cypher filtering on `published_at >= datetime() - duration('P7D')`, group by topic, feed into summarizer agent; output text + bullet list with Telegram links.
- **Recent OpenAI News:** Query `MATCH (a:Article)-[:MENTIONS]->(o:Entity {name:'OpenAI'}) WHERE a.published_at > datetime() - duration('P14D') RETURN a`. If no direct match, use vector search seeded with "OpenAI news" embedding.
- **Cool VLM Projects:** Query `MATCH (a:Article)-[:FEATURES]->(p:Project)-[:ABOUT]->(:Topic {name:'VLM'})` or vector filter using keywords "vision-language"; ranking by recency + engagement metrics stored on Article nodes.
- **Image-Edit Models:** Query topics/entities containing "image editing"; results list `a.title`, `a.telegram_url`.
- **Trending Topics:** Count article relationships grouped by `Topic` for time windows and compare.
- **Creators Dominance:** Run Neo4j GDS centrality on `(:Entity {type:'Person'|'Org'})` nodes connected to recent `Article` nodes.
- **Contradictions:** Use `REFUTES` edges created by reasoning agents to highlight conflicts.
- **Open Tasks:** Query `(:Task {status:'open'})-[:TRIGGERED_BY]->(:Article)` to remind editors.

Each answering workflow is an n8n sub-workflow: Cypher query → optional vector retrieval → LLM summarization → response channel (Telegram, email, dashboard).

### 8.3 Maintenance & Monitoring
- Daily job to re-score similarity edges and close stale duplicates.
- Weekly job to recompute topic centroids using article embeddings.
- Metrics logged back into Neo4j or external observability (n8n analytics / Grafana): ingestion time, duplicate rate, agent success/failure counts.

## 9. Integrations & Deployment Notes
- **n8n as host:** use HTTP Request node or custom function node to interact with Neo4j Bolt HTTP API. Credentials stored in n8n credentials vault.
- **Embedding providers:** start with OpenAI text-embedding-3-large; keep abstraction so we can swap to local models if needed.
- **Neo4j Aura or self-hosted:** ensure APOC & GDS available for advanced querying. Configure vector index and concurrency tuned for ~hundreds of articles/day.
- **Security:** store secrets in n8n, restrict Neo4j to VPN/IP allowlist, enable query parameterization.
- **Testing:** create staging Neo4j db + n8n workspace mirroring production flows.

## 10. Roadmap
1. **Phase 0 (Week 0):** finalize schema, stand up Neo4j instance, connect from n8n.
2. **Phase 1 (Weeks 1-2):** build ingestion workflow + basic agents (classification, embedding, dedup alerting).
3. **Phase 2 (Weeks 3-4):** implement answering workflows for the four priority questions.
4. **Phase 3 (Weeks 5-6):** add trend analytics, maintenance agents, dashboards.
5. **Phase 4:** expand to bi-directional automations (auto-publishing, knowledge insights to other systems).

## 11. Open Questions / Decisions Needed
- Final embedding provider and dimensionality? (impacts vector index config)
- How to store raw article text for compliance (S3 vs. database)?
- Should duplicates be merged or just cross-linked? merge strategy TBD.
- What SLA/latency do editors expect for QA responses?
- Do we require multilingual support from day one?
- How will we monitor LLM/agent hallucinations—human-in-loop workflow needed?

## 12. Appendices
- Reference inspiration article linked above.
- Potential libraries: LangChain (agent orchestration), LlamaIndex (graph RAG), Neo4j GDS.
