export function renderArticle(list, emptyMessage = "暂无相关报告数据") {

  const wrap = document.getElementById("articleWrap");

  if (!wrap) {
    return;
  }


  wrap.innerHTML = `<div class="timeline-axis"></div>`;


  if (!Array.isArray(list) || list.length === 0) {

    wrap.insertAdjacentHTML("beforeend", `

      <div class="
        wood-border
        bg-paperBg
        dark:bg-gray-900
        p-6 mb-7
        card-paper-hover
        animate-slideBase
      ">

        <h3 class="article-title">
          暂无内容
        </h3>

        <p class="
          text-inkMid
          dark:text-gray-300
          my-4
        ">
          ${emptyMessage}
        </p>

      </div>

    `);

    return;
  }


  // 按发布时间升序排列（时间线从旧到新）
  const sorted = [...list].sort(
    (a, b) => (a.published_at || a.date || "9999-99-99").localeCompare(b.published_at || b.date || "9999-99-99")
  );

  sorted.forEach((item, idx) => {
    const impact = item.impact || Math.round((item.hot || 0) / 25) || 1;
    const dotColor = impact >= 4
      ? "bg-sealRed"
      : impact >= 3
        ? "bg-bronzeGold"
        : "bg-bambooGreen";

    // 来源标签
    const sourceLabel = (item.tags || []).find(
      t => /^[A-Z]/.test(t) || /[\u4e00-\u9fa5]/.test(t) === false
    ) || (item.tags || [])[0] || "Unknown";

    const tagHtml = (item.tags || []).map(tag => {

      if (tag.includes("热门")) {

        return `
        <span class="
        tag-label
        px-2 py-0.5
        rounded-sm
        bg-bronzeGold/20
        text-bronzeGold
        text-xs">
        ${tag}
        </span>`;
      }

      if (["大模型", "多模态"].includes(tag)) {

        return `
        <span class="
        tag-label
        px-2 py-0.5
        rounded-sm
        bg-sealRed/10
        text-sealRed
        text-xs">
        ${tag}
        </span>`;
      }

      if (["产品更新", "办公AI", "ToB"].includes(tag)) {

        return `
        <span class="
        tag-label
        px-2 py-0.5
        rounded-sm
        bg-bambooGreen/10
        text-bambooGreen
        text-xs">
        ${tag}
        </span>`;
      }

      return `
      <span class="
      tag-label
      px-2 py-0.5
      rounded-sm
      bg-oldCyan/10
      text-oldCyan
      text-xs">
      ${tag}
      </span>`;

    }).join("");


    // 时间线序号 + 卡片（左侧红点由 timeline-dot 绝对定位）
    const card = `

      <div class="relative mb-7 animate-slideBase" style="animation-delay:${Math.min(idx * 0.05, 0.6)}s">
        <div class="timeline-dot ${dotColor}"></div>

        <div class="wood-border bg-paperBg dark:bg-gray-900 p-6 ml-6 card-paper-hover">

          <!-- 卡片顶部：序号 + 来源 + 热度星 -->
          <div class="flex items-center justify-between text-xs text-inkLight dark:text-gray-400 mb-2">
            <span class="font-mono">№ ${String(idx + 1).padStart(2, "0")}</span>
            <span class="flex items-center gap-2">
              <span class="px-2 py-0.5 bg-inkDark/5 dark:bg-white/10 text-inkDark dark:text-gray-200 rounded-sm font-semibold">
                ${sourceLabel}
              </span>
              <span class="text-bronzeGold" title="热度">
                ${"★".repeat(impact)}<span class="text-inkLight/40 dark:text-gray-600">${"★".repeat(5 - impact)}</span>
              </span>
            </span>
          </div>

          <a href="${item.link}" target="_blank" class="block">

            <h3 class="article-title dark:text-gray-100">
              ${item.title}
            </h3>

            <div class="flex gap-2 mt-2 flex-wrap">
              ${tagHtml}
            </div>

          </a>

          <div class="text-inkLight dark:text-gray-400 text-sm mt-3">
            发布日期：${item.published_at || item.date || "—"}
          </div>

          <p class="text-inkMid dark:text-gray-300 line-clamp-2 my-4">
            ${item.desc}
          </p>

          <div class="flex gap-3">
            <a href="${item.link}"
              target="_blank"
              class="btn-paper bg-inkDark dark:bg-gray-100 text-white dark:text-gray-900 px-3 py-1 text-sm">
              阅读原文
            </a>
          </div>

        </div>
      </div>

    `;

    wrap.insertAdjacentHTML("beforeend", card);
  });
}

