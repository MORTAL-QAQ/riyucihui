"""检查方舟 API Key 对 Seedream 配图模型是否有权限（不打印密钥明文）。

用法：
    python dev_tools/check_ark_key.py                  # 读仓库根目录 ApiKey.txt
    python dev_tools/check_ark_key.py <key>            # 直接给 key
    python dev_tools/check_ark_key.py --file <path>    # 指定密钥文件
    ARK_KEY=<key> python dev_tools/check_ark_key.py    # 走环境变量

支持两种密钥文件格式：
    1. 单行：直接是 API Key（形如 ark-xxxx / 一长串）
    2. 两行：``API Key ID: ...`` / ``API Key Secret: ...``（控制台导出格式）

退出码：0=有权限可出图，2=无权限(403)，3=模型未开通(404)，1=其他错误
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:                                          # Windows 控制台默认 GBK，强制 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import httpx

MODEL = os.getenv("ARK_IMAGE_MODEL", "doubao-seedream-5-0-260128")
BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")


def extract_key(text: str) -> str:
    """从密钥文件内容里取出真正用于 Bearer 的 key。"""
    for line in text.splitlines():
        low = line.lower()
        if ":" in line and "secret" in low:
            return line.split(":", 1)[1].strip()
    for line in text.splitlines():
        line = line.strip()
        if line and ":" not in line:
            return line
    return ""


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--file":
        key = extract_key(Path(args[1]).read_text(encoding="utf-8"))
    elif args:
        key = args[0].strip()
    elif os.getenv("ARK_KEY"):
        key = os.environ["ARK_KEY"].strip()
    else:
        default = Path(__file__).resolve().parents[2] / "ApiKey.txt"
        if not default.exists():
            print(f"[ERR] 未找到密钥文件：{default}")
            return 1
        key = extract_key(default.read_text(encoding="utf-8"))

    if not key:
        print("[ERR] 未能从输入中解析出密钥")
        return 1

    masked = f"{key[:8]}…{key[-4:]}" if len(key) > 14 else "***"
    print(f"模型    : {MODEL}")
    print(f"密钥    : {masked}（长度 {len(key)}）")
    print(f"端点    : {BASE_URL}/images/generations")

    try:
        resp = httpx.post(
            f"{BASE_URL}/images/generations",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            json={
                "model": MODEL,
                "prompt": "a red apple on a wooden table, natural light",
                "sequential_image_generation": "disabled",
                "response_format": "url",
                "size": "1K",
                "stream": False,
                "watermark": True,
            },
            timeout=120,
        )
    except httpx.HTTPError as exc:
        print(f"[ERR] 请求失败：{exc}")
        return 1

    print(f"HTTP    : {resp.status_code}")

    if resp.status_code == 200:
        urls = [d.get("url") for d in (resp.json().get("data") or [])]
        print("[OK] 该 key 有权限，已成功出图")
        for u in urls:
            print("     图片 URL:", u[:120])
        return 0

    snippet = resp.text[:300]
    print("响应    :", snippet)
    if resp.status_code == 403:
        print()
        print("[403] 密钥本身有效，但缺少该模型的权限。")
        print("      处理：方舟控制台 → API Key 管理 → 编辑该 key → 模型权限")
        print(f"            勾选「全部模型」或 {MODEL} → 保存")
        return 2
    if resp.status_code == 404 and "ModelNotOpen" in snippet:
        print()
        print("[404] 账号尚未开通该模型。")
        print(f"      处理：方舟控制台 → 开通管理 → 开通 {MODEL}")
        return 3

    print("[ERR] 未知错误，见上方响应")
    return 1


if __name__ == "__main__":
    sys.exit(main())
