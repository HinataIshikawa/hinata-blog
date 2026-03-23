import anthropic
import csv
import os
import sys
from datetime import date, datetime
from duckduckgo_search import DDGS
from urllib.parse import quote

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CSV_FILE = "products.csv"
BLOG_URL = "https://hinataishikawa.github.io/hinata-blog"

def get_product():
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} が見つかりません")
        sys.exit(1)

    with open(CSV_FILE, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    if not reader:
        print("Error: products.csv が空です")
        sys.exit(1)

    # スコア順ソート
    try:
        reader.sort(key=lambda x: float(x.get("スコア", 0)), reverse=True)
    except:
        pass

    # 20時→偶数インデックス、21時→奇数インデックス
    hour = datetime.now().hour
    index = (date.today().toordinal() * 2 + (1 if hour >= 21 else 0)) % len(reader)
    return reader[index]

def search_product_info(product_name):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{product_name} 特徴 レビュー スペック", max_results=5))
            snippets = " ".join([r["body"] for r in results])
            return snippets[:1000]
    except Exception as e:
        print(f"Search warning: {e}")
        return ""

def get_category(product_name):
    categories = {
        "ガジェット": ["イヤホン", "充電器", "ケーブル", "スマホ", "タブレット", "PC"],
        "家電": ["冷蔵庫", "洗濯機", "エアコン", "掃除機", "ドライヤー"],
        "ファッション": ["シャツ", "パンツ", "靴", "バッグ"],
        "美容": ["シャンプー", "化粧水", "乳液"],
        "生活用品": ["タオル", "枕", "布団", "カーテン"],
    }
    name_lower = product_name.lower()
    for cat, keywords in categories.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return cat
    return "その他"

def generate_article(product_name, link, target, score=None):
    product_info = search_product_info(product_name)
    category = get_category(product_name)
    score_text = f"（評価スコア: {score}/5.0）" if score else ""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""以下の商品について、Amazonアフィリエイト用のブログ記事をHTML形式で書いてください。

商品名: {product_name}
カテゴリ: {category}
ターゲット: {target if target and target != "なし" else "一般"}
評価: {score_text}
参考情報: {product_info}
アフィリエイトリンク: {link}

条件:
- 日本語、口語体、テンション高め
- 800〜1200文字
- SEOを意識したh1,h2タグを使う
- 商品の特徴を3〜5個箇条書きで書く
- 最後に必ずアフィリエイトリンクを含むボタンを入れる
- bodyタグやhtmlタグは不要、h1から始まる本文だけ出力
- リンクは必ず {link} を使う
- ボタンは以下の形式で: <a href="{link}" style="display: inline-block; padding: 15px 40px; background-color: #FF9900; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">Amazonでチェック</a>"""
        }]
    )
    content = message.content[0].text
    
    # Remove Markdown code block markers if present
    if content.startswith('```html'):
        content = content[7:]  # Remove ```html
    if content.startswith('```'):
        content = content[3:]  # Remove ```
    if content.endswith('```'):
        content = content[:-3]  # Remove trailing ```
    
    # Remove article tags if present
    content = content.replace('<article>', '').replace('</article>', '')
    content = content.strip()
    return content

def generate_description(product_name, category):
    """記事のdescriptionを生成（SEO用）"""
    descriptions = {
        "ガジェット": f"{product_name}の特徴、レビュー、スペックを詳しく解説。Amazonアフィリエイト対応。",
        "家電": f"{product_name}の最新情報、価格、機能を比較。Amazonで購入できます。",
        "ファッション": f"{product_name}のおすすめコーディネートと購入ガイド。トレンド情報も掲載。",
        "美容": f"{product_name}の効果、使い方、口コミをまとめました。Amazonで今すぐ購入。",
        "生活用品": f"{product_name}で生活がもっと快適に。特徴と選び方を解説します。",
    }
    return descriptions.get(category, f"{product_name}のおすすめ情報をお届け。Amazonアフィリエイト対応。")

def build_html(product_name, article_content, category, filename):
    """メタタグ・OGP・Twitter Cardを含むHTMLを生成"""
    today = date.today().strftime("%Y年%m月%d日")
    description = generate_description(product_name, category)
    article_url = f"{BLOG_URL}/articles/{filename}"
    
    # OGP用の画像（デフォルト）
    og_image = f"{BLOG_URL}/og-image.jpg"
    
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{description}">
    <meta name="keywords" content="{product_name}, {category}, Amazon, アフィリエイト, レビュー">
    <meta name="author" content="Hinata">
    
    <!-- OGP (Open Graph Protocol) -->
    <meta property="og:title" content="{product_name} レビュー・特徴まとめ">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{article_url}">
    <meta property="og:image" content="{og_image}">
    <meta property="og:site_name" content="Hinataのおすすめ商品ブログ">
    <meta property="og:locale" content="ja_JP">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{product_name} レビュー・特徴まとめ">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{og_image}">
    
    <!-- 記事のメタデータ -->
    <meta property="article:published_time" content="{date.today().isoformat()}">
    <meta property="article:author" content="Hinata">
    <meta property="article:section" content="{category}">
    
    <!-- Canonical URL -->
    <link rel="canonical" href="{article_url}">
    
    <title>{product_name} レビュー・特徴まとめ</title>
    <style>
        body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; }}
        h1 {{ color: #333; border-bottom: 2px solid #ff9900; padding-bottom: 10px; }}
        h2 {{ color: #555; }}
        .buy-btn {{ display: inline-block; background: #ff9900; color: white; padding: 12px 24px; 
                   text-decoration: none; border-radius: 4px; font-weight: bold; margin: 20px 0; }}
        .buy-btn:hover {{ background: #e68a00; }}
        .meta {{ color: #888; font-size: 0.9em; }}
        .tag {{ background: #eee; padding: 2px 8px; border-radius: 3px; font-size: 0.85em; }}
    </style>
</head>
<body>
    <p class="meta"><span class="tag">{category}</span> 投稿日: {today}</p>
    {article_content}
    <hr>
    <p><a href="index.html">← 記事一覧に戻る</a></p>
</body>
</html>"""

def update_index(articles_dir):
    """index.htmlの記事一覧を更新"""
    files = sorted(
        [f for f in os.listdir(articles_dir) if f.endswith(".html")],
        reverse=True
    )

    items = ""
    for fname in files[:50]:  # 最新50件
        # ファイル名から日付と商品名を取得
        parts = fname.replace(".html", "").split("-", 3)
        if len(parts) >= 4:
            date_str = f"{parts[0]}/{parts[1]}/{parts[2]}"
            title = parts[3].replace("-", " ")
        else:
            date_str = ""
            title = fname.replace(".html", "")
        items += f'<li><a href="articles/{fname}">{title}</a> <span style="color:#888;font-size:0.9em">{date_str}</span></li>\n'

    index_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="大学生ドラマーのHinataが、Amazon厳選商品を毎日紹介するアフィリエイトブログです。ガジェット、家電、ファッション、美容など幅広いカテゴリの商品をレビューしています。">
    <meta name="keywords" content="アフィリエイト, Amazon, 商品レビュー, ガジェット, 家電, ファッション, 美容">
    
    <!-- OGP -->
    <meta property="og:title" content="Hinataのおすすめ商品ブログ">
    <meta property="og:description" content="Amazon厳選商品を毎日紹介しています！">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{BLOG_URL}/">
    <meta property="og:site_name" content="Hinataのおすすめ商品ブログ">
    <meta property="og:locale" content="ja_JP">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="Hinataのおすすめ商品ブログ">
    <meta name="twitter:description" content="Amazon厳選商品を毎日紹介しています！">
    
    <title>Hinataのアフィリエイトブログ</title>
    <style>
        body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #ff9900; padding-bottom: 10px; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ padding: 10px 0; border-bottom: 1px solid #eee; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>📦 Hinataのおすすめ商品ブログ</h1>
    <p>Amazon厳選商品を毎日紹介しています！</p>
    <ul>
{items}
    </ul>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_content)
    print("index.html を更新しました")

