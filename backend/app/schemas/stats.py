from uuid import UUID
from pydantic import BaseModel


class SeasonStatOut(BaseModel):
    id                 : UUID
    team_id            : UUID
    season_year        : int
    su_wins            : int
    su_losses          : int
    ats_wins           : int
    ats_losses         : int
    ats_pushes         : int
    div_su_wins        : int
    div_su_losses      : int
    div_ats_wins       : int
    div_ats_losses     : int
    home_fav_ats_w     : int
    home_fav_ats_l     : int
    home_dog_ats_w     : int
    home_dog_ats_l     : int
    road_fav_ats_w     : int
    road_fav_ats_l     : int
    road_dog_ats_w     : int
    road_dog_ats_l     : int
    ou_overs           : int
    ou_unders          : int
    ou_pushes          : int
    points_for_avg     : float | None
    points_against_avg : float | None
    off_pass_avg       : float | None
    off_rush_avg       : float | None
    off_total_avg      : float | None
    def_pass_avg       : float | None
    def_rush_avg       : float | None
    def_total_avg      : float | None
    off_ypr        : float | None = None
    def_ypr        : float | None = None
    ret_off_starters : int | None = None
    ret_def_starters : int | None = None
    recruit_rank     : int | None = None
    recruit_5star    : int | None = None
    recruit_4star    : int | None = None
    recruit_3star    : int | None = None
    recruit_total    : int | None = None

    class Config:
        from_attributes = True


class SeasonStatUpdate(BaseModel):
    su_wins            : int | None = None
    su_losses          : int | None = None
    ats_wins           : int | None = None
    ats_losses         : int | None = None
    ats_pushes         : int | None = None
    div_su_wins        : int | None = None
    div_su_losses      : int | None = None
    div_ats_wins       : int | None = None
    div_ats_losses     : int | None = None
    home_fav_ats_w     : int | None = None
    home_fav_ats_l     : int | None = None
    home_dog_ats_w     : int | None = None
    home_dog_ats_l     : int | None = None
    road_fav_ats_w     : int | None = None
    road_fav_ats_l     : int | None = None
    road_dog_ats_w     : int | None = None
    road_dog_ats_l     : int | None = None
    ou_overs           : int | None = None
    ou_unders          : int | None = None
    ou_pushes          : int | None = None
    points_for_avg     : float | None = None
    points_against_avg : float | None = None
    off_pass_avg       : float | None = None
    off_rush_avg       : float | None = None
    off_total_avg      : float | None = None
    def_pass_avg       : float | None = None
    def_rush_avg       : float | None = None
    def_total_avg      : float | None = None


class SOSStatOut(BaseModel):
    id             : UUID
    team_id        : UUID
    season_year    : int
    sos_rank       : int | None
    team_win_total : float | None
    foe_win_total  : float | None
    vs_div_wins    : float | None
    vs_nondiv_wins : float | None
    opp_win_pct    : float | None
   
    class Config:
        from_attributes = True


class SOSStatUpdate(BaseModel):
    sos_rank       : int | None   = None
    team_win_total : float | None = None
    foe_win_total  : float | None = None
    vs_div_wins    : float | None = None
    vs_nondiv_wins : float | None = None
    opp_win_pct    : float | None = None


class TrendOut(BaseModel):
    id          : UUID
    team_id     : UUID
    season_year : int
    good_trends : str | None
    bad_trends  : str | None
    ugly_trends : str | None
    ou_trends   : str | None

    class Config:
        from_attributes = True


class TrendUpdate(BaseModel):
    good_trends : str | None = None
    bad_trends  : str | None = None
    ugly_trends : str | None = None
    ou_trends   : str | None = None

class ScheduleGameOut(BaseModel):
    id            : UUID
    team_id       : UUID
    season_year   : int
    game_num      : int
    opponent      : str | None = None
    game_date     : str | None = None
    is_home       : bool = True
    opp_record    : str | None = None
    adv           : float | None = None
    line          : float | None = None
    points_for    : int | None = None
    points_against: int | None = None
    su_result     : str | None = None
    ats_result    : str | None = None
    ou_result     : str | None = None
    ou_line       : float | None = None
    ats_scorecard : str | None = None

    class Config:
        from_attributes = True

class TeamPlaybookOut(BaseModel):
    id                 : UUID
    team_id            : UUID
    season_year        : int
    team_theme         : str | None = None
    win_total          : float | None = None
    win_total_odds     : str | None = None
    opp_win_total      : float | None = None
    playoff_yes_odds   : str | None = None
    playoff_no_odds    : str | None = None
    narrative          : str | None = None
    stat_you_will_like : str | None = None
    power_play         : str | None = None
    coaches_corner     : str | None = None
    q1_trends          : str | None = None
    q2_trends          : str | None = None
    q3_trends          : str | None = None
    q4_trends          : str | None = None
    division_data      : str | None = None
    draft_grades    : str | None = None
    first_round     : str | None = None
    steal_of_draft  : str | None = None
    

    class Config:
        from_attributes = True

class ATSHistoryOut(BaseModel):
    id             : UUID
    team_id        : UUID
    season_year    : int
    coach_name     : str | None = None
    game_num       : int
    opponent       : str | None = None
    is_home        : bool = True
    is_neutral     : bool = False
    is_playoff     : bool = False
    points_for     : int | None = None
    points_against : int | None = None
    su_result      : str | None = None
    line           : float | None = None
    ats_result     : str | None = None
    ou_result      : str | None = None
    ou_line        : float | None = None
    game_type      : str | None = None

    class Config:
        from_attributes = True