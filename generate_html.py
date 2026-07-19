import json
import os
import sys
from datetime import datetime
from html import escape
from typing import Any

# Windowsターミナルの文字化け対策
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

INPUT_JSON_PATH = os.path.join(
    PROJECT_DIR,
    "output",
    "ranking.json"
)

# GitHub Pagesでは、リポジトリ直下のindex.htmlを公開する
OUTPUT_HTML_PATH = os.path.join(
    PROJECT_DIR,
    "index.html"
)

SITE_TITLE = "今日の楽天値下げランキング"
RANKING_LIMIT = 100


def load_ranking_data() -> dict[str, Any]:
    """ranking.jsonを読み込む。"""
    if not os.path.exists(INPUT_JSON_PATH):
        raise FileNotFoundError(
            f"{INPUT_JSON_PATH} が見つかりません。\n"
            "先に python compare.py を実行してください。"
        )

    with open(
        INPUT_JSON_PATH,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "ranking.json の形式が正しくありません。"
        )

    ranking = data.get("ranking")

    if not isinstance(ranking, list):
        raise ValueError(
            "ranking.json に ranking 配列がありません。"
        )

    return data


def format_generated_at(value: str) -> str:
    """ISO形式の日時を表示用に整える。"""
    if not value:
        return "更新日時不明"

    try:
        generated_at = datetime.fromisoformat(value)

        return generated_at.strftime(
            "%Y年%m月%d日 %H:%M"
        )

    except ValueError:
        return value


def format_price(value: Any) -> str:
    """価格をカンマ区切りで表示する。"""
    try:
        return f"{int(value):,}円"

    except (TypeError, ValueError):
        return "-"


def create_ranking_card(
    item: dict[str, Any]
) -> str:
    """商品1件分のHTMLを作る。"""
    try:
        rank = int(item.get("rank", 0))

    except (TypeError, ValueError):
        rank = 0

    item_name = escape(
        str(
            item.get(
                "item_name",
                "商品名不明"
            )
        )
    )

    shop_name = escape(
        str(
            item.get(
                "shop_name",
                ""
            )
        )
    )

    item_url = escape(
        str(
            item.get(
                "item_url",
                ""
            )
        ),
        quote=True
    )

    previous_price = format_price(
        item.get("previous_price")
    )

    current_price = format_price(
        item.get("current_price")
    )

    discount_amount = format_price(
        item.get("discount_amount")
    )

    try:
        discount_rate = (
            f"{float(item.get('discount_rate', 0)):.1f}%OFF"
        )

    except (TypeError, ValueError):
        discount_rate = "-"

    if rank == 1:
        rank_class = "rank-first"
        rank_label = "🥇 1位"

    elif rank == 2:
        rank_class = "rank-second"
        rank_label = "🥈 2位"

    elif rank == 3:
        rank_class = "rank-third"
        rank_label = "🥉 3位"

    else:
        rank_class = ""
        rank_label = f"{rank}位"

    shop_html = ""

    if shop_name:
        shop_html = f"""
            <p class="shop-name">
                ショップ：{shop_name}
            </p>
        """

    link_html = ""

    if item_url:
        link_html = f"""
            <a
                class="product-link"
                href="{item_url}"
                target="_blank"
                rel="noopener noreferrer sponsored"
            >
                楽天市場で商品を見る
            </a>
        """

    return f"""
        <article class="ranking-card {rank_class}">
            <div class="rank-badge">
                {rank_label}
            </div>

            <div class="product-content">
                <h2 class="product-name">
                    {item_name}
                </h2>

                {shop_html}

                <div class="price-area">
                    <div class="old-price">
                        <span class="price-label">
                            前回価格
                        </span>

                        <span class="price-value">
                            {previous_price}
                        </span>
                    </div>

                    <div class="price-arrow">
                        →
                    </div>

                    <div class="new-price">
                        <span class="price-label">
                            現在価格
                        </span>

                        <span class="price-value">
                            {current_price}
                        </span>
                    </div>
                </div>

                <div class="discount-area">
                    <span class="discount-amount">
                        {discount_amount}値下げ
                    </span>

                    <span class="discount-rate">
                        {discount_rate}
                    </span>
                </div>

                {link_html}
            </div>
        </article>
    """


