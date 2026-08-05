from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge.embedding import cosine_similarity, embed_text
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeSource

DOMAIN_TERMS = (
    "饮食",
    "营养",
    "食物",
    "热量",
    "蛋白",
    "减脂",
    "增肌",
    "节食",
    "运动",
    "训练",
    "恢复",
    "跑步",
    "散步",
    "游泳",
    "骑车",
    "瑜伽",
    "消耗",
    "睡眠",
    "失眠",
    "食欲",
    "起床",
    "健康",
    "疾病",
    "诊断",
    "治疗",
    "医生",
    "处方",
    "药",
    "孕期",
    "进食障碍",
    "胸痛",
    "晕厥",
)

SOURCE_ALIASES = {
    "healthy-diet": ("饮食", "营养", "食物", "热量", "蛋白", "减脂", "增肌", "节食"),
    "physical-activity": (
        "运动",
        "训练",
        "恢复",
        "跑步",
        "散步",
        "游泳",
        "骑车",
        "瑜伽",
        "胸闷",
        "消耗",
    ),
    "sleep-health": ("睡眠", "失眠", "食欲", "起床", "白天"),
    "journey-safety": ("疾病", "诊断", "治疗", "医生", "处方", "药", "孕期", "进食障碍", "替代"),
}


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    source_slug: str
    title: str
    source_url: str
    version: str
    region: str
    text: str
    score: float


def retrieve(
    db: Session, query: str, *, limit: int = 3, minimum_score: float = 0.16
) -> list[RetrievedChunk]:
    if not any(term in query for term in DOMAIN_TERMS):
        return []
    query_vector = embed_text(query)
    rows = db.execute(
        select(KnowledgeChunk, KnowledgeDocument, KnowledgeSource)
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
        .where(KnowledgeSource.is_active.is_(True), KnowledgeDocument.is_active.is_(True))
    )
    ranked: list[RetrievedChunk] = []
    for chunk, document, source in rows:
        score = cosine_similarity(query_vector, [float(value) for value in chunk.embedding])
        topics = [str(item) for item in chunk.metadata_json.get("topics", [])]
        topic_hits = sum(topic in query for topic in topics)
        if topic_hits:
            score += min(0.3, topic_hits * 0.15)
        alias_hits = sum(alias in query for alias in SOURCE_ALIASES.get(source.slug, ()))
        if alias_hits:
            score += min(0.45, alias_hits * 0.2)
        if score >= minimum_score:
            ranked.append(
                RetrievedChunk(
                    chunk_id=str(chunk.id),
                    document_id=str(document.id),
                    source_slug=source.slug,
                    title=document.title,
                    source_url=source.source_url,
                    version=source.version,
                    region=source.region,
                    text=chunk.text,
                    score=round(score, 6),
                )
            )
    return sorted(ranked, key=lambda item: (-item.score, item.chunk_id))[:limit]
