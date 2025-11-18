"""Agentic knowledge graph Python prototype (end-to-end scenario).

This script bootstraps Gemini embeddings + Neo4j, ingests synthetic Telegram
articles, triggers duplicate detection, and runs representative queries (weekly
digest, OpenAI news, VLM projects, image-editing updates) to validate the
pipeline before translating it to n8n agents.
"""
from __future__ import annotations

import hashlib
import math
import os
import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence
from urllib.parse import urlparse

import google.generativeai as genai
import requests
from dotenv import load_dotenv
from neo4j import GraphDatabase

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SKILLS_ENV = BASE_DIR / ".skills" / ".env"
DEFAULT_LOCAL_ENV = BASE_DIR / ".env.local"
VECTOR_INDEX_NAME = "article_embedding_idx"


def _load_env_file_if_kv(path: Path) -> None:
    if not path.exists():
        return
    try:
        sample = path.read_text(encoding="utf-8")
    except OSError:
        return
    if "=" not in sample:
        return
    load_dotenv(path, override=False)


@dataclass
class EntityRef:
    name: str
    type: str  # e.g., Org, Person, Product


@dataclass
class ProjectRef:
    name: str
    topics: List[str]
    description: str | None = None


@dataclass
class Article:
    telegram_message_id: str
    title: str
    body: str
    telegram_url: str
    published_at: datetime
    source_channel: str
    topics: List[str] = field(default_factory=list)
    entities: List[EntityRef] = field(default_factory=list)
    projects: List[ProjectRef] = field(default_factory=list)


class EnvConfig:
    REQUIRED = [
        "GEMINI_API_KEY",
        "GOOGLE_EMBEDDING_MODEL",
        "NEO4J_URI",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
    ]

    def __init__(self) -> None:
        for env_file in (DEFAULT_SKILLS_ENV, DEFAULT_LOCAL_ENV):
            _load_env_file_if_kv(env_file)

        missing = [key for key in self.REQUIRED if not os.getenv(key)]
        if missing:
            raise RuntimeError(f"Missing environment variables: {missing}")

        self.gemini_api_key = os.environ["GEMINI_API_KEY"]
        self.embedding_model = os.environ["GOOGLE_EMBEDDING_MODEL"]
        self.neo4j_uri = os.environ["NEO4J_URI"]
        self.neo4j_user = os.environ["NEO4J_USERNAME"]
        self.neo4j_password = os.environ["NEO4J_PASSWORD"]
        self.neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        parsed = urlparse(self.neo4j_uri)
        if not parsed.hostname:
            raise RuntimeError("NEO4J_URI must include a hostname")
        self.neo4j_host = parsed.hostname
        query_template = os.getenv("NEO4J_QUERY_API_URL")
        if query_template:
            self.neo4j_query_url = query_template.format(databaseName=self.neo4j_database)
        else:
            self.neo4j_query_url = (
                f"https://{self.neo4j_host}/db/{self.neo4j_database}/query/v2"
            )


class GeminiEmbeddingService:
    def __init__(self, api_key: str, model: str) -> None:
        genai.configure(api_key=api_key)
        self.model = model
        self._dimensions: int | None = None

    def embed(self, text: str) -> List[float]:
        response = genai.embed_content(model=self.model, content=text)
        embedding = response.get("embedding")
        if not embedding:
            raise RuntimeError("Gemini did not return an embedding")
        return list(map(float, embedding))

    @property
    def dimensions(self) -> int:
        if self._dimensions is None:
            probe = genai.embed_content(model=self.model, content="dimension probe")
            embedding = probe.get("embedding") or []
            self._dimensions = len(embedding)
        return self._dimensions


class HashEmbeddingService:
    """Deterministic fallback embedder built from token hashes."""

    def __init__(self, dim: int = 256) -> None:
        self._dimensions = dim
        self._token_cache: Dict[str, List[float]] = {}

    def embed(self, text: str) -> List[float]:
        tokens = re.findall(r"\w+", text.lower()) or ["empty"]
        vectors = [self._token_vector(token) for token in tokens]
        aggregated = [sum(values) / len(vectors) for values in zip(*vectors)]
        return aggregated

    def _token_vector(self, token: str) -> List[float]:
        if token in self._token_cache:
            return self._token_cache[token]
        seed = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        rng = random.Random(seed)
        vector = [rng.uniform(-1.0, 1.0) for _ in range(self._dimensions)]
        self._token_cache[token] = vector
        return vector

    @property
    def dimensions(self) -> int:
        return self._dimensions


