export async function fetchReport() {
  const res = await fetch("/api/report");
  return await res.json();
}