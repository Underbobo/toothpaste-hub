#!/usr/bin/env python3
"""
牙膏资讯采集脚本
数据来源：国家药监局、市场监管总局、行业媒体、新闻聚合
"""
import asyncio
import aiohttp
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


async def fetch(session, url, timeout=20):
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=timeout), ssl=False) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception as e:
        print(f"[ERROR] {url}: {e}")
    return None


def calc_score(item):
    score = 50.0
    if item.get("category") == "regulation":
        score += 30
    elif item.get("category") == "recall":
        score += 20
    elif item.get("category") == "announcement":
        score += 15
    t = item.get("time", "")
    try:
        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        days_old = (datetime.now(timezone.utc) - dt).days
        score += max(0, 10 - days_old * 0.3)
    except:
        pass
    title = item.get("title", "")
    hot_keywords = ["牙膏监督管理办法", "新规", "牙膏管理办法", "功效宣称", "备案", "禁售", "召回", "不合格", "国家标准"]
    for kw in hot_keywords:
        if kw in title:
            score += 5
    return round(min(score, 100), 1)


async def scrape_nmpa(session):
    """国家药监局化妆品公告"""
    items = []
    try:
        url = "https://www.nmpa.gov.cn/xxgk/chpzhh/cosmetics/"
        html = await fetch(session, url, timeout=15)
        if html:
            # 提取化妆品相关公告链接
            links = re.findall(r'href="(/xxgk/[^"]*cosmetic[^"]*)"[^>]*>([^<]{10,120})</a>', html, re.I)
            for path, title in links[:8]:
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                if "牙膏" in title_clean or "口腔" in title_clean:
                    items.append({
                        "title": title_clean,
                        "url": f"https://www.nmpa.gov.cn{path}",
                        "source": "国家药监局",
                        "category": "announcement",
                        "time": datetime.now(timezone.utc).isoformat(),
                    })
    except Exception as e:
        print(f"[NMPA ERROR] {e}")
    print(f"[国家药监局] 采集 {len(items)} 条")
    return items


async def scrape_samr(session):
    """市场监管总局法规"""
    items = []
    try:
        url = "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/"
        html = await fetch(session, url, timeout=15)
        if html:
            links = re.findall(r'href="(/zw/[^"]*\.html)"[^>]*>([^<]{10,120})</a>', html)
            for path, title in links[:8]:
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                if "牙膏" in title_clean or "化妆品" in title_clean:
                    items.append({
                        "title": title_clean,
                        "url": f"https://www.samr.gov.cn{path}",
                        "source": "市场监管总局",
                        "category": "regulation",
                        "time": datetime.now(timezone.utc).isoformat(),
                    })
    except Exception as e:
        print(f"[SAMR ERROR] {e}")
    print(f"[市场监管总局] 采集 {len(items)} 条")
    return items


async def scrape_bing_news(session):
    """必应新闻搜索牙膏相关"""
    items = []
    try:
        queries = ["牙膏新规", "牙膏管理办法", "牙膏监督", "牙膏召回"]
        for q in queries:
            url = f"https://www.bing.com/news/search?q={quote(q)}&form=PTNR"
            html = await fetch(session, url, timeout=15)
            if html:
                cards = re.findall(r'<a[^>]*class="title"[^>]*href="([^"]*)"[^>]*>([^<]{10,200})</a>', html)
                for link, title in cards[:5]:
                    title_clean = re.sub(r'<[^>]+>', '', title).strip()
                    if len(title_clean) < 10:
                        continue
                    cat = "industry"
                    if "召回" in title_clean or "不合格" in title_clean:
                        cat = "recall"
                    elif "办法" in title_clean or "规定" in title_clean or "规范" in title_clean:
                        cat = "regulation"
                    elif "公告" in title_clean or "通报" in title_clean:
                        cat = "announcement"
                    items.append({
                        "title": title_clean,
                        "url": link if link.startswith("http") else f"https://www.bing.com{link}",
                        "source": "新闻聚合",
                        "category": cat,
                        "time": datetime.now(timezone.utc).isoformat(),
                    })
            await asyncio.sleep(1)
    except Exception as e:
        print(f"[Bing ERROR] {e}")
    print(f"[必应新闻] 采集 {len(items)} 条")
    return items


async def scrape_gov_zhengce(session):
    """中国政府网政策文件"""
    items = []
    try:
        url = "https://www.gov.cn/zhengce/zhengceku/search.htm?q=牙膏"
        html = await fetch(session, url, timeout=15)
        if html:
            links = re.findall(r'href="(/zhengce/zhengceku/[^"]*)"[^>]*>([^<]{10,120})</a>', html)
            for path, title in links[:6]:
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                items.append({
                    "title": title_clean,
                    "url": f"https://www.gov.cn{path}",
                    "source": "中国政府网",
                    "category": "regulation",
                    "time": datetime.now(timezone.utc).isoformat(),
                })
    except Exception as e:
        print(f"[Gov ERROR] {e}")
    print(f"[中国政府网] 采集 {len(items)} 条")
    return items


async def main():
    print("=" * 50)
    print("  牙膏资讯采集器")
    print("=" * 50)

    async with aiohttp.ClientSession() as session:
        tasks = [
            scrape_nmpa(session),
            scrape_samr(session),
            scrape_bing_news(session),
            scrape_gov_zhengce(session),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items = []
    for r in results:
        if isinstance(r, list):
            all_items.extend(r)

    # 去重
    seen = set()
    unique = []
    for item in all_items:
        key = item["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # 打分排序
    for item in unique:
        item["score"] = calc_score(item)
    unique.sort(key=lambda x: x["score"], reverse=True)

    # 排名
    for i, item in enumerate(unique):
        item["rank"] = i + 1

    print(f"\n[汇总] 去重后 {len(unique)} 条资讯")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(unique[:50], f, ensure_ascii=False, indent=2)

    print("[完成] data.json 已更新")


if __name__ == "__main__":
    asyncio.run(main())
