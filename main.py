import sys
import requests

from config import APP_ID, ACCESS_KEY
from database import create_database, insert_item
from genres import GENRES

sys.stdout.reconfigure(encoding="utf-8")

create_database()

url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"

for keyword_name, keyword in GENRES:

    print(f"\n===== {keyword_name} =====")

    params = {
        "applicationId": APP_ID,
        "accessKey": ACCESS_KEY,
        "keyword": keyword,
        "hits": 30,
        "page": 1,
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(response.text)
        continue

    data = response.json()

    for item in data["Items"]:

        product = item["Item"]

        insert_item(
            product["itemCode"],
            product["itemName"],
            product["itemPrice"],
            product["shopName"],
            product["itemUrl"]
        )

        print(product["itemName"])