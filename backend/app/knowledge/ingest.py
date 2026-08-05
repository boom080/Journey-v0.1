import hashlib
import json
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.settings import get_settings
from app.knowledge.embedding import EMBEDDING_VERSION, embed_text
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeSource

BUNDLE_PATH = Path(__file__).parent / "sources" / "journey_core_v1.json"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _chunks(content: str, maximum: int = 420) -> list[str]:
    paragraphs = [item.strip() for item in content.split("\n") if item.strip()]
    result: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 1 > maximum:
            result.append(current)
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip()
    if current:
        result.append(current)
    return result


def ingest_builtin_knowledge(db: Session) -> int:
    if not get_settings().seed_builtin_knowledge:
        return 0
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    active_slugs: set[str] = set()
    ingested = 0
    for source_data in bundle["sources"]:
        slug = source_data["slug"]
        active_slugs.add(slug)
        source_hash = _hash(json.dumps(source_data, ensure_ascii=False, sort_keys=True))
        source = db.scalar(select(KnowledgeSource).where(KnowledgeSource.slug == slug))
        if source is None:
            source = KnowledgeSource(
                slug=slug,
                title=source_data["title"],
                source_url=source_data["source_url"],
                region=source_data["region"],
                license_note=source_data["license_note"],
                version=source_data["version"],
                content_hash=source_hash,
                is_active=True,
            )
            db.add(source)
            db.flush()
        else:
            source.title = source_data["title"]
            source.source_url = source_data["source_url"]
            source.region = source_data["region"]
            source.license_note = source_data["license_note"]
            source.version = source_data["version"]
            source.content_hash = source_hash
            source.is_active = True
        active_documents: set[tuple[str, str]] = set()
        for document_data in source_data["documents"]:
            active_documents.add((document_data["external_id"], source_data["version"]))
            document = db.scalar(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.source_id == source.id,
                    KnowledgeDocument.external_id == document_data["external_id"],
                    KnowledgeDocument.version == source_data["version"],
                )
            )
            content_hash = _hash(document_data["content"])
            if document is None:
                document = KnowledgeDocument(
                    source_id=source.id,
                    external_id=document_data["external_id"],
                    title=document_data["title"],
                    version=source_data["version"],
                    content=document_data["content"],
                    content_hash=content_hash,
                    metadata_json=document_data["metadata"],
                    is_active=True,
                )
                db.add(document)
                db.flush()
                rebuild_chunks = True
            else:
                rebuild_chunks = document.content_hash != content_hash
                document.title = document_data["title"]
                document.content = document_data["content"]
                document.content_hash = content_hash
                document.metadata_json = document_data["metadata"]
                document.is_active = True
                if not rebuild_chunks:
                    rebuild_chunks = not db.scalar(
                        select(KnowledgeChunk.id).where(KnowledgeChunk.document_id == document.id)
                    )
            if rebuild_chunks:
                db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
                for index, text in enumerate(_chunks(document_data["content"])):
                    db.add(
                        KnowledgeChunk(
                            source_id=source.id,
                            document_id=document.id,
                            chunk_index=index,
                            text=text,
                            checksum=_hash(text),
                            embedding=embed_text(text),
                            metadata_json={
                                **document_data["metadata"],
                                "embedding_version": EMBEDDING_VERSION,
                                "bundle_version": bundle["bundle_version"],
                            },
                        )
                    )
                    ingested += 1
        for document in db.scalars(
            select(KnowledgeDocument).where(KnowledgeDocument.source_id == source.id)
        ):
            document.is_active = (document.external_id, document.version) in active_documents
    for source in db.scalars(select(KnowledgeSource)):
        if source.slug not in active_slugs:
            source.is_active = False
    db.commit()
    return ingested


def deactivate_source(db: Session, slug: str) -> bool:
    source = db.scalar(select(KnowledgeSource).where(KnowledgeSource.slug == slug))
    if source is None:
        return False
    source.is_active = False
    db.commit()
    return True


if __name__ == "__main__":
    with SessionLocal() as session:
        ingest_builtin_knowledge(session)
