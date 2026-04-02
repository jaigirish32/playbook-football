import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class SeasonStat(Base):
    __tablename__ = "season_stats"

    id           : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id      : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    season_year  : Mapped[int]            = mapped_column(Integer, nullable=False)

    # Straight Up
    su_wins      : Mapped[int]            = mapped_column(Integer, default=0)
    su_losses    : Mapped[int]            = mapped_column(Integer, default=0)

    # ATS overall
    ats_wins     : Mapped[int]            = mapped_column(Integer, default=0)
    ats_losses   : Mapped[int]            = mapped_column(Integer, default=0)
    ats_pushes   : Mapped[int]            = mapped_column(Integer, default=0)

    # Division record
    div_su_wins   : Mapped[int]           = mapped_column(Integer, default=0)
    div_su_losses : Mapped[int]           = mapped_column(Integer, default=0)
    div_ats_wins  : Mapped[int]           = mapped_column(Integer, default=0)
    div_ats_losses: Mapped[int]           = mapped_column(Integer, default=0)

    # Home / Away ATS splits
    home_fav_ats_w : Mapped[int]          = mapped_column(Integer, default=0)
    home_fav_ats_l : Mapped[int]          = mapped_column(Integer, default=0)
    home_dog_ats_w : Mapped[int]          = mapped_column(Integer, default=0)
    home_dog_ats_l : Mapped[int]          = mapped_column(Integer, default=0)
    road_fav_ats_w : Mapped[int]          = mapped_column(Integer, default=0)
    road_fav_ats_l : Mapped[int]          = mapped_column(Integer, default=0)
    road_dog_ats_w : Mapped[int]          = mapped_column(Integer, default=0)
    road_dog_ats_l : Mapped[int]          = mapped_column(Integer, default=0)

    # Over / Under
    ou_overs     : Mapped[int]            = mapped_column(Integer, default=0)
    ou_unders    : Mapped[int]            = mapped_column(Integer, default=0)
    ou_pushes    : Mapped[int]            = mapped_column(Integer, default=0)

    # Scoring averages
    points_for_avg      : Mapped[float | None] = mapped_column(Float)
    points_against_avg  : Mapped[float | None] = mapped_column(Float)

    # Yardage averages
    off_pass_avg  : Mapped[float | None]  = mapped_column(Float)
    off_rush_avg  : Mapped[float | None]  = mapped_column(Float)
    off_total_avg : Mapped[float | None]  = mapped_column(Float)
    def_pass_avg  : Mapped[float | None]  = mapped_column(Float)
    def_rush_avg  : Mapped[float | None]  = mapped_column(Float)
    def_total_avg : Mapped[float | None]  = mapped_column(Float)
    off_ypr        : Mapped[float | None] = mapped_column(Float, nullable=True)
    def_ypr        : Mapped[float | None] = mapped_column(Float, nullable=True)
    # CFB recruiting & returning starters
    ret_off_starters : Mapped[int | None] = mapped_column(Integer, nullable=True)
    ret_def_starters : Mapped[int | None] = mapped_column(Integer, nullable=True)
    recruit_rank     : Mapped[int | None] = mapped_column(Integer, nullable=True)
    recruit_5star    : Mapped[int | None] = mapped_column(Integer, nullable=True)
    recruit_4star    : Mapped[int | None] = mapped_column(Integer, nullable=True)
    recruit_3star    : Mapped[int | None] = mapped_column(Integer, nullable=True)
    recruit_total    : Mapped[int | None] = mapped_column(Integer, nullable=True)

    # pgvector embedding for chatbot
    embedding    : Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    updated_at   : Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="season_stats")

    __table_args__ = (
        UniqueConstraint("team_id", "season_year", name="uq_season_stat_team_year"),
        Index("ix_season_stats_team_year", "team_id", "season_year"),
    )

    def __repr__(self) -> str:
        return f"<SeasonStat team={self.team_id} year={self.season_year}>"


class SOSStat(Base):
    __tablename__ = "sos_stats"

    id             : Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id        : Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    season_year    : Mapped[int]           = mapped_column(Integer, nullable=False)
    sos_rank       : Mapped[int | None]    = mapped_column(Integer)
    team_win_total : Mapped[float | None]  = mapped_column(Float)
    foe_win_total  : Mapped[float | None]  = mapped_column(Float)
    vs_div_wins    : Mapped[float | None]  = mapped_column(Float)
    vs_nondiv_wins : Mapped[float | None]  = mapped_column(Float)
    opp_win_pct    : Mapped[float | None]  = mapped_column(Float)
    updated_at     : Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="sos_stats")

    __table_args__ = (
        UniqueConstraint("team_id", "season_year", name="uq_sos_team_year"),
    )

    def __repr__(self) -> str:
        return f"<SOSStat team={self.team_id} year={self.season_year}>"


