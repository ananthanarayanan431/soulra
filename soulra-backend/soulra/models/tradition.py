from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from soulra.database import Base


class Tradition(Base):
    __tablename__ = "traditions"

    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    origin: Mapped[str] = mapped_column(String(120), nullable=False)
    era: Mapped[str] = mapped_column(String(40), nullable=False)
    user_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
