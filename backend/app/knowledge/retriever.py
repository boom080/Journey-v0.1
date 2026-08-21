import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge.embedding import cosine_similarity, embed_text
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeSource

RETRIEVER_VERSION = "journey-hybrid-reranker-2.0.0"

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
    "主食",
    "卡路里",
    "不吃饭",
    "瘦",
    "作息",
    "熬夜",
    "睡前",
    "呼吸暂停",
    "手环",
    "手表",
    "医学",
)

SOURCE_ALIASES = {
    "healthy-diet": (
        "饮食",
        "营养",
        "食物",
        "热量",
        "卡路里",
        "蛋白",
        "主食",
        "蔬菜",
        "水果",
        "减脂",
        "增肌",
        "节食",
        "不吃饭",
        "食量",
        "瘦",
    ),
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
        "胸痛",
        "疼痛",
        "晕厥",
        "距离",
        "频率",
        "强度",
        "手环",
        "手表",
        "消耗",
    ),
    "sleep-health": (
        "睡眠",
        "失眠",
        "食欲",
        "起床",
        "白天",
        "熬夜",
        "作息",
        "睡前",
        "睡不好",
        "呼吸暂停",
    ),
    "journey-safety": (
        "疾病",
        "诊断",
        "治疗",
        "医生",
        "处方",
        "药",
        "孕期",
        "进食障碍",
        "替代",
        "胸闷",
        "胸痛",
        "晕厥",
        "医学",
        "严重",
        "长期",
        "专业",
        "只靠",
        "判断",
        "功能明显受影响",
    ),
}

OUT_OF_SCOPE_PATTERNS = (
    r"特定品牌.*精确",
    r"GPS.*轨迹",
    r"基因报告.*精确",
    r"核磁",
    r"没有提供任何记录.*精确预测",
    r"最新批次.*检测结果",
    r"注射多少.*胰岛素",
    r"星座.*减脂",
    r"未授权.*病历",
)


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
    db: Session,
    query: str,
    *,
    limit: int = 3,
    minimum_score: float = 0.16,
    rerank: bool = True,
) -> list[RetrievedChunk]:
    if rerank and any(re.search(pattern, query, re.I) for pattern in OUT_OF_SCOPE_PATTERNS):
        return []
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
        vector_score = cosine_similarity(query_vector, [float(value) for value in chunk.embedding])
        score = vector_score
        topics = [str(item) for item in chunk.metadata_json.get("topics", [])]
        topic_hits = sum(topic in query for topic in topics)
        if topic_hits:
            score += min(0.3, topic_hits * 0.15)
        alias_hits = sum(alias in query for alias in SOURCE_ALIASES.get(source.slug, ()))
        if rerank:
            # v2 hybrid reranking keeps the local vector baseline but makes explicit,
            # auditable domain evidence dominant. This avoids an external reranker service.
            score = max(0.0, vector_score) * 0.35
            score += min(0.75, alias_hits * 0.2)
            score += min(0.25, topic_hits * 0.12)
        elif alias_hits:
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
