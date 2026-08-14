from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import AchievementListResponse
from fastapi import HTTPException

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import AchievementListResponse
from ..services.achievement_service import ACHIEVEMENTS, CATEGORIES, _award, get_user_achievements

router = APIRouter(prefix="/api/achievements", tags=["achievement"])

_EASTER_EGG_KEYS = {"konami_code"}


@router.get("", response_model=AchievementListResponse)
def list_achievements(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = get_user_achievements(db, user.id)
    return {"achievements": items, "categories": CATEGORIES}


@router.post("/award/{key}")
def award_achievement(
    key: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Award an easter-egg style achievement (client-triggered)."""
    if key not in _EASTER_EGG_KEYS:
        raise HTTPException(status_code=404, detail="成就不存在")
    if key not in ACHIEVEMENTS:
        raise HTTPException(status_code=404, detail="成就不存在")
    if _award(db, user.id, key):
        db.commit()
        return {"awarded": True, "name": ACHIEVEMENTS[key]["name"], "icon": ACHIEVEMENTS[key]["icon"]}
    return {"awarded": False, "message": "已拥有此成就"}
