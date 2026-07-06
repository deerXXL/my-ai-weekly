import { filterByCat, searchFilter } from "./filter.js";
import { renderArticle, renderHot } from "./render.js";

let articleSource = [];

document.addEventListener("DOMContentLoaded", async () => {
  const box = document.getElementById("categoryBox");
  const toggleBtn = document.getElementById("toggleCategoryBox");

  console.log("box:", box);
  console.log("btn:", toggleBtn);

  if (!box || !toggleBtn) {
    console.error("❌ 找不到元素");
    return;
  }

  toggleBtn.addEventListener("click", () => {
    box.classList.toggle("open");
  });
});
  console.log("app.js 已加载");

  const response = await fetch("/api/report");
  articleSource = await response.json();

  renderArticle(articleSource);
  renderHot(articleSource);

  // 显示分类面板
  // document.getElementById("categoryBox")?.classList.remove("hidden");

  bindCategory();
  bindSearch();

  if (toggleBtn && box) {
    toggleBtn.addEventListener("click", () => {
      box.classList.toggle("open");
  });
}

function bindCategory() {
  const btns = document.querySelectorAll(".cat-btn");
  console.log("按钮数量:", btns.length);

  btns.forEach(btn => {
    btn.addEventListener("click", (e) => {

      const cat = e.currentTarget.dataset.cat;

      console.log("🔥点击分类:", cat);

      // active切换
      btns.forEach(b => b.classList.remove("active"));
      e.currentTarget.classList.add("active");

      const filtered = filterByCat(articleSource, cat);

      renderArticle(filtered);
    });
  });
}

function bindSearch() {
  const input = document.getElementById("searchInput");

  if (!input) return;

  input.addEventListener("input", (e) => {
    const list = searchFilter(articleSource, e.target.value);
    renderArticle(list);
    renderHot(list);
  });
}