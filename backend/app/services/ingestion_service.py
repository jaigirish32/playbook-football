"""
ingestion_service.py
Orchestrates the full PDF ingestion pipeline:
  1. Analyze PDF with Azure DI
  2. Classify each page
  3. Parse team data, coach data, SOS data
  4. Upsert into database
  5. Generate embeddings for chatbot

Called by ingest.py — runs once per season.
"""

from sqlalchemy.orm import Session
from app.services.azure_di import (
    analyze_pdf,
    extract_tables,
    extract_page_text,
    get_low_confidence_pages,
)
from app.services.azure_openai import (
    get_embedding,
    build_team_embedding_text,
)
from app.repositories.team_repo import upsert_team
from app.repositories.coach_repo import upsert_coach, upsert_coach_stats
from app.repositories.stats_repo import upsert_season_stat, upsert_sos_stat


def run_ingestion(db: Session, pdf_path: str) -> dict:
    """
    Main entry point called by ingest.py.
    Returns a summary of what was ingested.
    """
    print(f"Analyzing PDF: {pdf_path}")
    result = analyze_pdf(pdf_path)

    total_pages    = len(result.pages)
    flagged_pages  = get_low_confidence_pages(result, threshold=0.80)

    print(f"Total pages  : {total_pages}")
    print(f"Flagged pages: {flagged_pages}")

    summary = {
        "total_pages"  : total_pages,
        "flagged_pages": flagged_pages,
        "teams_upserted": 0,
        "stats_upserted": 0,
        "errors"        : [],
    }

    # Tables extracted from the full document
    tables = extract_tables(result)

    # --- Ingest coaches data chart (pages 8-9 in PDF) ---
    # This will be expanded in ingest.py with exact page mapping
    print("Ingestion service ready.")
    print("Page-level parsing handled in ingest.py")

    return summary


def generate_embeddings_for_all_teams(db: Session) -> int:
    """
    After ingestion — generate pgvector embeddings
    for every season_stat row that doesn't have one yet.
    Returns count of embeddings generated.
    """
    from app.models.stats import SeasonStat
    from app.models.team import Team

    stats = (
        db.query(SeasonStat)
        .join(Team)
        .filter(SeasonStat.embedding == None)
        .all()
    )

    count = 0
    for stat in stats:
        try:
            text = build_team_embedding_text(
                team_name = stat.team.name,
                year      = stat.season_year,
                stat      = {
                    "su_wins"       : stat.su_wins,
                    "su_losses"     : stat.su_losses,
                    "ats_wins"      : stat.ats_wins,
                    "ats_losses"    : stat.ats_losses,
                    "ats_pushes"    : stat.ats_pushes,
                    "ou_overs"      : stat.ou_overs,
                    "ou_unders"     : stat.ou_unders,
                    "home_fav_ats_w": stat.home_fav_ats_w,
                    "home_fav_ats_l": stat.home_fav_ats_l,
                    "home_dog_ats_w": stat.home_dog_ats_w,
                    "home_dog_ats_l": stat.home_dog_ats_l,
                    "road_fav_ats_w": stat.road_fav_ats_w,
                    "road_fav_ats_l": stat.road_fav_ats_l,
                    "road_dog_ats_w": stat.road_dog_ats_w,
                    "road_dog_ats_l": stat.road_dog_ats_l,
                },
            )
            stat.embedding = get_embedding(text)
            db.commit()
            count += 1
            print(f"Embedded: {stat.team.name} {stat.season_year}")
        except Exception as e:
            print(f"Failed embedding {stat.id}: {e}")

    return count