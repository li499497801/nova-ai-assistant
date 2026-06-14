PLUGIN_NAME = "联网搜索"
PLUGIN_DESCRIPTION = "搜索互联网获取实时信息"
PLUGIN_KEYWORDS = ["搜索", "搜一下", "查一下", "最新", "新闻", "search", "联网"]

import requests
import re

def execute(params: str) -> str:
    """联网搜索：先用 DuckDuckGo API，再用 HTML 抓取补充"""
    query = params.strip()
    if not query:
        return "请提供搜索内容，例如：搜索 今日新闻"

    results = []

    # 方法1: DuckDuckGo Instant Answer API
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        if data.get("Abstract"):
            results.append(f"【摘要】{data['Abstract']}")
            if data.get("AbstractURL"):
                results.append(f"来源: {data['AbstractURL']}")

        if data.get("Answer"):
            results.append(f"【答案】{data['Answer']}")

        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"• {topic['Text']}")

    except Exception:
        pass

    # 方法2: DuckDuckGo HTML 搜索（抓取搜索结果页面）
    if len(results) < 2:
        try:
            r = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            r.raise_for_status()
            html = r.text

            # 提取搜索结果
            snippets = re.findall(r'class="result__snippet">(.*?)</a>', html, re.DOTALL)
            titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
            urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', html, re.DOTALL)

            if titles:
                results.append("\n【搜索结果】")
                for i in range(min(5, len(titles))):
                    title = re.sub(r'<[^>]+>', '', titles[i]).strip()
                    snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
                    url = re.sub(r'<[^>]+>', '', urls[i]).strip() if i < len(urls) else ""
                    results.append(f"{i+1}. {title}")
                    if snippet:
                        results.append(f"   {snippet}")
                    if url:
                        results.append(f"   链接: {url}")

        except Exception:
            pass

    if results:
        return "\n".join(results)

    return f"未找到「{query}」的相关结果。你可以尝试换个关键词搜索。"
