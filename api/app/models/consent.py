"""Table `consents` (cahier A.6) : preuve horodatée du consentement (A-AUTH-01, Loi 25).

On ne modifie ni ne supprime jamais une ligne : un retrait de consentement remplit `revoked_at`,
ce qui conserve l'historique comme preuve.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConsentType(str, enum.Enum):
    PRIVACY = "privacy"  # politique de confidentialité (obligatoire à l'inscription)
    MARKETING = "marketing"  # courriels promotionnels (sur adhésion seulement, A-PRV-04)


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[ConsentType] = mapped_column(
        Enum(
            ConsentType,
            name="consent_type",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda types: [t.value for t in types],
            length=20,
        )
    )
    version: Mapped[str] = mapped_column(String(20))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
