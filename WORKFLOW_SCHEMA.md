# n8n Workflow Cheat Sheet

Use this as a quick reference while wiring the new ingestion/publishing flow.

## High-Level Steps
1. **Telegram Trigger** – receive message, capture `message_id`, channel, raw text/media.
2. **Structured Preprocess (Code node)** – emit `article` object (`rawText`, `telegramMessageId`, `channelId`, `mediaType`, `mediaFileId`) plus `agentPrompt` for later LLM calls.
3. **Embedding Builder** – call Google/Gemini embedding API on `article.rawText`; store vector for reuse.
4. **Duplicate Query (Neo4j Query API)** – `CALL db.index.vector.queryNodes(...)`; get candidate articles with scores + links.
5. **Decision Branch**
   - If score ≥ threshold → notify editor in Telegram/Slack with inline buttons.
   - Otherwise auto-approve and continue.
6. **Editor Confirmation Node**
   - Wait for button/webhook response.
   - “Skip” → send notification and end.
   - “Publish” → proceed.
7. **Gemini Flash Metadata Extractor** – with predefined JSON schema (title, summary, topics, entities, CTA, tags). Only runs after approval.
8. **Metadata Validation** – ensure required fields; set defaults if missing.
9. **Publishing Agent (MCP)** – post approved article to destination; capture publish link/ID.
10. **Neo4j Writeback (Query API)** – MERGE `Article` node with metadata + embedding; attach Topic/Entity/Project nodes; set status & timestamps.
11. **Success Notification** – message editor with publish link & confirmation.
12. **Error Handling** – workflow-level catch node alerts editors if any step fails.

## Data Objects
- `article`: `{ telegramMessageId, channelId, rawText, mediaType, mediaFileId }`
- `embedding`: `{ vector: number[], model: string }`
- `duplicateMatches`: `[ { telegram_message_id, title, telegram_url, score } ]`
- `metadata`: Gemini schema (title, summary, topics[], entities[{name,type}], tags[], ctaText, ctaLink, publishNotes)`
- `publishResult`: `{ destinationUrl, destinationMessageId }`
- `status`: stored in Neo4j (`received → pending_decision → approved → published → ingested`)

Keep this file open while assembling the n8n workflow so each node maps directly to these steps. Update the cheat sheet if we refine thresholds, schemas, or additional agents.
