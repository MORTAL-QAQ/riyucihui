"""检查方舟 API Key 对 Seedream 配图模型是否有权限（不打印密钥明文）。

用法：
    python dev_tools/check_ark_key.py                  # 读仓库根目录 ApiKey.txt，测默认模型
    python dev_tools/check_ark_key.py <key>            # 直接给 key
    python dev_tools/check_ark_key.py --file <path>    # 指定密钥文件
    python dev_tools/check_ark_key.py --map            # 列出在售 Seedream 模型并逐个实测权限
    ARK_KEY=<key> python dev_tools/check_ark_key.py    # 走环境变量

支持两种密钥文件格式：
    1. 单行：直接是 API Key（形如 ark-xxxx / 一长串）
    2. 两行：``API Key ID: ...`` / ``API Key Secret: ...``（控制台导出格式）

退出码：0=有权限可出图，2=无权限(403)，3=模型未开通(404)，1=其他错误
"""
import os
import sys
from pathlib import Path

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
        if ":" in line and "secret" in line.lower():
            return line.split(":", 1)[1].strip()
    for line in text.splitlines():
        line = line.strip()
        if line and ":" not in line:
            return line
    return ""


def resolve_key(args: list) -> str:
    """从命令行参数 / 环境变量 / 默认文件中取出真正用于 Bearer 的 key。"""
    if args and args[0] == "--file":
        return extract_key(Path(args[1]).read_text(encoding="utf-8"))
    if args and not args[0].startswith("--"):
        return args[0].strip()
    if os.getenv("ARK_KEY"):
        return os.environ["ARK_KEY"].strip()
    default = Path(__file__).resolve().parents[2] / "ApiKey.txt"
    if not default.exists():
        print(f"[ERR] 未找到密钥文件：{default}")
        return ""
    return extract_key(default.read_text(encoding="utf-8"))


def call_model(key: str, model: str, size: str = "2048x2048") -> tuple:
    """调用一次出图接口，返回 (状态码, 错误码, 图片URL或空)。"""
    try:
        resp = httpx.post(
            f"{BASE_URL}/images/generations",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "prompt": "a red apple on a wooden table, natural light",
                "response_format": "url",
                "size": size,
                "watermark": False,
            },
            timeout=180,
        )
    except httpx.HTTPError as exc:
        return 0, str(exc), ""
    if resp.status_code == 200:
        url = ((resp.json().get("data") or [{}])[0]).get("url", "")
        return 200, "", url
    try:
        err = resp.json().get("error", {})
        return resp.status_code, err.get("code", ""), ""
    except ValueError:
        return resp.status_code, resp.text[:80], ""


def list_image_models(key: str) -> list:
    """列出账号可见的图像生成模型（含 status，Shutdown 表示已下线）。"""
    try:
        resp = httpx.get(f"{BASE_URL}/models", headers={"Authorization": f"Bearer {key}"}, timeout=60)
        resp.raise_for_status()
        return [
            m for m in resp.json().get("data", [])
            if m.get("domain") == "ImageGeneration" and "seedream" in m.get("id", "")
        ]
    except Exception as exc:
        print(f"[ERR] 获取模型列表失败：{exc}")
        return []


def run_map(key: str) -> int:
    """逐模型实测权限，输出地图——用来定位「该给 key 授权哪个模型」。"""
    models = list_image_models(key)
    if not models:
        return 1

    print(f"账号可见的 Seedream 模型（共 {len(models)} 个）\n")
    usable = []
    for m in models:
        mid, status = m["id"], m.get("status", "")
        if status == "Shutdown":
            print(f"  [已下线] {mid}   ← 平台已停用，任何 key 都调不通")
            continue
        code, errcode, url = call_model(key, mid)
        if code == 200:
            print(f"  [可出图] {mid}")
            usable.append(mid)
        elif code == 403:
            print(f"  [缺授权] {mid}  ← 账号已开通，但该 key 无权限（去控制台给 key 加模型权限）")
        elif code == 404 and errcode == "ModelNotOpen":
            print(f"  [未开通] {mid}  ← 账号还没开通这个模型（先去开通管理）")
        else:
            print(f"  [{code} {errcode}] {mid}")

    print()
    if usable:
        print("可用模型：" + "、".join(usable))
        print(f"→ 生产切换：把 IMAGE_PROVIDER 保持 ark，VOLCANO_IMAGE_MODEL 设为 {usable[0]}")
        return 0
    print("该 key 目前没有任何可出图的 Seedream 模型。")
    print("→ 请在方舟控制台：① 开通管理里开通目标模型；② API Key 管理里给该 key 授权该模型")
    return 2


def main() -> int:
    args = sys.argv[1:]
    key = resolve_key(args)

    if not key:
        print("[ERR] 未能从输入中解析出密钥")
        return 1

    masked = f"{key[:8]}…{key[-4:]}" if len(key) > 14 else "***"
    print(f"密钥    : {masked}（长度 {len(key)}）")

    if "--map" in args:
        return run_map(key)

    print(f"模型    : {MODEL}")
    print(f"端点    : {BASE_URL}/images/generations")

    status, errcode, url = call_model(key, MODEL)
    print(f"HTTP    : {status}")

    if status == 200:
        print("[OK] 该 key 有权限，已成功出图")
        print("     图片 URL:", url[:120])
        return 0

    if status == 403:
        print()
        print("[403] 密钥本身有效，但缺少该模型的权限。")
        print("      处理：方舟控制台 → API Key 管理 → 编辑该 key → 模型权限")
        print(f"            勾选「全部模型」或 {MODEL} → 保存")
        print("      排查：python dev_tools/check_ark_key.py --map 可看全账号模型的可用情况")
        return 2

    if status == 404 and errcode == "ModelNotOpen":
        print()
        print("[404] 账号尚未开通该模型。")
        print(f"      处理：方舟控制台 → 开通管理 → 开通 {MODEL}")
        return 3

    if status == 404 and errcode == "InvalidEndpointOrModel.NotFound":
        print()
        print("[404] 该模型不存在或已下线（如 Seedream 3.0 已 Shutdown）。")
        print("      处理：改用 --map 列出当前在售模型，换一个可用的模型 ID")
        return 3

    print(f"[ERR] 错误码 {errcode}，见上方响应")
    return 1


if __name__ == "__main__":
    sys.exit(main())
