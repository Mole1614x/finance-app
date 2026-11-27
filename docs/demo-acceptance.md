# ARTH 0.14.0 — desktop demo release candidate

This is a simulated finance portfolio application, not a production financial service. The final phase adds a combined API acceptance journey and a migration/restart test. Test evidence comes from the exact CI run, not this checklist. No results for PR 16 are claimed until executed.

## Run locally
From the repo root, on a graphical desktop with Python 3.11, Docker and Compose:
    sh scripts/start-demo.sh
In a separate terminal:
    sh scripts/start-mobile.sh
The first script checks readiness and the second checks the backend before opening Kivy. Stop the mobile app normally and stop the backend with docker compose down (without -v). Restart by using the same commands. Do not delete database volumes or overwrite existing secrets. Review docs/release.md for pre-Alembic database adoption and migration instructions.

## Acceptance coverage
The combined test uses two fictional demo accounts, OTP login, initial balances, peer QR identifier, persisted pending reference, retry and cancellation, utility bill and recharge, cashback, savings goal, budget, local assistant, ML review, receipts, cross-account scope, logout and full double-entry reconciliation. A second test upgrades an isolated SQLite baseline, retains user balances, then reopens database connections and validates payment/cancellation durability. PostgreSQL/Redis and Compose jobs remain in CI. Desktop graphical smoke is separate from full user interaction. Run python -m pytest backend/tests/test_demo_acceptance.py for just the final acceptance tests.

## Verification record
PRs 1–14 merged after their checks passed. PR 15 was merged at user request with Android testing deferred: CI run 45970162733 passed backend, PostgreSQL/Redis, Compose and desktop smoke; APK failed and emulator skipped. PR 16 checks remain to be run. Android jobs stay enabled and failures are reported, not converted to success. No validated Android artifact, physical device, real camera, iOS, production signing, exact Figma parity, live Gemini call, real-world fraud model validation or actual money rails. Persistent recovery covers peer sends only; service and savings recovery remain in-memory. No real financial or identity information.

## Manual demo checklist
Sign up two fictional @example.com users, use displayed demo OTP, initialize accounts, copy the recipient identifier, send simulated money, confirm receipt and balances, verify cancellation and restart recovery, buy a demo utility bill and inspect cashback, set a savings goal/budget, view insights and local assistant, log out. Record actual environment and pass/fail. The full desktop interaction checklist and Android device checklist still require hands-on testing.
