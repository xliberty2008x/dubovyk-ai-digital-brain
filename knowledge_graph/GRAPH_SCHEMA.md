# Knowledge Graph Schema

This repository treats every Telegram post we ingest as an `Article` node with supporting `Topic` and `Entity` references. This document captures the contract so n8n workflows, Python tools, and Neo4j stay consistent.

## Nodes

### `Article`
| Property | Type | Description |
| --- | --- | --- |
| `telegram_message_id` | string (PK) | Unique ID from Telegram. Constraint + lookup key. |
| `channel_id` | string | Telegram channel numeric ID (e.g., `-100…`). |
| `channel_username` | string | Public handle like `dubovyk_ai` (optional). |
| `telegram_url` | string | Canonical `https://t.me/<username>/<message_id>` permalink. |
| `raw_text` | string | Full text/caption used for embeddings + enrichment. |
| `title` | string | Headline-style title extracted by LLM. |
| `summary` | string | Multi-sentence Ukrainian summary. |
| `topics` | string[] | Canonical topic labels (see Metadata Contract). |
| `tags` | string[] | Free-form tags (hashtags, keywords). |
| `entities` | map[] | JSON array of `{name, entityType}` for quick filtering. |
| `cta_text` | string | Call-to-action copy if present. |
| `cta_link` | string | URL referenced in CTA. |
| `media_type` | string | `photo`, `video`, `document`, `audio`, etc. |
| `media_file_id` | string | Telegram file id for reuse/downloads. |
| `embedding` | float[3072] | Gemini embedding stored for vector search. |
| `status` | string | `ingested`, `pending_decision`, etc. |
| `ingested_at` | datetime | Timestamp when the KG workflow finished. |
| `published_at` | datetime | Telegram publish time if available. |

Indexes/constraints:
- `CONSTRAINT article_telegram_unique IF NOT EXISTS FOR (a:Article) REQUIRE a.telegram_message_id IS UNIQUE`
- `VECTOR INDEX article_embedding_idx FOR (a:Article) ON (a.embedding)` using cosine similarity and 3,072 dims.

### `Topic`
| Property | Type | Description |
| --- | --- | --- |
| `name` | string (PK) | Canonical topic label (lowercase). |
| `category` | string | Optional grouping (`ai_research`, `product`, etc.). |

### `Entity`
| Property | Type | Description |
| --- | --- | --- |
| `name` | string (PK) | Entity canonical name (company, person, project). |
| `entity_type` | string | One of `person`, `company`, `project`, `technology`, `other`. |
| `aliases` | string[] | Optional alternate spellings. |

### `Channel`
| Property | Type | Description |
| --- | --- | --- |
| `id` | string (PK) | Telegram channel id. |
| `username` | string | Public handle. |
| `title` | string | Display name. |

## Relationships

| Relationship | Direction | Description |
| --- | --- | --- |
| `(:Channel)-[:PUBLISHED]->(:Article)` | Channel → Article | Connects article to its origin channel. |
| `(:Article)-[:SIMILAR_TO {score, last_checked}]->(:Article)` | Article → Article | Duplicate detection edges built from embedding similarity. |
| `(:Article)-[:ABOUT]->(:Topic)` | Article → Topic | Article focuses primarily on the topic. |
| `(:Article)-[:MENTIONS {context}] -> (:Entity)` | Article → Entity | Article references the entity; optional `context` (quote, mention, launch). |
| `(:Article)-[:PROMOTES]->(:Entity)` | Article → Entity | Optional link when CTA references a product/company. |

Future-proof fields: `projects` (specialized node later), `events`, etc.

## Required Inputs per Article
To create an Article node we need at minimum:
1. `telegram_message_id`
2. `channel_id` or `channel_username`
3. `raw_text`
4. Gemini `embedding`
5. Metadata JSON matching `knowledge_graph/METADATA_CONTRACT.md`

n8n workflows should validate these before hitting the Neo4j Query API.
