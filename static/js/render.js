export function renderArticle(list) {

  const wrap = document.getElementById("articleWrap");
  wrap.innerHTML = `<div class="timeline-axis"></div>`;

  list.forEach((item, idx) => {

    const tagHtml = (item.tags || []).map(tag => {
      if (tag.includes("热榜")) {
        return `<span class="tag-label px-2 py-0.5 rounded-sm bg-bronzeGold/20 text-bronzeGold text-xs">${tag}</span>`;
      }
      if (["大模型","多模态"].includes(tag)) {
        return `<span class="tag-label px-2 py-0.5 rounded-sm bg-sealRed/10 text-sealRed text-xs">${tag}</span>`;
      }
      if (["产品更新","办公AI","ToB"].includes(tag)) {
        return `<span class="tag-label px-2 py-0.5 rounded-sm bg-bambooGreen/10 text-bambooGreen text-xs">${tag}</span>`;
      }
      return `<span class="tag-label px-2 py-0.5 rounded-sm bg-oldCyan/10 text-oldCyan text-xs">${tag}</span>`;
    }).join("");

    const card = `
      <div class="wood-border bg-paperBg p-6 mb-7 card-paper-hover animate-slideBase">
        <a href="${item.link}" target="_blank" class="block">
          <h3 class="article-title">${item.title}</h3>
          <div class="flex gap-2 mt-2 flex-wrap">${tagHtml}</div>
        </a>

        <div class="text-inkLight text-sm mt-3">发布日期：${item.date}</div>
        <p class="text-inkMid line-clamp-2 my-4">${item.desc}</p>

        <div class="flex gap-3">
          <a href="${item.link}" target="_blank" class="btn-paper bg-inkDark text-white px-3 py-1 text-sm">
            阅读原文
          </a>
        </div>
      </div>
    `;

    wrap.insertAdjacentHTML("beforeend", card);
  });
}

// ====================== 热榜 ======================
export function renderHot(list) {
  const hotWrap = document.getElementById("hotWrap");
  const hotList = [...list].sort((a,b)=>b.hot-a.hot).slice(0,3);

  hotWrap.innerHTML = hotList.map(item => `
    <div class="p-3 bg-inkDark/5">
      <a href="${item.link}" target="_blank">
        <div class="font-bold">${item.title}</div>
        <div class="text-xs text-sealRed">热度 ${item.hot}</div>
      </a>
    </div>
  `).join("");
}