class TeamTrend(Base):
    __tablename__ = "team_trends"

    id          : Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id     : Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    season_year : Mapped[int]        = mapped_column(Integer, nullable=False)
    good_trends : Mapped[str | None] = mapped_column(Text)
    bad_trends  : Mapped[str | None] = mapped_column(Text)
    ugly_trends : Mapped[str | None] = mapped_column(Text)
    ou_trends   : Mapped[str | None] = mapped_column(Text)
    updated_at  : Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="trends")

    __table_args__ = (
        UniqueConstraint("team_id", "season_year", name="uq_trend_team_year"),
    )

    def __repr__(self) -> str:
        return f"<TeamTrend team={self.team_id} year={self.season_year}>"

class ScheduleGame(Base):
    __tablename__ = "schedule_games"

    id           : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id      : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    season_year  : Mapped[int]            = mapped_column(Integer, nullable=False)
    game_num     : Mapped[int]            = mapped_column(Integer, nullable=False)  # 1-based game order

    # Game info
    opponent     : Mapped[str | None]     = mapped_column(Text)
    game_date    : Mapped[str | None]     = mapped_column(Text)   # "9/7" format
    is_home      : Mapped[bool]           = mapped_column(default=True)
    is_neutral   : Mapped[bool]           = mapped_column(default=False)

    # Opponent win-loss at time of game
    opp_record   : Mapped[str | None]     = mapped_column(Text)   # "5-12"

    # Line
    line         : Mapped[float | None]   = mapped_column(Float)  # negative = favorite

    adv : Mapped[float | None] = mapped_column(Float)  # opening spread

    # Result (blank for future games)
    points_for   : Mapped[int | None]     = mapped_column(Integer)
    points_against: Mapped[int | None]    = mapped_column(Integer)
    su_result    : Mapped[str | None]     = mapped_column(Text)   # "W" or "L"
    ats_result   : Mapped[str | None]     = mapped_column(Text)   # "W", "L", "P"
    ou_result    : Mapped[str | None]     = mapped_column(Text)   # "O", "U", "P"
    ou_line      : Mapped[float | None]   = mapped_column(Float)

    # ATS scorecard note e.g. "1-6 L7"
    ats_scorecard: Mapped[str | None]     = mapped_column(Text)

    updated_at   : Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    team: Mapped["Team"] = relationship("Team", back_populates="schedule_games")

    __table_args__ = (
        UniqueConstraint("team_id", "season_year", "game_num", name="uq_schedule_team_year_game"),
        Index("ix_schedule_team_year", "team_id", "season_year"),
    )


class GameLog(Base):
    __tablename__ = "game_logs"

    id           : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id      : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    season_year  : Mapped[int]            = mapped_column(Integer, nullable=False)
    game_num     : Mapped[int]            = mapped_column(Integer, nullable=False)

    # Game info
    opponent     : Mapped[str | None]     = mapped_column(Text)
    game_date    : Mapped[str | None]     = mapped_column(Text)
    is_home      : Mapped[bool]           = mapped_column(default=True)
    opp_record   : Mapped[str | None]     = mapped_column(Text)

    # Results
    points_for   : Mapped[int | None]     = mapped_column(Integer)
    points_against: Mapped[int | None]    = mapped_column(Integer)
    su_result    : Mapped[str | None]     = mapped_column(Text)
    line         : Mapped[float | None]   = mapped_column(Float)
    ats_result   : Mapped[str | None]     = mapped_column(Text)
    ou_line      : Mapped[float | None]   = mapped_column(Float)
    ou_result    : Mapped[str | None]     = mapped_column(Text)

    # Yardage stats
    off_ypr      : Mapped[float | None]   = mapped_column(Float)
    off_rush     : Mapped[int | None]     = mapped_column(Integer)
    off_pass     : Mapped[int | None]     = mapped_column(Integer)
    off_total    : Mapped[int | None]     = mapped_column(Integer)
    def_total    : Mapped[int | None]     = mapped_column(Integer)
    def_pass     : Mapped[int | None]     = mapped_column(Integer)
    def_rush     : Mapped[int | None]     = mapped_column(Integer)
    def_ypr      : Mapped[float | None]   = mapped_column(Float)

    # Score and first downs
    result_score : Mapped[str | None]     = mapped_column(Text)   # "28-24"
    first_downs  : Mapped[str | None]     = mapped_column(Text)   # "22-18"

    updated_at   : Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    team: Mapped["Team"] = relationship("Team", back_populates="game_logs")

    __table_args__ = (
        UniqueConstraint("team_id", "season_year", "game_num", name="uq_gamelog_team_year_game"),
        Index("ix_gamelog_team_year", "team_id", "season_year"),
    )


