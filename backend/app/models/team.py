import uuid
import enum
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Enum, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.coach import Coach
    from app.models.stats import SeasonStat, SOSStat, TeamTrend


class LeagueEnum(str, enum.Enum):
    NFL = "NFL"
    CFB = "CFB"


class Team(Base):
    __tablename__ = "teams"

    id               : Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name             : Mapped[str]        = mapped_column(String(100), nullable=False)
    abbreviation     : Mapped[str]        = mapped_column(String(10),  nullable=False)
    league           : Mapped[LeagueEnum] = mapped_column(Enum(LeagueEnum), nullable=False, index=True)
    conference       : Mapped[str | None] = mapped_column(String(50))
    division         : Mapped[str | None] = mapped_column(String(50))
    stadium          : Mapped[str | None] = mapped_column(String(150))
    stadium_surface  : Mapped[str | None] = mapped_column(String(20))
    stadium_city     : Mapped[str | None] = mapped_column(String(100))
    stadium_capacity : Mapped[int | None] = mapped_column(Integer)
    website          : Mapped[str | None] = mapped_column(String(255))
    logo_url         : Mapped[str | None] = mapped_column(String(500))
    is_active        : Mapped[bool]       = mapped_column(Boolean, default=True)
    created_at       : Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at       : Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    coach        : Mapped["Coach"]            = relationship("Coach", back_populates="team", uselist=False, cascade="all, delete-orphan")
    season_stats : Mapped[list["SeasonStat"]] = relationship("SeasonStat", back_populates="team", cascade="all, delete-orphan")
    sos_stats    : Mapped[list["SOSStat"]]    = relationship("SOSStat", back_populates="team", cascade="all, delete-orphan")
    trends       : Mapped[list["TeamTrend"]]  = relationship("TeamTrend", back_populates="team", cascade="all, delete-orphan")
    schedule_games : Mapped[list["ScheduleGame"]] = relationship("ScheduleGame", back_populates="team", cascade="all, delete-orphan")
    game_logs      : Mapped[list["GameLog"]]      = relationship("GameLog",      back_populates="team", cascade="all, delete-orphan")
    draft_picks    : Mapped[list["DraftPick"]]    = relationship("DraftPick",    back_populates="team", cascade="all, delete-orphan")
    playbook: Mapped[list["TeamPlaybook"]] = relationship("TeamPlaybook", back_populates="team")
    ats_history: Mapped[list["ATSHistory"]] = relationship("ATSHistory", back_populates="team")
    __table_args__ = (
        UniqueConstraint("abbreviation", "league", name="uq_team_abbr_league"),
    )

    def __repr__(self) -> str:
        return f"<Team {self.abbreviation} ({self.league})>"