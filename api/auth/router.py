import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api._lib.db import get_db
from api._lib.email import send_reset_email
from api._lib.models import PasswordResetToken, User, UserProfile
from api._lib.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from api._lib.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from api._lib.config import get_settings

router = APIRouter()


def _make_tokens(user_id: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


def _create_default_profile(session, user_id: str) -> None:
    profile = UserProfile(user_id=user_id)
    session.add(profile)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    with get_db() as session:
        existing = session.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email")

        user = User(
            email=body.email,
            password_hash=hash_password(body.password),
            name=body.name,
        )
        session.add(user)
        session.flush()
        _create_default_profile(session, user.id)
        user_id = user.id

    return _make_tokens(user_id)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    with get_db() as session:
        user = session.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
        if user:
            user_id = user.id
            password_hash = user.password_hash
        else:
            user_id = None
            password_hash = None

    if not user_id or not password_hash or not verify_password(body.password, password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    return _make_tokens(user_id)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest):
    user_id = decode_token(body.refresh_token, token_type="refresh")
    return _make_tokens(user_id)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(body: ForgotPasswordRequest):
    settings = get_settings()
    with get_db() as session:
        user = session.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
        if not user:
            return  # Ne pas révéler si l'email existe ou non

        token_value = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token_value,
            expires_at=expires_at,
        )
        session.add(reset_token)

    reset_url = f"{settings.app_url}/reset-password?token={token_value}"
    send_reset_email(body.email, reset_url)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(body: ResetPasswordRequest):
    with get_db() as session:
        record = session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == body.token)
        ).scalar_one_or_none()

        if not record:
            raise HTTPException(status_code=400, detail="Token invalide")
        if record.used:
            raise HTTPException(status_code=400, detail="Token déjà utilisé")
        if record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Token expiré")

        user = session.get(User, record.user_id)
        if not user:
            raise HTTPException(status_code=400, detail="Utilisateur introuvable")

        user.password_hash = hash_password(body.new_password)
        record.used = True


@router.post("/google-signin", response_model=TokenResponse)
def google_signin(body: dict):
    """Appelé par NextAuth après authentification Google."""
    google_id: str = body.get("google_id", "")
    email: str = body.get("email", "")
    name: str = body.get("name", "")

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Données Google manquantes")

    with get_db() as session:
        user = session.execute(select(User).where(User.google_id == google_id)).scalar_one_or_none()

        if not user:
            # Cherche par email (liaison de compte)
            user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user:
                user.google_id = google_id
            else:
                user = User(email=email, name=name, google_id=google_id)
                session.add(user)
                session.flush()
                _create_default_profile(session, user.id)
        user_id = user.id

    return _make_tokens(user_id)


@router.get("/me", response_model=UserResponse)
def me(user_id: str = None):
    """Retourne l'utilisateur courant. user_id injecté par le middleware."""
    with get_db() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        return UserResponse.model_validate(user)
