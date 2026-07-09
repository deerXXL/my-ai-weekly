import { searchFilter } from "./filter.js";
import { fetchReport, fetchArchive } from "./api.js";
import { renderArticle, renderHot } from "./render.js";

let articleSource = [];

document.addEventListener("DOMContentLoaded", async () => {
  loadMeta();
  try {
    const response = await fetch("/api/report");

    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }

    articleSource = await response.json();
    console.log("API数据:", articleSource);
    renderArticle(articleSource);
    renderHot(articleSource);

    loadArchive();

    bindSearch();
    bindQuickActions();
  } catch (error) {
    console.error("Failed to load report:", error);
    renderArticle([],
      "前后端连接失败：请确认通过 python web_app.py 启动，并访问 http://127.0.0.1:5000"
    );
    renderHot([]);
  }
});

function bindSearch() {
  const input = document.getElementById("searchInput");

  if (!input) {
    return;
  }

  input.addEventListener("input", (event) => {
    const keyword = event.target.value;
    const list = searchFilter(articleSource, keyword);

    renderArticle(list);
    renderHot(list);
  });
}

// 格式化双周区间显示：2026-06-25 → 2026.06.25
function fmtPeriod(start, end) {
  if (!start || !end) return "";
  return `${start.replace(/-/g, ".")} — ${end.replace(/-/g, ".")}`;
}

// 格式化归档标签：第N期 · 06.25 — 07.09
function fmtArchiveLabel(item) {
  const issue = item.issue_number ? `第${item.issue_number}期 · ` : "";
  const period = fmtPeriod(item.period_start, item.period_end);
  return `${issue}${period}`;
}

// 从归档项更新页面标题和统计周期
function updateMetaFromArchive(item) {
  const titleEl = document.getElementById("pageTitle");
  const periodEl = document.getElementById("periodRange");

  if (titleEl && item.title) {
    titleEl.textContent = item.title;
  } else if (titleEl && item.issue_number) {
    titleEl.textContent = `AI双周产品周报 · 第${item.issue_number}期`;
  }

  const period = fmtPeriod(item.period_start, item.period_end);
  if (periodEl && period) {
    periodEl.textContent = `${period}（双周）`;
  }
}

async function loadArchive() {

  const select = document.getElementById("weekSelect");
  const current = document.getElementById("currentWeek");


  if (!select) {
    return;
  }


  const archive = await fetchArchive();


  select.innerHTML = "";


  archive.forEach(item => {

    const option = document.createElement("option");

    option.value = item.file;

    const issueLabel = item.issue_number ? `第${item.issue_number}期 · ` : "";
    const periodStr = fmtPeriod(item.period_start, item.period_end);
    option.textContent = `${issueLabel}${periodStr}`;

    select.appendChild(option);

  });


  if (archive.length > 0) {

    current.textContent = fmtArchiveLabel(archive[0]);
    updateMetaFromArchive(archive[0]);
    select.addEventListener(
      "change",
      async () => {

        const file =
          select.value;

        console.log(
          "切换报告:",
          file
        );


        const articles =
          await fetchReport(file);



        articleSource = articles;



        renderArticle(articleSource);


        renderHot(articleSource);



        // 根据选中的归档项更新标题、统计周期、当前归档期
        const selected = archive.find(a => a.file === file);
        if (selected) {
          current.textContent = fmtArchiveLabel(selected);
          updateMetaFromArchive(selected);
        }


      }
    );


  }
}


// ============================================================
// 加载页面元信息（期号、统计周期等）
// ============================================================
async function loadMeta() {
  try {
    const res = await fetch("/api/meta");
    const meta = await res.json();

    const titleEl = document.getElementById("pageTitle");
    const periodEl = document.getElementById("periodRange");

    if (titleEl && meta.title) {
      titleEl.textContent = meta.title;
    }

    if (periodEl && meta.period_start && meta.period_end) {
      const start = meta.period_start.replace(/-/g, ".");
      const end = meta.period_end.replace(/-/g, ".");
      periodEl.textContent = `${start} \u2014 ${end}\uff08\u53cc\u5468\uff09`;
    } else if (periodEl && meta.date) {
      periodEl.textContent = meta.date;
    }
  } catch (e) {
    console.warn("无法加载页面元信息:", e);
  }
}


// ============================================================
// 4 个快捷操作按钮
// ============================================================
const ACTION_LABELS = {
  collect: "新增本期资讯",
  summarize: "批量整理周报摘要",
  export: "生成完整周报文档",
  archive: "往期周报归档库",
};

function bindQuickActions() {
  const buttons = document.querySelectorAll("[data-action]");

  if (!buttons.length) {
    return;
  }

  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      if (action === "collect") return runCollect(btn);
      if (action === "summarize") return runSummarize(btn);
      if (action === "export") return runExport(btn);
      if (action === "archive") return runArchive(btn);
    });
  });
}

