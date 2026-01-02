import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os
import datetime
import math

# 配置
USER_ID = 513997
BASE_URL = "https://www.luogu.com.cn/user/{}/practice".format(USER_ID)
PROBLEM_LIST_BASE = "https://www.luogu.com.cn/problem/list?type=luogu&difficulty="
API_BASE = "https://api.jerryz.com.cn/practice"

# 个人统计图片参数
PERSONAL_PARAMS = {
    "id": USER_ID,
    "custom": "true",
    "name": "AmaoFox",
    "color": "Red",
    "ccfLevel": 8,
    "tag": ""
}

# 制霸图片参数（全局总题数作为 passed，unpassed=0）
DOMINATION_PARAMS = {
    "id": 1,
    "custom": "true",
    "name": "制霸",
    "color": "Purple",
    "ccfLevel": 8,
    "tag": "制霸",
    "unpassed": 0
}

# 数据缓存文件
CACHE_FILE = os.path.join("data", "last_update.json")
README_PATH = "README.md"

# Markdown 标记
PERSONAL_MARKER_START = "<!-- PERSONAL_IMG_START -->"
PERSONAL_MARKER_END = "<!-- PERSONAL_IMG_END -->"
DOMINATION_MARKER_START = "<!-- DOMINATION_IMG_START -->"
DOMINATION_MARKER_END = "<!-- DOMINATION_IMG_END -->"
PROGRESS_MARKER_START = "<!-- PROGRESS_BADGE_START -->"
PROGRESS_MARKER_END = "<!-- PROGRESS_BADGE_END -->"
TIME_MARKER = "<!-- LAST_UPDATE:"

def load_cache():
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except json.JSONDecodeError:
            print("缓存文件损坏，已重置。")
            return {}
    return {}

