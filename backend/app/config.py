"""应用配置模块。

所有配置项从环境变量读取，支持 .env 文件。敏感信息（如 API Key）通过 secrets 服务解析，
支持 Docker secrets、环境变量等多种来源。
"""

import os

from dotenv import load_dotenv

# 生产容器（Docker secrets 挂载于 /run/secrets）不加载 .env，避免开发配置
# （如 DATABASE_URL=sqlite）经环境变量覆盖 secrets 注入的生产值。
# 仅本地开发（无 /run/secrets）时加载 .env。
if not os.path.isdir("/run/secrets"):
    load_dotenv()

from .services.secrets import resolve as _resolve_secret  # noqa: E402

# ── AI 服务配置 ──
# DeepSeek API：用于日语单词生成、短文撰写、语法分析和完型填空
DEEPSEEK_API_KEY = _resolve_secret("DEEPSEEK_API_KEY")      # API 密钥（必填）
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ── 火山引擎图片生成配置 ──
# 用于为词库单词生成 AI 配图（豆包 Seedream 模型）
VOLCANO_API_KEY = _resolve_secret("VOLCANO_API_KEY")
VOLCANO_IMAGE_MODEL = os.getenv("VOLCANO_IMAGE_MODEL", "doubao-seedream-5-0-260128")
VOLCANO_IMAGE_BASE_URL = os.getenv("VOLCANO_IMAGE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

# ── 图片生成通道（两套产品线，可通过 IMAGE_PROVIDER 切换） ──
#   ark    ：方舟大模型平台（Bearer + /images/generations，当前生产使用）
#   visual ：视觉智能开放平台（AK/SK v4 签名 + CVProcess 智能绘图）
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "ark")
# 视觉智能开放平台凭证（AK 形如 AKLT...，需在火山引擎控制台「访问密钥」获取）
VOLCANO_ACCESS_KEY = _resolve_secret("VOLCANO_ACCESS_KEY")
VOLCANO_SECRET_KEY = _resolve_secret("VOLCANO_SECRET_KEY")
# 智能绘图（文生图）模型标识：通用3.0-文生图 = high_aes_general_v30l_zt2i
# （实测：该 req_key 走 Action=CVProcess&Version=2022-08-31 可正常出图；
#   high_aes_general_v20 / v21 / v14 是平台认可但本账号未开通的旧模型）
VISUAL_REQ_KEY = os.getenv("VISUAL_REQ_KEY", "high_aes_general_v30l_zt2i")
VISUAL_API_ENDPOINT = os.getenv("VISUAL_API_ENDPOINT", "https://visual.volcengineapi.com")
VISUAL_API_REGION = os.getenv("VISUAL_API_REGION", "cn-north-1")
# 出图尺寸（实测 768/1024/1328 均支持）与文本引导强度
VISUAL_IMAGE_SIZE = int(os.getenv("VISUAL_IMAGE_SIZE", "1024"))
VISUAL_SCALE = float(os.getenv("VISUAL_SCALE", "2.5"))

# ── 数据库配置 ──
# SQLite 适用于单用户/轻量使用；生产环境可通过 DATABASE_URL 切换为 PostgreSQL。
# 生产容器中由 Docker secrets 注入（/run/secrets/DATABASE_URL），不落入 environment。
DATABASE_URL = _resolve_secret("DATABASE_URL") or "sqlite:///./data/words.db"

# ── 实验词单可见性 ──
# true （默认）：主题以「实验:」开头的实验词单向**全体被试开放**。
#   被试内设计（同一人同时学图文音词与纯文字词）下必需——否则未分组的学生看不到材料。
# false：恢复原先的「仅实验组（experiment_group=experiment）+ 管理员可见」的组间隔离。
EXPERIMENT_TOPIC_OPEN = os.getenv("EXPERIMENT_TOPIC_OPEN", "true").strip().lower() not in ("0", "false", "no")

# ── VOICEVOX 语音合成配置 ──
# VOICEVOX 是本地运行的日语 TTS 引擎，默认监听 localhost:50021
VOICEVOX_BASE_URL = os.getenv("VOICEVOX_BASE_URL", "http://localhost:50021")
VOICEVOX_SPEAKER = int(os.getenv("VOICEVOX_SPEAKER", "1"))  # 默认音色编号
# 自动检测 VOICEVOX 引擎可执行文件路径（项目根目录下的 linux-cpu-arm64/run）
_DEFAULT_ENGINE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "linux-cpu-arm64", "run",
)
VOICEVOX_ENGINE = os.getenv("VOICEVOX_ENGINE", _DEFAULT_ENGINE)

# ── CORS 跨域配置 ──
# 开发环境允许所有来源；生产环境应设置为具体域名
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# ── JWT 认证配置 ──
# SECRET_KEY 用于签发和验证 JWT Token，经 secrets 服务解析
# （优先级：环境变量 → Docker secrets → 系统凭据管理器 → .env）。
# 未配置时启动直接报错，避免多 worker/多实例下各进程随机密钥导致 Token 随机失效。
_SECRET_KEY = _resolve_secret("SECRET_KEY")
if not _SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY 未配置：请通过环境变量、Docker secrets 或 .env 设置 SECRET_KEY。"
        "生成方法: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )
SECRET_KEY = _SECRET_KEY

ALGORITHM = "HS256"                                              # JWT 签名算法
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # Token 有效期（默认24小时）

# ── 默认每日限额（#45：集中管理，auth 注册与 usage_service 共用，可通过环境变量覆盖） ──
DEFAULT_DAILY_AI_LIMIT = int(os.getenv("DEFAULT_DAILY_AI_LIMIT", "25"))
DEFAULT_DAILY_IMAGE_LIMIT = int(os.getenv("DEFAULT_DAILY_IMAGE_LIMIT", "3"))
DEFAULT_DAILY_WORD_LIMIT = int(os.getenv("DEFAULT_DAILY_WORD_LIMIT", "100"))
DEFAULT_DAILY_VOICE_LIMIT = int(os.getenv("DEFAULT_DAILY_VOICE_LIMIT", "50"))
