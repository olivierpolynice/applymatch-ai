"""Create the first administrator from deployment environment variables."""

import os

from app.db.session import SessionLocal
from app.services.admin_users import create_admin_user, get_admin_by_email


def main() -> None:
    email = os.getenv("ADMIN_EMAIL", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")

    if not email or not password:
        print("ADMIN_EMAIL/ADMIN_PASSWORD absents : création ignorée.")
        return

    with SessionLocal() as db:
        existing_admin = get_admin_by_email(db, email)

        if existing_admin is not None:
            print(f"Administrateur déjà présent : {existing_admin.email}")
            return

        admin = create_admin_user(db, email=email, password=password)

    print(f"Administrateur créé : {admin.email}")


if __name__ == "__main__":
    main()
