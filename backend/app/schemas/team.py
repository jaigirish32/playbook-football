from uuid import UUID
from pydantic import BaseModel
from app.models.team import LeagueEnum


class TeamCreate(BaseModel):
    name             : str
    abbreviation     : str
    league           : LeagueEnum = LeagueEnum.NFL
    conference       : str | None = None
    division         : str | None = None
    stadium          : str | None = None
    stadium_surface  : str | None = None
    stadium_city     : str | None = None
    stadium_capacity : int | None = None
    nickname         : str | None = None
    website          : str | None = None
    logo_url         : str | None = None


class TeamUpdate(BaseModel):
    name             : str | None = None
    abbreviation     : str | None = None
    conference       : str | None = None
    division         : str | None = None
    stadium          : str | None = None
    stadium_surface  : str | None = None
    stadium_city     : str | None = None
    stadium_capacity : int | None = None
    nickname         : str | None = None
    website          : str | None = None
    logo_url         : str | None = None


class CoachSummary(BaseModel):
    id              : UUID
    name            : str
    years_with_team : int
    record_su_wins  : int
    record_su_losses: int

    class Config:
        from_attributes = True


class SeasonStatSummary(BaseModel):
    season_year : int
    su_wins     : int
    su_losses   : int
    ats_wins    : int
    ats_losses  : int
    ats_pushes  : int
    ou_overs    : int
    ou_unders   : int

    class Config:
        from_attributes = True


class TeamOut(BaseModel):
    id               : UUID
    name             : str
    abbreviation     : str
    league           : LeagueEnum
    conference       : str | None
    division         : str | None
    stadium          : str | None
    stadium_surface  : str | None
    stadium_city     : str | None
    stadium_capacity : int | None
    nickname         : str | None = None
    website          : str | None
    logo_url         : str | None
    coach            : CoachSummary | None
    season_stats     : list[SeasonStatSummary]

    class Config:
        from_attributes = True


class TeamListOut(BaseModel):
    id           : UUID
    name         : str
    abbreviation : str
    league       : LeagueEnum
    conference   : str | None
    division     : str | None

    class Config:
        from_attributes = True