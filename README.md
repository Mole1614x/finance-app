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

For local infrastructure: python3 scripts/init_demo_env.py, then docker compose up --build -d. API at localhost:8000. Database and Redis remain on the internal Compose network. Local development credentials are not production secrets.

Android: see docs/android.md for the debug APK workflow and local installation. iOS packaging is planned.

See docs/architecture.md and docs/design.md. The mobile UI is a provisional foundation, not a pixel-verified Figma port.

## Demo authentication (PR 3)
Start the API first. Register a fictional @example.com account, use a demo password of eight or more characters and enter 9000000000. The server returns a demo OTP displayed in the app. See docs/authentication.md for limitations. The backend uses SQLite by default and PostgreSQL in Compose.

## Dashboard (PR 4)
After demo verification, the authenticated dashboard shows a synthetic balance and chart, profile editing and navigation to clearly labeled payment previews. See docs/dashboard.md.

## Simulated accounts (PR 5)
After signing in, open Bank accounts and initialize the demo checking and savings accounts. The backend records INR 8,500 of fictional opening funds once. The dashboard reads ledger balances. Internal moves can be tested through Swagger; see docs/ledger.md. No real money or banking.

## Demo peer payments (PR 6)
Initialize accounts for two fictional users. Copy the recipient's ARTH-only payment identifier from Receive, enter it and an amount in Send, review and confirm. No real money or UPI. QR display, decoded-text input and optional local camera scanning are implemented; physical camera testing is pending. See docs/payments.md.

## Transaction history (PR 7)
Open History to view completed demo ledger entries, filter by type and copy a simulated receipt. During an uncertain payment, check status using the same reference. See docs/transactions.md.

## Demo bills and rewards (PR 8)
Open Bills and recharge for fictional monthly bills and recharge plans. Confirm a purchase with simulated funds; cashback goes directly to demo checking. Rewards shows lifetime cashback. No real services are delivered. See docs/services.md.

## Financial insights (PR 9)
Open Financial insights for actual demo ledger monthly spending, categories, budgets, estimates and a savings goal. The local rule-based assistant and unusual spending heuristic use no external AI or real financial data. See docs/analytics.md.

## Demo release readiness (PR 10)
Use sh scripts/start-demo.sh to initialize private local secrets and start Compose. See docs/release.md for Alembic adoption, CI checks, limitations and local Kubernetes instructions. Existing databases require explicit baseline adoption after verification; do not delete existing data.

## Native UX (PR 11)
Shared mobile components and onboarding/navigation refinement. Run `python -m mobile.smoke` with a graphical display (CI uses Xvfb). Exact Figma asset matching remains blocked; see docs/native-ux.md.

## Optional Gemini assistant (PR 12)
The Financial assistant is local by default. For opt-in Gemini explanations of fictional aggregate data only, configure private `ARTH_AI_ENABLED=1`, `ARTH_GEMINI_API_KEY`, and `ARTH_GEMINI_MODEL`. Never commit secrets or use real financial data. See docs/ai-assistant.md.

## ML anomaly review (PR 13)
Open Financial insights > Anomaly review. A local Isolation Forest trained on fictional data highlights unusual spending patterns for review, never blocks a transaction. Run `python -m scripts.evaluate_anomaly_model` for held-out synthetic metrics. See docs/anomaly-model.md.

## QR and peer payment recovery (PR 14)
Scan an ARTH demo QR using the optional local camera, or paste its text. Peer payments keep the original reference across app restarts. Check, retry or safely cancel unresolved references after signing in again. Run Alembic upgrades for managed deployments. See docs/payment-recovery.md. Physical-device camera and APK tests remain pending.

## Android debug build (PR 15)
The CI workflow builds and checks an ARM64/x86-64 debug APK and runs an Android emulator smoke test. Download the APK only from a successful workflow artifact. Use ADB reverse for local-only backend access. See docs/android.md for setup and physical-device checklist.

## Final desktop demo (PR 16)
Run `sh scripts/start-demo.sh` in one terminal and `sh scripts/start-mobile.sh` in another. Stop the application normally and run `docker compose down` (without `-v`). See docs/demo-acceptance.md for acceptance coverage, migration/restart checks and outstanding limitations. Android build verification is deferred: PR 15 merged with failed APK CI and skipped emulator. No installable APK is claimed. Keep Android tests enabled and verify them separately before distribution.
