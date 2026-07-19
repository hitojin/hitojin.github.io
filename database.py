import os
import sqlite3
from typing import Any

DB_PATH = "data/prices.db"


def get_connection() -> sqlite3.Connection:
    """SQLiteデータベースへ接続する。"""
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


def create_database() -> None:
    """価格履歴テーブルとインデックスを作成する。"""
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_code TEXT NOT NULL,
                item_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                shop_name TEXT,
                item_url TEXT,
                fetched_at TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_item_code
            ON prices(item_code)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_fetched_at
            ON prices(fetched_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_item_code_id
            ON prices(item_code, id DESC)
        """)

        conn.commit()

    finally:
        conn.close()


def get_latest_price(
    conn: sqlite3.Connection,
    item_code: str
) -> int | None:
    """指定商品の最後に保存した価格を取得する。"""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT price
        FROM prices
        WHERE item_code = ?
        ORDER BY id DESC
        LIMIT 1
    """, (item_code,))

    row = cursor.fetchone()

    if row is None:
        return None

    return int(row["price"])


def save_price_if_changed(
    product: dict[str, Any]
) -> tuple[str, int | None]:
    """
    初回または価格変更時だけ価格を保存する。

    戻り値:
        ("new", None)            初めての商品
        ("changed", 前回価格)    価格が変わった
        ("unchanged", 前回価格)  価格に変化なし
    """
    item_code = str(product["itemCode"])
    current_price = int(product["itemPrice"])

    conn = get_connection()

    try:
        previous_price = get_latest_price(conn, item_code)

        if previous_price == current_price:
            return "unchanged", previous_price

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO prices (
                item_code,
                item_name,
                price,
                shop_name,
                item_url
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            item_code,
            str(product["itemName"]),
            current_price,
            str(product.get("shopName", "")),
            str(product.get("itemUrl", ""))
        ))

        conn.commit()

        if previous_price is None:
            return "new", None

        return "changed", previous_price

    finally:
        conn.close()