"""AI 服务 — DeepSeek API 调用封装。

本模块是 AI 生成功能的核心，所有与 DeepSeek API 的交互都在这里。

功能模块：
- 单词生成（generate_words / generate_words_stream）
- 短文撰写（generate_essay / generate_essay_stream）
- 完型填空（generate_cloze / generate_cloze_stream）
- 语法分析/纠错/辨析（analyze_grammar / correct_grammar / compare_grammar 及其流式版本）

流式 vs 非流式：
- 非流式函数返回 (result_dict, token_count) 元组，用于普通 JSON 响应
- 流式函数是生成器，yield {"chunk": str} 逐步输出，最后 yield {"done": True, "result": dict}
  流式输出经 SSE（Server-Sent Events）传给前端，实现打字机效果

JSON 解析：
- _parse_response() 用于数组输出（单词列表）
- _parse_dict_response() 用于字典输出（短文、语法、完型填空）
- 两者都有鲁棒的回退逻辑：去掉 markdown 代码块标记，用正则搜索 JSON
"""

import json
import re

from openai import OpenAI

from .. import config

SYSTEM_PROMPT = """你是一位专业的日语教师。根据用户提供的主题，生成{count}个相关的日语实用单词。

要求：
1. 每个单词必须紧密围绕主题
2. 优先选择常用、实用的词汇
3. 例句要自然地道，能体现单词的实际用法
4. 如果用户指定了JLPT难度等级（N5-N1），词汇和例句的难度要严格对应该等级
5. 如果用户提供了补充条件（如词性偏好、场景限制等），必须严格遵守

请严格按照以下JSON数组格式返回，不要包含markdown代码块标记或其他文字：
[
  {
    "japanese": "日本語",
    "kana": "にほんご",
    "chinese": "日语",
    "example_ja": "私は日本語を勉強しています。",
    "example_cn": "我正在学习日语。"
  }
]"""


_ai_client = None

def _build_client() -> OpenAI:
    global _ai_client
    if _ai_client is None:
        _ai_client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
    return _ai_client


def _parse_response(text: str) -> list[dict]:
    """Robust JSON extraction from LLM response."""
    # Strip markdown fences if present
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON array in the text
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从AI响应中提取JSON数组。原始响应: {text[:500]}")


def _build_user_prompt(topic, difficulty, extra, count, exclude_words):
    user_prompt = f"请为主题「{topic}」"
    if difficulty:
        user_prompt += f"，难度等级为{difficulty}"
    if extra:
        user_prompt += f"，补充要求：{extra}"
    user_prompt += f"生成{count}个相关日语单词。"
    if exclude_words:
        user_prompt += f"请确保生成的单词与以下已有单词均不同：{'、'.join(exclude_words)}。"
    return user_prompt


def generate_words(
    topic: str,
    difficulty: str | None = None,
    extra: str | None = None,
    count: int = 10,
    exclude_words: list[str] | None = None,
) -> tuple[list[dict], int]:
    """Call DeepSeek API to generate Japanese words for the given topic.
    Returns (words, total_tokens_used)."""
    client = _build_client()
    system_prompt = SYSTEM_PROMPT.replace("{count}", str(count))
    user_prompt = _build_user_prompt(topic, difficulty, extra, count, exclude_words)

    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=4096,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("DeepSeek API返回了空响应")

    tokens = response.usage.total_tokens if response.usage else 0
    return _parse_response(content), tokens


def generate_words_stream(
    topic: str,
    difficulty: str | None = None,
    extra: str | None = None,
    count: int = 10,
    exclude_words: list[str] | None = None,
):
    """Stream word generation from DeepSeek API. Yields dicts: {"chunk": str} or {"done": True, "result": list, "tokens": int}."""
    client = _build_client()
    system_prompt = SYSTEM_PROMPT.replace("{count}", str(count))
    user_prompt = _build_user_prompt(topic, difficulty, extra, count, exclude_words)

    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=4096,
        stream=True,
    )

    full = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            full += text
            yield {"chunk": text}

    try:
        words = _parse_response(full)
        yield {"done": True, "result": words}
    except ValueError as e:
        yield {"error": str(e)}


ESSAY_SYSTEM_PROMPT = """你是一位专业的日语教师和作家。\
根据用户指定的话题、字数要求和JLPT难度等级，撰写一篇日语短文。

要求：
1. 短文字数接近用户指定的字数
2. 语法和词汇难度严格对应JLPT等级（N5最简单，N1最难）
3. 必须尽可能多地使用用户提供的词汇表中的单词
4. 短文内容自然流畅，主题连贯
5. 如果用户指定了文体（如日记、信件、对话等），严格按照该文体风格撰写
6. 如果用户指定了标题，使用该标题作为短文标题
7. 在短文中使用的词汇表单词，用【】标记出来（例如：彼は【勉強】が好きです）
8. 同时提供完整的中文翻译

请严格按照以下JSON格式返回，不要包含markdown代码块标记或其他文字：
{
  "title": "短文标题",
  "essay": "日语短文内容...",
  "words_used": ["单词1", "单词2"],
  "chinese_translation": "中文翻译..."
}"""


