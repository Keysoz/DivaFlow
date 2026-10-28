"""Authentication, MFA and owner bootstrap (TASK-PUB-01)."""

import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cloud_api.audit import record_audit
from cloud_api.config import get_settings
from cloud_api.db import get_db
from cloud_api.deps import get_current_user, require_owner
from cloud_api.models import AuditLog, RefreshToken, User
from cloud_api.schemas import (
    AuditOut,
    BootstrapRequest,
    LoginRequest,
    MfaEnableRequest,
    MfaEnableResponse,
    MfaSetupRequest,
    MfaSetupResponse,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserOut,
)
from cloud_api.security import (
    create_access_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    hash_recovery_code,
    hash_refresh_token,
    new_recovery_codes,
    new_refresh_token,
    new_totp_secret,
    totp_uri,
    verify_password,
    verify_totp,
)

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()
FAILURE_ACTIONS = ("auth.login", "auth.mfa_setup", "auth.mfa_enable")
MAX_FAILURES = 5
FAILURE_WINDOW_MINUTES = 15


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _expires_at() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_days)


def _issue_tokens(db: Session, user: User) -> TokenPair:
    access = create_access_token(user.id, user.email, user.role)
    refresh = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh),
            expires_at=_expires_at(),
        )
    )
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_minutes * 60,
    )


def _get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def _check_failure_rate(
    db: Session,
    email: str,
    request: Request,
    actions: tuple[str, ...] = FAILURE_ACTIONS,
) -> None:
    since = datetime.now(UTC) - timedelta(minutes=FAILURE_WINDOW_MINUTES)
    base = [
        AuditLog.action.in_(actions),
        AuditLog.result == "failed",
        AuditLog.created_at >= since,
    ]
    conditions = [and_(func.lower(AuditLog.actor) == email.lower(), *base)]
    if request.client and request.client.host:
        conditions.append(and_(AuditLog.ip == request.client.host, *base))
    failures = db.scalar(select(func.count()).select_from(AuditLog).where(or_(*conditions)))
    if failures and failures >= MAX_FAILURES:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts; try again later",
        )


