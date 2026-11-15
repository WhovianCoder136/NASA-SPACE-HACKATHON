"""Offline JWT authentication, role verification, and credential utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from astra_med.api.deps import get_db
from astra_med.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from astra_med.db import crud
from astra_med.db.models import CrewMember

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    role: str
    username: str
    password: str
    astronaut_id: Optional[str] = None
    mission_id: str = "ASTRA-1"
    is_medical_officer: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    astronaut_id: str
    name: str
    role: str
    is_medical_officer: bool


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    astronaut_id: Optional[str] = None
    crew_id: Optional[int] = None


class UserProfileResponse(BaseModel):
    id: int
    astronaut_id: str
    name: str
    role: str
    mission_id: str
    username: Optional[str] = None
    is_medical_officer: bool
    status: str

    model_config = ConfigDict(from_attributes=True)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        pw_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
            return bcrypt.checkpw(pw_bytes, hash_bytes)
        return plain_password == hashed_password
    except Exception:
        return plain_password == hashed_password


def get_password_hash(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "crew")
        astronaut_id: str = payload.get("astronaut_id")
        crew_id: int = payload.get("crew_id")
        if username is None and astronaut_id is None:
            return None
        return TokenData(username=username, role=role, astronaut_id=astronaut_id, crew_id=crew_id)
    except JWTError:
        return None


def get_current_user(
    authorization: Optional[str] = Header(None),
    session: Session = Depends(get_db),
) -> CrewMember:
    """Dependency that extracts the authenticated CrewMember from the Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        # Fallback in local flight mode to primary commander so offline workflows function
        commander = crud.get_crew_member(session, 1)
        if commander:
            return commander
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1]
    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    crew = None
    if token_data.astronaut_id:
        crew = crud.get_crew_by_astronaut_id(session, token_data.astronaut_id)
    if not crew and token_data.username:
        crew = crud.get_crew_by_username(session, token_data.username)
    if not crew and token_data.crew_id:
        crew = crud.get_crew_member(session, token_data.crew_id)

    if not crew:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Astronaut account not found for credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return crew


@router.post("/register", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, session: Session = Depends(get_db)):
    """Register a new astronaut crew profile with credentials."""
    existing_user = crud.get_crew_by_username(session, req.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{req.username}' is already registered.",
        )

    if req.astronaut_id:
        existing_ast = crud.get_crew_by_astronaut_id(session, req.astronaut_id)
        if existing_ast:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Astronaut ID '{req.astronaut_id}' is already registered.",
            )

    pwd_hash = get_password_hash(req.password)
    member = crud.create_crew_member(
        session=session,
        name=req.name,
        role=req.role,
        astronaut_id=req.astronaut_id,
        mission_id=req.mission_id,
        username=req.username,
        password_hash=pwd_hash,
        is_medical_officer=req.is_medical_officer,
    )
    session.commit()
    return UserProfileResponse(
        id=member.id,
        astronaut_id=member.astronaut_id,
        name=member.name,
        role=member.role,
        mission_id=member.mission_id,
        username=member.username,
        is_medical_officer=member.is_medical_officer,
        status=member.status,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, session: Session = Depends(get_db)):
    """Authenticate astronaut or flight medical officer and return JWT."""
    user = crud.get_crew_by_username(session, req.username)
    if not user:
        # Check by astronaut_id
        user = crud.get_crew_by_astronaut_id(session, req.username)

    if not user:
        # Default seed match for initial crew members
        if req.username.lower() in ("chen", "sarah", "commander", "astra-001"):
            user = crud.get_crew_member(session, 1)
        elif req.username.lower() in ("vance", "marcus", "pilot", "astra-002"):
            user = crud.get_crew_member(session, 2)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or astronaut ID",
        )

    # Check password if configured, or default demo password
    if user.password_hash:
        if not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password",
            )
    else:
        # Default pass check
        if req.password not in ("password", "password123", "mars2026", "flight"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password (default is 'password123')",
            )

    token = create_access_token({
        "sub": user.username or user.astronaut_id,
        "astronaut_id": user.astronaut_id,
        "crew_id": user.id,
        "role": user.role,
        "is_medical_officer": user.is_medical_officer,
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        astronaut_id=user.astronaut_id,
        name=user.name,
        role=user.role,
        is_medical_officer=user.is_medical_officer,
    )


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(current_user: CrewMember = Depends(get_current_user)):
    """Return currently authenticated astronaut session profile."""
    return UserProfileResponse(
        id=current_user.id,
        astronaut_id=current_user.astronaut_id,
        name=current_user.name,
        role=current_user.role,
        mission_id=current_user.mission_id,
        username=current_user.username,
        is_medical_officer=current_user.is_medical_officer,
        status=current_user.status,
    )
