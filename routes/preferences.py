"""Preferences routes — save, get, update."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, User, Preference, new_id
from auth_core import get_current_user
from api_schemas import PreferenceRequest, PreferenceResponse

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


@router.put("", response_model=PreferenceResponse)
def save_preferences(
    req: PreferenceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save or update user's job search preferences. PUT = full replace."""
    pref = db.query(Preference).filter(Preference.user_id == user.id).first()

    if pref:
        # Update existing
        pref.target_roles = req.target_roles
        pref.locations = req.locations
        pref.salary_min = req.salary_min
        pref.salary_max = req.salary_max
        pref.remote_preference = req.remote_preference
        pref.company_size_preference = req.company_size_preference
        pref.industries = req.industries
        pref.dealbreakers = req.dealbreakers
        pref.updated_at = datetime.now(timezone.utc)
    else:
        # Create new
        pref = Preference(
            id=new_id(),
            user_id=user.id,
            target_roles=req.target_roles,
            locations=req.locations,
            salary_min=req.salary_min,
            salary_max=req.salary_max,
            remote_preference=req.remote_preference,
            company_size_preference=req.company_size_preference,
            industries=req.industries,
            dealbreakers=req.dealbreakers,
        )
        db.add(pref)

    db.commit()
    db.refresh(pref)

    return PreferenceResponse(
        id=pref.id,
        target_roles=pref.target_roles or [],
        locations=pref.locations or [],
        salary_min=pref.salary_min,
        salary_max=pref.salary_max,
        remote_preference=pref.remote_preference or "any",
        company_size_preference=pref.company_size_preference or [],
        industries=pref.industries or [],
        dealbreakers=pref.dealbreakers or [],
        updated_at=pref.updated_at,
    )


@router.get("", response_model=PreferenceResponse)
def get_preferences(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's job search preferences."""
    pref = db.query(Preference).filter(Preference.user_id == user.id).first()
    if not pref:
        raise HTTPException(status_code=404, detail="No preferences set yet")

    return PreferenceResponse(
        id=pref.id,
        target_roles=pref.target_roles or [],
        locations=pref.locations or [],
        salary_min=pref.salary_min,
        salary_max=pref.salary_max,
        remote_preference=pref.remote_preference or "any",
        company_size_preference=pref.company_size_preference or [],
        industries=pref.industries or [],
        dealbreakers=pref.dealbreakers or [],
        updated_at=pref.updated_at,
    )
