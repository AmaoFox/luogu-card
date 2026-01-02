import requests
from bs4 import BeautifulSoup
import re
import json
import time
import os
import datetime

# 配置
USER_ID = 513997
BASE_URL = "https://www.luogu.com.cn/user/{}/practice".format(USER_ID)
API_BASE = "https://api.jerryz.com.cn/practice"
FIXED_PARAMS = {
    "id": USER_ID,
    "custom": "true",
    "name": "AmaoFox",
    "color": "Red",
    "ccfLevel": 8,
    "tag": ""
}

# 数据缓存文件（用于限制频率）
CACHE_FILE = "data/last_update.json"
README_PATH = "README.md"  # 或 index.html，根据你用哪个
IMG_MARKER_START = "<!-- STAT_IMG_START -->"
IMG_MARKER_END = "<!-- STAT_IMG_END -->"
TIME_MARKER = "<!-- LAST_UPDATE:"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_page():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(BASE_URL, headers=headers)
    response.raise_for_status()
    return response.text

import re
import json

from bs4 import BeautifulSoup
import json

def parse_stats(html):
    soup = BeautifulSoup(html, "html.parser")
    
    # 找到指定的 script 标签
    script_tag = soup.find("script", {"id": "lentille-context", "type": "application/json"})
    
    if not script_tag:
        raise ValueError("未能找到 <script id=\"lentille-context\"> 标签，请检查页面是否加载完整或结构变化")
    
    if not script_tag.string:
        raise ValueError("lentille-context 标签内容为空")
    
    json_str = script_tag.string.strip()
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}")
    
    # 根据你描述：根下有 "data" 字段，里面有 "passed" 和 "submitted"
    root = data.get("data", data)  # 以防万一直接是根
    
    passed_problems = root.get("passed", [])
    submitted_problems = root.get("submitted", [])  # unpassed
    
    # passed 统计：难度 0~7 对应 8 个位置
    passed_counts = [0] * 8
    
    for prob in passed_problems:
        prob_type = prob.get("type", "")
        difficulty = prob.get("difficulty", -1)
        
        if prob_type in ("P", "B") and 0 <= difficulty <= 7:
            passed_counts[difficulty] += 1
    
    # unpassed 统计
    unpassed_count = 0
    for prob in submitted_problems:
        prob_type = prob.get("type", "")
        if prob_type in ("P", "B"):
            unpassed_count += 1
    
    return passed_counts, unpassed_count

def generate_img_url(passed, unpassed):
    params = FIXED_PARAMS.copy()
    params["passed"] = ",".join(map(str, passed))
    params["unpassed"] = unpassed
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{API_BASE}?{query}"

def update_readme(img_url):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not os.path.exists(README_PATH):
        content = f"# 我的洛谷做题统计\n\n{IMG_MARKER_START}\n![洛谷练习统计]({img_url})\n{IMG_MARKER_END}\n\n{TIME_MARKER} {current_time} -->"
    else:
        with open(README_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 替换图片
        import re
        new_img_md = f"![洛谷练习统计]({img_url})"
        if IMG_MARKER_START in content and IMG_MARKER_END in content:
            content = re.sub(
                re.escape(IMG_MARKER_START) + ".*?" + re.escape(IMG_MARKER_END),
                f"{IMG_MARKER_START}\n{new_img_md}\n{IMG_MARKER_END}",
                content,
                flags=re.DOTALL
            )
        else:
            content += f"\n\n{IMG_MARKER_START}\n{new_img_md}\n{IMG_MARKER_END}"
        
        # 替换时间
        if TIME_MARKER in content:
            content = re.sub(
                re.escape(TIME_MARKER) + ".*?-->",
                f"{TIME_MARKER} {current_time} -->",
                content
            )
        else:
            content += f"\n\n{TIME_MARKER} {current_time} -->"
    
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    cache = load_cache()
    last_time = cache.get("last_update_time", 0)
    current_time = time.time()
    
    # 限制至少1小时一次
    if current_time - last_time < 3600:
        print("距离上次更新不到1小时，跳过。")
        return
    
    print("正在爬取页面...")
    html = fetch_page()
    debug_file = "debug_page.html"
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(html)
    passed, unpassed = parse_stats(html)
    img_url = generate_img_url(passed, unpassed)
    
    print(f"Passed: {passed}")
    print(f"Unpassed: {unpassed}")
    print(f"生成图片URL: {img_url}")
    
    update_readme(img_url)
    
    # 更新缓存
    cache["last_update_time"] = current_time
    cache["passed"] = passed
    cache["unpassed"] = unpassed
    save_cache(cache)
    
    print("更新完成！")

if __name__ == "__main__":
    main()