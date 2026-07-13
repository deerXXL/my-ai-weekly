import json
import re
from pathlib import Path

from openai import OpenAI
from app.models.raw_item import RawItem
from app.models.signal_card import SignalCard
from config import ARK_API_KEY, ARK_BASE_URL, ARK_MODEL

client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)

PROMPTS_DIR = Path("prompts")


def load_prompt_template(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")

def load_prompt(item):

    template = load_prompt_template(
        "signal.md"
    )

    return (
        template
        .replace(
            "{{title}}",
            item.title
        )
        .replace(
            "{{description}}",
            item.description or ""
        )
        .replace(
            "{{source}}",
            item.source
        )
        .replace(
            "{{url}}",
            item.url
        )
    )

def call_llm(
    prompt: str,
    system: str | None = None,
    max_tokens=2048
):
    """
    调用 DeepSeek / Ark 模型
    """

    response = client.chat.completions.create(
        model=ARK_MODEL,
        messages=[
            {
                "role": "system",
                "content": system or 
                "你是一位专业AI行业分析师，只输出JSON，不要输出其它内容。必须输出完整、合法的JSON，不要截断。"
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


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


def _derive_category(item):
    """当 LLM 解析失败时，根据标题/描述/source 推断一个合理的分类。"""
    text = f"{item.title or ''} {item.description or ''} {item.source or ''}".lower()

    if "github" in item.source.lower() or "开源" in text or "open-source" in text or "open source" in text:
        return "开源项目"
    if "benchmark" in text or "评测" in text or "测试" in text:
        return "产品评测"
    if "report" in text or "policy" in text or "rsp" in text or "研究" in text or "google research" in item.source.lower():
        return "行业报告"
    if "多模态" in text or "voice" in text or "image" in text or "video" in text or "视觉" in text:
        return "多模态"
    if "办公" in text or "workspace" in text or "work" in text:
        return "办公AI"
    if "企业" in text or "enterprise" in text or "partner" in text or "partner" in text or "government" in text or "云" in text:
        return "ToB"
    if "模型" in text or "gpt" in text or "claude" in text or "llm" in text or "fable" in text:
        return "大模型"
    if "产品" in text or "introduc" in text or "launch" in text or "available" in text or "tag" in text or "sonnet" in text:
        return "产品更新"
    return "AI"


def _derive_impact(item):
    """当 LLM 解析失败时，给一个默认热度，来源越权威越高。"""
    source = (item.source or "").lower()
    weights = {
        "openai": 5,
        "anthropic": 5,
        "huggingface": 4,
        "google research": 4,
        "techcrunch": 4,
        "venturebeat": 4,
        "机器之心": 3,
        "36氪": 3,
        "reddit": 2,
        "github": 3,
    }
    return weights.get(source, 2)


def _clean_fallback_title(title):
    """如果标题仍被拼接成 'CategoryJun 23, 2026Title...'，尝试拆出真实标题。"""
    if not title:
        return ""
    # 常见模式：可选分类 + 日期 + 真实标题
    m = re.search(
        r"(?:Product|Announcements|Case Study|Features)?\s*"
        r"(?:[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})?\s*"
        r"(.+)",
        title.strip(),
    )
    if m:
        return m.group(1).strip()
    return title.strip()


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

    data = parse_signal(
        raw,
        item,
        prompt=prompt
    )

    if not data:
        return {
            "title_zh": item.title,
            "summary": item.description or "",
            "impact": 2,
            "source": item.source,
            "url": item.url,
            "original_title": item.title,
            "image_url": (item.extra or {}).get("image_url") or "",
        }


    return {
        "title_zh": data.get("title_zh") or item.title,
        "summary": data.get("summary") or item.description or "",
        "impact": int(data.get("impact") or 3),
        "source": item.source,
        "url": item.url,
        "original_title": item.title,
        "image_url": (item.extra or {}).get("image_url") or "",
    }

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

    # LLM 解析失败时，用原始元数据生成一个可用的卡片，而不是暴露“解析失败”
    clean_title = _clean_fallback_title(item.title)
    insight = item.description if item.description and item.description != item.title else clean_title
    return SignalCard(
        signal=clean_title,
        insight=insight,
        category=_derive_category(item),
        impact=_derive_impact(item),
        source=item.source,
        title=clean_title,
        url=item.url,
        published_at=getattr(item, "published_at", None) or "",
    )


# ============================================================
# 为"批量整理周报摘要"按钮提供的工具函数
# 接受纯字典(从 weekly JSON 反序列化得到)，返回更新后的字典
# ============================================================

def _repair_unescaped_quotes(text: str) -> str:
    """修复字符串值内部未转义的双引号。

    模型在 bullets/summary 里常写出形如 '宜"渐进渗透"而非' 的文本，
    其中的英文双引号没有转义，导致 JSON 解析器误判字符串结束。
    逐字符扫描：在「字符串内部」遇到双引号时，若其后不是合法的结构性边界
    （逗号、冒号、括号、空白后接这些，或字符串结尾），则将其转义为 \\"。
    """
    out = []
    in_str = False
    escape = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if escape:
            out.append(ch)
            escape = False
            i += 1
            continue
        if ch == "\\":
            out.append(ch)
            escape = True
            i += 1
            continue
        if ch == '"':
            if not in_str:
                in_str = True
                out.append(ch)
                i += 1
                continue
            # 在字符串内部遇到了双引号，判断它是「字符串结束符」还是「内部未转义引号」
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            # 若紧跟结构边界，认为这是正常的字符串结束
            if j < n and text[j] in ",:}]":
                in_str = False
                out.append(ch)
                i += 1
                continue
            if j >= n:
                # 文件尾，按结束处理
                in_str = False
                out.append(ch)
                i += 1
                continue
            # 否则视为字符串内部的未转义双引号，转义它
            out.append('\\"')
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_json_response(content):

    text = _extract_json(content)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        return json.loads(_repair_simple_json(text))
    except json.JSONDecodeError:
        pass

    # 最后兜底：修复字符串内部未转义的双引号
    return json.loads(_repair_unescaped_quotes(text))

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
        template
        .replace(
            "{{max_items}}",
            str(max_items)
        )
        .replace(
            "{{candidates}}",
            "\n".join(lines)
        )
    )

    print(
        "[compose] 策展 + 核心摘要 + 技术总结..."
    )

    # 注意：模型在 bullets 文本里常写出未转义的双引号（如 "渐进渗透"），
    # 导致 JSON 解析失败。这里第一次用较大 token 避免截断；
    # 若仍解析失败，重试一次（重新生成通常能得到合法 JSON）。
    raw = call_llm(prompt, max_tokens=4096)
    try:
        return parse_json_response(raw)
    except Exception as exc:
        print(f"❌ compose 首次解析失败：{exc}，重试一次…")
        raw = call_llm(prompt, max_tokens=6144)
        return parse_json_response(raw)



def regenerate_signal_card(signal_dict: dict) -> dict:
    """
    根据已有周报数据重新生成摘要
    """

    class _Item:

        def __init__(self, t, d, u):

            self.title = t
            self.description = d
            self.url = u
            self.source = signal_dict.get(
                "source",
                ""
            )


    item = _Item(
        signal_dict.get(
            "title",
            ""
        ),

        signal_dict.get(
            "insight"
        )
        or signal_dict.get(
            "signal",
            ""
        ),

        signal_dict.get(
            "url",
            ""
        )
    )


    try:

        prompt = load_prompt(
            item
        )

        content = call_llm(
            prompt
        ).strip()


        data = parse_signal(
            content,
            item,
            prompt=prompt
        )


        if not data:
            raise ValueError(
                "LLM did not return valid JSON"
            )


        return {

            "signal":
                data.get(
                    "signal"
                )
                or signal_dict.get(
                    "signal",
                    ""
                ),


            "insight":
                data.get(
                    "insight"
                )
                or signal_dict.get(
                    "insight",
                    ""
                ),


            "category":
                data.get(
                    "category"
                )
                or signal_dict.get(
                    "category",
                    "AI"
                ),


            "impact":
                int(
                    data.get(
                        "impact"
                    )
                    or signal_dict.get(
                        "impact",
                        1
                    )
                ),

        }


    except Exception as exc:

        print(
            "regenerate_signal_card failed:",
            exc
        )


        return {

            "signal":
                signal_dict.get(
                    "signal",
                    ""
                ),


            "insight":
                signal_dict.get(
                    "insight",
                    ""
                ),


            "category":
                signal_dict.get(
                    "category",
                    "AI"
                ),


            "impact":
                signal_dict.get(
                    "impact",
                    1
                ),

        }