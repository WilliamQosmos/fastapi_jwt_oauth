from datetime import datetime

from sqlalchemy import ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, intpk


class Referrer(Base):
    __tablename__ = "referrers"

    id: Mapped[intpk]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    referrer_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(), nullable=False, server_default=func.now())
    until_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(),
        nullable=False,
        server_default=text("now() + interval '14 days'")
    )
