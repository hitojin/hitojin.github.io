import json
import os
import sqlite3
import sys
from datetime import datetime
from typing import Any

from database import DB_PATH, create_database

# Windowsターミナルの文字化け対策
sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_DIRECTORY = "output"
OUTPUT_JSON_PATH = os.path.join(OUTPUT_DIRECTORY, "ranking.json")

# JSONに保存する最大件数
RANKING_LIMIT = 100


def get_connection() -> sqlite3.Connection:
    """価格データベースへ接続する。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


def get_price_drop_ranking(
    limit: int = RANKING_LIMIT
) -> list[dict[str, Any]]:
    """
    各商品の最新価格と、その1つ前の価格を比較し、
    値下げされた商品を値下げ額順に取得する。
    """
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            WITH ranked_prices AS (
                SELECT
                    id,
                    item_code,
                    item_name,
                    price,
                    shop_name,
                    item_url,
                    fetched_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY item_code
                        ORDER BY id DESC
                    ) AS price_order
                FROM prices
            ),
            latest_prices AS (
                SELECT
                    item_code,
                    item_name,
                    price AS current_price,
                    shop_name,
                    item_url,
                    fetched_at AS current_fetched_at
                FROM ranked_prices
                WHERE price_order = 1
            ),
            previous_prices AS (
                SELECT
                    item_code,
                    price AS previous_price,
                    fetched_at AS previous_fetched_at
                FROM ranked_prices
                WHERE price_order = 2
            )
            SELECT
                latest.item_code,
                latest.item_name,
                previous.previous_price,
                latest.current_price,
                previous.previous_price - latest.current_price
                    AS discount_amount,
                ROUND(
                    (
                        (
                            previous.previous_price
                            - latest.current_price
                        ) * 100.0
                    ) / previous.previous_price,
                    1
                ) AS discount_rate,
                latest.shop_name,
                latest.item_url,
                previous.previous_fetched_at,
                latest.current_fetched_at
            FROM latest_prices AS latest
            INNER JOIN previous_prices AS previous
                ON latest.item_code = previous.item_code
            WHERE latest.current_price < previous.previous_price
            ORDER BY
                discount_amount DESC,
                discount_rate DESC,
                latest.current_price ASC
            LIMIT ?
            """,
            (limit,)
        )

        rows = cursor.fetchall()

        ranking: list[dict[str, Any]] = []

        for rank, row in enumerate(rows, start=1):
            ranking.append(
                {
                    "rank": rank,
                    "item_code": row["item_code"],
                    "item_name": row["item_name"],
                    "previous_price": int(row["previous_price"]),
                    "current_price": int(row["current_price"]),
                    "discount_amount": int(row["discount_amount"]),
                    "discount_rate": float(row["discount_rate"]),
                    "shop_name": row["shop_name"] or "",
                    "item_url": row["item_url"] or "",
                    "previous_fetched_at": row[
                        "previous_fetched_at"
                    ],
                    "current_fetched_at": row[
                        "current_fetched_at"
                    ],
                }
            )

        return ranking

    finally:
        conn.close()


def save_ranking_json(
    ranking: list[dict[str, Any]]
) -> None:
    """値下げランキングをJSONファイルへ保存する。"""
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

    output_data = {
        "generated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
        "count": len(ranking),
        "ranking": ranking,
    }

    with open(
        OUTPUT_JSON_PATH,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            output_data,
            file,
            ensure_ascii=False,
            indent=2
        )


def print_ranking(
    ranking: list[dict[str, Any]]
) -> None:
    """ランキングをターミナルへ表示する。"""
    print()
    print("=" * 100)
    print("今日の値下げランキング")
    print("=" * 100)

    if not ranking:
        print("値下げされた商品はまだありません。")
        print()
        print(
            "価格変更が保存された後に、"
            "ランキングへ商品が表示されます。"
        )
        return

    for item in ranking:
        print()
        print(
            f"{item['rank']:>3}位 "
            f"{item['discount_amount']:,}円値下げ "
            f"({item['discount_rate']:.1f}%OFF)"
        )
        print(
            f"     "
            f"{item['previous_price']:,}円"
            f" → "
            f"{item['current_price']:,}円"
        )
        print(f"     {item['item_name'][:80]}")

        if item["shop_name"]:
            print(f"     ショップ: {item['shop_name']}")

        if item["item_url"]:
            print(f"     URL: {item['item_url']}")


def main() -> None:
    """値下げランキングを生成する。"""
    create_database()

    ranking = get_price_drop_ranking(
        limit=RANKING_LIMIT
    )

    save_ranking_json(ranking)
    print_ranking(ranking)

    print()
    print("=" * 100)
    print("ランキング生成完了")
    print("=" * 100)
    print(f"ランキング件数 : {len(ranking):,}")
    print(f"出力先           : {OUTPUT_JSON_PATH}")
    print("=" * 100)


if __name__ == "__main__":
    main()