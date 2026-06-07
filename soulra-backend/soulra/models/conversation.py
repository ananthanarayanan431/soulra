import uuid
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, Text, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from soulra.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    thread_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    situation: Mapped[str] = mapped_column(Text, nullable=False)
    clarify_q: Mapped[str | None] = mapped_column(Text, nullable=True)
    clarify_ans: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    action_steps: Mapped[list["ActionStep"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    tradition_cards: Mapped[list["TraditionCard"]] = relationship(  # type: ignore[name-defined]
        back_populates="conversation", cascade="all, delete-orphan",
        order_by="TraditionCard.card_order"
    )


class ActionStep(Base):
    __tablename__ = "action_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="action_steps")
