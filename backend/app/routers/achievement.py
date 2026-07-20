from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import AchievementListResponse
from ..services.achievement_service import CATEGORIES, get_user_achievements

router = APIRouter(prefix="/api/achievements", tags=["achievement"])


@router.get("", response_model=AchievementListResponse)
def list_achievements(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = get_user_achievements(db, user.id)
    return {"achievements": items, "categories": CATEGORIES}
