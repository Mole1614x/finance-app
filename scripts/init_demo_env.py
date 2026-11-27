"""Create local demo secrets without overwriting existing values."""
import os
import secrets
from pathlib import Path

def main():
    path = Path(__file__).resolve().parents[1] / ".env"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(".env exists; unchanged.")
        return
    with os.fdopen(fd, "w") as f:
        f.write("ARTH_JWT_SECRET="+secrets.token_hex(32)+"\n")
        f.write("ARTH_DB_PASSWORD="+secrets.token_hex(24)+"\n")
    print("Created local .env; keep it private.")

if __name__ == "__main__":
    main()
