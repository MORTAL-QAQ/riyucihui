"""对比「旧提示词」与「新提示词」的出图效果，产物存到 docs/ 下供人工查看（不含任何密钥）。

用法（AK/SK 从环境变量读取，或从生产服务器 secrets 读取）：
    AK=... SK=... python dev_tools/gen_prompt_samples.py
    python dev_tools/gen_prompt_samples.py --from-server   # 通过 ssh 读取服务器 secrets

产出：docs/提示词对比/<序号>_<单词>_旧.jpg / _新.jpg / _新2.jpg
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

HOST, REGION, SERVICE = "visual.volcengineapi.com", "cn-north-1", "cv"
QUERY = "Action=CVProcess&Version=2022-08-31"
REQ_KEY = "high_aes_general_v30l_zt2i"
OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "提示词对比"

# 被测单词：(日语, 假名, 中文, 例句日, 例句中)
WORDS = [
    ("林檎", "りんご", "苹果", "林檎を食べます。", "吃苹果。"),
    ("電車", "でんしゃ", "电车", "電車で学校へ行きます。", "坐电车去学校。"),
    ("図書館", "としょかん", "图书馆", "図書館で勉強します。", "在图书馆学习。"),
    ("笑顔", "えがお", "笑容", "", ""),          # 无例句的边界情况
    ("花見", "はなみ", "赏樱花", "春は花見をします。", "春天去赏樱花。"),
]


def old_prompt(japanese, chinese, kana, example_ja, example_cn):
    """改造前的旧提示词（复现问题用）。"""
    ctx = ""
    if example_ja:
        ctx = f' The scene should be inspired by this example sentence: "{example_ja}"'
        if example_cn:
            ctx += f" ({example_cn})"
        ctx += "."
    return (
        f'A high-quality realistic photograph that clearly illustrates the Japanese word "{japanese}" '
        f"(meaning: {chinese}{', reading: ' + kana if kana else ''}). "
        f'The word "{japanese}" must be the most prominent and clearly visible subject in the image.'
        f"{ctx}"
        f'Professional photography style with natural lighting, sharp focus on "{japanese}", '
        f"and a clean uncluttered composition with shallow depth of field. "
        f"Photorealistic, detailed textures, vibrant but natural colors, no distracting elements. "
        f"Absolutely NO text, letters, characters, or watermarks in the image."
    )


def new_prompt(chinese, example_ja, example_cn):
    """新提示词（与 image_service._build_prompt_visual 保持一致）。"""
    src = (example_cn or example_ja or "").strip()
    scene = f"场景参考：{src}" if src else "场景为日常生活中真实可见的环境。"
    return (
        f"一张真实摄影风格的高清照片，画面主体是「{chinese}」，"
        f"物体位于画面中央、占据主要面积、清晰锐利、细节真实。"
        f"{scene}"
        "自然光线，真实质感，浅景深，背景干净简洁。"
        "画面中不要出现任何文字：不要汉字、不要日文假名、不要英文字母、不要数字，"
        "不要字幕、不要标题、不要标志、不要水印。"
        "不要海报、不要书籍封面、不要卡片、不要排版设计，"
        "只呈现真实的物体与场景，不要任何文字装饰。"
    )


def resolve_credentials(from_server: bool) -> tuple:
    if from_server:
        ak = subprocess.run(
            ["ssh", "root@101.37.204.74", "cat /opt/riyucihui/secrets/VOLCANO_ACCESS_KEY"],
            capture_output=True, text=True, check=True).stdout.strip()
        sk = subprocess.run(
            ["ssh", "root@101.37.204.74", "cat /opt/riyucihui/secrets/VOLCANO_SECRET_KEY"],
            capture_output=True, text=True, check=True).stdout.strip()
        return ak, sk
    return os.getenv("AK", ""), os.getenv("SK", "")


def signed_headers(ak, sk, payload):
    now = datetime.now(timezone.utc)
    x_date = now.strftime("%Y%m%dT%H%M%SZ")
    ph = hashlib.sha256(payload).hexdigest()
    ch = f"content-type:application/json\nhost:{HOST}\nx-content-sha256:{ph}\nx-date:{x_date}\n"
    signed = "content-type;host;x-content-sha256;x-date"
    cr = "\n".join(["POST", "/", QUERY, ch, signed, ph])
    scope = f"{x_date[:8]}/{REGION}/{SERVICE}/request"
    sts = "\n".join(["HMAC-SHA256", x_date, scope, hashlib.sha256(cr.encode()).hexdigest()])

    def _h(k, m):
        return hmac.new(k, m.encode(), hashlib.sha256).digest()

    k = _h(sk.encode(), x_date[:8])
    for part in (REGION, SERVICE, "request"):
        k = _h(k, part)
    sig = hmac.new(k, sts.encode(), hashlib.sha256).hexdigest()
    return {"Content-Type": "application/json", "Host": HOST, "X-Date": x_date,
            "X-Content-Sha256": ph,
            "Authorization": f"HMAC-SHA256 Credential={ak}/{scope}, SignedHeaders={signed}, Signature={sig}"}


def generate(ak, sk, prompt, size=1024) -> bytes:
    body = {"req_key": REQ_KEY, "prompt": prompt, "seed": -1, "scale": 2.5,
            "width": size, "height": size, "return_url": True}
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    r = httpx.post(f"https://{HOST}/?{QUERY}", content=payload,
                   headers=signed_headers(ak, sk, payload), timeout=180)
    r.raise_for_status()
    d = r.json()
    if d.get("code") != 10000:
        raise RuntimeError(f"code={d.get('code')} msg={d.get('message')}")
    inner = d.get("data") or {}
    urls = inner.get("image_urls") or []
    if urls:
        return httpx.get(urls[0], timeout=60).content
    b64 = (inner.get("binary_data_base64") or [""])[0]
    return base64.b64decode(b64)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-server", action="store_true", help="从生产服务器 secrets 读 AK/SK")
    args = ap.parse_args()

    ak, sk = resolve_credentials(args.from_server)
    if not ak or not sk:
        print("缺少 AK/SK（用环境变量 AK/SK 或 --from-server）")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"输出目录：{OUT_DIR}")

    for i, (jp, kana, cn, ex_ja, ex_cn) in enumerate(WORDS, 1):
        jobs = [
            ("旧", old_prompt(jp, cn, kana, ex_ja, ex_cn)),
            ("新", new_prompt(cn, ex_ja, ex_cn)),
            ("新2", new_prompt(cn, ex_ja, ex_cn)),   # 同提示词再出一张，看稳定性
        ]
        for tag, prompt in jobs:
            try:
                data = generate(ak, sk, prompt)
                path = OUT_DIR / f"{i}_{cn}_{tag}.jpg"
                path.write_bytes(data)
                print(f"  [{i}] {cn} {tag}: {len(data)} bytes -> {path.name}")
            except Exception as exc:
                print(f"  [{i}] {cn} {tag}: 失败 {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
