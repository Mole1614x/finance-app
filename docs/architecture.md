# Architecture
Mobile: Kivy/KivyMD, Python. Backend: FastAPI/Uvicorn modular monolith. PostgreSQL and Redis/Celery infrastructure provisioned locally, not yet wired to a ledger. Kubernetes deployment planned after configuration and security are stabilized.

Next: secure registration and OTP provider abstraction, profile, account simulation and atomic double-entry ledger with integer minor units, idempotency and audit records. Then transfers, QR, receipts, history, sandbox merchant payments, budgeting and analytics. No real bank or payment credentials in the demo. Real UPI requires approved provider integration and banking partners. AI and ML are later phases; no sensitive financial data to LLMs without explicit consent and minimization.