def _parse_dict_response(text: str) -> dict:
    """Robust JSON dict extraction from LLM response."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从AI响应中提取JSON对象。原始响应: {text[:500]}")


def _build_essay_prompt(topics, word_list, word_count, jlpt_level, genre=None, title=None):
    prompt = f"""话题：{"、".join(topics)}
JLPT等级：{jlpt_level}
字数要求：约{word_count}字"""
    if genre:
        prompt += f"\n文体：{genre}"
    if title:
        prompt += f"\n标题：{title}"
    prompt += f"""
可用词汇表：{"、".join(word_list)}

请根据以上要求撰写一篇日语短文。"""
    return prompt


def generate_essay(
    topics: list[str], word_list: list[str], word_count: int, jlpt_level: str,
    genre: str | None = None, title: str | None = None,
) -> tuple[dict, int]:
    """Call DeepSeek API to generate a Japanese essay incorporating given vocabulary.
    Returns (essay_data, total_tokens_used)."""
    client = _build_client()
    user_prompt = _build_essay_prompt(topics, word_list, word_count, jlpt_level, genre, title)

    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": ESSAY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=8192,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("DeepSeek API返回了空响应")

    tokens = response.usage.total_tokens if response.usage else 0
    return _parse_dict_response(content), tokens


def generate_essay_stream(
    topics: list[str], word_list: list[str], word_count: int, jlpt_level: str,
    genre: str | None = None, title: str | None = None,
):
    """Stream essay generation. Yields {"chunk": str} or {"done": True, "result": dict}."""
    client = _build_client()
    user_prompt = _build_essay_prompt(topics, word_list, word_count, jlpt_level, genre, title)

    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": ESSAY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=8192,
        stream=True,
    )

    full = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            full += text
            yield {"chunk": text}

    try:
        result = _parse_dict_response(full)
        yield {"done": True, "result": result}
    except ValueError as e:
        yield {"error": str(e)}


GRAMMAR_ANALYZE_PROMPT = """你是一位专业的日语教师。分析用户提供的日语句子中使用的语法点。

要求：
1. 识别句子中所有的语法点（助词用法、活用形、句型结构等）
2. 每个语法点给出：语法名称、含义、JLPT等级、在句中的用法解释
3. 如果可能，为每个语法点提供一个额外的例句及其中文翻译
4. 按语法点在句中出现的顺序排列

请严格按照以下JSON格式返回，不要包含markdown代码块标记或其他文字：
{
  "sentence": "原句",
  "points": [
    {
      "grammar": "〜てから",
      "meaning": "做完前项再做后项",
      "level": "N4",
      "explanation": "表示动作的先后顺序，前项完成后才进行后项",
      "example": "宿題をしてからゲームをします。",
      "example_cn": "做完作业之后玩游戏。"
    }
  ]
}"""

GRAMMAR_CORRECT_PROMPT = """你是一位专业的日语教师。检查用户提供的日语句子，找出语法错误并给出改正建议。

要求：
1. 仔细检查句子的语法、助词、活用、敬语等
2. 找出所有语法错误（如果有的话）
3. 对每个错误说明类型、错误片段、问题描述和修改建议
4. 给出完整的改正后句子
5. 如果句子完全正确，errors数组为空，corrected与original相同

请严格按照以下JSON格式返回，不要包含markdown代码块标记或其他文字：
{
  "original": "原句",
  "corrected": "改正后的句子",
  "errors": [
    {
      "type": "助词",
      "fragment": "が",
      "description": "此处应使用「は」表示主题",
      "suggestion": "将「が」改为「は」"
    }
  ]
}"""

GRAMMAR_COMPARE_PROMPT = """你是一位专业的日语教师。用户提供一个语法主题，请对比分析相关的语法点。

要求：
1. 找出与该主题相关的2-6个相似或易混淆的语法点
2. 用表格形式对比：语法名称、接续形式、含义、例句、例句中文
3. 提供一段总结，说明这些语法点的核心区别和使用场景
4. 例句要自然地道

