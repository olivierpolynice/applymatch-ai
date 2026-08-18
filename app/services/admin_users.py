from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AdminUser
from app.services.security import (
    hash_password,
    verify_password,
)


class AdminUserAlreadyExistsError(RuntimeError):
    pass


class AdminUserNotFoundError(RuntimeError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def validate_email_and_password(
    email: str,
    password: str,
) -> str:
    normalized_email = normalize_email(email)

    if not normalized_email or "@" not in normalized_email:
        raise ValueError(
            "Une adresse email valide est obligatoire."
        )

    if len(password) < 12:
        raise ValueError(
            "Le mot de passe doit contenir au moins 12 caractères."
        )

    return normalized_email


def get_admin_by_email(
    db: Session,
    email: str,
) -> AdminUser | None:
    return db.scalar(
        select(AdminUser).where(
            AdminUser.email == normalize_email(email),
        )
    )


def create_admin_user(
    db: Session,
    *,
    email: str,
    password: str,
) -> AdminUser:
    normalized_email = validate_email_and_password(
        email,
        password,
    )

    if get_admin_by_email(db, normalized_email):
        raise AdminUserAlreadyExistsError(
            "Un administrateur utilise déjà cette adresse email."
        )

    admin = AdminUser(
        email=normalized_email,
        hashed_password=hash_password(password),
        is_active=True,
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    return admin


def reset_admin_password(
    db: Session,
    *,
    email: str,
    password: str,
) -> AdminUser:
    normalized_email = validate_email_and_password(
        email,
        password,
    )

    admin = get_admin_by_email(
        db,
        normalized_email,
    )

    if admin is None:
        raise AdminUserNotFoundError(
            "Aucun administrateur trouvé avec cette adresse email."
        )

    admin.hashed_password = hash_password(password)
    admin.is_active = True

    db.commit()
    db.refresh(admin)

    return admin


def authenticate_admin(
    db: Session,
    *,
    email: str,
    password: str,
) -> AdminUser | None:
    admin = get_admin_by_email(
        db,
        email,
    )

    if admin is None or not admin.is_active:
        return None

    if not verify_password(
        password,
        admin.hashed_password,
    ):
        return None

    return admin