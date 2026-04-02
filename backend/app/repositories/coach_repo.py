from sqlalchemy.orm import Session, joinedload
from app.models.coach import Coach, CoachStat


def get_coach_by_team(db: Session, team_id: str) -> Coach | None:
    return (
        db.query(Coach)
        .options(joinedload(Coach.coach_stats))
        .filter(Coach.team_id == team_id)
        .first()
    )


def create_coach(db: Session, coach: Coach) -> Coach:
    db.add(coach)
    db.commit()
    db.refresh(coach)
    return coach


def update_coach(db: Session, coach: Coach, data: dict) -> Coach:
    for field, value in data.items():
        setattr(coach, field, value)
    db.commit()
    db.refresh(coach)
    return coach


def upsert_coach(db: Session, team_id: str, data: dict) -> Coach:
    """
    Used by ingest.py — insert or update coach for a team.
    """
    coach = get_coach_by_team(db, team_id)
    if coach:
        return update_coach(db, coach, data)
    coach = Coach(team_id=team_id, **data)
    return create_coach(db, coach)


def upsert_coach_stats(
    db      : Session,
    coach_id: str,
    data    : dict,
) -> CoachStat:
    stat = db.query(CoachStat).filter(
        CoachStat.coach_id == coach_id
    ).first()
    if stat:
        for field, value in data.items():
            setattr(stat, field, value)
        db.commit()
        db.refresh(stat)
        return stat
    stat = CoachStat(coach_id=coach_id, **data)
    db.add(stat)
    db.commit()
    db.refresh(stat)
    return stat