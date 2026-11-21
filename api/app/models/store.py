"""Tables `stores` et `staff_assignments` (cahier A.6).

L'authentification en a besoin pour l'affectation du personnel à un magasin (A-AUTH-05).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150))
    address: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(30))
    opening_hours: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StaffAssignment(Base):
    """Lien commis/gérant ↔ magasin."""

    __tablename__ = "staff_assignments"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True)

    user: Mapped["User"] = relationship(back_populates="store_assignments")  # noqa: F821
