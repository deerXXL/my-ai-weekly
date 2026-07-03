import json
from pathlib import Path

from openai import OpenAI

from app.models.signal_card import SignalCard

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    MODEL_NAME
)

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
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
        model=MODEL_NAME,
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
        temperature=0.3
    )

    return response.choices[0].message.content


def parse_signal(content, item):
    """
    解析模型返回结果
    """

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
            insight=content,
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