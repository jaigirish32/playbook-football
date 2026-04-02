from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user, require_admin
from app.repositories.coach_repo import (
    get_coach_by_team,
    update_coach,
    upsert_coach_stats,
)
from app.schemas.coach import (
    CoachOut,
    CoachUpdate,
    CoachStatUpdate,
    CoachStatOut,
)

router = APIRouter()


@router.get(
    "/{team_id}",
    response_model=CoachOut,
)
def get_coach(
    team_id: UUID,
    db     : Session = Depends(get_db),
    _               = Depends(get_current_user),
):
    coach = get_coach_by_team(db, str(team_id))
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    return coach


@router.put(
    "/{team_id}",
    response_model=CoachOut,
)
def update_coach_info(
    team_id: UUID,
    body   : CoachUpdate,
    db     : Session = Depends(get_db),
    _              = Depends(require_admin),
):
    coach = get_coach_by_team(db, str(team_id))
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    return update_coach(
        db, coach, body.model_dump(exclude_none=True)
    )


@router.put(
    "/{team_id}/stats",
    response_model=CoachStatOut,
)
def update_coach_stats(
    team_id: UUID,
    body   : CoachStatUpdate,
    db     : Session = Depends(get_db),
    _              = Depends(require_admin),
):
    coach = get_coach_by_team(db, str(team_id))
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    return upsert_coach_stats(
        db,
        str(coach.id),
        body.model_dump(exclude_none=True),
    )