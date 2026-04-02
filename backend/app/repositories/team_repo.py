from sqlalchemy.orm import Session, joinedload
from app.models.team import Team, LeagueEnum


def get_all_teams(
    db        : Session,
    league    : LeagueEnum = LeagueEnum.NFL,
    division  : str | None = None,
    conference: str | None = None,
) -> list[Team]:
    q = (
        db.query(Team)
        .options(
            joinedload(Team.coach),
            joinedload(Team.season_stats),
        )
        .filter(Team.league == league, Team.is_active == True)
    )
    if division:
        q = q.filter(Team.division == division)
    if conference:
        q = q.filter(Team.conference == conference)
    return q.order_by(Team.name).all()


def get_team_by_id(db: Session, team_id: str) -> Team | None:
    return (
        db.query(Team)
        .options(
            joinedload(Team.coach),
            joinedload(Team.season_stats),
            joinedload(Team.sos_stats),
            joinedload(Team.trends),
        )
        .filter(Team.id == team_id)
        .first()
    )


def get_team_by_abbreviation(
    db          : Session,
    abbreviation: str,
    league      : LeagueEnum = LeagueEnum.NFL,
) -> Team | None:
    return db.query(Team).filter(
        Team.abbreviation == abbreviation,
        Team.league == league,
    ).first()


def create_team(db: Session, team: Team) -> Team:
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def update_team(db: Session, team: Team, data: dict) -> Team:
    for field, value in data.items():
        setattr(team, field, value)
    db.commit()
    db.refresh(team)
    return team


def delete_team(db: Session, team: Team) -> None:
    db.delete(team)
    db.commit()


def upsert_team(db: Session, data: dict) -> Team:
    """
    Used by ingest.py — insert or update based on abbreviation + league.
    """
    team = get_team_by_abbreviation(
        db,
        data["abbreviation"],
        data.get("league", LeagueEnum.NFL),
    )
    if team:
        return update_team(db, team, data)
    team = Team(**data)
    return create_team(db, team)

def get_team_by_name(
    db    : Session,
    name  : str,
    league: LeagueEnum = LeagueEnum.NFL,
) -> Team | None:
    return db.query(Team).filter(
        Team.name == name,
        Team.league == league,
    ).first()

def upsert_team_by_name(db: Session, data: dict) -> Team:
    """
    Insert or update based on name + league (used for CFB teams).
    """
    team = get_team_by_name(
        db,
        data["name"],
        data.get("league", LeagueEnum.NFL),
    )
    if team:
        return update_team(db, team, data)
    team = Team(**data)
    return create_team(db, team)