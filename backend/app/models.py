"""数据库 ORM 模型定义。

定义了所有数据库表对应的 SQLAlchemy 模型类。
每个模型类映射一张数据库表，类属性映射表的列。

表结构：
- User: 用户账号
- UsageRecord: API 调用记录（用于用量限制）
- Word: 日语单词（按主题组织）
- StudyRecord: 学习记录（SM-2 间隔重复算法）
- Essay: AI 生成的日语短文
- Cloze: 完型填空练习
- GrammarCompare: 语法辨析结果
- Achievement: 用户成就
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from sqlalchemy.orm import deferred

from .database import Base


class User(Base):
    """用户表。

    设计说明：
    - token_version 递增可强制所有旧 Token 失效（踢出登录）
    - daily_ai_limit / daily_voice_limit 为 NULL 表示无限制
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(50), nullable=True)              # 显示名（昵称），默认取 username
    password_hash = Column(String(60), nullable=False)
    is_admin = Column(Boolean, default=False)
    token_version = Column(Integer, default=0)            # Token 版本号，递增后旧 Token 全部失效
    daily_ai_limit = Column(Integer, nullable=True)       # NULL=无限, N=每天N次AI调用
    daily_voice_limit = Column(Integer, nullable=True)    # NULL=无限, N=每天N次语音合成
    daily_image_limit = Column(Integer, nullable=True)    # NULL=无限, N=每天N张图片生成（默认普通用户3张）
    daily_word_limit = Column(Integer, nullable=True)     # NULL=无限, N=每天N个单词生成（默认普通用户100个）
    remark = Column(String(200), nullable=True)            # 管理员备注
    experiment_group = Column(String(20), nullable=True)   # 实验分组：experiment（实验组）/ control（对照组），NULL=未分组（大创实验用）
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UsageRecord(Base):
    """API 用量记录表。

    每次 AI 调用或语音合成都会记录一条，用于统计每日用量和执行用量限制。
    """
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind = Column(String(20), nullable=False, index=True)  # 调用类型：generate/essay/cloze/grammar_*/voice
    tokens_used = Column(Integer, default=0)                # 消耗的 Token 数量（流式调用为估算值）
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        # 每日限额统计热路径：WHERE user_id=? AND kind=? AND created_at>=?（#33）
        Index("ix_usage_user_kind_created", "user_id", "kind", "created_at"),
    )


class Word(Base):
    """日语单词表。

    每个单词包含日语写法、假名读音、中文释义和例句。
    按 topic（主题）分组，如「食べ物」「天気」等。
    """
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic = Column(String(100), nullable=False, index=True)    # 词单主题
    japanese = Column(String(100), nullable=False, index=True)  # 日语汉字/写法
    kana = Column(String(200), nullable=False, index=True)      # 假名读音
    chinese = Column(String(200), nullable=False, index=True)   # 中文释义
    example_ja = Column(String(500), nullable=False)            # 日语例句
    example_cn = Column(String(500), nullable=False)            # 例句中文翻译
    # deferred（#31）：大字段（base64 图片）默认不随常规查询加载，
    # 仅在显式 undefer / 延迟加载时才读取，避免列表整行加载巨量数据。
    image_base64 = deferred(Column(String, nullable=True))          # AI 生成的单词配图（base64 PNG）
    jlpt_level = Column(String(3), nullable=True, index=True)   # JLPT 等级 N1-N5
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class StudyRecord(Base):
    """学习记录表（SM-2 间隔重复算法）。

    每个单词对应一条学习记录，记录复习历史和下次复习日期。
    SM-2 算法根据回答质量（0-5）调整 easiness_factor、interval 和 repetition。
    """
    __tablename__ = "study_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    word_id = Column(
        Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    stage = Column(Integer, default=0)             # SM-2 推导的阶段：0-7，7=已掌握
    review_count = Column(Integer, default=0)      # 累计复习次数
    last_review_date = Column(Date, nullable=True) # 上次复习日期
    next_review_date = Column(Date, default=date.today)  # 下次复习日期
    easiness_factor = Column(Float, default=2.5)   # SM-2 简易度因子 EF，范围 [1.3, ∞)
    interval = Column(Integer, default=0)          # SM-2 当前复习间隔（天）
    repetition = Column(Integer, default=0)        # SM-2 连续正确次数

    __table_args__ = (
        # 待复习查询（study/due）：WHERE user_id=? AND next_review_date<=? ORDER BY next_review_date
        Index("ix_study_user_next", "user_id", "next_review_date"),
        # 成就连续学习天数（streak）：WHERE user_id=? AND last_review_date IS NOT NULL ORDER BY last_review_date
        Index("ix_study_user_lastreview", "user_id", "last_review_date"),
    )