class KnowledgeGraphBase:
    def __init__(self, embedding_dim: int) -> None:
        self.embedding_dim = embedding_dim
        self.ensure_schema()

    def close(self) -> None:
        return None

    def run_cypher(
        self, statement: str, parameters: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def ensure_schema(self) -> None:
        constraint_cypher = (
            "CREATE CONSTRAINT article_telegram_unique IF NOT EXISTS "
            "FOR (a:Article) REQUIRE a.telegram_message_id IS UNIQUE"
        )
        vector_index_cypher = f"""
        CREATE VECTOR INDEX {VECTOR_INDEX_NAME} IF NOT EXISTS
        FOR (a:Article) ON (a.embedding)
        OPTIONS {{indexConfig: {{
            `vector.dimensions`: {self.embedding_dim},
            `vector.similarity_function`: 'cosine'
        }}}}
        """
        self.run_cypher(constraint_cypher)
        self.run_cypher(vector_index_cypher)

    def upsert_article(self, article: Article, embedding: Sequence[float]) -> None:
        cypher = """
        MERGE (a:Article {telegram_message_id: $telegram_message_id})
        SET a.title = $title,
            a.body = $body,
            a.telegram_url = $telegram_url,
            a.source_channel = $source_channel,
            a.published_at = datetime($published_at),
            a.embedding = $embedding,
            a.status = 'ingested'
        """
        params = {
            "telegram_message_id": article.telegram_message_id,
            "title": article.title,
            "body": article.body,
            "telegram_url": article.telegram_url,
            "source_channel": article.source_channel,
            "published_at": article.published_at.isoformat(),
            "embedding": list(embedding),
        }
        self.run_cypher(cypher, params)

    def attach_topics(self, article: Article) -> None:
        if not article.topics:
            return
        cypher = """
        MATCH (a:Article {telegram_message_id: $telegram_message_id})
        FOREACH (topicName IN $topics |
            MERGE (t:Topic {name: topicName})
            ON CREATE SET t.created_at = datetime()
            MERGE (a)-[:ABOUT]->(t)
        )
        """
        self.run_cypher(
            cypher,
            {"telegram_message_id": article.telegram_message_id, "topics": article.topics},
        )

    def attach_entities(self, article: Article) -> None:
        if not article.entities:
            return
        cypher = """
        MATCH (a:Article {telegram_message_id: $telegram_message_id})
        FOREACH (entity IN $entities |
            MERGE (e:Entity {name: entity.name})
            ON CREATE SET e.type = entity.type, e.created_at = datetime()
            SET e.type = entity.type
            MERGE (a)-[:MENTIONS]->(e)
        )
        """
        self.run_cypher(
            cypher,
            {
                "telegram_message_id": article.telegram_message_id,
                "entities": [e.__dict__ for e in article.entities],
            },
        )

    def attach_projects(self, article: Article) -> None:
        if not article.projects:
            return
        cypher = """
        MATCH (a:Article {telegram_message_id: $telegram_message_id})
        FOREACH (project IN $projects |
            MERGE (p:Project {name: project.name})
            ON CREATE SET p.description = project.description, p.created_at = datetime()
            SET p.description = coalesce(project.description, p.description)
            MERGE (a)-[:FEATURES]->(p)
            FOREACH (topicName IN project.topics |
                MERGE (t:Topic {name: topicName})
                MERGE (p)-[:ABOUT]->(t)
            )
        )
        """
        self.run_cypher(
            cypher,
            {
                "telegram_message_id": article.telegram_message_id,
                "projects": [p.__dict__ for p in article.projects],
            },
        )

    def find_similar_articles(
        self,
        embedding: Sequence[float],
        telegram_message_id: str,
        limit: int = 5,
        min_score: float = 0.88,
    ) -> List[Dict[str, object]]:
        cypher = """
        CALL db.index.vector.queryNodes($index_name, $limit, $embedding)
        YIELD node, score
        WHERE node.telegram_message_id <> $telegram_message_id AND score >= $min_score
        RETURN node.telegram_message_id AS telegram_message_id,
               node.title AS title,
               node.telegram_url AS telegram_url,
               score
        ORDER BY score DESC
        """
        params = {
            "index_name": VECTOR_INDEX_NAME,
            "limit": limit,
            "embedding": list(embedding),
            "telegram_message_id": telegram_message_id,
            "min_score": min_score,
        }
        return self.run_cypher(cypher, params)

    def create_similarity_links(
        self, source_id: str, matches: List[Dict[str, object]]
    ) -> None:
        if not matches:
            return
        cypher = """
        UNWIND $matches AS match
        MATCH (source:Article {telegram_message_id: $source_id})
        MATCH (target:Article {telegram_message_id: match.telegram_message_id})
        MERGE (source)-[r:SIMILAR_TO]->(target)
        SET r.score = match.score,
            r.last_checked = datetime()
        """
        self.run_cypher(cypher, {"source_id": source_id, "matches": matches})

    def weekly_digest(self, days: int = 7) -> List[Dict[str, object]]:
        cypher = """
        MATCH (a:Article)
        WHERE a.published_at >= datetime() - duration({days: $days})
        OPTIONAL MATCH (a)-[:ABOUT]->(t:Topic)
        WITH a, collect(DISTINCT t.name) AS topics
        RETURN date(a.published_at) AS day,
               a.title AS title,
               a.telegram_url AS telegram_url,
               topics
        ORDER BY day DESC, title ASC
        """
        return self.run_cypher(cypher, {"days": days})

    def article_list_by_entity(self, entity_name: str, days: int = 14) -> List[Dict[str, object]]:
        cypher = """
        MATCH (a:Article)-[:MENTIONS]->(e:Entity {name: $entity})
        WHERE a.published_at >= datetime() - duration({days: $days})
        RETURN a.title AS title,
               a.telegram_url AS telegram_url,
               date(a.published_at) AS day
        ORDER BY a.published_at DESC
        """
        return self.run_cypher(cypher, {"entity": entity_name, "days": days})

    def vlm_projects(self, topic: str = "Vision-Language Models") -> List[Dict[str, object]]:
        cypher = """
        MATCH (a:Article)-[:FEATURES]->(p:Project)-[:ABOUT]->(t:Topic {name: $topic})
        RETURN p.name AS project,
               a.title AS title,
               a.telegram_url AS telegram_url,
               date(a.published_at) AS day
        ORDER BY a.published_at DESC
        """
        return self.run_cypher(cypher, {"topic": topic})

    def image_edit_news(self) -> List[Dict[str, object]]:
        cypher = """
        MATCH (a:Article)-[:ABOUT]->(t:Topic)
        WHERE t.name CONTAINS 'Image Edit'
        RETURN a.title AS title,
               a.telegram_url AS telegram_url,
               date(a.published_at) AS day,
               COLLECT(DISTINCT t.name) AS topics
        ORDER BY day DESC
        """
        return self.run_cypher(cypher)


class Neo4jKnowledgeGraph(KnowledgeGraphBase):
    def __init__(self, config: EnvConfig, embedding_dim: int) -> None:
        self._driver = GraphDatabase.driver(
            config.neo4j_uri, auth=(config.neo4j_user, config.neo4j_password)
        )
        self.database = config.neo4j_database
        super().__init__(embedding_dim)

    def run_cypher(
        self, statement: str, parameters: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        with self._driver.session(database=self.database) as session:
            params = parameters or {}
            result = session.run(statement, params)
            return [record.data() for record in result]

    def close(self) -> None:
        self._driver.close()


class Neo4jQueryAPIKnowledgeGraph(KnowledgeGraphBase):
    def __init__(self, config: EnvConfig, embedding_dim: int) -> None:
        self._session = requests.Session()
        self._session.auth = (config.neo4j_user, config.neo4j_password)
        self.base_url = config.neo4j_query_url
        super().__init__(embedding_dim)

    def run_cypher(
        self, statement: str, parameters: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {"statement": statement}
        if parameters:
            payload["parameters"] = parameters
        response = self._session.post(self.base_url, json=payload, timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Neo4j Query API error {response.status_code}: {response.text}"
            )
        data = response.json().get("data", {})
        fields = data.get("fields") or []
        values = data.get("values") or []
        records: List[Dict[str, Any]] = []
        for row in values:
            records.append(dict(zip(fields, row)))
        return records

    def close(self) -> None:
        self._session.close()


class InMemoryKnowledgeGraph:
    """Fallback graph implementation when Neo4j is unavailable."""

    def __init__(self, embedding_dim: int) -> None:
        self.embedding_dim = embedding_dim
        self.articles: Dict[str, Dict[str, Any]] = {}
        self.topic_index: Dict[str, set[str]] = defaultdict(set)
        self.entity_index: Dict[str, set[str]] = defaultdict(set)
        self.project_topics: Dict[str, List[str]] = {}
        self.project_articles: Dict[str, set[str]] = defaultdict(set)
        self.similarity_edges: List[Dict[str, object]] = []

    def close(self) -> None:
        return None

    def upsert_article(self, article: Article, embedding: Sequence[float]) -> None:
        self.articles[article.telegram_message_id] = {
            "article": article,
            "embedding": list(embedding),
            "topics": list(article.topics),
            "entities": [e.name for e in article.entities],
            "projects": [p.name for p in article.projects],
        }

    def attach_topics(self, article: Article) -> None:
        stored = self.articles[article.telegram_message_id]
        stored["topics"] = list(article.topics)
        for topic in article.topics:
            self.topic_index[topic].add(article.telegram_message_id)

    def attach_entities(self, article: Article) -> None:
        stored = self.articles[article.telegram_message_id]
        stored["entities"] = [e.name for e in article.entities]
        for entity in article.entities:
            self.entity_index[entity.name].add(article.telegram_message_id)

    def attach_projects(self, article: Article) -> None:
        stored = self.articles[article.telegram_message_id]
        stored["projects"] = [p.name for p in article.projects]
        for project in article.projects:
            self.project_topics[project.name] = list(project.topics)
            self.project_articles[project.name].add(article.telegram_message_id)

    def find_similar_articles(
        self,
        embedding: Sequence[float],
        telegram_message_id: str,
        limit: int = 5,
        min_score: float = 0.88,
    ) -> List[Dict[str, object]]:
        results: List[Dict[str, object]] = []
        for other_id, record in self.articles.items():
            if other_id == telegram_message_id:
                continue
            score = self._cosine_similarity(embedding, record["embedding"])
            if score >= min_score:
                article: Article = record["article"]
                results.append(
                    {
                        "telegram_message_id": other_id,
                        "title": article.title,
                        "telegram_url": article.telegram_url,
                        "score": score,
                    }
                )
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]

    @staticmethod
    def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if not norm_a or not norm_b:
            return 0.0
        return dot / (norm_a * norm_b)

    def create_similarity_links(
        self, source_id: str, matches: List[Dict[str, object]]
    ) -> None:
        timestamp = datetime.utcnow().isoformat()
        for match in matches:
            self.similarity_edges.append(
                {
                    "source": source_id,
                    "target": match["telegram_message_id"],
                    "score": match["score"],
                    "timestamp": timestamp,
                }
            )

    def weekly_digest(self, days: int = 7) -> List[Dict[str, object]]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        entries: List[Dict[str, object]] = []
        for record in self.articles.values():
            article: Article = record["article"]
            if article.published_at >= cutoff:
                entries.append(
                    {
                        "day": article.published_at.date(),
                        "title": article.title,
                        "telegram_url": article.telegram_url,
                        "topics": record["topics"],
                    }
                )
        entries.sort(key=lambda r: (r["day"], r["title"]), reverse=True)
        return entries

    def article_list_by_entity(
        self, entity_name: str, days: int = 14
    ) -> List[Dict[str, object]]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        results: List[Dict[str, object]] = []
        for article_id in self.entity_index.get(entity_name, []):
            article: Article = self.articles[article_id]["article"]
            if article.published_at >= cutoff:
                results.append(
                    {
                        "title": article.title,
                        "telegram_url": article.telegram_url,
                        "day": article.published_at.date(),
                    }
                )
        results.sort(key=lambda r: r["day"], reverse=True)
        return results

    def vlm_projects(self, topic: str = "Vision-Language Models") -> List[Dict[str, object]]:
        entries: List[Dict[str, object]] = []
        for project, topics in self.project_topics.items():
            if topic not in topics:
                continue
            for article_id in self.project_articles.get(project, []):
                article: Article = self.articles[article_id]["article"]
                entries.append(
                    {
                        "project": project,
                        "title": article.title,
                        "telegram_url": article.telegram_url,
                        "day": article.published_at.date(),
                    }
                )
        entries.sort(key=lambda r: r["day"], reverse=True)
        return entries

    def image_edit_news(self) -> List[Dict[str, object]]:
        entries: List[Dict[str, object]] = []
        for record in self.articles.values():
            article: Article = record["article"]
            topics = [topic for topic in record["topics"] if "Image Edit" in topic]
            if topics:
                entries.append(
                    {
                        "title": article.title,
                        "telegram_url": article.telegram_url,
                        "day": article.published_at.date(),
                        "topics": topics,
                    }
                )
        entries.sort(key=lambda r: r["day"], reverse=True)
        return entries


def chunk_text(text: str, max_chars: int = 2000) -> Iterable[str]:
    text = text.strip()
    for i in range(0, len(text), max_chars):
        yield text[i : i + max_chars]


class ScenarioRunner:
    def __init__(self, graph: Any, embedding_service: Any) -> None:
        self.graph = graph
        self.embedding_service = embedding_service
        self.duplicate_threshold = 0.4

    def run(self) -> None:
        articles = self.synthetic_articles()
        print(f"Ingesting {len(articles)} synthetic articles...")
        for article in articles:
            content = "\n\n".join(chunk_text(article.body))
            embedding = self.embedding_service.embed(content)
            self.graph.upsert_article(article, embedding)
            self.graph.attach_topics(article)
            self.graph.attach_entities(article)
            self.graph.attach_projects(article)
            matches = self.graph.find_similar_articles(
                embedding,
                telegram_message_id=article.telegram_message_id,
                min_score=self.duplicate_threshold,
            )
            if matches:
                print(f"- Potential duplicates for {article.title}:")
                for match in matches:
                    print(
                        f"    · {match['title']} (score={match['score']:.3f}) → {match['telegram_url']}"
                    )
                self.graph.create_similarity_links(article.telegram_message_id, matches)

        self.report_weekly_digest()
        self.report_openai_news()
        self.report_vlm_projects()
        self.report_image_edit_news()

    def report_weekly_digest(self) -> None:
        digest = self.graph.weekly_digest()
        grouped: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        for entry in digest:
            grouped[str(entry["day"])].append(entry)
        print("\nWeekly digest (last 7 days):")
        for day, entries in grouped.items():
            print(f"  {day}:")
            for item in entries:
                topic_list = ", ".join(filter(None, item["topics"]))
                print(
                    f"    - {item['title']} [{topic_list or 'No topic tags'}] → {item['telegram_url']}"
                )

    def report_openai_news(self) -> None:
        articles = self.graph.article_list_by_entity("OpenAI")
        print("\nRecent OpenAI news:")
        if not articles:
            print("  (none)")
            return
        for item in articles:
            print(f"  - {item['day']}: {item['title']} → {item['telegram_url']}")

    def report_vlm_projects(self) -> None:
        entries = self.graph.vlm_projects()
        print("\nCool VLM projects:")
        if not entries:
            print("  (none)")
            return
        for item in entries:
            print(
                f"  - {item['day']}: {item['project']} via {item['title']} → {item['telegram_url']}"
            )

    def report_image_edit_news(self) -> None:
        entries = self.graph.image_edit_news()
        print("\nImage editing model updates:")
        if not entries:
            print("  (none)")
            return
        for item in entries:
            topics = ", ".join(item["topics"]) if item["topics"] else "No topic tags"
            print(f"  - {item['day']}: {item['title']} [{topics}] → {item['telegram_url']}")

    @staticmethod
    def synthetic_articles() -> List[Article]:
        now = datetime.utcnow()
        return [
            Article(
                telegram_message_id="tg-1001",
                title="OpenAI ships Sora safety bundle",
                body=(
                    "OpenAI dropped a Sora safety update focused on watermarking,"
                    " improved classifiers, and new policy guardrails. Editors"
                    " received internal tooling to review generated clips before"
                    " they are published and the team highlighted upcoming video"
                    " filters." 
                ),
                telegram_url="https://t.me/content_lab/1001",
                published_at=now - timedelta(days=1),
                source_channel="content_lab",
                topics=["OpenAI", "Generative Video", "Policy"],
                entities=[EntityRef("OpenAI", "Org"), EntityRef("Sora", "Project")],
                projects=[
                    ProjectRef(
                        name="Sora Safety Belt",
                        topics=["Vision-Language Models", "Generative Video"],
                        description="New moderation layer for Sora videos",
                    )
                ],
            ),
            Article(
                telegram_message_id="tg-1002",
                title="LensForge open-sources its VLM agent toolkit",
                body=(
                    "LensForge unveiled Vision Relay, a toolkit that chains VLMs"
                    " with retrieval agents. The repo ships with Neo4j adapters,"
                    " telemetry hooks, and scripted evaluations for enterprise"
                    " copilots." 
                ),
                telegram_url="https://t.me/content_lab/1002",
                published_at=now - timedelta(days=2),
                source_channel="content_lab",
                topics=["Vision-Language Models", "Developer Tools"],
                entities=[EntityRef("LensForge", "Org")],
                projects=[
                    ProjectRef(
                        name="Vision Relay",
                        topics=["Vision-Language Models", "Agent Tooling"],
                        description="Open VLM agent stack",
                    )
                ],
            ),
            Article(
                telegram_message_id="tg-1003",
                title="Image editing model roundup",
                body=(
                    "Runway, Ideogram, and Adobe all quietly shipped image editing"
                    " improvements. Firefly added inpainting that keeps lighting"
                    " consistent, Ideogram rolled out typography aware edits, and"
                    " Runway's Gen-2 received a portrait refiner." 
                ),
                telegram_url="https://t.me/content_lab/1003",
                published_at=now - timedelta(days=3),
                source_channel="content_lab",
                topics=["Image Editing Models", "Generative AI"],
                entities=[
                    EntityRef("Adobe", "Org"),
                    EntityRef("Runway", "Org"),
                    EntityRef("Ideogram", "Org"),
                ],
                projects=[],
            ),
            Article(
                telegram_message_id="tg-1004",
                title="OpenAI partners with NewsDeck",
                body=(
                    "NewsDeck tapped OpenAI to power newsroom copilots that browse"
                    " archives, propose headlines, and anchor references back to"
                    " Neo4j topic graphs. The pilot covers investigative teams"
                    " in NYC and London." 
                ),
                telegram_url="https://t.me/content_lab/1004",
                published_at=now - timedelta(days=4),
                source_channel="content_lab",
                topics=["OpenAI", "News Automation"],
                entities=[EntityRef("OpenAI", "Org"), EntityRef("NewsDeck", "Org")],
                projects=[],
            ),
            Article(
                telegram_message_id="tg-1005",
                title="OpenAI ships Sora safety bundle (editor recap)",
                body=(
                    "Editors circulated a recap of the new Sora safety bundle."
                    " It reiterates the watermarking roadmap, classifiers, and"
                    " pre-publish review loop—almost identical to the launch"
                    " post but framed for team onboarding." 
                ),
                telegram_url="https://t.me/content_lab/1005",
                published_at=now - timedelta(days=1, hours=2),
                source_channel="content_lab",
                topics=["OpenAI", "Generative Video"],
                entities=[EntityRef("OpenAI", "Org"), EntityRef("Sora", "Project")],
                projects=[
                    ProjectRef(
                        name="Sora Safety Belt",
                        topics=["Vision-Language Models", "Generative Video"],
                    )
                ],
            ),
            Article(
                telegram_message_id="tg-0990",
                title="Meta's multimodal lab notes",
                body=(
                    "Meta Reality Labs described a six-month effort on perception"
                    " fused transformers. While adjacent to VLM work, it's mostly"
                    " background context and predates this week's focus." 
                ),
                telegram_url="https://t.me/content_lab/990",
                published_at=now - timedelta(days=12),
                source_channel="content_lab",
                topics=["Vision-Language Models", "Research"],
                entities=[EntityRef("Meta", "Org")],
                projects=[],
            ),
        ]


def build_embedding_service(config: EnvConfig):
    try:
        service = GeminiEmbeddingService(
            api_key=config.gemini_api_key, model=config.embedding_model
        )
        _ = service.dimensions  # force probe call so we know the model works
        print(f"Using Gemini embeddings via {service.model}.")
        return service
    except Exception as exc:
        print(
            "[WARN] Gemini embeddings unavailable due to "
            f"{exc}. Falling back to deterministic hash embeddings."
        )
        return HashEmbeddingService()


def build_graph_backend(config: EnvConfig, embedding_dim: int):
    try:
        graph = Neo4jKnowledgeGraph(config, embedding_dim=embedding_dim)
        print(f"Connected to Neo4j at {config.neo4j_uri}.")
        return graph
    except Exception as exc:
        print(
            "[WARN] Bolt driver unavailable due to "
            f"{exc}. Attempting Neo4j Query API fallback."
        )
        try:
            graph = Neo4jQueryAPIKnowledgeGraph(config, embedding_dim=embedding_dim)
            print(f"Connected to Neo4j Query API at {config.neo4j_query_url}.")
            return graph
        except Exception as http_exc:
            print(
                "[WARN] Query API unavailable due to "
                f"{http_exc}. Using in-memory graph backend for testing."
            )
            return InMemoryKnowledgeGraph(embedding_dim)


def main() -> None:
    config = EnvConfig()
    embedding_service = build_embedding_service(config)
    graph = build_graph_backend(config, embedding_service.dimensions)

    runner = ScenarioRunner(graph, embedding_service)
    runner.run()

    graph.close()


if __name__ == "__main__":
    main()
