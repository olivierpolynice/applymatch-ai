"""Connect ApplyMatch to Gmail locally with Google OAuth 2.0."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

from app.services.gmail_delivery import GMAIL_SCOPES


def main() -> None:
    load_dotenv()
    secret = Path(
        os.environ["GMAIL_CLIENT_SECRET_FILE"]
    ).expanduser().resolve()
    token = Path(
        os.getenv("GMAIL_TOKEN_FILE", "secrets/gmail-token.json")
    ).expanduser().resolve()
    flow = InstalledAppFlow.from_client_secrets_file(
        str(secret), GMAIL_SCOPES
    )
    credentials = flow.run_local_server(
        host="localhost",
        port=8765,
        authorization_prompt_message=(
            "Ouvre cette adresse dans ton navigateur : {url}"
        ),
        success_message=(
            "Gmail est connecté à ApplyMatch. Tu peux fermer cette fenêtre."
        ),
        open_browser=True,
    )
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(credentials.to_json(), encoding="utf-8")
    print(f"Connexion Gmail enregistrée dans : {token}")


if __name__ == "__main__":
    main()