class Essay(Base):
    """AI 生成的日语短文表。

    topics 和 words_used 以 JSON 字符串存储（如 '["天気","旅行"]'）。
    """
    __tablename__ = "essays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)                    # 短文标题
    content = Column(String(5000), nullable=False)                 # 日语短文内容（含【】标记的单词）
    chinese_translation = Column(String(5000), nullable=False)     # 中文翻译
    topics = Column(String(500), nullable=False)                   # JSON 数组：词单主题列表
    words_used = Column(String(2000), nullable=False)              # JSON 数组：使用的单词列表
    word_count = Column(Integer, default=300)                      # 文章字数
    jlpt_level = Column(String(3), default="N3")                   # JLPT 难度等级 N1-N5
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Cloze(Base):
    """完型填空练习表。

    passage 中包含 ____ 占位符，blanks 是 JSON 数组（每个元素含 id/answer/kana/hint）。
    """
    __tablename__ = "clozes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)                     # 练习标题
    passage = Column(String(5000), nullable=False)                  # 包含 ____ 占位符的填空短文
    blanks = Column(String(5000), nullable=False)                   # JSON 数组：[{id, answer, kana, hint}, ...]
    chinese_translation = Column(String(5000), nullable=False)      # 中文翻译
    topics = Column(String(500), nullable=False)                    # JSON 数组：词单主题列表
    length = Column(Integer, default=400)                           # 文章字数
    jlpt_level = Column(String(3), default="N3")                    # JLPT 难度等级
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GrammarCompare(Base):
    """语法辨析结果表。

    result 以 JSON 字符串存储，包含 {topic, summary, rows: [{grammar, pattern, meaning, example, example_cn}, ...]}。
    """
    __tablename__ = "grammar_compares"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic = Column(String(200), nullable=False)                     # 语法主题，如「ところ相关的语法」
    result = Column(String(10000), nullable=False)                  # JSON 字符串：{topic, summary, rows}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Achievement(Base):
    """成就表。

    每个用户 + 每个成就 key 只能有一条记录（UniqueConstraint）。
    """
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key = Column(String(50), nullable=False, index=True)            # 成就标识符，如 'words_100'
    achieved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))  # 首次达成时间

    __table_args__ = (UniqueConstraint("user_id", "key"),)          # 每个用户每个成就只记录一次


class LoginHistory(Base):
    """登录历史记录表。

    每次用户成功登录时记录一条，包含客户端 IP 和 User-Agent。
    用于审计和安全分析。
    """
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ip_address = Column(String(45), nullable=True)                   # 客户端 IP（IPv4 最多 15 字符，IPv6 最多 45 字符）
    user_agent = Column(String(500), nullable=True)                  # 客户端 User-Agent
    login_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)  # 登录时间


class Checkin(Base):
    """每日签到记录表。

    每个用户每天最多一条（UNIQUE(user_id, checkin_date)），checkin_date 为北京时区日期。
    签到当天会自动把「每日推荐单词」归入该用户的「签到单词」词单（words.topic）。
    """
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checkin_date = Column(Date, nullable=False)                      # 签到日期（北京时区）
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_checkin_user_date"),
        Index("ix_checkin_user_date", "user_id", "checkin_date"),
    )


class Post(Base):
    """社区帖子表（含管理员公告）。

    type: post（用户分享）/ announcement（管理员公告）
    is_pinned: 公告置顶（列表优先展示）
    """
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type = Column(String(20), nullable=False, default="post", index=True)  # post / announcement
    title = Column(String(100), nullable=False)
    content = Column(String(5000), nullable=False)
    is_pinned = Column(Boolean, default=False)                    # 置顶（公告常用）
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        # 社区列表：按类型 + 时间倒序
        Index("ix_posts_type_created", "type", "created_at"),
    )


class PostComment(Base):
    """帖子评论表。"""
    __tablename__ = "post_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        # 帖子详情：按时间顺序加载评论
        Index("ix_post_comments_post_created", "post_id", "created_at"),
    )


class PostLike(Base):
    """帖子点赞表（每用户每帖最多一次，Unique 约束防重复）。"""
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("post_id", "user_id"),)
