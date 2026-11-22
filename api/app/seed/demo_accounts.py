"""Comptes de démonstration, un par rôle (cahier §6.3) : `python -m app.seed.demo_accounts`.

Le cahier exige « un script d'amorçage [qui] crée des comptes de démonstration pour chaque rôle; les
identifiants sont transmis au responsable du projet en privé (pas dans le README) ». Ce script :

- crée `demo-client`, `demo-commis`, `demo-gerant` et `demo-admin` (rôles client, clerk, manager,
  admin) sur le domaine choisi (`--domaine`), courriel marqué vérifié (aucun fournisseur de courriel
  n'est requis pour la démonstration);
- affecte le commis et le gérant au magasin de Saint-Jérôme créé par `seed_l1`;
- ne contient, n'affiche et ne journalise AUCUN mot de passe : ils viennent uniquement des variables
  `DEMO_PASSWORD_CLIENT`, `DEMO_PASSWORD_COMMIS`, `DEMO_PASSWORD_GERANT` et `DEMO_PASSWORD_ADMIN`,
  choisies par l'opérateur (p. ex. dans un gestionnaire de mots de passe) puis transmises en privé;
- applique la politique de mot de passe (A-AUTH-03) et le hachage Argon2id;
- est idempotent : un compte existant n'est jamais modifié (sauf `--reinitialiser`, qui invalide aussi
  les sessions ouvertes);
- refuse la production sans `--allow-production`.

Le personnel (commis, gérant, administrateur) doit configurer la MFA TOTP à sa première connexion
(A-AUTH-06) : la réponse de connexion indique `mfa_setup_required`.
"""

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.core.errors import ValidationFailed
from app.models import StaffAssignment, Store, User, UserRole
from app.seed.seed_l1 import seed_uuid
from app.services.password_policy import validate_password

DEMO_STORE_KEY = "saint-jerome"


@dataclass(frozen=True)
class DemoAccount:
    key: str  # suffixe de l'adresse et de la variable d'environnement
    role: UserRole
    first_name: str
    last_name: str

    @property
    def env_var(self) -> str:
        return f"DEMO_PASSWORD_{self.key.upper()}"


ACCOUNTS = (
    DemoAccount("client", UserRole.CLIENT, "Démo", "Client"),
    DemoAccount("commis", UserRole.CLERK, "Démo", "Commis"),
    DemoAccount("gerant", UserRole.MANAGER, "Démo", "Gérant"),
    DemoAccount("admin", UserRole.ADMIN, "Démo", "Administrateur"),
)


@dataclass(frozen=True)
class Result:
    email: str
    role: str
    status: str  # « créé », « existant », « réinitialisé »


def email_for(account: DemoAccount, domain: str) -> str:
    return f"demo-{account.key}@{domain}".lower()


def _password_for(account: DemoAccount) -> str:
    password = os.environ.get(account.env_var, "")
    if not password:
        raise ValidationFailed("demo_password_missing", f"Définir la variable {account.env_var}.")
    return password


def run(db: Session, *, domain: str, reset: bool = False) -> list[Result]:
    """Crée ou vérifie les comptes de démonstration; valide la transaction (tout ou rien)."""
    store = db.get(Store, seed_uuid("store", DEMO_STORE_KEY))
    if store is None:
        raise ValidationFailed("demo_store_missing", "Lancer d'abord l'amorçage : python -m app.seed.seed_l1")
    results: list[Result] = []
    for account in ACCOUNTS:
        email = email_for(account, domain)
        existing = db.scalar(select(User).where(func.lower(User.email) == email))
        if existing is not None and not reset:
            results.append(Result(email, account.role.value, "existant"))
            continue
        password = _password_for(account)
        validate_password(password, email=email, first_name=account.first_name, last_name=account.last_name)
        if existing is None:
            user = User(
                email=email,
                password_hash=security.hash_password(password),
                role=account.role,
                first_name=account.first_name,
                last_name=account.last_name,
                language="fr",
                email_verified_at=datetime.now(UTC),
                is_active=True,
            )
            db.add(user)
            db.flush()
            if account.role in (UserRole.CLERK, UserRole.MANAGER):
                db.add(StaffAssignment(user_id=user.id, store_id=store.id))
            status = "créé"
        else:
            existing.password_hash = security.hash_password(password)
            existing.tokens_valid_after = datetime.now(UTC)  # invalide les sessions ouvertes
            status = "réinitialisé"
        results.append(Result(email, account.role.value, status))
    db.commit()
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Comptes de démonstration (un par rôle).")
    parser.add_argument(
        "--domaine", default="example.com", help="Domaine des adresses (défaut : example.com)."
    )
    parser.add_argument(
        "--reinitialiser", action="store_true", help="Remplacer le mot de passe des comptes existants."
    )
    parser.add_argument("--allow-production", action="store_true", help="Autoriser APP_ENV=production.")
    args = parser.parse_args(argv)
    if get_settings().is_production and not args.allow_production:
        print(
            "Refusé : APP_ENV=production. Relancer avec --allow-production si c'est voulu.", file=sys.stderr
        )
        return 2

    from app.db.session import SessionLocal  # connexion ouverte seulement ici

    with SessionLocal() as db:
        try:
            results = run(db, domain=args.domaine, reset=args.reinitialiser)
        except ValidationFailed as exc:
            print(f"Refusé : {exc.message}", file=sys.stderr)
            return 1
    for r in results:
        print(f"  {r.role:<8} {r.email:<36} {r.status}")
    print("\nPersonnel (commis, gérant, admin) : configurer la MFA TOTP à la première connexion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
