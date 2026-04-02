from sqlalchemy.orm import Session
from app.models.stats import SeasonStat, SOSStat, TeamTrend


# ── Season Stats ──────────────────────────────────────────────

def get_season_stats_by_team(
    db     : Session,
    team_id: str,
) -> list[SeasonStat]:
    return (
        db.query(SeasonStat)
        .filter(SeasonStat.team_id == team_id)
        .order_by(SeasonStat.season_year.desc())
        .all()
    )


def get_season_stat(
    db         : Session,
    team_id    : str,
    season_year: int,
) -> SeasonStat | None:
    return db.query(SeasonStat).filter(
        SeasonStat.team_id   == team_id,
        SeasonStat.season_year == season_year,
    ).first()


def upsert_season_stat(
    db         : Session,
    team_id    : str,
    season_year: int,
    data       : dict,
) -> SeasonStat:
    stat = get_season_stat(db, team_id, season_year)
    if stat:
        for field, value in data.items():
            setattr(stat, field, value)
        db.commit()
        db.refresh(stat)
        return stat
    stat = SeasonStat(team_id=team_id, season_year=season_year, **data)
    db.add(stat)
    db.commit()
    db.refresh(stat)
    return stat


def update_season_stat(
    db  : Session,
    stat: SeasonStat,
    data: dict,
) -> SeasonStat:
    for field, value in data.items():
        setattr(stat, field, value)
    db.commit()
    db.refresh(stat)
    return stat


def get_stat_by_id(db: Session, stat_id: str) -> SeasonStat | None:
    return db.query(SeasonStat).filter(
        SeasonStat.id == stat_id
    ).first()


# ── SOS Stats ─────────────────────────────────────────────────

def get_sos_stats_by_team(
    db     : Session,
    team_id: str,
) -> list[SOSStat]:
    return (
        db.query(SOSStat)
        .filter(SOSStat.team_id == team_id)
        .order_by(SOSStat.season_year.desc())
        .all()
    )


def upsert_sos_stat(
    db         : Session,
    team_id    : str,
    season_year: int,
    data       : dict,
) -> SOSStat:
    stat = db.query(SOSStat).filter(
        SOSStat.team_id    == team_id,
        SOSStat.season_year == season_year,
    ).first()
    if stat:
        for field, value in data.items():
            setattr(stat, field, value)
        db.commit()
        db.refresh(stat)
        return stat
    stat = SOSStat(team_id=team_id, season_year=season_year, **data)
    db.add(stat)
    db.commit()
    db.refresh(stat)
    return stat


# ── Team Trends ───────────────────────────────────────────────

def get_trend(
    db         : Session,
    team_id    : str,
    season_year: int,
) -> TeamTrend | None:
    return db.query(TeamTrend).filter(
        TeamTrend.team_id    == team_id,
        TeamTrend.season_year == season_year,
    ).first()


def upsert_trend(
    db         : Session,
    team_id    : str,
    season_year: int,
    data       : dict,
) -> TeamTrend:
    trend = get_trend(db, team_id, season_year)
    if trend:
        for field, value in data.items():
            setattr(trend, field, value)
        db.commit()
        db.refresh(trend)
        return trend
    trend = TeamTrend(team_id=team_id, season_year=season_year, **data)
    db.add(trend)
    db.commit()
    db.refresh(trend)
    return trend


def update_trend(
    db   : Session,
    trend: TeamTrend,
    data : dict,
) -> TeamTrend:
    for field, value in data.items():
        setattr(trend, field, value)
    db.commit()
    db.refresh(trend)
    return trend