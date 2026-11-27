from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal

from backend.app.auth import router as auth_router

app = FastAPI(title="ARTH API", version="0.2.0")
app.include_router(auth_router)

class Health(BaseModel):
    status: Literal["ok"] = "ok"
    mode: Literal["demo"] = "demo"

@app.get("/health", response_model=Health)
def health():
    return Health()

@app.get("/api/v1/demo/dashboard")
def dashboard():
    return {"mode": "demo", "currency": "INR", "balance_minor": 850000,
            "payments_enabled": False}
