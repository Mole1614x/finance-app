"""Local-only identity foundation; demo OTP is deliberately NOT proof of ownership."""
import hashlib
import hmac
import os
import secrets
import time
from functools import lru_cache
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, ForeignKey, Integer, String, create_engine, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

router = APIRouter(prefix="/api/v1/auth", tags=["demo authentication"])
hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)
SECRET = os.getenv("ARTH_JWT_SECRET") or secrets.token_hex(32)
ACCESS_TTL = 900
SESSION_TTL = 604800

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512))
    display_name: Mapped[str] = mapped_column(String(80), default="Demo user")

class Challenge(Base):
    __tablename__ = "auth_challenges"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires: Mapped[int] = mapped_column(Integer)
    code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

class LoginSession(Base):
    __tablename__ = "login_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires: Mapped[int] = mapped_column(Integer)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

@lru_cache(maxsize=1)
def engine():
    db = create_engine(os.getenv("DATABASE_URL", "sqlite:///./arth-demo.db"))
    Base.metadata.create_all(db)
    return db

def get_db():
    with Session(engine()) as db:
        yield db

def now():
    return int(time.time())

def digest(value: str):
    return hmac.new(SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()

def fail(status, detail):
    raise HTTPException(status_code=status, detail=detail)

class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)

class Ticket(BaseModel):
    challenge_id: str = Field(min_length=30, max_length=64)

class Verify(Ticket):
    code: str = Field(pattern=r"^[0-9]{4}$")

class Refresh(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=128)

class Profile(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)

def demo_email(value):
    email = value.strip().lower()
    local, sep, domain = email.partition("@")
    if not sep or domain != "example.com" or not local or any(c.isspace() or c == "@" for c in local):
        fail(400, "Use a fictional @example.com address only.")
    return email

def issue_challenge(db, user):
    ticket = Challenge(id=secrets.token_urlsafe(32), user_id=user.id, expires=now()+300)
    db.add(ticket)
    db.commit()
    return {"challenge_id": ticket.id, "expires_in": 300, "mode": "demo"}

@router.post("/register", status_code=201)
def register(data: Credentials, db: Session = Depends(get_db)):
    user = User(id=str(uuid4()), email=demo_email(data.email), password_hash=hasher.hash(data.password))
    db.add(user)
    try:
        db.flush()
        return issue_challenge(db, user)
    except IntegrityError:
        db.rollback()
        fail(409, "Demo account already exists.")

@router.post("/login")
def login(data: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == demo_email(data.email)))
    try:
        if not user or not hasher.verify(user.password_hash, data.password):
            fail(401, "Invalid credentials.")
    except VerificationError:
        fail(401, "Invalid credentials.")
    return issue_challenge(db, user)

class DemoOTPProvider:
    """Returns the code to the local caller; no real phone number or SMS."""
    def generate(self):
        return f"{secrets.randbelow(10000):04d}"

@router.post("/otp/request")
def request_otp(data: Ticket, db: Session = Depends(get_db)):
    code = DemoOTPProvider().generate()
    result = db.execute(update(Challenge).where(
        Challenge.id == data.challenge_id, Challenge.used.is_(False),
        Challenge.expires > now(), Challenge.code_hash.is_(None)
    ).values(code_hash=digest(data.challenge_id + ":" + code)))
    if result.rowcount != 1:
        fail(409, "Challenge invalid, expired or already issued. Sign in again.")
    db.commit()
    return {"demo_code": code, "mode": "demo", "sms_sent": False}

def token_response(session, refresh):
    access = jwt.encode({"sub": session.user_id, "sid": session.id,
                         "iat": now(), "exp": min(now()+ACCESS_TTL, session.expires),
                         "iss": "arth-demo", "aud": "arth-mobile"}, SECRET, algorithm="HS256")
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer", "expires_in": ACCESS_TTL}

@router.post("/otp/verify")
def verify_otp(data: Verify, db: Session = Depends(get_db)):
    ticket = db.get(Challenge, data.challenge_id)
    if not ticket or ticket.used or ticket.expires <= now() or not ticket.code_hash or ticket.attempts >= 5:
        fail(401, "Invalid or expired challenge.")
    match = hmac.compare_digest(ticket.code_hash, digest(data.challenge_id + ":" + data.code))
    conditions = (Challenge.id == ticket.id, Challenge.used.is_(False),
                  Challenge.expires > now(), Challenge.attempts < 5)
    if not match:
        db.execute(update(Challenge).where(*conditions).values(attempts=Challenge.attempts+1))
        db.commit()
        fail(401, "Incorrect demo code.")
    result = db.execute(update(Challenge).where(*conditions).values(used=True))
    if result.rowcount != 1:
        fail(401, "Challenge already consumed.")
    refresh = secrets.token_urlsafe(48)
    session = LoginSession(id=str(uuid4()), user_id=ticket.user_id,
                           refresh_hash=digest(refresh), expires=now()+SESSION_TTL)
    db.add(session)
    db.commit()
    return token_response(session, refresh)

def active_session(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if not credentials:
        fail(401, "Authentication required.")
    try:
        claims = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"],
                            issuer="arth-demo", audience="arth-mobile",
                            options={"require": ["sub", "sid", "exp", "iat"]})
    except jwt.PyJWTError:
        fail(401, "Invalid or expired token.")
    session = db.get(LoginSession, claims["sid"])
    if not session or session.revoked or session.expires <= now() or session.user_id != claims["sub"]:
        fail(401, "Session expired.")
    return session

@router.post("/refresh")
def refresh_session(data: Refresh, db: Session = Depends(get_db)):
    old = digest(data.refresh_token)
    session = db.scalar(select(LoginSession).where(LoginSession.refresh_hash == old))
    if not session or session.revoked or session.expires <= now():
        fail(401, "Invalid refresh token.")
    new = secrets.token_urlsafe(48)
    result = db.execute(update(LoginSession).where(LoginSession.id == session.id,
        LoginSession.refresh_hash == old, LoginSession.revoked.is_(False),
        LoginSession.expires > now()).values(refresh_hash=digest(new)))
    if result.rowcount != 1:
        fail(401, "Refresh token already used.")
    db.commit()
    return token_response(session, new)

@router.post("/logout")
def logout(session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    session.revoked = True
    db.commit()
    return {"status": "signed_out"}

@router.get("/me")
def me(session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    user = db.get(User, session.user_id)
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "mode": "demo"}

@router.patch("/me")
def profile(data: Profile, session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    user = db.get(User, session.user_id)
    name = data.display_name.strip()
    if not name:
        fail(400, "Display name cannot be blank.")
    user.display_name = name
    db.commit()
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "mode": "demo"}