def save_cache(data):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_page(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text

def parse_personal_stats(html):
    soup = BeautifulSoup(html, "html.parser")
    script_tag = soup.find("script", {"id": "lentille-context", "type": "application/json"})
    
    if not script_tag or not script_tag.string:
        raise ValueError("未能找到个人练习页面的 lentille-context JSON")
    
    data = json.loads(script_tag.string.strip())
    root = data.get("data", data)
    
    passed_problems = root.get("passed", [])
    submitted_problems = root.get("submitted", [])  # unpassed
    
    passed_counts = [0] * 8
    for prob in passed_problems:
        prob_type = prob.get("type", "")
        difficulty = prob.get("difficulty", -1)
        if prob_type in ("P", "B") and 0 <= difficulty <= 7:
            passed_counts[difficulty] += 1
    
    unpassed_count = sum(1 for prob in submitted_problems if prob.get("type", "") in ("P", "B"))
    
    return passed_counts, unpassed_count

def fetch_total_counts():
    total_counts = [0] * 8
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for diff in range(8):
        url = PROBLEM_LIST_BASE + str(diff)
        print(f"爬取难度 {diff} 总题数...")
        html = fetch_page(url)
        soup = BeautifulSoup(html, "html.parser")
        script_tag = soup.find("script", {"id": "lentille-context", "type": "application/json"})
        
        if not script_tag or not script_tag.string:
            print(f"警告：难度 {diff} 未找到 lentille-context，使用缓存或 0")
            continue
        
        try:
            data = json.loads(script_tag.string.strip())
            root = data.get("data", data)
            count = root.get("problems", {}).get("count", 0)
            total_counts[diff] = count
        except json.JSONDecodeError:
            print(f"难度 {diff} JSON 解析失败")
    
    return total_counts

def generate_img_url(params, passed=None, unpassed=None):
    p = params.copy()
    if passed is not None:
        p["passed"] = ",".join(map(str, passed))
    if unpassed is not None:
        p["unpassed"] = unpassed
    query = "&".join(f"{k}={v}" for k, v in p.items())
    return f"{API_BASE}?{query}"

def generate_progress_badge(percentage):
    # 使用 shields.io 生成徽章
    label = "加权制霸进度"
    message = f"{percentage:.10f}%".replace("%", "%25")
    color = "brightgreen" if percentage >= 5 else "red"
    style = "for-the-badge"
    return f"https://img.shields.io/badge/{label}-{message}-{color}?style={style}"

def update_readme(personal_url, domination_url, progress_url):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 三张图片的本地文件名
    personal_file = "personal-stats.svg"
    domination_file = "domination-progress.svg"
    progress_file = "weighted-progress.svg"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # 下载并保存三张图片
    def download_image(url, filename):
        try:
            print(f"正在下载图片: {filename}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"保存成功: {filename}")
        except Exception as e:
            print(f"下载 {filename} 失败: {e}（跳过保存本地文件）")
    
    download_image(personal_url, personal_file)
    download_image(domination_url, domination_file)
    download_image(progress_url, progress_file)
    
    # README 中使用本地图片的 Markdown（GitHub 会直接渲染）
    personal_md = f"![我的练习统计]({personal_file})"
    domination_md = f"![洛谷制霸进度]({domination_file})"
    progress_md = f"![加权制霸进度]({progress_file})"
    
    if not os.path.exists(README_PATH):
        content = "# AmaoFox 的洛谷之旅\n\n"
    else:
        with open(README_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    
    # 更新个人图
    if PERSONAL_MARKER_START in content:
        content = re.sub(
            re.escape(PERSONAL_MARKER_START) + r".*?" + re.escape(PERSONAL_MARKER_END),
            f"{PERSONAL_MARKER_START}\n{personal_md}\n{PERSONAL_MARKER_END}",
            content, flags=re.DOTALL
        )
    else:
        content += f"\n\n{PERSONAL_MARKER_START}\n{personal_md}\n{PERSONAL_MARKER_END}"
    
    # 更新制霸图
    if DOMINATION_MARKER_START in content:
        content = re.sub(
            re.escape(DOMINATION_MARKER_START) + r".*?" + re.escape(DOMINATION_MARKER_END),
            f"{DOMINATION_MARKER_START}\n{domination_md}\n{DOMINATION_MARKER_END}",
            content, flags=re.DOTALL
        )
    else:
        content += f"\n\n{DOMINATION_MARKER_START}\n{domination_md}\n{DOMINATION_MARKER_END}"
    
    # 更新进度徽章（shields.io 本身就是图片，所以也保存了）
    if PROGRESS_MARKER_START in content:
        content = re.sub(
            re.escape(PROGRESS_MARKER_START) + r".*?" + re.escape(PROGRESS_MARKER_END),
            f"{PROGRESS_MARKER_START}\n{progress_md}\n{PROGRESS_MARKER_END}",
            content, flags=re.DOTALL
        )
    else:
        content += f"\n\n{PROGRESS_MARKER_START}\n{progress_md}\n{PROGRESS_MARKER_END}"
    
    # 更新时间
    if TIME_MARKER in content:
        content = re.sub(
            re.escape(TIME_MARKER) + r".*?-->",
            f"{TIME_MARKER} {current_time} -->",
            content
        )
    else:
        content += f"\n\n{TIME_MARKER} {current_time} -->"
    
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("README.md 和三张本地图片已更新！")

def main():
    cache = load_cache()
    last_time = cache.get("last_update_time", 0)
    current_time = time.time()
    
    # 个人统计限制：1小时一次
    if current_time - last_time < 3500:
        print("距离上次个人统计更新不到1小时，跳过个人部分。")
    else:
        print("正在爬取个人练习数据...")
        html = fetch_page(BASE_URL)
        passed, unpassed = parse_personal_stats(html)
        personal_img_url = generate_img_url(PERSONAL_PARAMS, passed, unpassed)
        print(f"个人 Passed: {passed}")
        print(f"个人 Unpassed: {unpassed}")
        print(f"个人图片: {personal_img_url}")
        
        cache["last_update_time"] = current_time
        cache["personal_passed"] = passed
        cache["personal_unpassed"] = unpassed
        
    passed = cache.get("personal_passed", [0]*8)
    unpassed = cache.get("personal_unpassed", 0)
    personal_img_url = generate_img_url(PERSONAL_PARAMS, passed, unpassed)
    
    # 制霸总题数：每天更新一次
    total_last_time = cache.get("total_last_time", 0)
    if current_time - total_last_time > 86300:
        total_counts = fetch_total_counts()
        if sum(total_counts) == 0:
            print("所有难度总题数获取失败，使用缓存")
            total_counts = cache.get("total_counts", [0]*8)
        else:
            cache["total_counts"] = total_counts
            cache["total_last_time"] = current_time
    else:
        total_counts = cache.get("total_counts", [0]*8)
        print("使用缓存的制霸总题数")
    
    domination_img_url = generate_img_url(DOMINATION_PARAMS, total_counts)
    print(f"制霸总题数: {total_counts}")
    print(f"制霸图片: {domination_img_url}")
    
    # 加权制霸进度计算
    weights = [10 if i == 0 else i**2 for i in range(8)]  # [10,1,4,9,16,25,36,49]
    weighted = 0.0
    for i in range(8):
        if total_counts[i] > 0:
            weighted += (passed[i] / total_counts[i]) * weights[i]
    percentage = weighted / 150 * 100
    progress_url = generate_progress_badge(percentage)
    print(f"加权制霸进度: {percentage:.10f}%")
    
    # 更新 README
    update_readme(personal_img_url, domination_img_url, progress_url)
    save_cache(cache)
    print("所有更新完成！")

if __name__ == "__main__":
    main()
