"""Private local peer-payment references; no credentials or session tokens."""
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import UUID
try:
    from .payment_data import parse_identifier
except ImportError:
    from payment_data import parse_identifier

class PendingStore:
    def __init__(self, directory):
        self.path = Path(directory) / "pending-peer-payments.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        with closing(self.connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS pending (
                backend TEXT NOT NULL, owner TEXT NOT NULL,
                request_key TEXT NOT NULL, recipient TEXT NOT NULL,
                amount_minor INTEGER NOT NULL CHECK(amount_minor > 0),
                PRIMARY KEY(backend, owner))""")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        return db

    def get(self, backend, owner):
        with closing(self.connect()) as db:
            row = db.execute("SELECT request_key, recipient, amount_minor FROM pending WHERE backend=? AND owner=?",
                             (backend, owner)).fetchone()
        if row is None:
            return None
        result = dict(row)
        UUID(result["request_key"])
        parse_identifier(result["recipient"])
        if type(result["amount_minor"]) is not int or not 0 < result["amount_minor"] <= 100000000:
            raise ValueError("Invalid saved demo amount")
        return result

    def reserve(self, backend, owner, key, recipient, amount_minor):
        UUID(key)
        parse_identifier(recipient)
        if type(amount_minor) is not int or not 0 < amount_minor <= 100000000:
            raise ValueError("Invalid demo amount")
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT request_key,recipient,amount_minor FROM pending WHERE backend=? AND owner=?",
                                  (backend,owner)).fetchone()
            if existing and tuple(existing) != (key,recipient,amount_minor):
                raise ValueError("Resolve the existing pending payment first.")
            if not existing:
                db.execute("INSERT INTO pending VALUES (?,?,?,?,?)", (backend,owner,key,recipient,amount_minor))

    def clear(self, backend, owner, key):
        with closing(self.connect()) as db, db:
            db.execute("DELETE FROM pending WHERE backend=? AND owner=? AND request_key=?", (backend,owner,key))
