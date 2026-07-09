import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os
from openai import OpenAI

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
PUSHPLUS_TOKEN = os.environ.get('PUSHPLUS_TOKEN', '')

def translate_paper(title, summary):
    """翻译论文标题和摘要，保留关键术语"""
    if not DEEPSEEK_API_KEY:
        return title, summary
    
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    prompt = f"""请将以下英文学术论文的标题和摘要翻译成中文。

翻译规则：
1. 关键术语保留英文原文，后面用括号加中文解释
   例如：Transformer（ transformer是一种基于自注意力的神经网络架构）
   例如：RLHF（基于人类反馈的强化学习）
   例如：diffusion model（扩散模型，一种通过逐步去噪生成数据的生成模型）
   例如：LLM（大语言模型）
   例如：fine-tuning（微调，在预训练模型上进行特定任务训练）
2. 第一次出现的术语要解释，后面再出现可以只用中文
3. 翻译要通顺自然，符合中文阅读习惯
4. 保持学术严谨性

标题：{title}

摘要：{summary}

请输出翻译后的标题和摘要，格式如下：
【中文标题】
（翻译后的标题）

【中文摘要】
（翻译后的摘要）"""

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000
        )
        result = resp.choices[0].message.content
        
        # 解析翻译结果
        title_cn = title
        summary_cn = summary
        
        if "【中文标题】" in result and "【中文摘要】" in result:
            title_part = result.split("【中文标题】")[1].split("【中文摘要】")[0]
            summary_part = result.split("【中文摘要】")[1]
            title_cn = title_part.strip()
            summary_cn = summary_part.strip()
        
        return title_cn, summary_cn
    except Exception as e:
        print(f"翻译失败: {e}")
        return title, summary


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
            "max_results": 5,
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
            title_en = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
            summary_en = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
            authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)]
            link = entry.find('atom:id', ns).text
            
            papers.append({
                'title_en': title_en,
                'summary_en': summary_en,
                'authors': authors[:3],
                'url': link
            })
        except:
            continue
    
    print(f"解析 {len(papers)} 篇论文")
    
    if not papers:
        print("没有论文")
        return
    
    # 3. 翻译每篇论文
    for i, p in enumerate(papers):
        print(f"翻译第{i+1}篇: {p['title_en'][:50]}...")
        title_cn, summary_cn = translate_paper(p['title_en'], p['summary_en'])
        p['title_cn'] = title_cn
        p['summary_cn'] = summary_cn
    
    # 4. AI总结摘要
    summary_text = ""
    if DEEPSEEK_API_KEY:
        print("生成AI简报...")
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        
        text = "\n\n".join([
            f"论文{i+1}:\n英文标题: {p['title_en']}\n中文标题: {p['title_cn']}\n英文摘要: {p['summary_en'][:300]}\n中文摘要: {p['summary_cn'][:300]}"
            for i, p in enumerate(papers)
        ])
        
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": f"""请根据以下论文生成一份中英双语简报。

要求：
1. **今日概览**（中文，2-3句）
2. **重点推荐**（选出3篇最重要的，中文说明理由）
3. **每篇一句话总结**（中文）
4. **English Summary**（100词左右的英文总结，包括每篇一句英文简介）
5. 关键术语保留英文并加中文解释，如 LLM（大语言模型）

论文：
{text}"""}],
                temperature=0.7,
                max_tokens=4000
            )
            summary_text = resp.choices[0].message.content
            print("AI简报完成")
        except Exception as e:
            print(f"AI简报失败: {e}")
    
    # 5. 生成报告
    today = datetime.now().strftime('%Y-%m-%d')
    today_cn = datetime.now().strftime('%Y年%m月%d日')
    report = f"# 📄 AI论文速递 - {today_cn}\n\n"
    report += f"> 共 {len(papers)} 篇论文 | DeepSeek翻译+总结\n\n"
    
    if summary_text:
        report += summary_text + "\n\n---\n\n"
    
    report += "## 📚 论文详情（中英对照）\n\n"
    
    for i, p in enumerate(papers, 1):
        report += f"### {i}. {p['title_en']}\n\n"
        report += f"**中文标题**: {p['title_cn']}\n\n"
        report += f"**作者**: {', '.join(p['authors'])}\n\n"
        report += f"**英文摘要**: {p['summary_en'][:500]}...\n\n"
        report += f"**中文摘要**: {p['summary_cn']}\n\n"
        report += f"🔗 [查看原文]({p['url']})\n\n"
        report += "---\n\n"
    
    # 6. 保存
    os.makedirs('reports', exist_ok=True)
    filename = f"reports/{today}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"已保存: {filename}")
    
    # 7. 推送
    if PUSHPLUS_TOKEN:
        push_title = f"📄 AI论文速递 - {datetime.now().strftime('%m月%d日')}"
        push_content = (summary_text or "")[:4000]
        
        try:
            r = requests.post("http://www.pushplus.plus/send", json={
                "token": PUSHPLUS_TOKEN,
                "title": push_title,
                "content": push_content,
                "template": "markdown"
            }, timeout=10)
            if r.status_code == 200:
                print("推送成功")
        except Exception as e:
            print(f"推送异常: {e}")
    
    print("完成！")

if __name__ == "__main__":
    main()
