from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal

app = FastAPI(title="ARTH API", version="0.1.0")

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
