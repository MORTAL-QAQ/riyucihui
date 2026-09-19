"""火山引擎图片生成服务（双通道）。

- ark 通道：方舟大模型平台，`Bearer <API Key>` + `/images/generations`（豆包 Seedream）
- visual 通道：视觉智能开放平台，AK/SK v4 签名 + `CVProcess`（智能绘图 T2I）

流程：构造 prompt → 调用 API 生成图片（返回临时 URL）→ 下载图片 → 转为 base64 返回。
通道由配置 IMAGE_PROVIDER 决定（默认 ark）。
"""

import base64
import gc
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone

import httpx

from .. import config

# 复用 httpx 客户端，避免每次请求创建新连接池
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=120,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _client


def _build_prompt(japanese: str, chinese: str, kana: str, example_ja: str, example_cn: str) -> str:
    """构造图片生成 prompt：用例句场景 + 强调单词主体。"""
    example_context = ""
    if example_ja:
        example_context = (
            f" The scene should be inspired by this example sentence: \"{example_ja}\""
            f"{' (' + example_cn + ')' if example_cn else ''}."
        )
    return (
        f"A high-quality realistic photograph that clearly illustrates the Japanese word \"{japanese}\" "
        f"(meaning: {chinese}{', reading: ' + kana if kana else ''}). "
        f"The word \"{japanese}\" must be the most prominent and clearly visible subject in the image."
        f"{example_context}"
        f"Professional photography style with natural lighting, sharp focus on \"{japanese}\", "
        f"and a clean uncluttered composition with shallow depth of field. "
        f"Photorealistic, detailed textures, vibrant but natural colors, no distracting elements. "
        f"Absolutely NO text, letters, characters, or watermarks in the image."
    )


def _download_as_data_uri(image_url: str) -> str:
    """下载图片并转为 data URI（base64）。"""
    client = _get_client()
    image_bytes = None
    for attempt in range(3):
        try:
            img_resp = client.get(image_url, timeout=30)
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

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    result = f"data:image/png;base64,{b64}"
    del image_bytes, b64
    gc.collect()
    return result


def generate_word_image(japanese: str, chinese: str, kana: str = "", example_ja: str = "", example_cn: str = "") -> str | None:
    """为单词生成 AI 配图，返回 base64 编码的 PNG 图片字符串。

    Args:
        japanese: 日语单词（如「食べ物」）
        chinese: 中文释义（如「食物」）
        kana: 假名读音（可选）
        example_ja / example_cn: 例句（可选，用于构造场景）

    Returns:
        base64 编码的图片字符串（含 data:image/png;base64, 前缀），失败返回 None
    """
    prompt = _build_prompt(japanese, chinese, kana, example_ja, example_cn)

    if (config.IMAGE_PROVIDER or "ark").lower() == "visual":
        return _generate_via_visual(prompt)
    return _generate_via_ark(prompt)


def _generate_via_ark(prompt: str) -> str:
    """方舟通道：Bearer + /images/generations。"""
    if not config.VOLCANO_API_KEY:
        raise RuntimeError("未配置火山引擎 API Key（VOLCANO_API_KEY）")

    client = _get_client()
    try:
        resp = client.post(
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
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"火山方舟 API 请求失败: {e}")

    image_url = None
    if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
        image_url = data["data"][0].get("url")
    if not image_url:
        raise RuntimeError(f"火山方舟 API 未返回图片 URL: {data}")

    del data
    return _download_as_data_uri(image_url)


def _generate_via_visual(prompt: str) -> str:
    """视觉智能开放平台通道：AK/SK v4 签名 + CVProcess（智能绘图 T2I）。

    手写签名而非依赖 volcengine SDK：容器以非 root 运行，避免新增依赖与构建风险。
    """
    if not config.VOLCANO_ACCESS_KEY or not config.VOLCANO_SECRET_KEY:
        raise RuntimeError(
            "未配置视觉智能平台凭证（VOLCANO_ACCESS_KEY / VOLCANO_SECRET_KEY，"
            "需为火山引擎访问密钥 AK/SK，AK 形如 AKLT…）"
        )

    host = config.VISUAL_API_ENDPOINT.replace("https://", "").replace("http://", "").rstrip("/")
    body = {
        "req_key": config.VISUAL_REQ_KEY,
        "prompt": prompt,
        "width": 1024,
        "height": 1024,
        "return_url": True,
    }
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    query = "Action=CVProcess&Version=2022-08-31"

    resp = httpx.post(
        f"https://{host}/?{query}",
        content=payload,
        headers=_visual_signed_headers(host, query, payload),
        timeout=120,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"视觉智能平台 HTTP {resp.status_code}: {resp.text[:300]}")

    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"视觉智能平台返回非 JSON: {resp.text[:300]}")

    code = data.get("code")
    if code is not None and code != 10000:
        raise RuntimeError(f"视觉智能平台返回错误 code={code}: {data.get('message')}")

    inner = data.get("data") or {}

    # 优先使用返回的图片 URL
    urls = inner.get("image_urls") or []
    if urls:
        return _download_as_data_uri(urls[0])

    # 回退：直接返回 base64（binary_data_base64）
    b64_list = inner.get("binary_data_base64") or []
    if b64_list:
        return f"data:image/png;base64,{b64_list[0]}"

    raise RuntimeError(f"视觉智能平台未返回图片数据: {str(data)[:300]}")


def _visual_signed_headers(host: str, query: str, payload: bytes) -> dict:
    """按火山引擎签名算法 v4 生成视觉智能平台请求头。"""
    region = config.VISUAL_API_REGION
    service = "cv"
    algorithm = "HMAC-SHA256"

    now = datetime.now(timezone.utc)
    x_date = now.strftime("%Y%m%dT%H%M%SZ")
    short_date = x_date[:8]

    payload_hash = hashlib.sha256(payload).hexdigest()
    content_type = "application/json"

    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{host}\n"
        f"x-content-sha256:{payload_hash}\n"
        f"x-date:{x_date}\n"
    )
    canonical_request = "\n".join([
        "POST",
        "/",
        query,
        canonical_headers,
        signed_headers,
        payload_hash,
    ])

    credential_scope = f"{short_date}/{region}/{service}/request"
    string_to_sign = "\n".join([
        algorithm,
        x_date,
        credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])

    def _hmac(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = _hmac(config.VOLCANO_SECRET_KEY.encode("utf-8"), short_date)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, service)
    k_signing = _hmac(k_service, "request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization = (
        f"{algorithm} Credential={config.VOLCANO_ACCESS_KEY}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    return {
        "Content-Type": content_type,
        "Host": host,
        "X-Date": x_date,
        "X-Content-Sha256": payload_hash,
        "Authorization": authorization,
    }
