from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user, require_admin
from app.models.team import LeagueEnum, Team
from app.repositories.team_repo import (
    get_all_teams,
    get_team_by_id,
    get_team_by_abbreviation,
    create_team,
    update_team,
    delete_team,
)
from app.schemas.team import TeamCreate, TeamUpdate, TeamOut, TeamListOut

router = APIRouter()


# ── Static routes first (must come before /{team_id}) ─────────

@router.get(
    "/search",
    response_model=list[TeamListOut],
)
def search_teams(
    q     : str        = Query(..., min_length=2),
    league: LeagueEnum = Query(LeagueEnum.NFL),
    db    : Session    = Depends(get_db),
    _                  = Depends(get_current_user),
):
    return (
        db.query(Team)
        .filter(
            Team.league == league,
            Team.name.ilike(f"%{q}%"),
            Team.is_active == True,
        )
        .order_by(Team.name)
        .limit(10)
        .all()
    )


@router.get(
    "/abbr/{abbreviation}",
    response_model=TeamOut,
)
def get_team_by_abbr(
    abbreviation: str,
    league      : LeagueEnum = Query(LeagueEnum.NFL),
    db          : Session    = Depends(get_db),
    _                        = Depends(get_current_user),
):
    team = get_team_by_abbreviation(db, abbreviation.upper(), league)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


# ── List / Create ──────────────────────────────────────────────

@router.get(
    "",
    response_model=list[TeamListOut],
)
def list_teams(
    league    : LeagueEnum = Query(LeagueEnum.NFL),
    division  : str | None = Query(None),
    conference: str | None = Query(None),
    db        : Session    = Depends(get_db),
    _                      = Depends(get_current_user),
):
    return get_all_teams(db, league, division, conference)


@router.post(
    "",
    response_model=TeamOut,
    status_code=201,
)
def create_new_team(
    body: TeamCreate,
    db  : Session = Depends(get_db),
    _           = Depends(require_admin),
):
    team = Team(**body.model_dump())
    return create_team(db, team)


# ── Single team by ID ──────────────────────────────────────────

@router.get(
    "/{team_id}",
    response_model=TeamOut,
)
def get_team(
    team_id: UUID,
    db     : Session = Depends(get_db),
    _               = Depends(get_current_user),
):
    team = get_team_by_id(db, str(team_id))
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.put(
    "/{team_id}",
    response_model=TeamOut,
)
def update_existing_team(
    team_id: UUID,
    body   : TeamUpdate,
    db     : Session = Depends(get_db),
    _              = Depends(require_admin),
):
    team = get_team_by_id(db, str(team_id))
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return update_team(db, team, body.model_dump(exclude_none=True))


@router.delete(
    "/{team_id}",
    status_code=204,
)
def delete_existing_team(
    team_id: UUID,
    db     : Session = Depends(get_db),
    _              = Depends(require_admin),
):
    team = get_team_by_id(db, str(team_id))
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    delete_team(db, team)