请严格按照以下JSON格式返回，不要包含markdown代码块标记或其他文字：
{
  "topic": "用户输入的主题",
  "summary": "这些语法点的核心区别总结...",
  "rows": [
    {
      "grammar": "〜ところだ",
      "pattern": "辞書形＋ところだ",
      "meaning": "正要/刚要做某事",
      "example": "今から出かけるところです。",
      "example_cn": "现在正要出门。"
    }
  ]
}"""


def _grammar_call(system_prompt: str, user_prompt: str) -> tuple[dict, int]:
    """Call DeepSeek API for grammar tasks. Returns (data, tokens)."""
    client = _build_client()
    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        max_tokens=2048,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("DeepSeek API返回了空响应")
    tokens = response.usage.total_tokens if response.usage else 0
    return _parse_dict_response(content), tokens


def _grammar_call_stream(system_prompt: str, user_prompt: str):
    """Stream grammar analysis. Yields {"chunk": str} or {"done": True, "result": dict}."""
    client = _build_client()
    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        max_tokens=2048,
        stream=True,
    )

    full = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            full += text
            yield {"chunk": text}

    try:
        result = _parse_dict_response(full)
        yield {"done": True, "result": result}
    except ValueError as e:
        yield {"error": str(e)}


def analyze_grammar(sentence: str) -> tuple[dict, int]:
    """Analyze grammar points in a Japanese sentence."""
    return _grammar_call(
        GRAMMAR_ANALYZE_PROMPT,
        f"请分析以下日语句子中的语法点：\n{sentence}",
    )


def analyze_grammar_stream(sentence: str):
    """Stream grammar analysis."""
    return _grammar_call_stream(
        GRAMMAR_ANALYZE_PROMPT,
        f"请分析以下日语句子中的语法点：\n{sentence}",
    )


def correct_grammar(sentence: str) -> tuple[dict, int]:
    """Check grammar errors and suggest corrections."""
    return _grammar_call(
        GRAMMAR_CORRECT_PROMPT,
        f"请检查以下日语句子是否有语法错误：\n{sentence}",
    )


def correct_grammar_stream(sentence: str):
    """Stream grammar correction."""
    return _grammar_call_stream(
        GRAMMAR_CORRECT_PROMPT,
        f"请检查以下日语句子是否有语法错误：\n{sentence}",
    )


def compare_grammar(topic: str) -> tuple[dict, int]:
    """Compare and contrast related grammar points."""
    return _grammar_call(
        GRAMMAR_COMPARE_PROMPT,
        f"请对以下日语语法主题进行对比分析：{topic}",
    )


def compare_grammar_stream(topic: str):
    """Stream grammar comparison."""
    return _grammar_call_stream(
        GRAMMAR_COMPARE_PROMPT,
        f"请对以下日语语法主题进行对比分析：{topic}",
    )


# ── Cloze (完型填空) ──

CLOZE_SYSTEM_PROMPT = """你是一位专业的日语教师。根据用户指定的话题、字数要求和JLPT难度等级，\
生成一篇完型填空练习短文。

要求：
1. 短文必须紧密围绕用户提供的话题
2. 短文字数接近用户指定的长度（约{length}字）
3. 语法和词汇难度严格对应JLPT等级（N5最简单，N1最难）
4. 必须尽可能多地使用用户提供的词汇表中的单词作为填空目标
5. 短文内容自然流畅，主题连贯，适合日语学习者阅读
6. 选择{blank_count}个关键词汇作为填空（用____替代原文中的单词，四个下划线）
7. 尽可能均匀地将填空分布在全文中，避免集中在某一段落
8. 每个填空只替换一个单词
9. 同时提供完整的中文翻译

请严格按照以下JSON格式返回，不要包含markdown代码块标记或其他文字：
{
  "title": "短文标题",
  "passage": "今日は____に行きました。____がとても綺麗でした。",
  "blanks": [
    {"id": 0, "answer": "公園", "kana": "こうえん", "hint": "公园"},
    {"id": 1, "answer": "桜", "kana": "さくら", "hint": "樱花"}
  ],
  "chinese_translation": "今天去了公园。樱花非常漂亮。"
}

重要：passage中使用____（四个下划线）作为填空占位符，不可使用其他占位符。blanks数组中的id从0开始递增，顺序必须与passage中____出现的顺序严格一致。hint用中文提示该单词的含义。"""


def _build_cloze_prompt(topics, word_list, length, jlpt_level):
    blank_count = max(3, min(15, length // 80))
    prompt = f"""话题：{"、".join(topics)}
JLPT等级：{jlpt_level}
文章长度：约{length}字
填空数量：{blank_count}个
可用词汇表：{"、".join(word_list)}

请根据以上要求生成一篇完型填空练习短文。"""
    return prompt


def generate_cloze(
    topics: list[str], word_list: list[str], length: int, jlpt_level: str,
) -> tuple[dict, int]:
    """Call DeepSeek API to generate a cloze exercise passage.
    Returns (cloze_data, total_tokens_used)."""
    client = _build_client()
    user_prompt = _build_cloze_prompt(topics, word_list, length, jlpt_level)
    blank_count = max(3, min(15, length // 80))
    system_prompt = CLOZE_SYSTEM_PROMPT.replace("{length}", str(length)).replace("{blank_count}", str(blank_count))

    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=4096,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("DeepSeek API返回了空响应")

    tokens = response.usage.total_tokens if response.usage else 0
    return _parse_dict_response(content), tokens


def generate_cloze_stream(
    topics: list[str], word_list: list[str], length: int, jlpt_level: str,
):
    """Stream cloze generation. Yields {"chunk": str} or {"done": True, "result": dict}."""
    client = _build_client()
    user_prompt = _build_cloze_prompt(topics, word_list, length, jlpt_level)
    blank_count = max(3, min(15, length // 80))
    system_prompt = CLOZE_SYSTEM_PROMPT.replace("{length}", str(length)).replace("{blank_count}", str(blank_count))

    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=4096,
        stream=True,
    )

    full = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            full += text
            yield {"chunk": text}

    try:
        result = _parse_dict_response(full)
        yield {"done": True, "result": result}
    except ValueError as e:
        yield {"error": str(e)}
