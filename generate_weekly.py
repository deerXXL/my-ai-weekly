import json
import os
from datetime import datetime
from github_trending import fetch_github_trending

def generate_weekly():
    print('📝 开始生成周刊...')
    repos = fetch_github_trending()
    
    if not repos:
        print('⚠️ 没有获取到数据')
        return
    
    # 生成 Markdown 内容
    markdown = f'# AI周刊 · 第1期\n\n'
    markdown += f'> 生成时间: {datetime.now().strftime("%Y-%m-%d")}\n\n'
    markdown += f'## 🛠 本周热门工具 (GitHub Trending)\n\n'
    
    for i, repo in enumerate(repos, 1):
        markdown += f'### {i}. {repo["title"]}\n'
        markdown += f'- 📖 描述: {repo["description"]}\n'
        markdown += f'- 🔗 链接: {repo["link"]}\n\n'
    
    # 保存文件
    os.makedirs('output', exist_ok=True)
    filepath = f'output/weekly-{datetime.now().strftime("%Y%m%d")}.md'
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f'🎉 周刊生成成功！文件: {filepath}')

if __name__ == '__main__':
    generate_weekly()