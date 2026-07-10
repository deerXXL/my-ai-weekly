// 主题切换：亮/暗。状态写入 localStorage，首屏防闪烁由 index.html 内联脚本处理。

const KEY = "wb-theme";

function applyTheme(theme) {
  const html = document.documentElement;
  const icon = document.getElementById("themeIcon");
  const label = document.getElementById("themeLabel");

  if (theme === "dark") {
    html.classList.add("dark");
    if (icon) {
      icon.classList.remove("fa-moon-o");
      icon.classList.add("fa-sun-o");
    }
    if (label) label.textContent = "亮色";
  } else {
    html.classList.remove("dark");
    if (icon) {
      icon.classList.remove("fa-sun-o");
      icon.classList.add("fa-moon-o");
    }
    if (label) label.textContent = "暗色";
  }
}

export function initThemeToggle() {
  const btn = document.getElementById("themeToggle");
  if (!btn) return;

  // 初始化时按当前 html.dark 状态更新按钮
  const isDark = document.documentElement.classList.contains("dark");
  applyTheme(isDark ? "dark" : "light");

  btn.addEventListener("click", () => {
    const willBeDark = !document.documentElement.classList.contains("dark");
    applyTheme(willBeDark ? "dark" : "light");
    try {
      localStorage.setItem(KEY, willBeDark ? "dark" : "light");
    } catch (e) {
      // localStorage 被禁用时静默失败
    }
  });
}
