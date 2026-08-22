"""Open one prepared application in Chromium without submitting it."""

import argparse

from app.db.session import SessionLocal
from app.services.browser_assistance import (
    local_document_paths,
    open_assisted_browser,
    prepare_browser_assistance,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft-id", type=int, required=True)
    args = parser.parse_args()

    with SessionLocal() as db:
        session = prepare_browser_assistance(db, draft_id=args.draft_id)
        paths = local_document_paths(db, draft_id=args.draft_id)
        print(f"Plateforme : {session['platform']}")
        print(f"CV prêt : {paths['cv']}")
        print(f"Lettre PDF prête : {paths['letter_pdf']}")
        print(f"Lettre Word prête : {paths['letter_docx']}")
        print("Validation humaine obligatoire avant l'envoi.")
        open_assisted_browser(session["source_url"])


if __name__ == "__main__":
    main()