// --- 任务状态条 ---
function showStatus(name) {
  const box = document.getElementById("quickStatus");
  const nameEl = document.getElementById("quickStatusName");
  const pctEl = document.getElementById("quickStatusPercent");
  const bar = document.getElementById("quickStatusBar");
  const msg = document.getElementById("quickStatusMsg");
  if (!box) return;
  box.classList.remove("hidden");
  nameEl.textContent = `▶ ${name}`;
  pctEl.textContent = "0%";
  bar.style.width = "0%";
  msg.textContent = "任务已派发…";
}

function updateStatus(progress, message) {
  const pctEl = document.getElementById("quickStatusPercent");
  const bar = document.getElementById("quickStatusBar");
  const msg = document.getElementById("quickStatusMsg");
  if (pctEl) pctEl.textContent = `${progress}%`;
  if (bar) bar.style.width = `${progress}%`;
  if (msg) msg.textContent = message || "";
}

function hideStatus() {
  const box = document.getElementById("quickStatus");
  if (box) box.classList.add("hidden");
}

// 轮询后台任务
async function pollTask(tid) {
  const maxTries = 600; // 最多等 10 分钟（每秒一次）
  for (let i = 0; i < maxTries; i++) {
    try {
      const res = await fetch(`/api/task/${tid}`);
      const t = await res.json();
      updateStatus(t.progress || 0, t.message || "");

      if (t.status === "success") {
        return t;
      }
      if (t.status === "failed") {
        throw new Error(t.message || "任务失败");
      }
    } catch (e) {
      // 网络抖动，继续轮询
    }
    await new Promise(r => setTimeout(r, 1000));
  }
  throw new Error("任务超时");
}

// --- ① 新增本期资讯 ---
async function runCollect(btn) {
  if (!confirm(`确认启动【${ACTION_LABELS.collect}】?\n\n将抓取 9 个 AI 数据源并调用 LLM 重新分析，过程约 5–10 分钟。`)) {
    return;
  }
  showStatus(ACTION_LABELS.collect);
  btn.disabled = true;

  try {
    const res = await fetch("/api/collect", { method: "POST" });
    const data = await res.json();
    if (!data.task_id) throw new Error(data.message || "启动失败");
    await pollTask(data.task_id);

    alert("✅ 资讯采集完成，正在刷新页面…");
    location.reload();
  } catch (exc) {
    alert("❌ " + exc.message);
    hideStatus();
  } finally {
    btn.disabled = false;
  }
}

// --- ② 批量整理周报摘要 ---
async function runSummarize(btn) {
  if (!confirm(`确认启动【${ACTION_LABELS.summarize}】?\n\n将基于已采集的资讯重新调用 LLM 生成摘要。`)) {
    return;
  }
  showStatus(ACTION_LABELS.summarize);
  btn.disabled = true;

  try {
    const res = await fetch("/api/summarize", { method: "POST" });
    const data = await res.json();
    if (!data.task_id) throw new Error(data.message || "启动失败");
    await pollTask(data.task_id);

    alert("✅ 摘要整理完成，正在刷新页面…");
    location.reload();
  } catch (exc) {
    alert("❌ " + exc.message);
    hideStatus();
  } finally {
    btn.disabled = false;
  }
}

// --- ③ 生成完整周报文档 ---
async function runExport(btn) {
  showStatus(ACTION_LABELS.export);
  btn.disabled = true;

  try {
    updateStatus(30, "正在排版 Markdown…");
    const res = await fetch("/api/export", { method: "POST" });
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { msg = (await res.json()).message || msg; } catch(_) {}
      throw new Error(msg);
    }

    const blob = await res.blob();
    const sizeKB = (blob.size / 1024).toFixed(1);
    const disposition = res.headers.get("Content-Disposition") || "";
    const m = disposition.match(/filename\*=UTF-8''(.+?)(?:;|$)/);
    const filename = m ? decodeURIComponent(m[1]) : "weekly-export.md";

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    updateStatus(100, `已生成：${filename}（${sizeKB} KB）`);
    setTimeout(() => alert(
      `✅ 周报已生成\n文件：${filename}\n大小：${sizeKB} KB`
    ), 200);
  } catch (exc) {
    alert("❌ " + exc.message);
  } finally {
    hideStatus();
    btn.disabled = false;
  }
}

// --- ④ 往期周报归档库 ---
async function runArchive(btn) {
  // 直接把页头"切换归档期数"卡片滚到视野里，并把焦点交给 select
  const select = document.getElementById("weekSelect");
  if (select) {
    select.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => select.focus(), 350);
  }
  alert("已在顶部显示归档期数下拉框，可切换查看往期周报。");
}
