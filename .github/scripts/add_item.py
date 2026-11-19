import json
import os
import re
from PIL import Image, ImageDraw, ImageFont

# 入力値の取得
raw_data_str = os.environ.get("RAW_DATA", "{}").strip()
groups_input = os.environ.get("GROUPS", "").strip()
category = os.environ.get("CATEGORY", "雑誌").strip()
af_html = os.environ.get("AF_HTML", "").strip()
direct_image = os.environ.get("DIRECT_IMAGE", "").strip()
direct_url = os.environ.get("DIRECT_URL", "").strip()
custom_memo = os.environ.get("CUSTOM_MEMO", "").strip()

# 1. ブックマークレットデータのパース
try:
    raw = json.loads(raw_data_str)
except Exception:
    raw = {"title": raw_data_str, "date": "", "price": 0, "raw_memo": ""}

title = raw.get("title", "").strip()
date = raw.get("date", "").strip()
price = int(raw.get("price", 0))
raw_memo = raw.get("raw_memo", "").strip()

# 2. アフィリエイトHTMLから image と url を抽出（直接URL指定も可）
img_match = re.search(r'<img[^>]+src="([^"]+)"', af_html)
url_match = re.search(r'<a[^>]+href="([^"]+)"', af_html)

image_url = direct_image if direct_image else (img_match.group(1) if img_match else "")
item_url = direct_url if direct_url else (url_match.group(1) if url_match else (af_html if af_html.startswith("http") else ""))

# 3. メモの自動整形（手動指定があれば優先、なければ内容紹介から箇条書き生成）
if custom_memo:
    memo = custom_memo.replace("\\n", "\n")
else:
    sentences = [s.strip() for s in re.split(r'[。！!？?]', raw_memo) if len(s.strip()) > 4][:3]
    memo = "\n".join([f"・{s}" for s in sentences]) if sentences else f"・{title}"

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

# 5. items.json の先頭（または末尾）へ追記
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

# 外枠とヘッダー帯
draw.rectangle([24, 24, W - 24, H - 24], outline=accent, width=6)
draw.rectangle([24, 24, W - 24, 130], fill=accent)

font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
if not os.path.exists(font_path):
    font_path = "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"

font_badge = ImageFont.truetype(font_path, 42)
font_title = ImageFont.truetype(font_path, 46)
font_memo = ImageFont.truetype(font_path, 30)
font_footer = ImageFont.truetype(font_path, 28)

group_label = " × ".join(group_list) if group_list else "新刊情報"
draw.text((60, 52), f"【{group_label} / {category}情報】", fill=(255, 255, 255), font=font_badge)

# タイトル折り返し
def wrap_text(text, max_chars=22):
    lines = []
    for paragraph in text.split("\n"):
        while len(paragraph) > max_chars:
            lines.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars:]
        if paragraph:
            lines.append(paragraph)
    return lines

title_lines = wrap_text(title, 22)[:3]
y = 165
for line in title_lines:
    draw.text((60, y), line, fill=(30, 30, 35), font=font_title)
    y += 62

# メモ表示（最大3行）
y += 20
memo_lines = wrap_text(memo, 32)[:3]
for line in memo_lines:
    draw.text((60, y), line, fill=(75, 75, 85), font=font_memo)
    y += 44

# フッター（発売日・価格）
draw.line([(60, H - 125), (W - 60, H - 125)], fill=accent, width=3)
release_str = f"発売日：{date}" if date else "予約受付中"
price_str = f"価格：{price:,}円（税込）" if price else ""
draw.text((60, H - 100), f"{release_str} ｜ {price_str}", fill=dark_text, font=font_footer)

img_out_path = "x_posts/latest_post.png"
img.save(img_out_path)

# 7. X投稿用テキストの生成
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
