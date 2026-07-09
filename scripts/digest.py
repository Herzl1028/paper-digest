import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os
from openai import OpenAI

# 从环境变量读取密钥
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
PUSHPLUS_TOKEN = os.environ.get('PUSHPLUS_TOKEN', '')

def main():
    print("=" * 50)
    print("论文速递系统启动")
    print("=" * 50)
    
    # 1. 抓取论文
    print("正在搜索论文...")
    url = "http://export.arxiv.org/api/query"
    keywords = ["large language model", "artificial intelligence", "machine learning", "deep learning"]
    query = " OR ".join(f'all:"{k}"' for k in keywords)
    
    try:
        resp = requests.get(url, params={
            "search_query": query,
            "max_results": 10,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }, timeout=30)
        resp.raise_for_status()
        print("获取成功")
    except Exception as e:
        print(f"获取失败: {e}")
        return
    
    # 2. 解析论文
    papers = []
    root = ET.fromstring(resp.text)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    
    for entry in root.findall('atom:entry', ns):
        try:
            title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
            summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
            authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)]
            link = entry.find('atom:id', ns).text
            
            papers.append({
                'title': title,
                'summary': summary[:300],
                'authors': authors[:3],
                'url': link
            })
        except:
            continue
    
    print(f"解析 {len(papers)} 篇论文")
    
    if not papers:
        print("没有论文")
        return
    
    # 3. AI摘要
    summary_text = ""
    if DEEPSEEK_API_KEY:
        print("生成AI摘要...")
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        
        text = "\n\n".join([
            f"论文{i+1}: {p['title']}\n作者: {', '.join(p['authors'])}\n摘要: {p['summary']}"
            for i, p in enumerate(papers)
        ])
        
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": f"请总结以下论文，生成中文简报：1.今日概览 2.重点推荐3篇 3.每篇一句话总结\n\n{text}"}],
                temperature=0.7,
                max_tokens=4000
            )
            summary_text = resp.choices[0].message.content
            print("AI摘要完成")
        except Exception as e:
            print(f"AI摘要失败: {e}")
    
    # 4. 生成报告
    today = datetime.now().strftime('%Y-%m-%d')
    report = f"# 论文速递 - {datetime.now().strftime('%Y年%m月%d日')}\n\n"
    report += f"共 {len(papers)} 篇论文\n\n"
    
    if summary_text:
        report += summary_text + "\n\n---\n\n"
    
    report += "## 论文列表\n\n"
    for i, p in enumerate(papers, 1):
        report += f"### {i}. {p['title']}\n\n"
        report += f"**作者**: {', '.join(p['authors'])}\n\n"
        report += f"**摘要**: {p['summary']}...\n\n"
        report += f"[查看原文]({p['url']})\n\n---\n\n"
    
    # 5. 保存
    os.makedirs('reports', exist_ok=True)
    filename = f"reports/{today}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"已保存: {filename}")
    
    # 6. 推送
    if PUSHPLUS_TOKEN:
        push_title = f"📄 AI论文速递 - {datetime.now().strftime('%m月%d日')}"
        push_content = (summary_text or report[:2000]) + "\n\n[查看详情](https://github.com/Herzl1028/paper-digest)"
        
        try:
            r = requests.post("http://www.pushplus.plus/send", json={
                "token": PUSHPLUS_TOKEN,
                "title": push_title,
                "content": push_content,
                "template": "markdown"
            }, timeout=10)
            if r.status_code == 200:
                print("PushPlus推送成功")
            else:
                print(f"推送失败: {r.text}")
        except Exception as e:
            print(f"推送异常: {e}")
    
    print("完成！")

if __name__ == "__main__":
    main()
