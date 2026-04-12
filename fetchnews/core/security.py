from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import User, UserRole
from fetchnews.settings import Settings

PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
ROLE_PRIORITY = {
    UserRole.VIEWER: 0,
    UserRole.EDITOR: 1,
    UserRole.ADMIN: 2,
}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    )
    encoded_key = base64.urlsafe_b64encode(derived_key).decode("utf-8").rstrip("=")
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt}${encoded_key}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash.startswith(f"{PASSWORD_SCHEME}$"):
        return secrets.compare_digest(password, stored_hash)

    try:
        _scheme, iterations_value, salt, encoded_key = stored_hash.split("$", 3)
        iterations = int(iterations_value)
    except ValueError:
        return False

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    computed = base64.urlsafe_b64encode(derived_key).decode("utf-8").rstrip("=")
    return hmac.compare_digest(computed, encoded_key)


def role_satisfies(actual_role: str, required_role: str) -> bool:
    return ROLE_PRIORITY.get(UserRole(actual_role), -1) >= ROLE_PRIORITY.get(UserRole(required_role), 99)


def ensure_bootstrap_admin(session: Session, settings: Settings) -> User | None:
    if not settings.auth_enabled:
        return None

    user = session.scalar(select(User).where(User.username == settings.bootstrap_admin_username))
    if user is not None:
        return user

    user = User(
        username=settings.bootstrap_admin_username,
        display_name=settings.bootstrap_admin_display_name,
        role=UserRole.ADMIN,
        password_hash=hash_password(settings.bootstrap_admin_password),
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None

    user.last_login_at = datetime.now(UTC)
    session.flush()
    return user


def create_access_token(user: User, settings: Settings, *, now: datetime | None = None) -> tuple[str, datetime]:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "exp": int(expires_at.timestamp()),
        "iat": int(issued_at.timestamp()),
    }
    token = _encode_token(payload, settings.auth_secret_key)
    return token, expires_at


def decode_access_token(token: str, settings: Settings, *, now: datetime | None = None) -> dict[str, Any] | None:
    try:
        payload = _decode_token(token, settings.auth_secret_key)
    except ValueError:
        return None

    current_time = now or datetime.now(UTC)
    if int(payload.get("exp", 0)) < int(current_time.timestamp()):
        return None
    return payload


# ??? JWT?????? payload.signature ??? HMAC token?
# ?? JOSE header / alg / kid / aud / iss????????? JWT ???
def _encode_token(payload: dict[str, Any], secret_key: str) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = _urlsafe_b64encode(payload_json)
    signature = hmac.new(secret_key.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).digest()
    encoded_signature = _urlsafe_b64encode(signature)
    return f"{encoded_payload}.{encoded_signature}"


def _decode_token(token: str, secret_key: str) -> dict[str, Any]:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Malformed token") from exc

    expected_signature = hmac.new(secret_key.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).digest()
    actual_signature = _urlsafe_b64decode(encoded_signature)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("Invalid signature")

    payload = json.loads(_urlsafe_b64decode(encoded_payload))
    if not isinstance(payload, dict):
        raise ValueError("Invalid payload")
    return payload


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


class LoginRateLimiter:
    """In-memory sliding-window limiter for login failures."""

    def __init__(
        self,
        *,
        max_failures: int,
        window_seconds: int,
        block_seconds: int,
    ) -> None:
        self._max_failures = max(max_failures, 1)
        self._window = timedelta(seconds=max(window_seconds, 1))
        self._block = timedelta(seconds=max(block_seconds, 1))
        self._failures: dict[tuple[str, str], deque[datetime]] = {}
        self._blocked_until: dict[tuple[str, str], datetime] = {}
        self._lock = threading.Lock()

    def check(self, username: str, client_ip: str, *, now: datetime | None = None) -> datetime | None:
        current_time = now or datetime.now(UTC)
        key = (username or "", client_ip or "")
        with self._lock:
            blocked_until = self._blocked_until.get(key)
            if blocked_until is None:
                return None
            if current_time >= blocked_until:
                self._blocked_until.pop(key, None)
                self._failures.pop(key, None)
                return None
            return blocked_until

    def register_failure(self, username: str, client_ip: str, *, now: datetime | None = None) -> datetime | None:
        current_time = now or datetime.now(UTC)
        key = (username or "", client_ip or "")
        with self._lock:
            bucket = self._failures.setdefault(key, deque())
            bucket.append(current_time)
            window_start = current_time - self._window
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            if len(bucket) >= self._max_failures:
                blocked_until = current_time + self._block
                self._blocked_until[key] = blocked_until
                return blocked_until
            return None

    def register_success(self, username: str, client_ip: str) -> None:
        key = (username or "", client_ip or "")
        with self._lock:
            self._failures.pop(key, None)
            self._blocked_until.pop(key, None)


def build_login_rate_limiter(settings: Settings) -> LoginRateLimiter:
    return LoginRateLimiter(
        max_failures=settings.login_rate_limit_max_failures,
        window_seconds=settings.login_rate_limit_window_seconds,
        block_seconds=settings.login_rate_limit_block_seconds,
    )
