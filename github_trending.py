import requests
from bs4 import BeautifulSoup

def fetch_github_trending():
    print('🚀 开始抓取 GitHub Trending...')
    url = 'https://github.com/trending/javascript?since=daily'
    
    try:
        response = requests.get(url, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        repos = []
        
        # 找到所有仓库文章块
        articles = soup.find_all('article', class_='Box-row')
        for article in articles[:5]:  # 只取前5个
            # 提取标题
            h2 = article.find('h2')
            if h2:
                a = h2.find('a')
                title = a.get_text().strip().replace('\n', '').replace(' ', '')
                link = 'https://github.com' + a.get('href')
            else:
                continue
            
            # 提取描述
            desc = article.find('p')
            description = desc.get_text().strip() if desc else '暂无描述'
            
            repos.append({
                'title': title,
                'description': description,
                'link': link
            })
        
        print(f'✅ 抓取成功，共 {len(repos)} 个仓库')
        return repos
    except Exception as e:
        print(f'❌ 抓取失败: {e}')
        return []

# 测试运行
if __name__ == '__main__':
    result = fetch_github_trending()
    for r in result:
        print(f"\n{r['title']}")
        print(f"  {r['description']}")
        print(f"  {r['link']}")