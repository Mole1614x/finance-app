"""Run from repo root: python -m scripts.evaluate_anomaly_model."""
import json
from backend.app.anomaly_model import evaluate

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
