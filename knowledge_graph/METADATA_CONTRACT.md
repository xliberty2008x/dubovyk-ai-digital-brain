# Metadata Extraction Contract

n8n Prompt Builder + Gemini Flash must return JSON matching this contract so we can populate Neo4j without manual cleanup.

## JSON Schema
```json
{
  "title": "string",
  "summary": "string",
  "topics": ["string"],
  "topicDecisionRequired": "boolean",
  "tags": ["string"],
  "entities": [
    { "name": "string", "entityType": "person|company|project|technology|other" }
  ],
  "ctaText": "string",
  "ctaLink": "string"
}
```

### Field Rules
- **title** (required): concise Ukrainian headline (≤120 chars). Fallback: first clause of the post.
- **summary** (required): 2–4 sentences summarizing the entire post for knowledge-base use.
- **topics**: choose up to 3 from the canonical taxonomy below. No duplicates. If none apply, leave the array empty and set `topicDecisionRequired = true` so a follow-up agent can decide.
- **topicDecisionRequired**: boolean flag signaling the downstream agent to review/assign a topic. Always `false` when at least one canonical topic is selected.
- **tags**: free-form keywords/hashtags (≤6). Lowercase and deduplicate.
- **entities**: only real nouns. Use provided entity types; omit empty entries.
- **ctaText/ctaLink**: capture CTA if the post includes explicit instructions or URLs; leave empty string when absent.

## Canonical Topic Taxonomy
Used for `topics[]` and graph queries.

1. `agentic_ai`
2. `model_context_protocol`
3. `frontier_models`
4. `multimodality`
5. `retrieval_augmented_generation`
6. `fine_tuning_and_customization`
7. `developer_tools_and_frameworks`
8. `ai_hardware_and_infrastructure`
9. `open_source_ecosystem`
10. `enterprise_ai_and_automation`
11. `responsible_ai_and_governance`

If a post does not match any of the above, the LLM must return `"topics": []` and `"topicDecisionRequired": true` to route the item to the topic-decider agent.

LLM prompt should encourage exact matches to the list. Downstream validators must discard unknown topics or map them to `other`.

## Entity Types
- `person`
- `company`
- `project`
- `technology`
- `other`

## Validation Checklist
1. Ensure JSON parses without comments/trailing commas.
2. Trim whitespace around every string.
3. Deduplicate `topics`, `tags`, and `entities` by lowercase value.
4. Ensure `ctaLink` is a valid URL (prefix with `https://` if bare domain).
5. Set fallback values (e.g., `title`, `summary`) before writing to Neo4j.

See `knowledge_graph/SEARCH_PLAYBOOK.md` for how these fields drive queries.
