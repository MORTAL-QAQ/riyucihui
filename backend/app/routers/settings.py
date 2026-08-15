import json
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import config
from ..auth import get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import User
from ..schemas import ChangePasswordRequest, UpdateNameRequest

router = APIRouter(prefix="/api", tags=["settings"])

SETTINGS_FILE = Path(__file__).parent.parent.parent / "data" / "settings.json"

DEFAULT_SETTINGS = {
    "speaker": config.VOICEVOX_SPEAKER,
    "speed": 1.0,
    "pitch": 0.0,
    "intonation": 1.0,
    "volume": 1.0,
}


def read_settings():
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_SETTINGS, **data}
        except (json.JSONDecodeError, ValueError):
            pass
    return dict(DEFAULT_SETTINGS)


def _write_settings(data: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class SettingsOut(BaseModel):
    speaker: int
    speed: float
    pitch: float
    intonation: float
    volume: float


class SettingsUpdate(BaseModel):
    speaker: int = Field(default=1, ge=0, le=100)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=0.0, ge=-0.15, le=0.15)
    intonation: float = Field(default=1.0, ge=0.0, le=2.0)
    volume: float = Field(default=1.0, ge=0.0, le=2.0)


@router.get("/speakers")
async def list_speakers(user: User = Depends(get_current_user)):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{config.VOICEVOX_BASE_URL}/speakers")
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="获取音色列表失败")
            return resp.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="VOICEVOX Engine 未运行")


@router.get("/settings", response_model=SettingsOut)
def get_settings(user: User = Depends(get_current_user)):
    return SettingsOut(**read_settings())


@router.put("/settings", response_model=SettingsOut)
def update_settings(body: SettingsUpdate, user: User = Depends(get_current_user)):
    data = body.model_dump()
    _write_settings(data)
    return SettingsOut(**data)


@router.put("/settings/password")
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码：验证旧密码 → 更新哈希 → 递增 token_version 使旧 Token 全部失效。"""
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")

    user.password_hash = hash_password(body.new_password)
    user.token_version = (user.token_version or 0) + 1
    db.commit()
    return {"message": "密码已修改，请重新登录"}


@router.put("/settings/name")
def update_name(
    body: UpdateNameRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改显示名（昵称）。"""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="昵称不能为空")
    user.name = name[:50]
    db.commit()
    return {"message": "昵称已更新", "name": user.name}
