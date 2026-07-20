"""应用配置模块。

所有配置项从环境变量读取，支持 .env 文件。敏感信息（如 API Key）通过 secrets 服务解析，
支持 Docker secrets、环境变量等多种来源。
"""

import os
import secrets
import sys

from dotenv import load_dotenv

# 加载 .env 文件中的环境变量（开发环境）
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

# ── 数据库配置 ──
# SQLite 适用于单用户/轻量使用；生产环境可通过 DATABASE_URL 切换为 PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/words.db")

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
# SECRET_KEY 用于签发和验证 JWT Token
# 未设置时自动生成随机密钥（每次重启后之前的 Token 会失效）
_SECRET_KEY = os.getenv("SECRET_KEY")
if _SECRET_KEY and _SECRET_KEY != "change-me-in-production":
    SECRET_KEY = _SECRET_KEY
else:
    SECRET_KEY = secrets.token_urlsafe(32)
    print(
        "\n" + "=" * 64 + "\n"
        "  WARNING: SECRET_KEY is not set.\n"
        "  A random key has been generated for this session.\n"
        "  All previously issued JWT tokens are now invalid.\n"
        "  Set SECRET_KEY in your .env file for persistence:\n"
        "    SECRET_KEY=" + SECRET_KEY + "\n"
        "=" * 64 + "\n",
        file=sys.stderr,
    )

ALGORITHM = "HS256"                                              # JWT 签名算法
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # Token 有效期（默认24小时）
