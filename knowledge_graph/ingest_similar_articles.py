"""Utility script to ingest a pair of similar WAN 2.5 articles.

Run this once to seed Neo4j with realistic data for the duplicate
detector. The script reads credentials from the usual .env files,
uses Gemini embeddings (3072 dims), and writes via the Query API so
results mirror the n8n HTTP node.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from textwrap import dedent

try:
    from prototype import (
        Article,
        EnvConfig,
        GeminiEmbeddingService,
        Neo4jQueryAPIKnowledgeGraph,
    )
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from .prototype import (
        Article,
        EnvConfig,
        GeminiEmbeddingService,
        Neo4jQueryAPIKnowledgeGraph,
    )


def _build_articles() -> list[Article]:
    now = datetime.utcnow()
    base_topics = [
        "WAN 2.5",
        "Multimodal Models",
        "Video Generation",
        "Image Editing",
    ]

    article_a = Article(
        telegram_message_id="1719",
        title="WAN 2.5 — український драфт під відео",
        body=dedent(
            """
            Ось український драфт для підпису до цього відео:

            WAN 2.5: переклад списку нових фішок ламає очі — від англійської до квазі-англійської. Виокремлю ключові моменти.

            Мультимодальність: підтримка тексту, зображень, відео та аудіо на вході й виході.
            Ліпсінк для кількох персонажів у кадрі.
            Покращене розуміння промптів та вхідних даних завдяки мультимодальному тренуванню.
            1080p HD, 10 секунд.
            Генерація та редагування зображень.

            • Архітектурні особливості: Нативна мультимодальність, глибока алігнація
            ∘ Нативна мультимодальна архітектура: Новий уніфікований фреймворк для розуміння та генерації, гнучко підтримує вхід/вихід тексту, зображень, відео та аудіо.
            ∘ Спільне мультимодальне тренування: Покращена алігнація модальностей завдяки спільному тренуванню на текстових, аудіо- та візуальних даних — ключ до аудіовізуальної синхронізації та кращого виконання інструкцій.
            ∘ Алігнація з людськими уподобаннями: Використовує RLHF для постійної адаптації до людських переваг, покращуючи якість зображень та динаміку відео.

            • Можливості відео: Аудіовізуальна синхронізація, кінематографічна якість
            ∘ Синхронізована генерація А/В: Нативно підтримує високофідельну, висококонсистентну генерацію відео з синхронізованим аудіо, включаючи вокал кількох осіб, звукові ефекти та BGM.
            ∘ Керування мультимодальним входом: Підтримує текст, зображення та аудіо як джерела для безмежної креативності.
            ∘ Кінематографічна естетика: Потужна динаміка та структурна стабільність з оновленою системою контролю, генерує 1080p HD відео тривалістю 10 с кінематографічної якості.

            • Можливості зображень: Креативний та точний контроль
            ∘ Просунута генерація зображень: Значно покращене виконання інструкцій для фотореалістичної якості, різноманітних художніх стилів, креативної типографіки та професійних графіків.
            ∘ Редагування зображень: Підтримує розмовне, інструкційне редагування з піксельною точністю для завдань на кшталт злиття концептів, трансформації матеріалів, зміни кольорів продуктів тощо.

            Деталі: https://wan.video/

            #dubovykai
            """
        ).strip(),
        telegram_url="https://t.me/dubovykai/1719",
        published_at=now - timedelta(minutes=5),
        source_channel="dubovykai",
        topics=list(base_topics),
    )

    article_b = Article(
        telegram_message_id="1720",
        title="WAN 2.5: мультимодальна збірка в деталях",
        body=dedent(
            """
            WAN 2.5 отримав україномовний опис для релізного відео, тож зібрав головні тези у більш розмовному стилі.

            Ключові апдейти:
            • справжня мультимодальність: один стек для текстових, візуальних та аудіо ввід/вивід, швидке перемикання між форматами;
            • синхронний ліпсінк навіть для кількох персонажів в кадрі;
            • тренування одразу на тексті, зображеннях та звуку, завдяки чому модель краще тримає промпт і структуру сцени;
            • рідний 1080p / 10 секунд із контрольованою камерою;
            • редактор і генератор картинок у тому ж пайплайні.

            Архітектура та тренування:
            - уніфікований мультимодальний фреймворк без костилів;
            - спільна оптимізація модальностей + RLHF, щоб збільшити якість відео та стабільність анімацій.

            Відеомодуль дозволяє подавати текст, аудіо чи референсне зображення, а на виході тримати кінематографічний кадр з точним аудіо-супроводом (включно з вокалом, шумами та музикою).

            Модуль зображень — це і покращений текст-ту-імідж, і точкові редакції: зміна кольорів продукту, злиття концептів чи типографіка у брендових стилях.

            Детальніше: https://wan.video/

            #dubovykai
            """
        ).strip(),
        telegram_url="https://t.me/dubovykai/1720",
        published_at=now,
        source_channel="dubovykai",
        topics=list(base_topics),
    )

    return [article_a, article_b]


def main() -> None:
    config = EnvConfig()
    embedder = GeminiEmbeddingService(config.gemini_api_key, config.embedding_model)
    graph = Neo4jQueryAPIKnowledgeGraph(config, embedder.dimensions)

    try:
        for article in _build_articles():
            embedding_input = f"{article.title}\n\n{article.body}"
            embedding = embedder.embed(embedding_input)
            graph.upsert_article(article, embedding)
            graph.attach_topics(article)
            print(
                f"Upserted article {article.telegram_message_id} with {len(embedding)}-dim embedding"
            )
    finally:
        graph.close()


if __name__ == "__main__":
    main()
