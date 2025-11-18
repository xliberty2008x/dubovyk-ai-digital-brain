# Search & Retrieval Playbook

This guide documents the primary question types our agents must answer and the Cypher/vector strategies that support them.

## 1. Duplicate Detection
- **Goal:** Given a new Telegram post, find near-identical historical articles.
- **Approach:** Embed incoming text with Gemini (3,072 dims) → `CALL db.index.vector.queryNodes('article_embedding_idx', $limit, $embedding)`.
- **Filters:** Exclude current `telegram_message_id`, require `score >= $min_score` (default 0.9).
- **Usage:** Deduplication agent, editor alerts, automatic `SIMILAR_TO` edges.

## 2. Topic/Tag Retrieval
- **Question:** “Give me 10 recent posts about fine-tuning.”
- **Cypher:**
```cypher
MATCH (a:Article)
WHERE any(topic IN a.topics WHERE topic = $topic)
RETURN a.title, a.telegram_url, a.summary
ORDER BY coalesce(a.ingested_at, datetime()) DESC
LIMIT 10;
```
- **Notes:** topics come from `METADATA_CONTRACT.md`; fallback to text search when topic not found.

## 3. Entity-Centric Queries
- **Question:** “What has been said about OpenAI in the last 14 days?”
- **Cypher:**
```cypher
MATCH (a:Article)-[:MENTIONS]->(e:Entity {name: $entity})
WHERE a.published_at >= datetime() - duration({days: $days})
RETURN a.title, a.telegram_url, a.summary
ORDER BY a.published_at DESC;
```
- **Fallback:** when `Entity` node absent, match against `a.entities` array or run embedding search seeded with entity description.

## 4. CTA/Link Tracking
- **Question:** “Which posts drove traffic to wan.video?”
- **Cypher:**
```cypher
MATCH (a:Article)
WHERE a.cta_link CONTAINS $domain
RETURN a.title, a.cta_text, a.telegram_url;
```
- **Use Cases:** marketing attribution, follow-up workflows.

## 5. Digest/Timeline Queries
- **Question:** “List last week’s articles grouped by day + topic.”
```cypher
MATCH (a:Article)
WHERE a.published_at >= datetime() - duration({days: 7})
UNWIND a.topics AS topic
RETURN date(a.published_at) AS day, topic, collect({title: a.title, url: a.telegram_url}) AS posts
ORDER BY day DESC;
```
- **Consumers:** Summarization agent, weekly newsletter builder.

## 6. Free-Form Semantic Search
- **When to use:** Users ask questions not covered by strict filters (e.g., “What’s new with multimodal video editing and lip sync?”).
- **Approach:**
  1. Embed the user query with Gemini.
  2. Run `db.index.vector.queryNodes` to get top-N candidates.
  3. Re-rank or filter by `topics`, `entities`, or `published_at` thresholds.
- **Optional:** feed hits into LLM for synthesis.

## 7. Hybrid RAG (Metadata + Vector)
- **Goal:** Combine structured filters (topics, entities, CTAs) with semantic similarity, then craft grounded answers via LLM.
- **Pipeline:**
  1. LLM-based query analyzer converts the user request into a JSON plan (e.g., desired topics, entity names, time range, free-text reminder).
  2. Apply metadata filters first (Cypher `WHERE` clauses). Example output from analyzer:
     ```json
     { "topics": ["fine_tuning"], "entity": "OpenAI", "days": 30, "query": "fine-tuning updates" }
     ```
  3. For the remaining `query` text, run vector search to surface semantically relevant articles.
  4. Merge/filter the union (structured hits ∩ vector hits or top-N union with dedupe).
  5. Pass the final set (title, summary, Telegram URL, metadata) into an LLM to produce the response while citing each source.
- **LLM Instructions:**
  - Return both the structured Cypher fragment and the free-text query.
  - Stick to canonical topic names from `METADATA_CONTRACT.md`.
  - Default date range to 30 days when absent.
  - Always provide at least one structured filter (topic/entity) before falling back to pure vector search.
- **Usage:** user-facing assistants (“Find long-form explainers about fine-tuning WAN 2.5”), digests, analyst workflows.

## 8. Similarity Edge Maintenance
- **Purpose:** Refresh `SIMILAR_TO` relationships and scores.
- **Method:** Schedule job that iterates through active articles, re-runs vector search, and updates `SIMILAR_TO` edges where score ≥ threshold. Also decay `last_checked` for auditing.

## Implementation Notes
- Always return Telegram URLs plus `title`/`summary` to keep responses human-readable.
- Limit result sets (default 10) to avoid long agent responses.
- For multilingual/English searches, rely on embeddings rather than keyword matching.

Keep this playbook updated as new question types emerge so Prompt Builder + downstream agents know which fields they must populate.
