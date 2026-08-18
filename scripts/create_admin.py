from getpass import getpass

from app.db.session import SessionLocal
from app.services.admin_users import (
    create_admin_user,
    get_admin_by_email,
    reset_admin_password,
)


def main() -> None:
    email = input(
        "Adresse email administrateur : "
    ).strip()

    with SessionLocal() as db:
        existing_admin = get_admin_by_email(
            db,
            email,
        )

        if existing_admin is not None:
            confirmation = input(
                (
                    "Cet administrateur existe déjà. "
                    "Réinitialiser son mot de passe ? (o/n) : "
                )
            ).strip().casefold()

            if confirmation not in {"o", "oui"}:
                raise SystemExit(
                    "Réinitialisation annulée."
                )

        password = getpass(
            "Nouveau mot de passe administrateur : "
        )
        password_confirmation = getpass(
            "Confirme le nouveau mot de passe : "
        )

        if password != password_confirmation:
            raise SystemExit(
                "Les mots de passe ne correspondent pas."
            )

        try:
            if existing_admin is not None:
                admin = reset_admin_password(
                    db,
                    email=email,
                    password=password,
                )
                message = "Mot de passe réinitialisé"
            else:
                admin = create_admin_user(
                    db,
                    email=email,
                    password=password,
                )
                message = "Administrateur créé"
        except ValueError as error:
            raise SystemExit(str(error)) from error

    print(
        f"{message} : {admin.email} (id={admin.id})"
    )


if __name__ == "__main__":
    main()