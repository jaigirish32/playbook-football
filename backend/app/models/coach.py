import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Coach(Base):
    __tablename__ = "coaches"

    id               : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id          : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), unique=True, nullable=False)
    name             : Mapped[str]       = mapped_column(String(150), nullable=False)
    years_with_team  : Mapped[int]       = mapped_column(Integer, default=1)
    record_su_wins   : Mapped[int]       = mapped_column(Integer, default=0)
    record_su_losses : Mapped[int]       = mapped_column(Integer, default=0)

    record_ats_wins   : Mapped[int | None] = mapped_column(Integer, nullable=True)
    record_ats_losses : Mapped[int | None] = mapped_column(Integer, nullable=True)
    record_ats_pushes : Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpr               : Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpr_off           : Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpr_def           : Mapped[int | None] = mapped_column(Integer, nullable=True)    
    ret_off_starters  : Mapped[int | None] = mapped_column(Integer, nullable=True)
    ret_def_starters  : Mapped[int | None] = mapped_column(Integer, nullable=True)
    recruit_rank_2025 : Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at       : Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at       : Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    team        : Mapped["Team"]      = relationship("Team", back_populates="coach")
    coach_stats : Mapped["CoachStat"] = relationship("CoachStat", back_populates="coach", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Coach {self.name}>"


class CoachStat(Base):
    __tablename__ = "coach_stats"

    id       : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coach_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("coaches.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Home / Away
    home_ats_w    : Mapped[int] = mapped_column(Integer, default=0)
    home_ats_l    : Mapped[int] = mapped_column(Integer, default=0)
    away_ats_w    : Mapped[int] = mapped_column(Integer, default=0)
    away_ats_l    : Mapped[int] = mapped_column(Integer, default=0)

    # Favourite / Underdog
    fav_ats_w     : Mapped[int] = mapped_column(Integer, default=0)
    fav_ats_l     : Mapped[int] = mapped_column(Integer, default=0)
    dog_ats_w     : Mapped[int] = mapped_column(Integer, default=0)
    dog_ats_l     : Mapped[int] = mapped_column(Integer, default=0)

    # Rest / Revenge
    rest_ats_w    : Mapped[int] = mapped_column(Integer, default=0)
    rest_ats_l    : Mapped[int] = mapped_column(Integer, default=0)
    rev_ats_w     : Mapped[int] = mapped_column(Integer, default=0)
    rev_ats_l     : Mapped[int] = mapped_column(Integer, default=0)
    vs_rev_ats_w  : Mapped[int] = mapped_column(Integer, default=0)
    vs_rev_ats_l  : Mapped[int] = mapped_column(Integer, default=0)

    # Off result
    off_win_ats_w  : Mapped[int] = mapped_column(Integer, default=0)
    off_win_ats_l  : Mapped[int] = mapped_column(Integer, default=0)
    off_loss_ats_w : Mapped[int] = mapped_column(Integer, default=0)
    off_loss_ats_l : Mapped[int] = mapped_column(Integer, default=0)

    # Division splits
    div_ats_w     : Mapped[int] = mapped_column(Integer, default=0)
    div_ats_l     : Mapped[int] = mapped_column(Integer, default=0)
    ndiv_ats_w    : Mapped[int] = mapped_column(Integer, default=0)
    ndiv_ats_l    : Mapped[int] = mapped_column(Integer, default=0)

    # Score thresholds
    allow35_ats_w : Mapped[int] = mapped_column(Integer, default=0)
    allow35_ats_l : Mapped[int] = mapped_column(Integer, default=0)
    score35_ats_w : Mapped[int] = mapped_column(Integer, default=0)
    score35_ats_l : Mapped[int] = mapped_column(Integer, default=0)


    updated_at    : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    coach: Mapped["Coach"] = relationship("Coach", back_populates="coach_stats")

    def __repr__(self) -> str:
        return f"<CoachStat coach_id={self.coach_id}>"