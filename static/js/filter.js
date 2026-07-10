export function searchFilter(list, key) {

  if (!key.trim()) return list;

  const k = key.toLowerCase();

  return list.filter(i =>
    i.title.toLowerCase().includes(k) ||
    i.desc.toLowerCase().includes(k) ||
    i.tags.some(t =>
      t.toLowerCase().includes(k)
    )
  );

}