import urllib.request
import json
import ssl
import re
import time
import os
from typing import List, Dict, Any

# 忽略 SSL 证书校验，防止部分采集站证书过期导致请求中断
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 采集站配置
SOURCES = [
    {
        'name': '暴风资源',
        'api': 'https://bfzyapi.com/api.php/provide/vod/',
        'prefer_flag': 'bfzym3u8',
    },
    {
        'name': '量子资源',
        'api': 'http://cj.lziapi.com/api.php/provide/vod/',
        'prefer_flag': 'lzm3u8',
    }
]

def fetch_json(url: str, timeout: int = 15) -> Dict[str, Any]:
    """安全请求 JSON 接口"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            return json.loads(content)
    except Exception as e:
        print(f"[WARN] 请求失败 {url}: {e}")
        return {}

def parse_play_urls(vod_play_from: str, vod_play_url: str, prefer_flag: str = '') -> List[Dict[str, str]]:
    """
    解析 MacCMS 的播放地址字符串:
    从多个播放源 (以 $$$ 分隔) 中挑选出最优 m3u8 源，然后解析出每一集的名称和链接
    """
    if not vod_play_url:
        return []

    from_list = vod_play_from.split('$$$') if vod_play_from else []
    url_groups = vod_play_url.split('$$$')

    chosen_group = url_groups[0]
    # 优先挑选含有 prefer_flag 或 m3u8 的播放组
    for i, f in enumerate(from_list):
        if i < len(url_groups):
            if (prefer_flag and prefer_flag in f) or ('m3u8' in f.lower()):
                chosen_group = url_groups[i]
                break

    episodes = []
    # 剧集之间以 # 分割
    parts = chosen_group.split('#')
    for part in parts:
        if '$' in part:
            ep_name, ep_url = part.split('$', 1)
        else:
            ep_name = '全集/正片'
            ep_url = part

        ep_name = ep_name.strip()
        ep_url = ep_url.strip()

        # 确保播放地址是有效的 m3u8 或 mp4 直链
        if ep_url.startswith('http') and ('.m3u8' in ep_url or '.mp4' in ep_url or 'share' in ep_url or 'video' in ep_url):
            episodes.append({'name': ep_name, 'url': ep_url})

    return episodes

def classify_vod(type_name: str) -> str:
    """对原始分类进行归一化归类，在 ntplayer 里按大类精美展示"""
    t = type_name or ''
    if any(k in t for k in ['动作', '喜剧', '爱情', '科幻', '恐怖', '剧情', '战争', '悬疑', '犯罪', '电影']):
        return '🎬 热门电影'
    elif any(k in t for k in ['国产', '内地', '华语']):
        return '📺 国产热播剧'
    elif any(k in t for k in ['欧美', '美剧', '英剧']):
        return '🌍 欧美剧场'
    elif any(k in t for k in ['日剧', '韩剧', '泰剧', '海外']):
        return '🌏 日韩泰剧'
    elif any(k in t for k in ['港剧', '台剧']):
        return '🇭🇰 港台经典'
    elif any(k in t for k in ['动漫', '动画', '国漫', '日漫']):
        return '🎨 热门动漫'
    elif any(k in t for k in ['短剧', '微短剧', '女频', '男频', '爽剧']):
        return '⚡ 热门短剧'
    elif any(k in t for k in ['综艺']):
        return '🎤 精彩综艺'
    elif any(k in t for k in ['纪录']):
        return '📚 纪录大片'
    elif any(k in t for k in ['体育', '足球', '篮球']):
        return '⚽ 体育赛事'
    return '✨ 综合精选'

def collect_from_source(source_conf: Dict[str, str], max_pages: int = 5, hours: int = 48) -> List[Dict[str, Any]]:
    """从单个源采集数据，默认采集最近 48 小时有更新的内容"""
    base_api = source_conf['api']
    prefer_flag = source_conf.get('prefer_flag', '')
    collected = []
    
    print(f"[*] 开始采集 [{source_conf['name']}] (最近 {hours} 小时更新)...")
    for pg in range(1, max_pages + 1):
        url = f"{base_api}?ac=videolist&h={hours}&pg={pg}&pagesize=50"
        data = fetch_json(url)
        vod_list = data.get('list', [])
        if not vod_list:
            break

        print(f"  - 第 {pg} 页: 获取到 {len(vod_list)} 条记录")
        for vod in vod_list:
            name = vod.get('vod_name', '').strip()
            pic = vod.get('vod_pic', '').strip()
            type_name = vod.get('type_name', '').strip()
            vod_play_from = vod.get('vod_play_from', '')
            vod_play_url = vod.get('vod_play_url', '')

            if not name or not vod_play_url:
                continue

            episodes = parse_play_urls(vod_play_from, vod_play_url, prefer_flag)
            if not episodes:
                continue

            collected.append({
                'name': name,
                'pic': pic,
                'category': classify_vod(type_name),
                'raw_type': type_name,
                'episodes': episodes,
                'source': source_conf['name']
            })

        time.sleep(0.5)

    print(f"[+] [{source_conf['name']}] 采集完成，共抓取有效影视 {len(collected)} 部")
    return collected

def generate_m3u(vod_items: List[Dict[str, Any]], output_path: str):
    """
    将影视列表生成为 ntplayer 深度优化的 M3U 订阅文件
    """
    lines = ['#EXTM3U']
    
    for item in vod_items:
        name = item['name']
        pic = item['pic']
        cat = item['category']
        episodes = item['episodes']

        # 如果只有 1 集（如电影），直接归入电影分类
        if len(episodes) == 1:
            ep = episodes[0]
            display_title = name if '正片' in ep['name'] or '全集' in ep['name'] else f"{name} {ep['name']}"
            lines.append(f'#EXTINF:-1 tvg-logo="{pic}" group-title="{cat}",{display_title}')
            lines.append(ep['url'])
        else:
            # 多集影视（电视剧、短剧、动漫）：
            # 分组名写成 "电视剧·狂飙" 或 "分类 - 片名"，使 ntPlayer 列表中清晰归纳每一集
            group_name = f"{cat} · {name}"
            for ep in episodes:
                lines.append(f'#EXTINF:-1 tvg-logo="{pic}" group-title="{group_name}",{name} {ep["name"]}')
                lines.append(ep['url'])

    content = '\n'.join(lines) + '\n'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] 已成功生成 ntPlayer 订阅文件: {output_path} (包含 {len(lines)//2} 个播放条目)")

def main():
    all_vods = []
    seen_names = set()

    for src in SOURCES:
        try:
            items = collect_from_source(src, max_pages=3, hours=48)
            for it in items:
                # 简单去重，先抓到的优质源优先保留
                if it['name'] not in seen_names:
                    seen_names.add(it['name'])
                    all_vods.append(it)
        except Exception as e:
            print(f"[ERR] 采集 {src['name']} 出错: {e}")

    print(f"\n[+] 聚合去重后总片源数: {len(all_vods)} 部")
    
    # 生成完整版订阅
    generate_m3u(all_vods, 'vod.m3u')

    # 生成轻量版（前 100 部热门，适合手机端秒级加载）
    lite_vods = all_vods[:100]
    generate_m3u(lite_vods, 'vod_lite.m3u')

if __name__ == '__main__':
    main()
