你是一位 AI 周刊主编。以下是从近两周候选资讯中分析出的条目（含 index、title_zh、summary、impact、source）。

请从中选出最适合「行业动态」栏目的 {{max_items}} 条，并生成本期概览与技术总结。

严格返回 JSON：
{
  "selected_indices": [0, 2, 5],
  "industry_notes": {
    "0": "30-60字使用场景或体验说明，仅对模型/工具/产品类条目填写，其余留空字符串",
    "2": ""
  },
  "core_summary": "120-200字中文核心摘要，概括近两周AI领域最重要突破与趋势，语气像科技周刊编辑",
  "tech_summary": {
    "title_suffix": "三大趋势",
    "trends": [
      {"index": 1, "title": "趋势标题", "body": "60-100字说明"}
    ],
    "feasibility": [
      {"index": 1, "title": "应用方向", "bullets": ["**标签：** 说明", "普通要点"]}
    ]
  }
}

约束：
- selected_indices 长度不超过 {{max_items}}，按 impact 与代表性选取，避免同质重复
- industry_notes 的 key 为候选 index 字符串，仅对入选且适合补充「使用说明」的条目填写（如新模型、新工具、开源项目），融资/政策/事故类留空
- 至少 3 条来自国内源（AI工具集、AIbase、XixAI）
- trends 恰好 3 条，feasibility 恰好 3 条
- 全部使用中文
- 不要 Markdown 代码块

候选条目：
{{candidates}}
