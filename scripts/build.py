#!/usr/bin/env python3
"""Data-driven build for wayref.github.io.

Fetches live data from the 5 source repos and regenerates all 6 pages.
Runs in GitHub Actions (scripts/build.py) and locally for testing.
Stdlib only. Usage: python3 build.py [output_dir]
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
RAW = "https://raw.githubusercontent.com/wayref/{repo}/main/{path}"
GH = "https://github.com/wayref/{repo}"
API = "https://api.github.com/repos/wayref/{repo}/contents/{path}"

TODAY = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "showcase-sync"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def fetch_json(url):
    return json.loads(fetch(url))


def raw_url(repo, path):
    from urllib.parse import quote
    return RAW.format(repo=repo, path=quote(path))


def count_yaml_items(text):
    """Count YAML list entries (lines starting with optional indent + '- ')."""
    return sum(1 for ln in text.splitlines() if re.match(r"^\s*- ", ln))


def count_section_items(text, start_key, end_keys):
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith(start_key))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if any(lines[i].startswith(k) for k in end_keys):
            end = i
            break
    return sum(1 for ln in lines[start:end] if ln.startswith("- "))


def count_dns_forwards(text):
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("dns:"))
    end = next(i for i, ln in enumerate(lines) if ln.startswith("real_ip_domains:"))
    return sum(1 for ln in lines[start:end] if ln.strip().startswith("- proxy_rule_set:"))


def strip_quotes(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse_yaml_name_desc(text):
    name = desc = ""
    for ln in text.splitlines():
        if ln.startswith("name:") and not name:
            name = strip_quotes(ln.split(":", 1)[1])
        elif ln.startswith("description:") and not desc:
            desc = strip_quotes(ln.split(":", 1)[1])
        if name and desc:
            break
    return name, desc


def parse_sgmodule_desc(text):
    for ln in text.splitlines():
        if ln.startswith("#!desc="):
            return ln[len("#!desc="):].strip()
    return ""


# ---------- fetch live data ----------
print("fetching live data...")

config_yaml = fetch(raw_url("Egern-Config", "懒人配置.yaml"))
config = {
    "rules": count_section_items(config_yaml, "rules:", ["modules:"]),
    "dns": count_dns_forwards(config_yaml),
    "modules": count_section_items(config_yaml, "modules:", []),
}
print("config:", config)

RULE_FILES = [
    ("Apple.yaml", "Apple 全家桶", "Apple.yaml"),
    ("China.yaml", "国内域名", "Repcz/China.yaml"),
    ("Meta.yaml", "Meta 全家桶", "Meta.yaml"),
    ("Emby.yaml", "Emby 相关", "Emby.yaml"),
    ("AI.yaml", "AI 服务", "hin0ka/AI.yaml"),
    ("国外网盘.yaml", "网盘服务", "国外网盘.yaml"),
]
rules = []
for fname, label, path in RULE_FILES:
    text = fetch(raw_url("Egern-Rule-Set", path))
    rules.append({"file": fname, "label": label, "path": path,
                  "count": count_yaml_items(text)})
print("rules:", [(r["file"], r["count"]) for r in rules])

FOREIGN_RULE_FILES = [
    ("Netflix.yaml", "奈飞", "Repcz/Netflix.yaml"),
    ("Disney.yaml", "迪士尼", "Repcz/Disney.yaml"),
    ("Spotify.yaml", "音乐", "Repcz/Spotify.yaml"),
    ("YouTube.yaml", "视频", "Repcz/YouTube.yaml"),
    ("HBO.yaml", "流媒体", "Repcz/HBO.yaml"),
    ("PrimeVideo.yaml", "流媒体", "Repcz/PrimeVideo.yaml"),
    ("Hulu.yaml", "流媒体", "Repcz/Hulu.yaml"),
    ("Amazon.yaml", "购物", "Repcz/Amazon.yaml"),
    ("Google.yaml", "搜索", "Repcz/Google.yaml"),
    ("Telegram.yaml", "聊天", "Repcz/Telegram.yaml"),
    ("Twitter.yaml", "社交", "Repcz/Twitter.yaml"),
    ("TikTok.yaml", "短视频", "Repcz/TikTok.yaml"),
]
foreign_rules = []
for fname, label, path in FOREIGN_RULE_FILES:
    text = fetch(raw_url("Egern-Rule-Set", path))
    foreign_rules.append({"file": fname, "label": label, "path": path,
                          "count": count_yaml_items(text)})
print("foreign rules:", [(r["file"], r["count"]) for r in foreign_rules])

icons_data = fetch_json(raw_url("Egern-Icons", "Egern-Icons.json"))
icons = icons_data["icons"]
print("icons:", len(icons))

WIDGET_ORDER = ["订阅流量", "我的天气", "今日油价", "岁时黄历", "时间倒计时",
                "IP检测", "网络诊断雷达", "流媒体解锁", "机场订阅"]
widgets = []
for entry in fetch_json(API.format(repo="Egern-Widgets", path="")):
    if entry["type"] == "file" and entry["name"].endswith(".yaml"):
        text = fetch(raw_url("Egern-Widgets", entry["name"]))
        name, desc = parse_yaml_name_desc(text)
        widgets.append({"name": name or entry["name"][:-5], "desc": desc,
                        "file": entry["name"]})
widgets.sort(key=lambda w: WIDGET_ORDER.index(w["name"])
             if w["name"] in WIDGET_ORDER else 99)
print("widgets:", [w["name"] for w in widgets])

modules = []
for entry in fetch_json(API.format(repo="Egern-Modules", path="")):
    if entry["type"] == "file" and entry["name"].endswith(".sgmodule"):
        text = fetch(raw_url("Egern-Modules", entry["name"]))
        modules.append({"name": entry["name"][:-len(".sgmodule")],
                        "desc": parse_sgmodule_desc(text),
                        "file": entry["name"]})
modules.sort(key=lambda m: m["name"])
print("modules:", [m["name"] for m in modules])

# ---------- templates (same design as approved) ----------
CSS = """
@property --beam-angle { syntax: '<angle>'; initial-value: 0deg; inherits: false; }
@keyframes beam-spin { to { --beam-angle: 360deg; } }
@keyframes sweep-btn { 0% { left: -60%; opacity: 0; } 10% { opacity: 1; } 60% { left: 130%; opacity: 1; } 75%, 100% { left: 130%; opacity: 0; } }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #04070D; color: #fff; font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif; }
a { text-decoration: none; }
.page { max-width: 560px; margin: 0 auto; padding: 18px 16px 20px; min-height: 100vh; background: radial-gradient(500px 180px at 50% -30px, rgba(10,132,255,.28), transparent 70%), linear-gradient(rgba(10,132,255,.03) 1px, transparent 1px), linear-gradient(90deg, rgba(10,132,255,.03) 1px, transparent 1px), #04070D; background-size: auto, 28px 28px, 28px 28px; }
.hero { text-align: center; }
.pill { display: inline-block; font-size: 11px; color: #64D2FF; border: 1px solid rgba(100,210,255,.4); background: rgba(10,132,255,.08); padding: 4px 12px; border-radius: 999px; }
h1 { font-size: 24px; font-weight: 800; margin-top: 12px; letter-spacing: 2px; background: linear-gradient(90deg, #fff 15%, #0A84FF 55%, #64D2FF); -webkit-background-clip: text; background-clip: text; color: transparent; text-shadow: 0 0 24px rgba(10,132,255,.35); }
.sub { color: #7C9CC4; font-size: 12px; margin-top: 7px; letter-spacing: 1px; }
.divider { width: 120px; height: 2px; margin: 10px auto 0; background: linear-gradient(90deg, transparent, #0A84FF, #64D2FF, transparent); border-radius: 2px; }
.cards { display: grid; gap: 12px; margin-top: 20px; }
.beam { --beam-angle: 0deg; border: 1.5px solid transparent; border-radius: 14px; background: linear-gradient(#0B1220,#0B1220) padding-box, conic-gradient(from var(--beam-angle), rgba(10,132,255,.12) 0%, #0A84FF 12%, #64D2FF 22%, rgba(10,132,255,.12) 38%, rgba(10,132,255,.12) 62%, #0A84FF 74%, #64D2FF 84%, rgba(10,132,255,.12) 100%) border-box; animation: beam-spin 4s linear infinite; }
.beam.d2 { animation-delay: -1s; } .beam.d3 { animation-delay: -2s; } .beam.d4 { animation-delay: -3s; } .beam.d5 { animation-delay: -2s; }
.card-inner { padding: 14px; }
.card-title { font-size: 17px; font-weight: 700; display: flex; align-items: center; justify-content: space-between; }
.card-repo { font-size: 12px; color: #7C9CC4; margin-top: 3px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.tag-rec { font-size: 11px; color: #0A84FF; border: 1px solid rgba(10,132,255,.5); background: rgba(10,132,255,.12); padding: 2px 8px; border-radius: 999px; }
.desc { color: #C7D8EC; font-size: 13px; margin-top: 10px; line-height: 1.5; }
.pills { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
.pills span { font-size: 11px; background: rgba(10,132,255,.12); border: 1px solid rgba(10,132,255,.3); color: #9CC8FF; padding: 3px 9px; border-radius: 999px; }
.actions { margin-top: 12px; display: flex; gap: 8px; }
.btn-sweep { position: relative; overflow: hidden; display: inline-block; padding: 6px 14px; font-size: 12px; border-radius: 8px; border: 1px solid rgba(10,132,255,.55); background: rgba(10,132,255,.14); color: #EAF4FF; text-align: center; cursor: pointer; }
.btn-sweep::after { content: ''; position: absolute; top: 0; bottom: 0; width: 36px; background: linear-gradient(105deg, transparent, rgba(100,210,255,.30) 50%, transparent); transform: skewX(-18deg); animation: sweep-btn 4s ease-in-out infinite; pointer-events: none; }
.beam-btn { --beam-angle: 0deg; display: inline-block; border: 1.5px solid transparent; border-radius: 8px; background: linear-gradient(#0B1220,#0B1220) padding-box, conic-gradient(from var(--beam-angle), rgba(10,132,255,.15) 0%, #0A84FF 15%, #64D2FF 28%, rgba(10,132,255,.15) 45%, rgba(10,132,255,.15) 65%, #0A84FF 78%, #64D2FF 90%, rgba(10,132,255,.15) 100%) border-box; animation: beam-spin 4s linear infinite; animation-delay: -2s; padding: 6px 14px; font-size: 12px; color: #9CC8FF; }
.copy-btn { --beam-angle: 0deg; display: block; width: 100%; margin-top: 12px; text-align: center; border: 1.5px solid transparent; border-radius: 8px; background: linear-gradient(rgba(10,132,255,.20),rgba(10,132,255,.12)) padding-box, conic-gradient(from var(--beam-angle), rgba(10,132,255,.15) 0%, #0A84FF 15%, #64D2FF 28%, rgba(10,132,255,.15) 45%, rgba(10,132,255,.15) 65%, #0A84FF 78%, #64D2FF 90%, rgba(10,132,255,.15) 100%) border-box; animation: beam-spin 4s linear infinite; animation-delay: -1s; padding: 8px 14px; font-size: 13px; color: #EAF4FF; cursor: pointer; }
.back { display: inline-block; font-size: 12px; color: #9CC8FF; margin-bottom: 14px; }
.sec-title { font-size: 15px; font-weight: 700; margin: 18px 0 8px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 11px 2px; border-bottom: 1px solid rgba(10,132,255,.12); }
.row:last-child { border-bottom: none; }
.row-name { font-size: 14px; font-weight: 600; }
.row-sub { font-size: 12px; color: #7C9CC4; margin-top: 2px; line-height: 1.5; }
.copy-mini { font-size: 12px; color: #EAF4FF; border: 1px solid rgba(10,132,255,.55); background: rgba(10,132,255,.14); border-radius: 8px; padding: 5px 10px; white-space: nowrap; cursor: pointer; }
.steps { margin-top: 8px; display: grid; gap: 8px; }
.step { display: flex; gap: 10px; font-size: 13px; color: #C7D8EC; line-height: 1.5; }
.step b { color: #0A84FF; flex-shrink: 0; }
.note { margin-top: 14px; font-size: 12px; color: #7C9CC4; line-height: 1.6; }
.icon-grid { margin-top: 10px; display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }
.icon-grid img { width: 100%; border-radius: 10px; display: block; }
.icon-grid .cap { font-size: 10px; color: #7C9CC4; text-align: center; margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.footer { color: #5B7A9E; font-size: 11px; margin-top: 20px; text-align: center; letter-spacing: 1px; }
"""

JS = """
<script>
function copyText(t, el) {
  function done() { if (el) { var o = el.textContent; el.textContent = '已复制'; setTimeout(function(){ el.textContent = o; }, 1500); } }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(t).then(done, function(){ fallback(); });
  } else { fallback(); }
  function fallback() {
    var ta = document.createElement('textarea');
    ta.value = t; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); done(); } catch(e) {}
    document.body.removeChild(ta);
  }
}
</script>
"""

FOOTER = f'<div class="footer">最后更新 {TODAY} · 每天自动同步</div>'


def page(title, body):
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"<title>{title}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
            f"<div class=\"page\">\n{body}\n{FOOTER}\n</div>\n{JS}\n</body>\n</html>\n")


def gh_url(repo):
    return GH.format(repo=repo)


def write(rel, html):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", rel, len(html), "bytes")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def detail_head(name, repo, desc):
    return (f"<a class=\"back\" href=\"../\">← 返回总站</a>"
            f"<div class=\"card-title\" style=\"font-size:19px;\"><span>{esc(name)}</span></div>"
            f"<div class=\"card-repo\">{repo}</div>"
            f"<div class=\"desc\">{esc(desc)}</div>")


def copy_block(label, url):
    return f"<div class=\"copy-btn\" onclick=\"copyText('{url}', this)\">{label}</div>"


def fmt(n):
    return f"{n:,}"


# ---------- hub ----------
CONFIG_SUB = "https://raw.githubusercontent.com/wayref/Egern-Config/main/懒人配置.yaml"
rule_pills = "".join(
    f"<span>{r['file'].replace('.yaml', '')} {fmt(r['count'])}</span>"
    for r in rules[:4])
hub_cards = [
    ("懒人配置", "Egern-Config", "开箱即用，自己填机场链接就行",
     [f"{config['rules']} 条规则", f"{config['dns']} 条 DNS 转发", f"{config['modules']} 个模块"],
     True, "beam"),
    ("规则", "Egern-Rule-Set", "域名规则集，配置里引用的规则都在这，每天自动同步",
     None, False, "beam d2"),
    ("图标", "Egern-Icons", "108×108 圆角方块图标",
     [f"{fmt(len(icons))} 个图标"], False, "beam d3"),
    ("小组件", "Egern-Widgets", "桌面小组件，纯黑风格，订阅流量、天气、油价、黄历都在这",
     [f"{len(widgets)} 个小组件"], False, "beam d4"),
    ("模块", "Egern-Modules", "Egern 功能模块",
     [f"{len(modules)} 个模块"], False, "beam d5"),
]
cards_html = []
for name, repo, desc, pills, featured, cls in hub_cards:
    tag = '<span class="tag-rec">推荐</span>' if featured else ""
    pills_html = rule_pills if pills is None else "".join(f"<span>{p}</span>" for p in pills)
    copy_html = (f"<div class=\"copy-btn\" onclick=\"copyText('{CONFIG_SUB}', this)\">复制订阅链接</div>"
                 if featured else "")
    cards_html.append(
        f"<div class=\"{cls}\"><div class=\"card-inner\">"
        f"<div class=\"card-title\"><span>{name}</span>{tag}</div>"
        f"<div class=\"card-repo\">{repo}</div>"
        f"<div class=\"desc\">{desc}</div>"
        f"<div class=\"pills\">{pills_html}</div>"
        f"{copy_html}"
        f"<div class=\"actions\"><a class=\"btn-sweep\" href=\"{repo}/\">查看详情</a>"
        f"<a class=\"beam-btn\" href=\"{gh_url(repo)}\">GitHub 仓库</a></div>"
        f"</div></div>"
    )
hub_body = (
    "<div class=\"hero\">"
    f"<div class=\"pill\">5 个仓库 · 最后更新 {TODAY}</div>"
    "<h1>Egern 仓库</h1>"
    "<div class=\"sub\">EGERN 配置 · 规则 · 图标 · 小组件 · 模块</div>"
    "<div class=\"divider\"></div>"
    "</div>"
    "<div class=\"cards\">" + "".join(cards_html) + "</div>"
)
write("index.html", page("Egern 仓库", hub_body))

# ---------- Egern-Config ----------
cfg_body = (
    detail_head("懒人配置", "Egern-Config", "开箱即用，自己填机场链接就行")
    + copy_block("复制订阅链接", CONFIG_SUB)
    + "<div class=\"sec-title\">使用方法</div><div class=\"steps\">"
    "<div class=\"step\"><b>1</b><span>复制上面的订阅链接</span></div>"
    "<div class=\"step\"><b>2</b><span>在 Egern 里添加订阅，粘贴链接</span></div>"
    "<div class=\"step\"><b>3</b><span>填入自己的机场订阅链接，就能用了</span></div>"
    "</div>"
    "<div class=\"sec-title\">包含内容</div>"
    f"<div class=\"row\"><div><div class=\"row-name\">{config['rules']} 条规则</div>"
    "<div class=\"row-sub\">国内直连、国外分流，覆盖常用服务</div></div></div>"
    f"<div class=\"row\"><div><div class=\"row-name\">{config['dns']} 条 DNS 转发</div>"
    "<div class=\"row-sub\">国内外分流解析，加密 DoH</div></div></div>"
    f"<div class=\"row\"><div><div class=\"row-name\">{config['modules']} 个模块</div>"
    "<div class=\"row-sub\">BoxJS、Sub-Store、Script-Hub</div></div></div>"
    f"<div style=\"margin-top:14px;\"><a class=\"beam-btn\" href=\"{gh_url('Egern-Config')}\">GitHub 仓库</a></div>"
)
write("Egern-Config/index.html", page("懒人配置 · Egern 仓库", cfg_body))

# ---------- Egern-Rule-Set ----------
def rule_rows(rs):
    out = []
    for r in rs:
        url = raw_url("Egern-Rule-Set", r["path"])
        out.append(
            f"<div class=\"row\"><div><div class=\"row-name\">{esc(r['file'])}</div>"
            f"<div class=\"row-sub\">{esc(r['label'])} · {fmt(r['count'])} 条</div></div>"
            f"<span class=\"copy-mini\" onclick=\"copyText('{url}', this)\">复制链接</span></div>"
        )
    return "".join(out)
rules_body = (
    detail_head("规则", "Egern-Rule-Set", "域名规则集，上面是懒人配置在用的规则，下面是国外热门服务的规则，复制链接就能引用，每天自动同步上游")
    + "<div class=\"sec-title\">配置在用</div>" + rule_rows(rules)
    + "<div class=\"sec-title\">国外热门规则</div>" + rule_rows(foreign_rules)
    + "<div class=\"note\">每天 02:00 UTC 自动同步上游，有变化自动更新。直接复制链接，在 Egern 里按需引用。</div>"
    f"<div style=\"margin-top:14px;\"><a class=\"beam-btn\" href=\"{gh_url('Egern-Rule-Set')}\">GitHub 仓库</a></div>"
)
write("Egern-Rule-Set/index.html", page("规则 · Egern 仓库", rules_body))

# ---------- Egern-Icons ----------
icons_sub = RAW.format(repo="Egern-Icons", path="Egern-Icons.json")
PREVIEW_ICONS = ["OpenAI", "Meta", "Google", "Telegram", "YouTube", "TikTok",
                 "X", "GitHub", "TencentCloud", "Spotify", "Instagram",
                 "Facebook", "WhatsApp", "Hulu", "Twitch", "Reddit",
                 "PlayStation", "Xbox"]
by_name = {it["name"]: it for it in icons}
preview = [by_name[n] for n in PREVIEW_ICONS if n in by_name]
missing = [n for n in PREVIEW_ICONS if n not in by_name]
if missing:
    print("preview icons missing:", missing)
grid = "".join(
    f"<div><img src=\"{esc(it['url'])}\" alt=\"{esc(it['name'])}\" loading=\"lazy\">"
    f"<div class=\"cap\">{esc(it['name'])}</div></div>"
    for it in preview
)
icons_body = (
    detail_head("图标", "Egern-Icons", "108×108 圆角方块图标")
    + copy_block("复制图标订阅链接", icons_sub)
    + "<div class=\"sec-title\">包含内容</div>"
    f"<div class=\"row\"><div><div class=\"row-name\">{fmt(len(icons))} 个图标</div>"
    "<div class=\"row-sub\">108×108 圆角方块，持续更新</div></div></div>"
    "<div class=\"sec-title\">预览</div>"
    f"<div class=\"icon-grid\">{grid}</div>"
    "<div class=\"note\">Egern 会缓存图标订阅，更新后看不到新图标时，删掉订阅重新添加。</div>"
    f"<div style=\"margin-top:14px;\"><a class=\"beam-btn\" href=\"{gh_url('Egern-Icons')}\">GitHub 仓库</a></div>"
)
write("Egern-Icons/index.html", page("图标 · Egern 仓库", icons_body))

# ---------- Egern-Widgets ----------
wrows = []
for w in widgets:
    url = raw_url("Egern-Widgets", w["file"])
    sub = f"<div class=\"row-sub\">{esc(w['desc'])}</div>" if w["desc"] else ""
    wrows.append(
        f"<div class=\"row\"><div><div class=\"row-name\">{esc(w['name'])}</div>{sub}</div>"
        f"<span class=\"copy-mini\" onclick=\"copyText('{url}', this)\">复制链接</span></div>"
    )
widgets_body = (
    detail_head("小组件", "Egern-Widgets", "桌面小组件，纯黑风格")
    + f"<div class=\"sec-title\">{len(widgets)} 个小组件</div>" + "".join(wrows)
    + "<div class=\"note\">每个小组件都是一个模块文件，复制链接后在 Egern 里添加模块订阅即可使用。</div>"
    f"<div style=\"margin-top:14px;\"><a class=\"beam-btn\" href=\"{gh_url('Egern-Widgets')}\">GitHub 仓库</a></div>"
)
write("Egern-Widgets/index.html", page("小组件 · Egern 仓库", widgets_body))

# ---------- Egern-Modules ----------
mrows = []
for m in modules:
    url = raw_url("Egern-Modules", m["file"])
    sub = f"<div class=\"row-sub\">{esc(m['desc'])}</div>" if m["desc"] else ""
    mrows.append(
        f"<div class=\"row\"><div><div class=\"row-name\">{esc(m['name'])}</div>{sub}</div>"
        f"<span class=\"copy-mini\" onclick=\"copyText('{url}', this)\">复制链接</span></div>"
    )
mods_body = (
    detail_head("模块", "Egern-Modules", "Egern 功能模块")
    + f"<div class=\"sec-title\">模块列表</div>" + "".join(mrows)
    + "<div class=\"note\">复制链接后在 Egern 里添加模块订阅即可使用。</div>"
    f"<div style=\"margin-top:14px;\"><a class=\"beam-btn\" href=\"{gh_url('Egern-Modules')}\">GitHub 仓库</a></div>"
)
write("Egern-Modules/index.html", page("模块 · Egern 仓库", mods_body))

print("all pages built, date:", TODAY)