def create_empty_message() -> str:
    """ランキング0件時のHTMLを作る。"""
    return """
        <section class="empty-ranking">
            <div class="empty-icon">
                📉
            </div>

            <h2>
                現在、値下げ商品はありません
            </h2>

            <p>
                新しい価格変更が確認されると、
                ここにランキングが表示されます。
            </p>
        </section>
    """


def build_html(
    data: dict[str, Any]
) -> str:
    """公開用HTML全文を作る。"""
    ranking = data.get(
        "ranking",
        []
    )

    generated_at = format_generated_at(
        str(
            data.get(
                "generated_at",
                ""
            )
        )
    )

    cards: list[str] = []

    for item in ranking[:RANKING_LIMIT]:
        if isinstance(item, dict):
            cards.append(
                create_ranking_card(item)
            )

    if cards:
        ranking_html = "\n".join(cards)

    else:
        ranking_html = create_empty_message()

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <meta
        name="description"
        content="楽天市場の商品価格を毎日比較し、値下げ額の大きい商品をランキング形式で紹介します。"
    >

    <title>
        {escape(SITE_TITLE)}
    </title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            margin: 0;
            padding: 0;
            background: #f4f6f8;
            color: #222222;
            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                "Yu Gothic",
                "Hiragino Kaku Gothic ProN",
                Meiryo,
                sans-serif;
            line-height: 1.6;
        }}

        .site-header {{
            background:
                linear-gradient(
                    135deg,
                    #bf0000,
                    #e60012
                );
            color: #ffffff;
            padding: 36px 20px 32px;
            text-align: center;
        }}

        .site-header h1 {{
            margin: 0;
            font-size: clamp(
                24px,
                5vw,
                42px
            );
            line-height: 1.25;
        }}

        .site-description {{
            max-width: 760px;
            margin: 14px auto 0;
            font-size: 15px;
            opacity: 0.95;
        }}

        .updated-at {{
            margin-top: 12px;
            font-size: 13px;
            opacity: 0.85;
        }}

        .container {{
            width: min(
                100% - 24px,
                1000px
            );
            margin: 28px auto 60px;
        }}

        .ranking-summary {{
            margin-bottom: 20px;
            padding: 18px 20px;
            border-radius: 14px;
            background: #ffffff;
            box-shadow:
                0 4px 16px
                rgba(0, 0, 0, 0.06);
        }}

        .ranking-summary strong {{
            color: #bf0000;
        }}

        .ranking-card {{
            position: relative;
            display: grid;
            grid-template-columns: 90px 1fr;
            gap: 20px;
            margin-bottom: 18px;
            padding: 24px;
            border-radius: 16px;
            background: #ffffff;
            box-shadow:
                0 6px 20px
                rgba(0, 0, 0, 0.07);
        }}

        .rank-badge {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 90px;
            border-radius: 14px;
            background: #f1f3f5;
            color: #333333;
            font-size: 21px;
            font-weight: 700;
            text-align: center;
        }}

        .rank-first .rank-badge {{
            background:
                linear-gradient(
                    135deg,
                    #fff2a8,
                    #f6c945
                );
        }}

        .rank-second .rank-badge {{
            background:
                linear-gradient(
                    135deg,
                    #f4f4f4,
                    #c8c8c8
                );
        }}

        .rank-third .rank-badge {{
            background:
                linear-gradient(
                    135deg,
                    #f3c19b,
                    #c77a3b
                );
            color: #ffffff;
        }}

        .product-name {{
            margin: 0;
            font-size: 20px;
            line-height: 1.45;
            overflow-wrap: anywhere;
        }}

        .shop-name {{
            margin: 8px 0 0;
            color: #666666;
            font-size: 14px;
        }}

        .price-area {{
            display: flex;
            align-items: center;
            gap: 18px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}

        .old-price,
        .new-price {{
            display: flex;
            flex-direction: column;
        }}

        .price-label {{
            color: #777777;
            font-size: 13px;
        }}

        .price-value {{
            font-size: 22px;
            font-weight: 700;
        }}

        .old-price .price-value {{
            color: #777777;
            text-decoration: line-through;
        }}

        .new-price .price-value {{
            color: #bf0000;
        }}

        .price-arrow {{
            color: #999999;
            font-size: 24px;
            font-weight: 700;
        }}

        .discount-area {{
            display: flex;
            gap: 10px;
            margin-top: 18px;
            flex-wrap: wrap;
        }}

        .discount-amount,
        .discount-rate {{
            display: inline-flex;
            align-items: center;
            min-height: 36px;
            padding: 7px 13px;
            border-radius: 999px;
            font-size: 15px;
            font-weight: 700;
        }}

        .discount-amount {{
            background: #fff0f0;
            color: #bf0000;
        }}

        .discount-rate {{
            background: #fff7d6;
            color: #8a5a00;
        }}

        .product-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 46px;
            margin-top: 20px;
            padding: 11px 22px;
            border-radius: 10px;
            background: #bf0000;
            color: #ffffff;
            font-weight: 700;
            text-decoration: none;
            transition:
                transform 0.15s ease,
                opacity 0.15s ease;
        }}

        .product-link:hover {{
            opacity: 0.9;
            transform: translateY(-1px);
        }}

        .empty-ranking {{
            padding: 64px 24px;
            border-radius: 18px;
            background: #ffffff;
            text-align: center;
            box-shadow:
                0 6px 20px
                rgba(0, 0, 0, 0.06);
        }}

        .empty-icon {{
            font-size: 54px;
        }}

        .empty-ranking h2 {{
            margin: 16px 0 8px;
        }}

        .empty-ranking p {{
            margin: 0;
            color: #666666;
        }}

        .site-footer {{
            padding: 28px 20px;
            background: #202124;
            color: #d7d7d7;
            text-align: center;
            font-size: 13px;
        }}

        .site-footer p {{
            margin: 6px 0;
        }}

        @media (max-width: 640px) {{
            .site-header {{
                padding-top: 28px;
            }}

            .container {{
                width: min(
                    100% - 16px,
                    1000px
                );
                margin-top: 16px;
            }}

            .ranking-card {{
                grid-template-columns: 1fr;
                gap: 14px;
                padding: 18px;
            }}

            .rank-badge {{
                min-height: 54px;
            }}

            .product-name {{
                font-size: 17px;
            }}

            .price-area {{
                gap: 12px;
            }}

            .price-value {{
                font-size: 19px;
            }}

            .product-link {{
                width: 100%;
            }}
        }}
    </style>
