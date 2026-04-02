import hashlib
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.cache import AICache


def make_cache_key(question: str) -> str:
    return hashlib.md5(
        question.strip().lower().encode()
    ).hexdigest()


def get_cached_response(
    db          : Session,
    question    : str,
) -> AICache | None:
    key = make_cache_key(question)
    now = datetime.now(timezone.utc)
    return db.query(AICache).filter(
        AICache.question_hash == key,
        AICache.expires_at    >  now,
    ).first()


def save_cached_response(
    db          : Session,
    question    : str,
    response    : str,
    ttl_hours   : int = 24,
) -> AICache:
    from datetime import timedelta
    key = make_cache_key(question)
    now = datetime.now(timezone.utc)

    db.merge(AICache(
        question_hash = key,
        question      = question,
        response      = response,
        created_at    = now,
        expires_at    = now + timedelta(hours=ttl_hours),
    ))
    db.commit()


def vector_search(
    db          : Session,
    question_vec: list[float],
    limit       : int = 12,
) -> list:
    """
    pgvector cosine similarity search.
    Returns season_stat IDs ordered by relevance.
    """
    vec_str = "[" + ",".join(str(v) for v in question_vec) + "]"
    rows = db.execute(
        text("""
            SELECT id
            FROM season_stats
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :limit
        """),
        {"vec": vec_str, "limit": limit},
    ).fetchall()
    return [row[0] for row in rows]


def clean_expired_cache(db: Session) -> int:
    """
    Delete expired cache rows.
    Call this periodically — e.g. once a day.
    """
    now = datetime.now(timezone.utc)
    deleted = db.query(AICache).filter(
        AICache.expires_at < now
    ).delete()
    db.commit()
    return deleted