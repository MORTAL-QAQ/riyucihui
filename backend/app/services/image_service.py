"""火山引擎图片生成服务。

调用豆包 Seedream 模型为日语单词生成配图。
流程：构造 prompt → 调用 API 生成图片（返回临时 URL）→ 下载图片 → 转为 base64 返回。
"""

import base64
import time

import httpx

from .. import config


def generate_word_image(japanese: str, chinese: str, kana: str = "") -> str | None:
    """为单词生成 AI 配图，返回 base64 编码的 PNG 图片字符串。

    Args:
        japanese: 日语单词（如「食べ物」）
        chinese: 中文释义（如「食物」）
        kana: 假名读音（可选）

    Returns:
        base64 编码的图片字符串（含 data:image/png;base64, 前缀），失败返回 None
    """
    if not config.VOLCANO_API_KEY:
        raise RuntimeError("未配置火山引擎 API Key（VOLCANO_API_KEY）")

    # 构造图片生成 prompt
    prompt = (
        f"日语单词「{japanese}」的配图，中文意思：{chinese}。"
        f"简洁可爱的插画风格，画面干净明亮，适合日语学习卡片使用。"
        f"不要出现任何文字。"
    )

    # 1. 调用火山引擎 API 生成图片
    try:
        resp = httpx.post(
            f"{config.VOLCANO_IMAGE_BASE_URL}/images/generations",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.VOLCANO_API_KEY}",
            },
            json={
                "model": config.VOLCANO_IMAGE_MODEL,
                "prompt": prompt,
                "sequential_image_generation": "disabled",
                "response_format": "url",
                "size": "2K",
                "stream": False,
                "watermark": True,
            },
            timeout=120,  # 图片生成可能需要较长时间
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"火山引擎 API 请求失败: {e}")

    # 2. 提取图片 URL
    image_url = None
    if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
        image_url = data["data"][0].get("url")
    if not image_url:
        raise RuntimeError(f"火山引擎 API 未返回图片 URL: {data}")

    # 3. 下载图片（含重试）
    image_bytes = None
    for attempt in range(3):
        try:
            img_resp = httpx.get(image_url, timeout=30)
            img_resp.raise_for_status()
            image_bytes = img_resp.content
            break
        except httpx.HTTPError:
            if attempt < 2:
                time.sleep(1)
            else:
                raise RuntimeError("下载生成的图片失败，已重试3次")

    if not image_bytes:
        raise RuntimeError("下载图片内容为空")

    # 4. 转为 base64（含 data URI 前缀）
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"
