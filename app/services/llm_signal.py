import json
from pathlib import Path

from openai import OpenAI

from app.models.signal_card import SignalCard

from config import (
    ARK_API_KEY,
    ARK_BASE_URL,
    ARK_MODEL
)

client = OpenAI(
    api_key=ARK_API_KEY,
    base_url=ARK_BASE_URL
)

PROMPT_PATH = Path("prompts/signal.md")


def load_prompt(item):
    """
    读取 Prompt 模板并替换内容
    """
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    prompt = prompt.replace("{{title}}", item.title)
    prompt = prompt.replace("{{description}}", item.description)
    prompt = prompt.replace("{{url}}", item.url)

    return prompt


def call_llm(prompt, max_tokens=2048):
    """
    调用 DeepSeek / Ark 模型
    """

    response = client.chat.completions.create(
        model=ARK_MODEL,
        messages=[
            {
                "role": "system",
                "content": "你是一位专业AI行业分析师，只输出JSON，不要输出其它内容。必须输出完整、合法的JSON，不要截断。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content


def _extract_json(text):
    """
    从文本中提取JSON对象，处理markdown代码块、首尾截断等常见问题
    """
    text = text.strip()

    # 移除markdown代码块标记
    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    # 如果内容被截断（末尾不是}），尝试找到最后一个完整的JSON对象
    if not text.endswith("}"):
        last_brace = text.rfind("}")
        if last_brace > 0:
            text = text[:last_brace + 1]

    return text


def _repair_simple_json(text):
    """
    简单修复：尝试补全缺失的引号/括号。如果无法修复则返回原文。
    """
    text = text.strip()

    # 确保对象闭合
    open_braces = text.count("{") - text.count("}")
    if open_braces > 0:
        text += "}" * open_braces

    # 确保字符串值在最后一项缺失引号时修复
    if text and not text.endswith('"') and not text.endswith("}"):
        # 尝试补上缺失的引号和大括号
        text = text.rstrip(",") + '\"}'

    return text


def parse_signal(content, item, prompt=None):
    """
    解析模型返回结果，带 JSON 提取/修复和一次重试
    """

    def _try_parse(raw):
        cleaned = _extract_json(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 尝试简单修复后再解析
            repaired = _repair_simple_json(cleaned)
            return json.loads(repaired)

    # 第一次解析
    try:
        data = _try_parse(content)
        if "signal" in data:
            return data
    except Exception as e:
        print("❌ JSON解析失败：", e)
        print("原始内容:", content[:500])

    # 如果提供了 prompt，使用更大 token 上限重试一次
    if prompt:
        print("🔄 尝试用更大 token 重试解析...")
        try:
            retry_content = call_llm(prompt, max_tokens=4096)
            data = _try_parse(retry_content)
            if "signal" in data:
                print("✅ 重试解析成功")
                return data
        except Exception as e2:
            print("❌ 重试解析仍失败：", e2)

    return None


def build_signal_card(data, item):
    """
    将解析出的 JSON 字典转为 SignalCard
    """
    if not data or "signal" not in data:
        raise ValueError("Invalid LLM output")

    return SignalCard(
        signal=data.get("signal", ""),
        insight=data.get("insight", ""),
        category=data.get("category", "AI"),
        impact=int(data.get("impact", 1) or 1),
        source=item.source,
        title=item.title,
        url=item.url,
        published_at=getattr(item, "published_at", None) or "",
    )


def generate_signal(item):
    """
    对外唯一入口
    """

    prompt = load_prompt(item)

    content = call_llm(prompt)
    print("LLM RAW:", content[:300])

    data = parse_signal(content, item, prompt=prompt)

    if data:
        try:
            return build_signal_card(data, item)
        except Exception as exc:
            print("构建 SignalCard 失败:", exc)

    return SignalCard(
        signal=item.title or "parse_error",
        insight="AI解析失败，请重新生成",
        category="Unknown",
        impact=0,
        source=item.source,
        title=item.title,
        url=item.url,
        published_at=getattr(item, "published_at", None) or "",
    )


# ============================================================
# 为"批量整理周报摘要"按钮提供的工具函数
# 接受纯字典(从 weekly JSON 反序列化得到)，返回更新后的字典
# ============================================================

def regenerate_signal_card(signal_dict: dict) -> dict:
    """
    根据 weekly JSON 中已存在的 signal 字典，重新调用 LLM 生成摘要。
    输入字段期望: title / url / source / insight(可空)
    返回新字典: {signal, insight, category, impact}，失败时保留原值。
    """
    import json as _json

    # 构造一个伪 item 以复用 load_prompt
    class _Item:
        def __init__(self, t, d, u):
            self.title = t
            self.description = d
            self.url = u

    item = _Item(
        signal_dict.get("title", ""),
        signal_dict.get("insight") or signal_dict.get("signal") or "",
        signal_dict.get("url", ""),
    )

    try:
        prompt = load_prompt(item)
        content = call_llm(prompt).strip()
        data = parse_signal(content, item, prompt=prompt)

        if not data:
            raise ValueError("LLM did not return valid JSON")

        return {
            "signal": data.get("signal") or signal_dict.get("signal", ""),
            "insight": data.get("insight") or signal_dict.get("insight", ""),
            "category": data.get("category") or signal_dict.get("category", "AI"),
            "impact": int(data.get("impact") or signal_dict.get("impact") or 1),
        }
    except Exception as exc:
        print("regenerate_signal_card failed:", exc)
        return {
            "signal": signal_dict.get("signal", ""),
            "insight": signal_dict.get("insight", ""),
            "category": signal_dict.get("category", "AI"),
            "impact": signal_dict.get("impact", 1),
        }