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


def call_llm(prompt):
    """
    调用 DeepSeek
    """

    response = client.chat.completions.create(
        model=ARK_MODEL,
        messages=[
            {
                "role": "system",
                "content": "你是一位专业AI行业分析师，只输出JSON，不要输出其它内容。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content



def parse_signal(content, item):
    """
    解析模型返回结果
    """

    content = content.strip()

    if content.startswith("```"):
        content = content.replace("```json","")
        content = content.replace("```","")
    try:

        data = json.loads(content)

        if "signal" not in data:
           raise ValueError(f"Invalid LLM output: {data}")

        return SignalCard(
            signal=data["signal"],
            insight=data["insight"],
            category=data["category"],
            impact=int(data["impact"]),
            source=item.source,
            title=item.title,
            url=item.url
        )

    except Exception as e:

        print("❌ JSON解析失败：", e)
        print(content)

        return SignalCard(
            signal="parse_error",
            insight="AI解析失败，请重新生成",
            category="Unknown",
            impact=0,
            source=item.source,
            title=item.title,
            url=item.url
        )


def generate_signal(item):
    """
    对外唯一入口
    """

    prompt = load_prompt(item)

    content = call_llm(prompt)
    print("LLM RAW:", content)

    return parse_signal(content, item)


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
        content = call_llm(load_prompt(item)).strip()
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "")
        data = _json.loads(content)
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