def generate_sitemap(articles_dir):
    """sitemap.xmlを生成（SEO用）"""
    files = sorted(
        [f for f in os.listdir(articles_dir) if f.endswith(".html")],
        reverse=True
    )
    
    sitemap_urls = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{BLOG_URL}/</loc>
        <lastmod>{date.today().isoformat()}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
"""
    
    for fname in files:
        # ファイル名から日付を取得
        parts = fname.replace(".html", "").split("-", 3)
        if len(parts) >= 3:
            try:
                file_date = f"{parts[0]}-{parts[1]}-{parts[2]}"
            except:
                file_date = date.today().isoformat()
        else:
            file_date = date.today().isoformat()
        
        article_url = f"{BLOG_URL}/articles/{fname}"
        sitemap_urls += f"""    <url>
        <loc>{article_url}</loc>
        <lastmod>{file_date}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>
"""
    
    sitemap_urls += """</urlset>"""
    
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_urls)
    print(f"sitemap.xml を生成しました（{len(files)}件の記事）")

def main():
    product = get_product()
    name = product["商品名"]
    link = product["リンク"]
    target = product.get("ターゲット", "なし")
    score = product.get("スコア")

    print(f"記事生成中: {name}")

    article_content = generate_article(name, link, target, score)
    category = get_category(name)
    
    # articlesフォルダに保存
    os.makedirs("articles", exist_ok=True)
    today_str = date.today().strftime("%Y-%m-%d")
    safe_name = name.replace(" ", "-").replace("/", "-")[:30]
    filename = f"{today_str}-{safe_name}.html"
    
    html = build_html(name, article_content, category, filename)

    with open(f"articles/{filename}", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"保存: articles/{filename}")

    update_index("articles")
    generate_sitemap("articles")

if __name__ == "__main__":
    main()
