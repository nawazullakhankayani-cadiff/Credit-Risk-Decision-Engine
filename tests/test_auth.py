"""Tests for the web auth backend (users, login, sessions)."""
import os
import tempfile

import pytest

# Point the auth DB at a temp file BEFORE importing the module.
_TMP = tempfile.mkdtemp()
os.environ["CREDIT_AUTH_DB"] = os.path.join(_TMP, "test_app.db")

from credit_risk.web import auth  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    # fresh DB per test
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(auth.DB_PATH.as_posix() + suffix)
        except OSError:
            pass
    auth.init_db()


def test_password_hash_roundtrip():
    h = auth.hash_password("hunter2")
    assert "$" in h and h != "hunter2"
    assert auth.verify_password("hunter2", h)
    assert not auth.verify_password("wrong", h)


def test_demo_users_seeded_and_login_by_id_and_company():
    u1 = auth.authenticate("EMP001", "demo1234")
    assert u1.company_name == "Acme Lending"
    u2 = auth.authenticate("northwind finance", "demo1234")  # case-insensitive company
    assert u2.employer_id == "EMP002"


def test_bad_password_rejected():
    with pytest.raises(auth.AuthError):
        auth.authenticate("EMP001", "nope")


def test_register_and_duplicate_guard():
    u = auth.register_user("EMP900", "Zeta Bank", "secret9", full_name="Sam")
    assert u.employer_id == "EMP900"
    assert auth.authenticate("Zeta Bank", "secret9").full_name == "Sam"
    with pytest.raises(auth.AuthError):
        auth.register_user("EMP900", "Other Co", "secret9")     # dup id
    with pytest.raises(auth.AuthError):
        auth.register_user("EMP901", "zeta bank", "secret9")    # dup company (ci)
    with pytest.raises(auth.AuthError):
        auth.register_user("EMP902", "Tiny", "123")             # weak password


def test_session_lifecycle_records_login_and_logout():
    tok = auth.start_session("EMP001", "1.2.3.4")
    assert auth.session_user(tok).employer_id == "EMP001"
    hist = auth.session_history("EMP001")
    assert hist and hist[0].logout_utc is None and hist[0].ip == "1.2.3.4"
    auth.end_session(tok)
    assert auth.session_user(tok) is None                       # invalidated
    assert auth.session_history("EMP001")[0].logout_utc is not None


def test_unknown_token_is_anonymous():
    assert auth.session_user("does-not-exist") is None
    assert auth.session_user(None) is None


def test_cross_namespace_collision_rejected():
    auth.register_user("ACME", "Acme Co", "secret9")
    # new employer_id equals an existing company name
    with pytest.raises(auth.AuthError):
        auth.register_user("Acme Co", "Different Co", "secret9")
    # new company name equals an existing employer_id
    with pytest.raises(auth.AuthError):
        auth.register_user("EMPX", "ACME", "secret9")


def test_expired_session_is_invalid(monkeypatch):
    monkeypatch.setattr(auth, "SESSION_TTL_HOURS", -1)   # already expired on creation
    tok = auth.start_session("EMP001")
    assert auth.session_user(tok) is None


def test_end_all_sessions():
    t1 = auth.start_session("EMP003")
    t2 = auth.start_session("EMP003")
    assert auth.session_user(t1) and auth.session_user(t2)
    auth.end_all_sessions("EMP003")
    assert auth.session_user(t1) is None and auth.session_user(t2) is None
