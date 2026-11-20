"""session absolute expiry and token invalidation

- refresh_tokens.session_expires_at : fin absolue d'une session (30 jours max., OWASP A07).
- users.tokens_valid_after : les jetons d'accès émis avant cette date sont refusés
  (rempli lors d'une réinitialisation du mot de passe).

Revision ID: aa6b82a168aa
Revises: 7217efbff6be
Create Date: 2026-11-20 15:29:35.795794+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa6b82a168aa"
down_revision: str | None = "7217efbff6be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("tokens_valid_after", sa.DateTime(timezone=True), nullable=True))

    # Colonne obligatoire ajoutée à une table qui peut déjà contenir des lignes : on l'ajoute d'abord
    # facultative, on remplit les lignes existantes, puis on la rend obligatoire. (Ajouter directement
    # NOT NULL, comme l'avait généré Alembic, échouerait dès qu'une session existe.)
    op.add_column("refresh_tokens", sa.Column("session_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE refresh_tokens "
        "SET session_expires_at = GREATEST(expires_at, created_at + INTERVAL '30 days')"
    )
    op.alter_column("refresh_tokens", "session_expires_at", nullable=False)


def downgrade() -> None:
    op.drop_column("refresh_tokens", "session_expires_at")
    op.drop_column("users", "tokens_valid_after")
