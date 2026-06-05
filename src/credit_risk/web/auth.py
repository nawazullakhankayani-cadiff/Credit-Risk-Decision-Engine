"""Authentication & session management — dependency-light, stdlib + sqlite only.

Provides:
  * a SQLite-backed user store (employer_id, company_name, email, salted PBKDF2 hash),
  * registration + login (by **employer ID or company name** + password),
  * cookie sessions with server-side records that capture **login & logout times**,
  * a seed of demo accounts so the site works out of the box.

No plaintext passwords are ever stored. Tokens are random 256-bit URL-safe strings.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from credit_risk.config import PATHS

DB_PATH = Path(os.getenv("CREDIT_AUTH_DB", str(PATHS.data / "app.db")))
_PBKDF2_ROUNDS = 200_000
COOKIE_NAME = "crre_session"
SESSION_TTL_HOURS = int(os.getenv("CREDIT_SESSION_TTL_HOURS", "24"))


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
@dataclass
class User:
    employer_id: str
    company_name: str
    email: str
    full_name: str
    created_utc: str


@dataclass
class Session:
    token: str
    employer_id: str
    login_utc: str
    logout_utc: Optional[str]
    ip: Optional[str]


def _fmt(dt: datetime) -> str:
    # Fixed-width, constant suffix → lexicographic comparison matches chronological order.
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _now() -> str:
    return _fmt(datetime.now(timezone.utc))


def _future(hours: int) -> str:
    return _fmt(datetime.now(timezone.utc) + timedelta(hours=hours))


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #
def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Return 'salt_hex$hash_hex' using PBKDF2-HMAC-SHA256."""
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                             bytes.fromhex(salt_hex), _PBKDF2_ROUNDS)
    return secrets.compare_digest(dk.hex(), hash_hex)


# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                employer_id  TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                email        TEXT,
                full_name    TEXT,
                pw_hash      TEXT NOT NULL,
                created_utc  TEXT NOT NULL
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token       TEXT PRIMARY KEY,
                employer_id TEXT NOT NULL,
                login_utc   TEXT NOT NULL,
                logout_utc  TEXT,
                expires_utc TEXT,
                ip          TEXT,
                FOREIGN KEY (employer_id) REFERENCES users(employer_id)
            )""")
        # case-insensitive lookup helper for company-name login
        conn.execute("CREATE INDEX IF NOT EXISTS idx_company ON users(company_name)")
        # migrate older DBs that predate the expiry column
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(sessions)")]
        if "expires_utc" not in cols:
            conn.execute("ALTER TABLE sessions ADD COLUMN expires_utc TEXT")
    _seed_demo_users()


class AuthError(Exception):
    pass


def _row_to_user(r: sqlite3.Row) -> User:
    return User(r["employer_id"], r["company_name"], r["email"] or "",
                r["full_name"] or r["employer_id"], r["created_utc"])


# --------------------------------------------------------------------------- #
# Registration & login
# --------------------------------------------------------------------------- #
def register_user(employer_id: str, company_name: str, password: str,
                  email: str = "", full_name: str = "") -> User:
    employer_id = (employer_id or "").strip()
    company_name = (company_name or "").strip()
    if not employer_id or not company_name or not password:
        raise AuthError("Employer ID, company name and password are required.")
    if len(password) < 6:
        raise AuthError("Password must be at least 6 characters.")
    with closing(_connect()) as conn, conn:
        exists = conn.execute("SELECT 1 FROM users WHERE employer_id = ?",
                              (employer_id,)).fetchone()
        if exists:
            raise AuthError(f"Employer ID '{employer_id}' is already registered.")
        dupe_co = conn.execute(
            "SELECT 1 FROM users WHERE lower(company_name) = lower(?)",
            (company_name,)).fetchone()
        if dupe_co:
            raise AuthError(f"Company '{company_name}' is already registered.")
        # Cross-namespace uniqueness: an Employer ID must not collide with any existing
        # company name, and vice versa — otherwise login-by-identifier is ambiguous.
        if conn.execute("SELECT 1 FROM users WHERE lower(company_name) = lower(?)",
                        (employer_id,)).fetchone():
            raise AuthError("That Employer ID collides with an existing company name.")
        if conn.execute("SELECT 1 FROM users WHERE employer_id = ?",
                        (company_name,)).fetchone():
            raise AuthError("That company name collides with an existing Employer ID.")
        created = _now()
        conn.execute(
            "INSERT INTO users VALUES (?,?,?,?,?,?)",
            (employer_id, company_name, email.strip(), (full_name or "").strip(),
             hash_password(password), created))
    return User(employer_id, company_name, email, full_name or employer_id, created)


def authenticate(identifier: str, password: str) -> User:
    """Look up by employer_id, falling back to company_name (case-insensitive), then
    verify the password. Exact Employer-ID match is tried first so the resolved identity
    is deterministic even if an ID and a company name happen to share a string."""
    identifier = (identifier or "").strip()
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE employer_id = ?",
                          (identifier,)).fetchone()
        if row is None:
            row = conn.execute("SELECT * FROM users WHERE lower(company_name) = lower(?)",
                             (identifier,)).fetchone()
    if not row or not verify_password(password, row["pw_hash"]):
        raise AuthError("Invalid credentials. Check your Employer ID / company name and password.")
    return _row_to_user(row)


def get_user(employer_id: str) -> Optional[User]:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE employer_id = ?",
                          (employer_id,)).fetchone()
    return _row_to_user(row) if row else None


# --------------------------------------------------------------------------- #
# Sessions (with login / logout timestamps)
# --------------------------------------------------------------------------- #
def start_session(employer_id: str, ip: Optional[str] = None) -> str:
    token = secrets.token_urlsafe(32)
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO sessions (token, employer_id, login_utc, expires_utc, ip) VALUES (?,?,?,?,?)",
            (token, employer_id, _now(), _future(SESSION_TTL_HOURS), ip))
    return token


def end_session(token: str) -> None:
    if not token:
        return
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE sessions SET logout_utc = ? WHERE token = ? AND logout_utc IS NULL",
                     (_now(), token))


def end_all_sessions(employer_id: str) -> None:
    """Invalidate every active session for a user (e.g. on password change / 'log out everywhere')."""
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE sessions SET logout_utc = ? WHERE employer_id = ? AND logout_utc IS NULL",
                     (_now(), employer_id))


def session_user(token: Optional[str]) -> Optional[User]:
    """Resolve an *active* (not logged-out, not expired) session token to its user."""
    if not token:
        return None
    with closing(_connect()) as conn:
        row = conn.execute(
            """SELECT u.* FROM sessions s JOIN users u ON u.employer_id = s.employer_id
               WHERE s.token = ? AND s.logout_utc IS NULL
                 AND (s.expires_utc IS NULL OR s.expires_utc > ?)""",
            (token, _now())).fetchone()
    return _row_to_user(row) if row else None


def session_history(employer_id: str, limit: int = 50) -> List[Session]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            """SELECT * FROM sessions WHERE employer_id = ?
               ORDER BY login_utc DESC LIMIT ?""", (employer_id, limit)).fetchall()
    return [Session(r["token"], r["employer_id"], r["login_utc"], r["logout_utc"], r["ip"])
            for r in rows]


def last_login(employer_id: str, exclude_token: Optional[str] = None) -> Optional[str]:
    """The previous login time (for the dashboard 'last login' line)."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT token, login_utc FROM sessions WHERE employer_id = ? ORDER BY login_utc DESC LIMIT 5",
            (employer_id,)).fetchall()
    for r in rows:
        if r["token"] != exclude_token:
            return r["login_utc"]
    return None


# --------------------------------------------------------------------------- #
# Demo seed
# --------------------------------------------------------------------------- #
DEMO_USERS = [
    ("EMP001", "Acme Lending", "ops@acme-lending.example", "Alex Carter", "demo1234"),
    ("EMP002", "Northwind Finance", "risk@northwind.example", "Priya Shah", "demo1234"),
    ("EMP003", "Sterling Credit Union", "admin@sterling.example", "Jordan Lee", "demo1234"),
]


def _seed_demo_users() -> None:
    with closing(_connect()) as conn:
        have = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    if have:
        return
    for eid, co, email, name, pw in DEMO_USERS:
        try:
            register_user(eid, co, pw, email=email, full_name=name)
        except AuthError:
            pass
