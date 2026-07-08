#!/usr/bin/env python3
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os
from openai import OpenAI

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

KEYWORDS = [
    "large language model",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "neural network"
]

def fetch_papers(max_results=10):
    print("正在从arXiv搜索最新论文...")
    url = "http://export.arxiv.org/api/query"
    search_query = " OR ".join(f'all:"{kw}"' for kw in KEYWORDS)
    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        print("成功获取论文数据")
        return response.text
    except Exception as e:
        print(f"获取论文失败: {e}")
        return None

def parse_papers(xml_data):
    if not xml_data:
        return []
    papers = []
    root = ET.fromstring(xml_data)
    ns = {
        'atom': 'http://www.w3.org/2005/Atom',
        'arxiv': 'http://arxiv.org/schemas/atom'
    }
    for entry in root.findall('atom:entry', ns):
        try:
            title = entry.find('atom:title', ns).text
            title = title.strip().replace('\n', ' ').replace('  ', ' ')
            summary = entry.find('atom:summary', ns).text
            summary = summary.strip().replace('\n', ' ').replace('  ', ' ')
            authors = []
            for author in entry.findall('atom:author', ns):
                name = author.find('atom:name', ns).text
                authors.append(name)
            url = entry.find('atom:id', ns).text
            published = entry.find('atom:published', ns).text[:10]
            papers.append({
                'title': title,
                'summary': summary,
                'authors': authors,
                'url': url,
                'published': published
            })
        except Exception as e:
            print(f"解析论文时出错: {e}")
            continue
    print(f"成功解析 {len(papers)} 篇论文")
    return papers

def generate_ai_summary(papers):
    if not DEEPSEEK_API_KEY:
        print("未配置DeepSeek API密钥")
        return None
    if not papers:
        return None
    print("正在调用DeepSeek生成智能摘要...")
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )
    papers_text = ""
    for i, paper in enumerate(papers, 1):
        authors_short = ', '.join(paper['authors'][:3])
        if len(paper['authors']) > 3:
            authors_short += '等'
        papers_text += f"论文{i}: {paper['title']}\n作者: {authors_short}\n摘要: {paper['summary'][:300]}\n\n"
    prompt = f"请根据以下最新论文生成中文简报：1.今日概览 2.重点推荐3篇 3.每篇一句话总结\n\n{papers_text}"
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        summary = response.choices[0].message.content
        print("AI摘要生成成功")
        return summary
    except Exception as e:
        print(f"AI摘要生成失败: {e}")
        return None

def generate_report(papers, ai_summary):
    today = datetime.now().strftime('%Y年%m月%d日')
    report = f"# AI论文速递 - {today}\n\n"
    report += f"共 {len(papers)} 篇论文\n\n"
    if ai_summary:
        report += ai_summary
        report += "\n\n---\n\n"
    report += "## 完整论文列表\n\n"
    for i, paper in enumerate(papers, 1):
        authors_text = ', '.join(paper['authors'][:3])
        if len(paper['authors']) > 3:
            authors_text += f' 等{len(paper["authors"])}位作者'
        report += f"### {i}. {paper['title']}\n\n"
        report += f"作者: {authors_text}\n\n"
        report += f"日期: {paper['published']}\n\n"
        report += f"摘要: {paper['summary'][:200]}...\n\n"
        report += f"[查看原文]({paper['url']})\n\n"
        report += "---\n\n"
    return report

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    text = message[:4000]
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': text}
    try:
        requests.post(url, json=data, timeout=10)
        print("Telegram推送成功")
        return True
    except Exception as e:
        print(f"Telegram推送失败: {e}")
        return False

def main():
    print("=" * 40)
    print("论文速递系统启动")
    print("=" * 40)
    xml_data = fetch_papers(max_results=10)
    if not xml_data:
        return
    papers = parse_papers(xml_data)
    if not papers:
        print("今天没有找到新论文")
        return
    ai_summary = generate_ai_summary(papers)
    report = generate_report(papers, ai_summary)
    os.makedirs('reports', exist_ok=True)
    filename = f"reports/{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"报告已保存: {filename}")
    if ai_summary:
        send_telegram(ai_summary[:3500])
    print("论文速递完成！")

if __name__ == "__main__":
    main()
