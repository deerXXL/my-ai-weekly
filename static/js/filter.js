const categoryMap = {
  all: [],
  llm: ["llm", "gpt", "openai", "claude"],
  update: ["update", "release", "launch"],
  report: ["report", "analysis"],
  multimodal: ["vision", "image", "audio"],
  tob: ["enterprise", "saas", "b2b"],
  office: ["copilot", "office", "workflow"]
};

export function filterByCat(list, cat) {
  if (cat === "all") return list;

  const keywords = categoryMap[cat] || [];

  return list.filter(item => {
    const text = (
      (item.title || "") +
      (item.desc || "") +
      ((item.tags || []).join(" "))
    ).toLowerCase();

    return keywords.some(k =>
      text.includes(k.toLowerCase())
    );
  });
}

export function searchFilter(list, key) {
  if (!key.trim()) return list;

  const k = key.toLowerCase();

  return list.filter(i =>
    i.title.toLowerCase().includes(k) ||
    i.desc.toLowerCase().includes(k) ||
    i.tags.some(t => t.toLowerCase().includes(k))
  );
}