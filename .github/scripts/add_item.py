import json
import os
import re
from PIL import Image, ImageDraw, ImageFont

raw_data_str = os.environ.get("RAW_DATA", "{}").strip()
groups_input = os.environ.get("GROUPS", "").strip()
category = os.environ.get("CATEGORY", "雑誌").strip()
af_html = os.environ.get("AF_HTML", "").strip()
custom_memo = os.environ.get("CUSTOM_MEMO", "").strip()

# 1. ブックマークレットデータのパース
try:
    raw = json.loads(raw_data_str)
except Exception:
    raw = {"title": raw_data_str, "date": "", "price": 0}

title = raw.get("title", "").strip()
date = raw.get("date", "").strip()
price = int(raw.get("price", 0))

# 2. アフィリエイトHTMLから image と url を抽出
img_match = re.search(r'<img[^>]+src="([^"]+)"', af_html)
url_match = re.search(r'<a[^>]+href="([^"]+)"', af_html)

image_url = img_match.group(1) if img_match else ""
item_url = url_match.group(1) if url_match else (af_html if af_html.startswith("http") else "")

# 3. メモ整形（専用チャットで作った3行要約をそのまま反映）
memo = custom_memo.replace("\\n", "\n") if custom_memo else f"・{title}"

# 4. グループ判定（1つなら "group"、複数なら "groups"）
group_list = [g.strip() for g in re.split(r'[,、/]', groups_input) if g.strip()]

new_item = {}
if len(group_list) == 1:
    new_item["group"] = group_list[0]
elif len(group_list) > 1:
    new_item["groups"] = group_list
else:
    new_item["group"] = "その他"

new_item.update({
    "category": category,
    "title": title,
    "date": date,
    "price": price,
    "image": image_url,
    "url": item_url,
    "memo": memo
})

# 5. items.json へ追記
json_path = "items.json"
if os.path.exists(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        items = json.load(f)
else:
    items = []

items.insert(0, new_item)

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

# 6. X告知用PNG画像の自動生成（1200x675 16:9）
os.makedirs("x_posts", exist_ok=True)
W, H = 1200, 675

COLOR_MAP = {
    "乃木坂46": ((126, 48, 168), (248, 240, 255), (90, 25, 130)),
    "櫻坂46": ((241, 157, 181), (255, 248, 250), (200, 80, 120)),
    "日向坂46": ((91, 188, 228), (242, 251, 255), (30, 130, 180)),
    "AKB48": ((233, 82, 149), (255, 242, 248), (190, 40, 110)),
}
main_group = group_list[0] if group_list else "アイドル"
accent, bg_color, dark_text = COLOR_MAP.get(main_group, ((70, 90, 130), (245, 247, 252), (40, 55, 90)))

img = Image.new("RGB", (W, H), bg_color)
draw = ImageDraw.Draw(img)

draw.rectangle([20, 20, W - 20, H - 20], outline=accent, width=8)
draw.rectangle([20, 20, W - 20, 118], fill=accent)

font_path = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"

font_badge = ImageFont.truetype(font_path, 38)
font_title = ImageFont.truetype(font_path, 42)
font_memo = ImageFont.truetype(font_path, 25)
font_footer = ImageFont.truetype(font_path, 28)

group_label = " × ".join(group_list) if group_list else "新刊情報"
draw.text((55, 48), f"【{group_label} / {category}情報】", fill=(255, 255, 255), font=font_badge)

def wrap_text(text, max_chars=40):
    lines = []
    for paragraph in text.split("\n"):
        while len(paragraph) > max_chars:
            lines.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars:]
        if paragraph:
            lines.append(paragraph)
    return lines

# タイトル（最大2行）
title_lines = wrap_text(title, 25)[:2]
y = 148
for line in title_lines:
    draw.text((55, y), line, fill=(30, 30, 35), font=font_title)
    y += 54

# メモ（3行要約が途中で切れないよう最大6行・1行40文字まで表示）
y += 14
memo_lines = wrap_text(memo, 40)[:6]
for line in memo_lines:
    draw.text((55, y), line, fill=(65, 65, 75), font=font_memo)
    y += 36

draw.line([(55, H - 105), (W - 55, H - 105)], fill=accent, width=3)
release_str = f"発売日：{date}" if date else "予約受付中"
price_str = f"価格：{price:,}円（税込）" if price else ""
draw.text((55, H - 82), f"{release_str} ｜ {price_str}", fill=dark_text, font=font_footer)

img.save("x_posts/latest_post.png")

hashtags = " ".join([f"#{g}" for g in group_list])
post_text = f"""【{group_label} {category}情報】

『{title}』
{memo}

📅 発売日：{date}
💰 価格：{price:,}円（税込）

{hashtags} #アイドル雑誌 #写真集

👇予約・詳細リンクはリプ欄へ！"""

with open("x_posts/latest_post.txt", "w", encoding="utf-8") as f:
    f.write(post_text)

print("=== 生成されたX投稿文 ===")
print(post_text)