class DraftPick(Base):
    __tablename__ = "draft_picks"

    id          : Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id     : Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    draft_year  : Mapped[int]         = mapped_column(Integer, nullable=False)
    round_num   : Mapped[int | None]  = mapped_column(Integer)
    player_name : Mapped[str | None]  = mapped_column(Text)
    position    : Mapped[str | None]  = mapped_column(Text)
    height      : Mapped[str | None]  = mapped_column(Text)
    weight      : Mapped[int | None]  = mapped_column(Integer)
    college     : Mapped[str | None]  = mapped_column(Text)
    updated_at  : Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    team: Mapped["Team"] = relationship("Team", back_populates="draft_picks")

    __table_args__ = (
        Index("ix_draft_team_year", "team_id", "draft_year"),
    )

class TeamPlaybook(Base):
    __tablename__ = "team_playbook"

    id                 : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id            : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    season_year        : Mapped[int]            = mapped_column(Integer, nullable=False)
    team_theme         : Mapped[str | None]     = mapped_column(Text)
    win_total          : Mapped[float | None]   = mapped_column(Float)
    win_total_odds     : Mapped[str | None]     = mapped_column(Text)
    opp_win_total      : Mapped[float | None]   = mapped_column(Float)
    playoff_yes_odds   : Mapped[str | None]     = mapped_column(Text)
    playoff_no_odds    : Mapped[str | None]     = mapped_column(Text)
    narrative          : Mapped[str | None]     = mapped_column(Text)
    stat_you_will_like : Mapped[str | None]     = mapped_column(Text)
    power_play         : Mapped[str | None]     = mapped_column(Text)
    coaches_corner     : Mapped[str | None]     = mapped_column(Text)
    q1_trends          : Mapped[str | None]     = mapped_column(Text)
    q2_trends          : Mapped[str | None]     = mapped_column(Text)
    q3_trends          : Mapped[str | None]     = mapped_column(Text)
    q4_trends          : Mapped[str | None]     = mapped_column(Text)
    division_data      : Mapped[str | None]     = mapped_column(Text)
    draft_grades    : Mapped[str | None] = mapped_column(Text)
    first_round     : Mapped[str | None] = mapped_column(Text)
    steal_of_draft  : Mapped[str | None] = mapped_column(Text)
    updated_at         : Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    

    team: Mapped["Team"] = relationship("Team", back_populates="playbook")

    __table_args__ = (
        UniqueConstraint("team_id", "season_year", name="uq_playbook_team_year"),
    )

class ATSHistory(Base):
    __tablename__ = "ats_history"

    id             : Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id        : Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    season_year    : Mapped[int]          = mapped_column(Integer, nullable=False)
    coach_name     : Mapped[str | None]   = mapped_column(Text)
    game_num       : Mapped[int]          = mapped_column(Integer, nullable=False)
    opponent       : Mapped[str | None]   = mapped_column(Text)
    is_home        : Mapped[bool]         = mapped_column(default=True)
    is_neutral     : Mapped[bool]         = mapped_column(default=False)
    is_playoff     : Mapped[bool]         = mapped_column(default=False)
    points_for     : Mapped[int | None]   = mapped_column(Integer)
    points_against : Mapped[int | None]   = mapped_column(Integer)
    su_result      : Mapped[str | None]   = mapped_column(Text)
    line           : Mapped[float | None] = mapped_column(Float)
    ats_result     : Mapped[str | None]   = mapped_column(Text)
    ou_result      : Mapped[str | None]   = mapped_column(Text)
    ou_line        : Mapped[float | None] = mapped_column(Float)
    game_type      : Mapped[str | None]   = mapped_column(Text)
    updated_at     : Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    team: Mapped["Team"] = relationship("Team", back_populates="ats_history")

    __table_args__ = (
        UniqueConstraint("team_id", "season_year", "game_num", name="uq_ats_history_team_year_game"),
    )