@router.post("/bootstrap", response_model=MfaSetupResponse, status_code=201)
def bootstrap(
    payload: BootstrapRequest,
    request: Request,
    x_bootstrap_token: str = Header(default=""),
    db: Session = Depends(get_db),
) -> MfaSetupResponse:
    """Create the single owner account, once, guarded by the bootstrap token."""
    expected = settings.bootstrap_token.get_secret_value()
    if not secrets.compare_digest(x_bootstrap_token, expected):
        record_audit(
            db,
            actor=str(payload.email),
            action="auth.bootstrap",
            result="failed",
            detail="invalid bootstrap token",
            request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bootstrap token")
    if db.scalar(select(func.count()).select_from(User)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Owner already exists")
    secret = new_totp_secret()
    user = User(
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role="owner",
        totp_secret_encrypted=encrypt_secret(secret),
        mfa_enabled=False,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Owner already exists"
        ) from exc
    record_audit(db, actor=user.email, action="auth.bootstrap", target=user.email, request=request)
    db.commit()
    return MfaSetupResponse(secret=secret, otpauth_uri=totp_uri(secret, user.email))


@router.post("/mfa/setup", response_model=MfaSetupResponse)
def mfa_setup(
    payload: MfaSetupRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MfaSetupResponse:
    email = str(payload.email)
    _check_failure_rate(db, email, request, ("auth.mfa_setup", "auth.mfa_enable"))
    user = _get_user_by_email(db, email)
    if user is None or not verify_password(payload.password, user.password_hash):
        record_audit(
            db,
            actor=email,
            action="auth.mfa_setup",
            result="failed",
            detail="invalid credentials",
            request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    if user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA already enabled")
    if user.totp_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MFA is already initialized; use the audited reset procedure",
        )
    secret = new_totp_secret()
    user.totp_secret_encrypted = encrypt_secret(secret)
    record_audit(db, actor=user.email, action="auth.mfa_setup", target=user.email, request=request)
    db.commit()
    return MfaSetupResponse(secret=secret, otpauth_uri=totp_uri(secret, user.email))


@router.post("/mfa/enable", response_model=MfaEnableResponse)
def mfa_enable(
    payload: MfaEnableRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MfaEnableResponse:
    email = str(payload.email)
    _check_failure_rate(db, email, request, ("auth.mfa_setup", "auth.mfa_enable"))
    user = _get_user_by_email(db, email)
    if user is None or not verify_password(payload.password, user.password_hash):
        record_audit(
            db,
            actor=email,
            action="auth.mfa_enable",
            result="failed",
            detail="invalid credentials",
            request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    if user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA already enabled")
    if not user.totp_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Start MFA setup first")
    secret = decrypt_secret(user.totp_secret_encrypted)
    if not verify_totp(secret, payload.code):
        record_audit(
            db,
            actor=user.email,
            action="auth.mfa_enable",
            result="failed",
            detail="invalid mfa code",
            request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
    codes = new_recovery_codes(8)
    user.mfa_enabled = True
    user.recovery_codes_hashed = json.dumps([hash_recovery_code(code) for code in codes])
    record_audit(db, actor=user.email, action="auth.mfa_enable", target=user.email, request=request)
    db.commit()
    return MfaEnableResponse(recovery_codes=codes)


def _consume_recovery_code(user: User, code: str) -> bool:
    if not user.recovery_codes_hashed:
        return False
    hashes = json.loads(user.recovery_codes_hashed)
    target = hash_recovery_code(code)
    if target not in hashes:
        return False
    hashes.remove(target)
    user.recovery_codes_hashed = json.dumps(hashes)
    return True


@router.post("/login", response_model=TokenPair)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenPair:
    email = str(payload.email)
    _check_failure_rate(db, email, request, ("auth.login",))
    user = _get_user_by_email(db, email)
    if user is None or not verify_password(payload.password, user.password_hash):
        record_audit(
            db,
            actor=email,
            action="auth.login",
            result="failed",
            detail="invalid credentials",
            request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        record_audit(
            db,
            actor=user.email,
            action="auth.login",
            result="failed",
            detail="inactive user",
            request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    if user.role == "owner" and not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="MFA setup required for the owner"
        )
    if user.mfa_enabled:
        if not payload.totp and not payload.recovery_code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="mfa_required")
        verified = False
        if payload.totp and user.totp_secret_encrypted:
            verified = verify_totp(decrypt_secret(user.totp_secret_encrypted), payload.totp)
        elif payload.recovery_code:
            verified = _consume_recovery_code(user, payload.recovery_code)
        if not verified:
            record_audit(
                db,
                actor=user.email,
                action="auth.login",
                result="failed",
                detail="invalid mfa",
                request=request,
            )
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
    tokens = _issue_tokens(db, user)
    user.last_login_at = datetime.now(UTC)
    record_audit(db, actor=user.email, action="auth.login", target=user.email, request=request)
    db.commit()
    return tokens


def _revoke_all(db: Session, user_id: int) -> None:
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))


@router.post("/refresh", response_model=TokenPair)
def refresh(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenPair:
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = datetime.now(UTC)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    if _as_utc(stored.expires_at) < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired refresh token"
        )
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    if stored.revoked:
        _revoke_all(db, stored.user_id)
        record_audit(
            db,
            actor=user.email,
            action="auth.refresh_reuse",
            result="failed",
            detail="replayed refresh token; all sessions revoked",
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    rotated = db.execute(
        update(RefreshToken)
        .where(RefreshToken.id == stored.id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
    if cast(Any, rotated).rowcount != 1:
        _revoke_all(db, stored.user_id)
        record_audit(
            db,
            actor=user.email,
            action="auth.refresh_reuse",
            result="failed",
            detail="concurrent refresh; all sessions revoked",
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    tokens = _issue_tokens(db, user)
    record_audit(db, actor=user.email, action="auth.refresh", target=user.email, request=request)
    db.commit()
    return tokens


@router.post("/logout", status_code=204)
def logout(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if stored:
        stored.revoked = True
        user = db.get(User, stored.user_id)
        record_audit(
            db,
            actor=user.email if user else str(stored.user_id),
            action="auth.logout",
            request=request,
        )
        db.commit()
    else:
        record_audit(
            db,
            actor=None,
            action="auth.logout",
            result="failed",
            detail="unknown refresh token",
            request=request,
        )
        db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        mfa_enabled=user.mfa_enabled,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@admin_router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    request: Request,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> UserOut:
    if payload.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="A second owner is not allowed"
        )
    if _get_user_by_email(db, str(payload.email)) is not None:
        record_audit(
            db,
            actor=owner.email,
            action="admin.user_create",
            target=str(payload.email),
            result="failed",
            detail="email already exists",
            request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    user = User(
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already exists"
        ) from exc
    record_audit(
        db, actor=owner.email, action="admin.user_create", target=user.email, request=request
    )
    db.commit()
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        mfa_enabled=user.mfa_enabled,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@admin_router.get("/audit", response_model=list[AuditOut])
def audit_log(
    limit: int = 50,
    admin: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> list[AuditOut]:
    limit = max(1, min(limit, 200))
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).all()
    return [
        AuditOut(
            id=row.id,
            actor=row.actor,
            action=row.action,
            target=row.target,
            result=row.result,
            ip=row.ip,
            created_at=row.created_at,
        )
        for row in rows
    ]
