from sqlalchemy.orm import Session, joinedload
from app.models.stats import SeasonStat
from app.models.team import Team, LeagueEnum
from app.repositories.chat_repo import (
    get_cached_response,
    save_cached_response,
    vector_search,
)
from app.services.azure_openai import get_embedding, chat_completion

SYSTEM_PROMPT = """You are the Playbook Football assistant.
You are an expert on NFL and CFB stats, ATS records, 
strength of schedule, and betting trends.
Answer questions using ONLY the stats data provided.
Be specific — cite win-loss records, ATS percentages, 
and relevant splits. Keep answers concise and direct.
If the data is insufficient to answer, say so clearly."""


def build_context(stats_rows: list) -> tuple[str, list[str]]:
    """
    Convert DB rows into plain text context for the LLM.
    Returns the context string and list of team names used.
    """
    lines = []
    names = []

    for row in stats_rows:
        ats_total = row.ats_wins + row.ats_losses
        ats_pct   = round(row.ats_wins / max(ats_total, 1) * 100, 1)

        line = (
            f"{row.team.name} {row.season_year}: "
            f"SU {row.su_wins}-{row.su_losses} | "
            f"ATS {row.ats_wins}-{row.ats_losses}-{row.ats_pushes} ({ats_pct}%) | "
            f"O/U {row.ou_overs}-{row.ou_unders} | "
            f"Home dog ATS {row.home_dog_ats_w}-{row.home_dog_ats_l} | "
            f"Road dog ATS {row.road_dog_ats_w}-{row.road_dog_ats_l} | "
            f"Home fav ATS {row.home_fav_ats_w}-{row.home_fav_ats_l}"
        )
        lines.append(line)

        if row.team.name not in names:
            names.append(row.team.name)

    return "\n".join(lines), names


def answer_question(db: Session, question: str) -> dict:
    """
    Main chatbot function.
    1. Check cache
    2. Embed question
    3. Vector search
    4. Build context
    5. Call GPT-4o-mini
    6. Cache and return
    """

    # Step 1 — check cache
    cached = get_cached_response(db, question)
    if cached:
        return {
            "answer" : cached.response,
            "cached" : True,
            "sources": [],
        }

    # Step 2 — embed the question
    question_vec = get_embedding(question)

    # Step 3 — vector search in pgvector
    stat_ids = vector_search(db, question_vec, limit=12)

    # Step 4 — fetch matching rows with team info
    if stat_ids:
        stats_rows = (
            db.query(SeasonStat)
            .options(joinedload(SeasonStat.team))
            .filter(SeasonStat.id.in_(stat_ids))
            .all()
        )
    else:
        # Fallback — return recent NFL stats if no embeddings exist yet
        stats_rows = (
            db.query(SeasonStat)
            .join(Team)
            .options(joinedload(SeasonStat.team))
            .filter(Team.league == LeagueEnum.NFL)
            .order_by(SeasonStat.season_year.desc())
            .limit(12)
            .all()
        )

    # Step 5 — build context and call GPT-4o-mini
    context, source_names = build_context(stats_rows)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role"   : "user",
            "content": f"Question: {question}\n\nStats data:\n{context}",
        },
    ]

    answer = chat_completion(messages, max_tokens=500, temperature=0.2)

    # Step 6 — cache for 24 hours
    save_cached_response(db, question, answer, ttl_hours=24)

    return {
        "answer" : answer,
        "cached" : False,
        "sources": source_names,
    }