# Python Prototype (/init)

We consulted the `n8n_skill` skill kit (see `.skills/n8n_skill`) to follow the "Prototype in Python first" guidance before moving to n8n. This folder hosts the initial prototype code.

## Files
- `prototype.py`: boots a Gemini embedding client, ensures Neo4j schema, writes a sample article, and performs a similarity search.
- `requirements.txt`: minimal dependencies (`google-generativeai`, `neo4j`, `python-dotenv`).

## Prerequisites
1. Populate `.skills/.env` with the environment variables outlined in `AGENTS.md` (already done):
   - `GEMINI_API_KEY`
   - `GOOGLE_EMBEDDING_MODEL`
   - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
2. (Optional) Create `.env.local` for developer-specific overrides.
3. Python 3.10+ recommended.

## Setup & Run
```bash
cd knowledge_graph
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python prototype.py
```

Expected behavior:
1. Loads env vars (preferring `.skills/.env`).
2. Initializes Gemini embeddings and detects embedding dimensions for the Neo4j vector index.
3. Ensures the `Article` constraint + `article_embedding_idx` vector index exist.
4. Upserts synthetic articles, triggers duplicate detection, and runs the four key queries (weekly digest, OpenAI news, VLM projects, image-editing updates).

## Fallback Behavior
- **Embeddings:** if the provided `GEMINI_API_KEY` is invalid or rate-limited, the script falls back to a deterministic hash-based embedding service that still produces consistent vectors for duplicate detection.
- **Graph backend:** the script first tries the Bolt driver using `NEO4J_URI`. If Bolt is unreachable (common on networks that block port 7687), it automatically calls the Aura Query API over HTTPS (`https://<host>/db/<database>/query/v2`, override with `NEO4J_QUERY_API_URL`). Only if both fail do we fall back to the in-memory graph that mimics the same Cypher-backed APIs so we can exercise the full workflow offline.
- Both fallbacks print warnings so you know when you’re not hitting the real services; swap in valid credentials/endpoints to exercise the production path.

Customize `prototype.py` to feed real Telegram payloads, chunking logic, and additional agents before porting the pattern into n8n.
