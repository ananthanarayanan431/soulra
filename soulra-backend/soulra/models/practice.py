import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from soulra.database import Base


class PracticeArc(Base):
    __tablename__ = "practice_arcs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    theme: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    current_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    days: Mapped[list["PracticeDay"]] = relationship(
        back_populates="arc", cascade="all, delete-orphan", order_by="PracticeDay.day_number"
    )


class PracticeDay(Base):
    __tablename__ = "practice_days"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    arc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("practice_arcs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    day_label: Mapped[str] = mapped_column(String(10), nullable=False)
    task_title: Mapped[str] = mapped_column(Text, nullable=False)
    task_body: Mapped[str] = mapped_column(Text, nullable=False)
    morning_quote: Mapped[str] = mapped_column(Text, nullable=False)
    morning_author: Mapped[str] = mapped_column(Text, nullable=False)
    morning_citation: Mapped[str] = mapped_column(Text, nullable=False)
    morning_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    evening_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    reflection_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reflection_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    arc: Mapped["PracticeArc"] = relationship(back_populates="days")