</head>

<body>
    <header class="site-header">
        <h1>
            🔥 今日の楽天値下げランキング
        </h1>

        <p class="site-description">
            楽天市場の商品価格を定期的に比較し、
            値下げ額の大きい商品をランキングで紹介します。
        </p>

        <p class="updated-at">
            最終更新：{escape(generated_at)}
        </p>
    </header>

    <main class="container">
        <section class="ranking-summary">
            現在のランキング掲載数：
            <strong>{len(cards)}件</strong>
        </section>

        {ranking_html}
    </main>

    <footer class="site-footer">
        <p>
            当サイトは楽天アフィリエイトを利用しています。
        </p>

        <p>
            商品価格や在庫状況は変更される場合があります。
        </p>

        <p>
            購入前に楽天市場の商品ページで
            最新情報をご確認ください。
        </p>
    </footer>
</body>
</html>
"""


def save_html(
    html: str
) -> None:
    """index.htmlをUTF-8で保存する。"""
    with open(
        OUTPUT_HTML_PATH,
        "w",
        encoding="utf-8",
        newline=""
    ) as file:
        file.write(html)


def main() -> None:
    """ranking.jsonからindex.htmlを生成する。"""
    try:
        data = load_ranking_data()
        html = build_html(data)
        save_html(html)

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        OSError
    ) as error:
        print()
        print("=" * 80)
        print("HTML生成に失敗しました")
        print("=" * 80)
        print(error)
        print("=" * 80)

        sys.exit(1)

    ranking = data.get(
        "ranking",
        []
    )

    print()
    print("=" * 80)
    print("GitHub Pages用HTMLの生成が完了しました")
    print("=" * 80)
    print(
        f"ランキング件数 : "
        f"{len(ranking):,}"
    )
    print(
        f"出力先           : "
        f"{OUTPUT_HTML_PATH}"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()