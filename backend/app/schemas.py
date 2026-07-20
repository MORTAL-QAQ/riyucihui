"""Pydantic 请求/响应数据模型。

所有 API 的输入验证和输出序列化都通过这些 schema 定义。
使用 Pydantic Field 进行字段校验（长度、正则模式、数值范围等）。

命名约定：
- XXXRequest: 客户端请求体
- XXXResponse: 单条响应体
- XXXOut: 数据库查询输出（通常配置 from_attributes = True）
- XXXListResponse: 分页列表响应
"""

from datetime import datetime

from pydantic import BaseModel, Field

# ── Auth ──
USERNAME_PATTERN = r"^[a-zA-Z0-9_一-鿿]+$"


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, pattern=USERNAME_PATTERN)
    password: str = Field(..., min_length=6, max_length=72)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    is_admin: bool = False


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool = False
    created_at: datetime
    new_achievements: list[dict] | None = None

    class Config:
        from_attributes = True


# ── Words ──
class WordFields(BaseModel):
    """日语单词共享字段"""

    japanese: str = Field(..., min_length=1, max_length=100)
    kana: str = Field(..., min_length=1, max_length=200)
    chinese: str = Field(..., min_length=1, max_length=200)
    example_ja: str = Field(..., min_length=0, max_length=500)
    example_cn: str = Field(..., min_length=0, max_length=500)
    image_base64: str | None = None  # AI 生成配图（base64 PNG）
    jlpt_level: str | None = None    # JLPT 等级 N1-N5


class WordItem(WordFields):
    """AI 生成的单个单词（未入库）"""

    model_config = {"exclude_none": False}


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=100, pattern=r"^\S.*")
    difficulty: str | None = Field(default=None, pattern=r"^N[1-5]$")
    extra: str | None = Field(default=None, max_length=200)
    count: int = Field(default=10, ge=5, le=50)
    exclude_words: list[str] | None = None
    stream: bool = False


class GenerateResponse(BaseModel):
    topic: str
    words: list[WordItem]


class WordOut(WordFields):
    """数据库中的单词"""

    id: int
    topic: str
    created_at: datetime

    class Config:
        from_attributes = True


class WordListResponse(BaseModel):
    words: list[WordOut]
    total: int


class SaveWordsRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=100)
    words: list[WordItem] = Field(..., min_length=1, max_length=50)
    jlpt_level: str | None = Field(default=None, pattern=r"^N[1-5]$")


class EssayRequest(BaseModel):
    topics: list[str] = Field(..., min_length=1, max_length=20)
    words: list[str] | None = None
    word_count: int = Field(default=300, ge=100, le=1500)
    jlpt_level: str = Field(default="N3", pattern=r"^N[1-5]$")
    genre: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=100)
    stream: bool = False


class EssayResponse(BaseModel):
    title: str
    essay: str
    words_used: list[str]
    chinese_translation: str


class EssaySaveRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    chinese_translation: str = Field(..., max_length=5000)
    topics: list[str] = Field(..., min_length=1, max_length=50)
    words_used: list[str] = Field(..., max_length=200)
    word_count: int = Field(default=300, ge=10, le=2000)
    jlpt_level: str = Field(default="N3", pattern=r"^N[1-5]$")


class EssayOut(BaseModel):
    id: int
    title: str
    content: str
    chinese_translation: str
    topics: list[str]
    words_used: list[str]
    word_count: int
    jlpt_level: str
    created_at: datetime

    class Config:
        from_attributes = True


class EssayListResponse(BaseModel):
    essays: list[EssayOut]
    total: int


# ── Cloze ──
class ClozeBlank(BaseModel):
    id: int = Field(..., ge=0)
    answer: str = Field(..., min_length=1, max_length=100)
    kana: str = Field(..., min_length=1, max_length=200)
    hint: str = Field(default="", max_length=200)


class ClozeGenerateRequest(BaseModel):
    topics: list[str] = Field(..., min_length=1, max_length=20)
    words: list[str] | None = None
    length: int = Field(default=400, ge=100, le=1000)
    jlpt_level: str = Field(default="N3", pattern=r"^N[1-5]$")
    stream: bool = False


class ClozeGenerateResponse(BaseModel):
    title: str
    passage: str
    blanks: list[ClozeBlank]
    chinese_translation: str


class ClozeSaveRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    passage: str = Field(..., min_length=1, max_length=5000)
    blanks: list[ClozeBlank] = Field(..., min_length=1, max_length=50)
    chinese_translation: str = Field(..., max_length=5000)
    topics: list[str] = Field(..., min_length=1, max_length=50)
    length: int = Field(default=400, ge=100, le=1000)
    jlpt_level: str = Field(default="N3", pattern=r"^N[1-5]$")


class ClozeOut(BaseModel):
    id: int
    title: str
    passage: str
    blanks: list[ClozeBlank]
    chinese_translation: str
    topics: list[str]
    length: int
    jlpt_level: str
    created_at: datetime

    class Config:
        from_attributes = True


class ClozeListResponse(BaseModel):
    clozes: list[ClozeOut]
    total: int


# ── Image Cards ──
class ImageCardOut(BaseModel):
    """图片词卡（已有配图的单词）"""
    id: int
    japanese: str
    kana: str
    chinese: str
    example_ja: str
    example_cn: str
    image_base64: str
    topic: str


class ImageCardTopic(BaseModel):
    """按词单分组的图片词卡"""
    topic: str
    count: int
    words: list[ImageCardOut]


class ImageCardListResponse(BaseModel):
    """图片词卡列表响应"""
    topics: list[ImageCardTopic]
    total_images: int


# ── Grammar ──
class GrammarAnalyzeRequest(BaseModel):
    sentence: str = Field(..., min_length=1, max_length=500)
    stream: bool = False


class GrammarPoint(BaseModel):
    grammar: str
    meaning: str
    level: str
    explanation: str
    example: str = ""
    example_cn: str = ""


class GrammarAnalyzeResponse(BaseModel):
    sentence: str
    points: list[GrammarPoint]


class GrammarCorrectRequest(BaseModel):
    sentence: str = Field(..., min_length=1, max_length=500)
    stream: bool = False


class GrammarError(BaseModel):
    type: str
    fragment: str
    description: str
    suggestion: str


class GrammarCorrectResponse(BaseModel):
    original: str
    corrected: str
    errors: list[GrammarError]


class GrammarCompareRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    stream: bool = False


class GrammarCompareRow(BaseModel):
    grammar: str
    pattern: str
    meaning: str
    example: str
    example_cn: str


class GrammarCompareResponse(BaseModel):
    topic: str
    summary: str
    rows: list[GrammarCompareRow]


class GrammarCompareSaveRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    result: str = Field(..., min_length=1, max_length=10000)  # JSON string


# ── Achievement ──
class AchievementOut(BaseModel):
    key: str
    category: str
    name: str
    description: str
    icon: str
    achieved: bool
    achieved_at: datetime | None = None

    class Config:
        from_attributes = True


class AchievementListResponse(BaseModel):
    achievements: list[AchievementOut]
    categories: dict[str, str] = {}


class GrammarCompareOut(BaseModel):
    id: int
    topic: str
    result: str  # JSON string
    created_at: datetime

    class Config:
        from_attributes = True


class GrammarCompareListResponse(BaseModel):
    items: list[GrammarCompareOut]
    total: int
