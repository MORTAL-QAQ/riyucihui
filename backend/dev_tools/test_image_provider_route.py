"""校验图片生成通道分发与提示词约束（不发起真实网络请求）。

运行：cd backend && python dev_tools/test_image_provider_route.py

重点断言「提示词中不出现日文字符」与「含禁止生成文字的约束」——这两条是
「图上文字占比过大 / 有时主体丢失」问题的修复依据，回归时不能被改回去。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

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

JP = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")   # 平假名 + 片假名


def check_prompt(label, prompt, must_have, must_lack):
    for token in must_have:
        if token not in prompt:
            failures.append(f"{label} 提示词缺少「{token}」")
    for token in must_lack:
        if token in prompt:
            failures.append(f"{label} 提示词不应出现「{token}」")
    hit = JP.search(prompt)
    if hit:
        failures.append(f"{label} 提示词含日文字符「{hit.group()}」（会诱发模型把字画进图里）")


# ── 1. ark 通道（英文提示词）──
config.IMAGE_PROVIDER = "ark"
calls.clear()
res = image_service.generate_word_image("食べ物", "食物", "たべもの", "食べ物が好きです。", "喜欢好吃的东西。")
if calls[0][0] != "ark" or not res.startswith("data:image/png;base64,ARK"):
    failures.append(f"ark 通道分发错误: {calls}")
ark_prompt = calls[0][1]
check_prompt("ark", ark_prompt,
             must_have=["食物", "喜欢好吃的东西。", "NO text"],
             must_lack=["食べ物", "たべもの", "食べ物が好きです。"])

# 无中文例句时不得回退到日文例句（否则又会把日文塞进提示词）
calls.clear()
image_service.generate_word_image("笑顔", "笑容", "えがお", "笑顔が素敵です。", "")
if JP.search(calls[0][1]):
    failures.append("ark 在缺中文例句时回退用了日文例句")

# ── 2. visual 通道（中文提示词）──
config.IMAGE_PROVIDER = "visual"
calls.clear()
res = image_service.generate_word_image("林檎", "苹果", "りんご", "林檎を食べます。", "吃苹果。")
if calls[0][0] != "visual" or not res.startswith("data:image/png;base64,VISUAL"):
    failures.append(f"visual 通道分发错误: {calls}")
vis_prompt = calls[0][1]
check_prompt("visual", vis_prompt,
             must_have=["苹果", "吃苹果。", "不要出现任何文字"],
             must_lack=["林檎", "りんご"])

# ── 3. 缺凭证时视觉通道报错清晰 ──
config.VOLCANO_ACCESS_KEY = ""
config.VOLCANO_SECRET_KEY = ""
try:
    _real_generate_via_visual("test prompt")
    failures.append("视觉通道缺少凭证时未报错")
except RuntimeError as exc:
    if "VOLCANO_ACCESS_KEY" not in str(exc):
        failures.append(f"视觉通道报错信息不明确: {exc}")

if failures:
    print("FAIL")
    for f in failures:
        print(" -", f)
    sys.exit(1)

print("PASS: 通道路由正常；提示词不含日文字符、含禁文字约束（ark 英文 / visual 中文）")
