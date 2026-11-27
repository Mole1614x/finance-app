# ARTH (अर्थ)
Pay. Manage. Prosper.

Python-first mobile finance application. This foundation is a demonstration only; no real money, bank credentials or UPI PINs are accepted.

## Run locally
Use Python 3.11. From the repository root:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r backend/requirements.txt
    python -m uvicorn backend.app.main:app --reload

Open http://localhost:8000/docs. Run tests with python -m pytest backend/tests.

For the desktop mobile preview, in a separate Python environment:

    pip install -r mobile/requirements.txt
    python -m mobile.main

For local infrastructure: docker compose up --build. API at localhost:8000. Database and Redis remain on the internal Compose network. Local development credentials are not production secrets.

Android: install Buildozer on a supported Linux host, then cd mobile && buildozer android debug (not yet validated). iOS packaging is planned.

See docs/architecture.md and docs/design.md. The mobile UI is a provisional foundation, not a pixel-verified Figma port.

## Demo authentication (PR 3)
Start the API first. Register a fictional @example.com account, use a demo password of eight or more characters and enter 9000000000. The server returns a demo OTP displayed in the app. See docs/authentication.md for limitations. The backend uses SQLite by default and PostgreSQL in Compose.
