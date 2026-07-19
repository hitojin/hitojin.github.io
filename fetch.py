import sys
import time
from typing import Any

import requests

from config import ACCESS_KEY, APP_ID
from database import create_database, save_price_if_changed
from genres import GENRES

# Windowsターミナルの文字化け対策
sys.stdout.reconfigure(encoding="utf-8")

API_URL = (
    "https://openapi.rakuten.co.jp/"
    "ichibams/api/IchibaItem/Search/20260701"
)

HITS_PER_PAGE = 30
MAX_PAGES_PER_KEYWORD = 3

REQUEST_TIMEOUT_SECONDS = 30
REQUEST_INTERVAL_SECONDS = 1.0

# 通信エラー時の最大試行回数
MAX_RETRIES = 3

# 再試行までの待ち時間
RETRY_WAIT_SECONDS = 3


def fetch_page(
    session: requests.Session,
    keyword: str,
    page: int
) -> dict[str, Any] | None:
    """
    楽天APIから1ページ取得する。

    通信失敗やHTTPエラーの場合は最大3回まで再試行する。
    """
    params = {
        "applicationId": APP_ID,
        "accessKey": ACCESS_KEY,
        "keyword": keyword,
        "hits": HITS_PER_PAGE,
        "page": page,
        "format": "json",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                API_URL,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS
            )

            print(
                f"  HTTP {response.status_code} "
                f"| 試行 {attempt}/{MAX_RETRIES}"
            )

            response.raise_for_status()

            data = response.json()

            if not isinstance(data, dict):
                print("  エラー: API応答が辞書形式ではありません。")
                return None

            return data

        except requests.Timeout:
            print(
                f"  タイムアウトしました。"
                f"{RETRY_WAIT_SECONDS}秒後に再試行します。"
            )

        except requests.HTTPError:
            print("  HTTPエラーが発生しました。")
            print("  応答内容:", response.text[:500])

            # 認証エラーの場合、再試行しても直らないため中断
            if response.status_code in (400, 401, 403):
                return None

            # アクセス制限やサーバーエラーは再試行
            if response.status_code not in (429, 500, 502, 503, 504):
                return None

        except requests.RequestException as error:
            print(f"  通信エラー: {error}")

        except ValueError as error:
            print(f"  JSON解析エラー: {error}")
            return None

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_WAIT_SECONDS * attempt)

    print(
        f"  エラー: {keyword} のページ{page}を"
        f"{MAX_RETRIES}回試しましたが取得できませんでした。"
    )

    return None


def extract_products(
    data: dict[str, Any]
) -> list[dict[str, Any]]:
    """API応答から商品情報を取り出す。"""
    products: list[dict[str, Any]] = []

    items = data.get("Items", [])

    if not isinstance(items, list):
        return products

    for wrapper in items:
        if not isinstance(wrapper, dict):
            continue

        product = wrapper.get("Item")

        if not isinstance(product, dict):
            continue

        products.append(product)

    return products


