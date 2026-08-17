from getpass import getpass

from app.db.session import SessionLocal
from app.services.admin_users import (
    AdminUserAlreadyExistsError,
    create_admin_user,
)


def main() -> None:
    email = input(
        "Adresse email administrateur : "
    ).strip()
    password = getpass(
        "Mot de passe administrateur : "
    )
    password_confirmation = getpass(
        "Confirme le mot de passe : "
    )

    if password != password_confirmation:
        raise SystemExit(
            "Les mots de passe ne correspondent pas."
        )

    try:
        with SessionLocal() as db:
            admin = create_admin_user(
                db,
                email=email,
                password=password,
            )
    except (
        AdminUserAlreadyExistsError,
        ValueError,
    ) as error:
        raise SystemExit(str(error)) from error

    print(
        "Administrateur créé : "
        f"{admin.email} (id={admin.id})"
    )


if __name__ == "__main__":
    main()