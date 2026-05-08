from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from api._lib.db import get_db
from api._lib.models import User, UserProfile
from api._lib.schemas import ProfileResponse, ProfileUpdateRequest, UserResponse
from api._lib.security import get_current_user_id

router = APIRouter()


@router.get("", response_model=ProfileResponse)
def get_profile(user_id: str = Depends(get_current_user_id)):
    with get_db() as session:
        profile = session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        ).scalar_one_or_none()
        if not profile:
            raise HTTPException(status_code=404, detail="Profil introuvable")
        return ProfileResponse.model_validate(profile)


@router.put("", response_model=ProfileResponse)
def update_profile(body: ProfileUpdateRequest, user_id: str = Depends(get_current_user_id)):
    with get_db() as session:
        profile = session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        ).scalar_one_or_none()
        if not profile:
            raise HTTPException(status_code=404, detail="Profil introuvable")

        for field, value in body.model_dump(exclude_none=True).items():
            setattr(profile, field, value)

        session.flush()
        return ProfileResponse.model_validate(profile)


@router.get("/me", response_model=UserResponse)
def get_me(user_id: str = Depends(get_current_user_id)):
    with get_db() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        return UserResponse.model_validate(user)
