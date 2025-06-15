import secrets
from uuid import UUID, uuid4
from pydantic import BaseModel
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi_sessions.backends.implementations import InMemoryBackend
from fastapi_sessions.session_verifier import SessionVerifier
from fastapi_sessions.frontends.implementations import SessionCookie, CookieParameters
from core.config import SESSION_SECRET_KEY

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# --- Session Management ---

# Pydantic model for session data
class SessionData(BaseModel):
    user_id: str
    username: str
    email: str

# In-memory backend for session storage
backend = InMemoryBackend[UUID, SessionData]()

# Basic session verifier
class BasicVerifier(SessionVerifier[UUID, SessionData]):
    def __init__(
        self,
        *,
        identifier: str,
        auto_error: bool,
        backend: InMemoryBackend[UUID, SessionData],
        auth_http_exception: HTTPException,
    ):
        self._identifier = identifier
        self._auto_error = auto_error
        self._backend = backend
        self._auth_http_exception = auth_http_exception

    @property
    def identifier(self):
        return self._identifier

    @property
    def backend(self):
        return self._backend

    @property
    def auto_error(self):
        return self._auto_error

    @property
    def auth_http_exception(self):
        return self._auth_http_exception

    def verify_session(self, model: SessionData) -> bool:
        """Verify the session data. For this basic verifier, we trust any valid model."""
        return True

# Exception for unauthorized access
auth_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN, detail="Invalid session"
)

# Initialize the verifier
verifier = BasicVerifier(
    identifier="general_verifier",
    auto_error=True,
    backend=backend,
    auth_http_exception=auth_exception,
)

# Cookie parameters for the session
cookie_params = CookieParameters()

# Session cookie manager
cookie = SessionCookie(
    cookie_name="session_id",
    identifier="general_verifier",
    auto_error=True,
    secret_key=SESSION_SECRET_KEY,  # Use secret key from config
    cookie_params=cookie_params,
)

optional_cookie = SessionCookie(
    cookie_name="session_id",
    identifier="general_verifier",
    auto_error=False,
    secret_key=SESSION_SECRET_KEY,
    cookie_params=cookie_params,
)