export function renderHot(list) {

  const hotWrap = document.getElementById("hotWrap");
  if (!hotWrap) return;


  if (!Array.isArray(list) || list.length === 0) {

    hotWrap.innerHTML = `
    <div class="p-3 bg-inkDark/5 dark:bg-white/10 text-sm text-inkMid dark:text-gray-300">
    暂无热点
    </div>`;
    return;
  }


  // 计算热点评估
  const total = list.length;
  const avgImpact = list.reduce(
    (s, x) => s + (x.impact || Math.round((x.hot || 0) / 25) || 1), 0
  ) / total;
  const topItem = [...list].sort(
    (a, b) => (b.impact || 0) - (a.impact || 0)
  )[0];

  // 类别统计
  const catCount = {};
  list.forEach(x => {
    const cat = (x.tags || [])[0] || "AI";
    catCount[cat] = (catCount[cat] || 0) + 1;
  });
  const sortedCats = Object.entries(catCount)
    .sort((a, b) => b[1] - a[1]);
  const dominantCat = sortedCats[0]?.[0] || "—";


  // Top 3
  const hotList = [...list]
    .sort((a, b) => (b.impact || 0) - (a.impact || 0))
    .slice(0, 3);


  hotWrap.innerHTML = `

    <!-- 热点评估面板 -->
    <div class="mb-4 p-3 bg-sealRed/5 dark:bg-sealRed/10 border border-sealRed/20 rounded-sm">
      <div class="text-xs font-semibold text-sealRed mb-2 flex items-center gap-1">
        <i class="fa fa-line-chart"></i> 热点评估
      </div>

      <div class="grid grid-cols-3 gap-1 text-center mb-2">
        <div class="bg-paperBg dark:bg-gray-800 py-1.5 px-1 rounded-sm">
          <div class="text-base font-bold text-sealRed">${total}</div>
          <div class="text-[10px] text-inkLight dark:text-gray-400">信号总数</div>
        </div>
        <div class="bg-paperBg dark:bg-gray-800 py-1.5 px-1 rounded-sm">
          <div class="text-base font-bold text-bronzeGold">${avgImpact.toFixed(1)}</div>
          <div class="text-[10px] text-inkLight dark:text-gray-400">平均热度</div>
        </div>
        <div class="bg-paperBg dark:bg-gray-800 py-1.5 px-1 rounded-sm">
          <div class="text-base font-bold text-bambooGreen">${dominantCat}</div>
          <div class="text-[10px] text-inkLight dark:text-gray-400">主导类别</div>
        </div>
      </div>

      <div class="text-[11px] text-inkMid dark:text-gray-300 leading-snug">
        本期共 <span class="font-semibold text-sealRed">${total}</span> 条信号，
        平均热度 <span class="font-semibold text-bronzeGold">${avgImpact.toFixed(1)}/5</span>，
        类别分布：${sortedCats.slice(0, 3).map(([k, v]) =>
          `<span class="font-semibold">${k}</span> ${v}条`
        ).join("、")}
        ${sortedCats.length > 3 ? "等" : ""}。
        ${topItem ? `本期 TOP 1：<span class="font-semibold text-sealRed">${topItem.title.slice(0, 18)}${topItem.title.length > 18 ? "…" : ""}</span>` : ""}
      </div>
    </div>

    <!-- Top 3 列表 -->
    <div class="space-y-2">

      ${hotList.map((item, i) => {

        const impact = item.impact || Math.round((item.hot || 0) / 25) || 1;
        const medalColor = ["text-sealRed", "text-bronzeGold", "text-bambooGreen"][i] || "text-inkLight";
        const source = (item.tags || []).find(
          t => /^[A-Z]/.test(t) || /[\u4e00-\u9fa5]/.test(t) === false
        ) || (item.tags || [])[0] || "Unknown";

        return `
          <a href="${item.link}" target="_blank"
            class="block p-2 bg-inkDark/5 dark:bg-white/10 rounded-sm hover:bg-inkDark/10 dark:hover:bg-white/20 transition-colors">

            <div class="flex items-start gap-2">
              <span class="text-lg font-bold ${medalColor}">${["①", "②", "③"][i]}</span>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold dark:text-gray-100 line-clamp-2">
                  ${item.title}
                </div>
                <div class="flex items-center gap-2 mt-1 text-[11px]">
                  <span class="text-inkLight dark:text-gray-400">${source}</span>
                  <span class="text-bronzeGold">${"★".repeat(impact)}${"☆".repeat(5 - impact)}</span>
                </div>
              </div>
            </div>
          </a>
        `;
      }).join("")}

    </div>

  `;
}
