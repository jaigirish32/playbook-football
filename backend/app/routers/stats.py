from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user, require_admin
from app.models.stats import TeamPlaybook
from app.schemas.stats import TeamPlaybookOut
from app.models.stats import ATSHistory
from app.schemas.stats import ATSHistoryOut
from app.repositories.stats_repo import (
    get_season_stats_by_team,
    get_stat_by_id,
    update_season_stat,
    get_sos_stats_by_team,
    get_trend,
    update_trend,
)
from app.schemas.stats import (
    SeasonStatOut, SeasonStatUpdate,
    SOSStatOut, TrendOut, TrendUpdate,
    ScheduleGameOut,
)

from app.models.stats import ScheduleGame, GameLog, DraftPick

router = APIRouter()


# ── Season stats ──────────────────────────────────────────────

@router.get(
    "/season/{team_id}",
    response_model=list[SeasonStatOut],
)
def get_team_season_stats(
    team_id: UUID,
    db     : Session = Depends(get_db),
    _               = Depends(get_current_user),
):
    return get_season_stats_by_team(db, str(team_id))


@router.put(
    "/season/{stat_id}",
    response_model=SeasonStatOut,
)
def update_stat(
    stat_id: UUID,
    body   : SeasonStatUpdate,
    db     : Session = Depends(get_db),
    _              = Depends(require_admin),
):
    stat = get_stat_by_id(db, str(stat_id))
    if not stat:
        raise HTTPException(status_code=404, detail="Stat not found")
    return update_season_stat(
        db, stat, body.model_dump(exclude_none=True)
    )


# ── SOS stats ─────────────────────────────────────────────────

@router.get(
    "/sos/{team_id}",
    response_model=list[SOSStatOut],
)
def get_team_sos_stats(
    team_id: UUID,
    db     : Session = Depends(get_db),
    _               = Depends(get_current_user),
):
    return get_sos_stats_by_team(db, str(team_id))


# ── Trends ────────────────────────────────────────────────────

@router.get(
    "/trends/{team_id}/{year}",
    response_model=TrendOut,
)
def get_team_trends(
    team_id: UUID,
    year   : int,
    db     : Session = Depends(get_db),
    _               = Depends(get_current_user),
):
    trend = get_trend(db, str(team_id), year)
    if not trend:
        raise HTTPException(status_code=404, detail="Trends not found")
    return trend


@router.put(
    "/trends/{team_id}/{year}",
    response_model=TrendOut,
)
def update_team_trends(
    team_id: UUID,
    year   : int,
    body   : TrendUpdate,
    db     : Session = Depends(get_db),
    _              = Depends(require_admin),
):
    trend = get_trend(db, str(team_id), year)
    if not trend:
        raise HTTPException(status_code=404, detail="Trends not found")
    return update_trend(
        db, trend, body.model_dump(exclude_none=True)
    )

@router.get("/schedule/{team_id}", response_model=list[ScheduleGameOut])
def get_team_schedule(
    team_id: UUID,
    year   : int = Query(2025),
    db     : Session = Depends(get_db),
    _               = Depends(get_current_user),
):
    return db.query(ScheduleGame).filter(
        ScheduleGame.team_id == str(team_id),
        ScheduleGame.season_year == year,
    ).order_by(ScheduleGame.game_num).all()


@router.get("/gamelogs/{team_id}")
def get_team_gamelogs(
    team_id: UUID,
    year   : int = Query(2024),
    db     : Session = Depends(get_db),
    _               = Depends(get_current_user),
):
    return db.query(GameLog).filter(
        GameLog.team_id == str(team_id),
        GameLog.season_year == year,
    ).order_by(GameLog.game_num).all()


@router.get("/draftpicks/{team_id}")
def get_team_draftpicks(
    team_id   : UUID,
    draft_year: int = Query(2025),
    db        : Session = Depends(get_db),
    _                  = Depends(get_current_user),
):
    return db.query(DraftPick).filter(
        DraftPick.team_id == str(team_id),
        DraftPick.draft_year == draft_year,
    ).order_by(DraftPick.round_num).all()

@router.get("/playbook/{team_id}", response_model=list[TeamPlaybookOut])
def get_team_playbook(
    team_id    : UUID,
    season_year: int = Query(2025),
    db         : Session = Depends(get_db),
    _                   = Depends(get_current_user),
):
    return db.query(TeamPlaybook).filter(
        TeamPlaybook.team_id == str(team_id),
        TeamPlaybook.season_year == season_year,
    ).all()

@router.get("/ats-history/{team_id}", response_model=list[ATSHistoryOut])
def get_ats_history(
    team_id    : UUID,
    season_year: int = Query(2024),
    db         : Session = Depends(get_db),
    _                   = Depends(get_current_user),
):
    return db.query(ATSHistory).filter(
        ATSHistory.team_id == str(team_id),
        ATSHistory.season_year == season_year,
    ).order_by(ATSHistory.game_num).all()