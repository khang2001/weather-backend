"""
Phase 1 — S1 (bcrypt) + S2 (JWT) unit tests. No DB, no network.
"""
import pytest
from jose import jwt

from app.security import hash_password, verify_password, create_access_token
from app.config import JWT_SECRET, JWT_ALGORITHM


# --- S1: password hashing --------------------------------------------------

def test_hash_is_bcrypt_format():
    hashed = hash_password("hunter2")
    assert hashed.startswith("$2b$")
    assert hashed != "hunter2"


def test_verify_round_trips():
    hashed = hash_password("hunter2")
    assert verify_password("hunter2", hashed) is True


def test_verify_rejects_wrong_password():
    hashed = hash_password("hunter2")
    assert verify_password("wrong", hashed) is False


def test_same_password_hashes_differ():
    """bcrypt salts each hash — two hashes of the same password are different."""
    assert hash_password("same") != hash_password("same")


# --- S2: JWT ---------------------------------------------------------------

def test_token_encodes_user_id_in_sub():
    token = create_access_token(42)
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == "42"


def test_token_has_expiry_claim():
    token = create_access_token(1)
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert "exp" in payload


def test_tampered_token_fails_to_decode():
    token = create_access_token(1)
    tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    with pytest.raises(jwt.JWTError):
        jwt.decode(tampered, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def test_wrong_secret_fails_to_decode():
    token = create_access_token(1)
    with pytest.raises(jwt.JWTError):
        jwt.decode(token, "wrong-secret", algorithms=[JWT_ALGORITHM])
