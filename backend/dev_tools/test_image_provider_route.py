"""校验图片生成通道路由：默认走 ark，IMAGE_PROVIDER=visual 时走视觉平台分支。

不发起真实网络请求，仅替换两条通道的底层函数验证分发逻辑。
运行：cd backend && python dev_tools/test_image_provider_route.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config
from app.services import image_service

calls = []

def fake_ark(prompt):
    calls.append(("ark", prompt))
    return "data:image/png;base64,ARK"

def fake_visual(prompt):
    calls.append(("visual", prompt))
    return "data:image/png;base64,VISUAL"

_real_generate_via_visual = image_service._generate_via_visual
image_service._generate_via_ark = fake_ark
image_service._generate_via_visual = fake_visual

failures = []

# 1. 默认通道应为 ark
config.IMAGE_PROVIDER = "ark"
calls.clear()
res = image_service.generate_word_image("食べ物", "食物", "たべもの", "食べ物が好きです。", "喜欢食物。")
if calls[0][0] != "ark" or not res.startswith("data:image/png;base64,ARK"):
    failures.append(f"默认通道错误: {calls}")

# 2. prompt 应包含单词、释义、假名、例句
prompt = calls[0][1]
for token in ["食べ物", "食物", "たべもの", "食べ物が好きです。"]:
    if token not in prompt:
        failures.append(f"prompt 缺少 {token}")

# 3. IMAGE_PROVIDER=visual 时应走视觉平台分支
config.IMAGE_PROVIDER = "visual"
calls.clear()
res = image_service.generate_word_image("旅行", "旅行")
if calls[0][0] != "visual" or not res.startswith("data:image/png;base64,VISUAL"):
    failures.append(f"visual 通道错误: {calls}")

# 4. 视觉分支缺少凭证时应给出明确报错
config.VOLCANO_ACCESS_KEY = ""
config.VOLCANO_SECRET_KEY = ""
config.IMAGE_PROVIDER = "visual"
real_visual = _real_generate_via_visual
try:
    real_visual("test prompt")
    failures.append("缺少凭证时未报错")
except RuntimeError as exc:
    if "VOLCANO_ACCESS_KEY" not in str(exc):
        failures.append(f"报错信息不明确: {exc}")

if failures:
    print("FAIL")
    for f in failures:
        print(" -", f)
    sys.exit(1)

print("PASS: 图片通道路由正常（ark 默认 / visual 可切换 / 缺凭证报错清晰）")
