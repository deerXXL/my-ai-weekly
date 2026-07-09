import json
from pathlib import Path

from openai import OpenAI

from app.models.raw_item import RawItem
from config import ARK_API_KEY, ARK_BASE_URL, ARK_MODEL

client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)

PROMPTS_DIR = Path("prompts")


def load_prompt_template(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def call_llm(prompt: str, system: str | None = None) -> str:
    response = client.chat.completions.create(
        model=ARK_MODEL,
        messages=[
            {
                "role": "system",
                "content": system or "你是一位专业AI行业分析师，只输出JSON，不要输出其它内容。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content or ""


def parse_json_response(content: str) -> dict | list:
    text = content.strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def analyze_item(item: RawItem) -> dict:
    template = load_prompt_template("analyze_item.md")
    prompt = (
        template.replace("{{title}}", item.title)
        .replace("{{source}}", item.source)
        .replace("{{description}}", (item.description or "")[:800])
        .replace("{{url}}", item.url)
    )
    raw = call_llm(prompt)
    print(f"  [analyze] {item.title[:40]}...")
    data = parse_json_response(raw)
    return {
        "title_zh": data.get("title_zh") or item.title,
        "summary": data.get("summary") or item.description or "",
        "impact": int(data.get("impact") or 3),
        "source": item.source,
        "url": item.url,
        "original_title": item.title,
        "image_url": (item.extra or {}).get("image_url") or "",
    }


def compose_newsletter(candidates: list[dict], max_items: int = 6) -> dict:
    lines = []
    for i, c in enumerate(candidates):
        lines.append(
            f"[{i}] impact={c['impact']} source={c['source']}\n"
            f"title: {c['title_zh']}\n"
            f"summary: {c['summary']}\n"
        )
    template = load_prompt_template("compose_newsletter.md")
    prompt = (
        template.replace("{{max_items}}", str(max_items))
        .replace("{{candidates}}", "\n".join(lines))
    )
    raw = call_llm(prompt)
    print("[compose] 策展 + 核心摘要 + 技术总结...")
    return parse_json_response(raw)
