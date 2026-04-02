from uuid import UUID
from pydantic import BaseModel


class CoachCreate(BaseModel):
    name            : str
    years_with_team : int = 1
    record_su_wins  : int = 0
    record_su_losses: int = 0


class CoachUpdate(BaseModel):
    name            : str | None = None
    years_with_team : int | None = None
    record_su_wins  : int | None = None
    record_su_losses: int | None = None


class CoachStatUpdate(BaseModel):
    home_ats_w    : int | None = None
    home_ats_l    : int | None = None
    away_ats_w    : int | None = None
    away_ats_l    : int | None = None
    fav_ats_w     : int | None = None
    fav_ats_l     : int | None = None
    dog_ats_w     : int | None = None
    dog_ats_l     : int | None = None
    rest_ats_w    : int | None = None
    rest_ats_l    : int | None = None
    rev_ats_w     : int | None = None
    rev_ats_l     : int | None = None
    vs_rev_ats_w  : int | None = None
    vs_rev_ats_l  : int | None = None
    off_win_ats_w  : int | None = None
    off_win_ats_l  : int | None = None
    off_loss_ats_w : int | None = None
    off_loss_ats_l : int | None = None
    div_ats_w     : int | None = None
    div_ats_l     : int | None = None
    ndiv_ats_w    : int | None = None
    ndiv_ats_l    : int | None = None
    allow35_ats_w : int | None = None
    allow35_ats_l : int | None = None
    score35_ats_w : int | None = None
    score35_ats_l : int | None = None


class CoachStatOut(BaseModel):
    home_ats_w    : int
    home_ats_l    : int
    away_ats_w    : int
    away_ats_l    : int
    fav_ats_w     : int
    fav_ats_l     : int
    dog_ats_w     : int
    dog_ats_l     : int
    rest_ats_w    : int
    rest_ats_l    : int
    rev_ats_w     : int
    rev_ats_l     : int
    vs_rev_ats_w  : int
    vs_rev_ats_l  : int
    off_win_ats_w  : int
    off_win_ats_l  : int
    off_loss_ats_w : int
    off_loss_ats_l : int
    div_ats_w     : int
    div_ats_l     : int
    ndiv_ats_w    : int
    ndiv_ats_l    : int
    allow35_ats_w : int
    allow35_ats_l : int
    score35_ats_w : int
    score35_ats_l : int

    class Config:
        from_attributes = True


class CoachOut(BaseModel):
    id               : UUID
    name             : str
    years_with_team  : int
    record_su_wins   : int
    record_su_losses : int
    record_ats_wins   : int | None = None
    record_ats_losses : int | None = None
    record_ats_pushes : int | None = None
    rpr               : int | None = None
    rpr_off           : int | None = None
    rpr_def           : int | None = None
    ret_off_starters  : int | None = None
    ret_def_starters  : int | None = None
    recruit_rank_2025 : int | None = None
    coach_stats      : CoachStatOut | None
    class Config:
        from_attributes = True