def main() -> None:
    """商品価格を取得し、変更時だけデータベースへ保存する。"""
    create_database()

    api_item_count = 0
    new_count = 0
    changed_count = 0
    unchanged_count = 0
    duplicate_count = 0
    failed_page_count = 0

    processed_item_codes: set[str] = set()

    # キーワードごとの取得結果
    keyword_results: list[dict[str, Any]] = []

    with requests.Session() as session:
        for display_name, keyword in GENRES:
            print()
            print("=" * 80)
            print(f"検索中: {display_name}")
            print("=" * 80)

            keyword_item_count = 0
            keyword_page_count = 0
            keyword_failed = False
            reported_page_count: int | None = None
            reported_total_count: int | None = None

            for page in range(1, MAX_PAGES_PER_KEYWORD + 1):
                print(
                    f"{display_name}: "
                    f"ページ {page}/{MAX_PAGES_PER_KEYWORD} を取得中..."
                )

                data = fetch_page(
                    session=session,
                    keyword=keyword,
                    page=page
                )

                if data is None:
                    failed_page_count += 1
                    keyword_failed = True

                    print(
                        f"  {display_name} のページ{page}を"
                        "取得できなかったため、この検索語を中断します。"
                    )
                    break

                products = extract_products(data)

                page_count_value = data.get("pageCount")
                count_value = data.get("count")

                try:
                    reported_page_count = int(page_count_value)
                except (TypeError, ValueError):
                    reported_page_count = None

                try:
                    reported_total_count = int(count_value)
                except (TypeError, ValueError):
                    reported_total_count = None

                received_count = len(products)

                print(
                    f"  受信件数: {received_count}"
                    f" | API上の総件数: "
                    f"{reported_total_count if reported_total_count is not None else '不明'}"
                    f" | API上のページ数: "
                    f"{reported_page_count if reported_page_count is not None else '不明'}"
                )

                if received_count == 0:
                    print("  このページには商品がありません。")
                    break

                keyword_page_count += 1
                keyword_item_count += received_count
                api_item_count += received_count

                for product in products:
                    item_code = str(product.get("itemCode", "")).strip()
                    item_name = str(product.get("itemName", "")).strip()

                    if not item_code:
                        print("  商品コードがないためスキップしました。")
                        continue

                    if "itemPrice" not in product:
                        print(
                            f"  価格がないためスキップ: "
                            f"{item_name[:40]}"
                        )
                        continue

                    if item_code in processed_item_codes:
                        duplicate_count += 1
                        continue

                    processed_item_codes.add(item_code)

                    try:
                        status, previous_price = (
                            save_price_if_changed(product)
                        )
                    except (
                        KeyError,
                        TypeError,
                        ValueError
                    ) as error:
                        print(
                            f"  保存エラー: {error} | "
                            f"{item_name[:40]}"
                        )
                        continue

                    current_price = int(product["itemPrice"])

                    if status == "new":
                        new_count += 1

                        print(
                            f"  🆕 新規 "
                            f"{current_price:,}円 | "
                            f"{item_name[:50]}"
                        )

                    elif status == "changed":
                        changed_count += 1

                        if previous_price is None:
                            print(
                                f"  価格変更 "
                                f"{current_price:,}円 | "
                                f"{item_name[:50]}"
                            )
                            continue

                        difference = (
                            current_price - int(previous_price)
                        )

                        if difference < 0:
                            print(
                                f"  🔥 値下げ "
                                f"{int(previous_price):,}円 → "
                                f"{current_price:,}円 "
                                f"({abs(difference):,}円安) | "
                                f"{item_name[:50]}"
                            )
                        else:
                            print(
                                f"  ⬆ 値上げ "
                                f"{int(previous_price):,}円 → "
                                f"{current_price:,}円 "
                                f"({difference:,}円高) | "
                                f"{item_name[:50]}"
                            )

                    else:
                        unchanged_count += 1

                if (
                    reported_page_count is not None
                    and page >= reported_page_count
                ):
                    print("  API上の最終ページに到達しました。")
                    break

                time.sleep(REQUEST_INTERVAL_SECONDS)

            keyword_results.append({
                "name": display_name,
                "items": keyword_item_count,
                "pages": keyword_page_count,
                "api_total": reported_total_count,
                "api_pages": reported_page_count,
                "failed": keyword_failed,
            })

            # キーワードを切り替える前にも少し待つ
            time.sleep(REQUEST_INTERVAL_SECONDS)

    print()
    print("=" * 100)
    print("キーワード別取得結果")
    print("=" * 100)

    for result in keyword_results:
        status_text = "失敗あり" if result["failed"] else "正常"

        api_total_text = (
            f"{result['api_total']:,}"
            if result["api_total"] is not None
            else "不明"
        )

        api_pages_text = (
            str(result["api_pages"])
            if result["api_pages"] is not None
            else "不明"
        )

        print(
            f"{result['name']:<18}"
            f" 取得={result['items']:>3}件"
            f" 実取得ページ={result['pages']}"
            f" API総件数={api_total_text}"
            f" APIページ数={api_pages_text}"
            f" 状態={status_text}"
        )

    print()
    print("=" * 100)
    print("取得処理が完了しました")
    print("=" * 100)
    print(f"APIから取得した件数 : {api_item_count:,}")
    print(f"重複を除いた商品数   : {len(processed_item_codes):,}")
    print(f"新規保存             : {new_count:,}")
    print(f"価格変更を保存       : {changed_count:,}")
    print(f"価格変化なし         : {unchanged_count:,}")
    print(f"検索間の重複         : {duplicate_count:,}")
    print(f"取得失敗ページ       : {failed_page_count:,}")
    print("=" * 100)

    if failed_page_count > 0:
        print()
        print("注意:")
        print(
            "取得失敗ページがあります。"
            "この実行結果はランキング生成に使用しない方が安全です。"
        )


if __name__ == "__main__":
    main()