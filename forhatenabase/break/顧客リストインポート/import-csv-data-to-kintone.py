import pandas as pd
import requests
import time

# 入力ファイル
fields_csv = 'kintone_fields_break_kokyaku.csv'
data_csv = 'BREAKデータ移行 - 顧客リスト (8).csv'#C:\Users\takui\forhatenabase\break\顧客リストインポート\BREAKデータ移行 - 顧客リスト (5).csv

# アプリ設定（あとで置き換えてください）
API_TOKEN = 'nC1nrNfzEV6RpnfWUMjfbiiGqzKJ8RGJ0I4fkxk8'
APP_ID = '9'
DOMAIN = 'break-c.cybozu.com'  # 例: 'xxxx.cybozu.com'

# フィールドコード一覧を取得（1列目）
field_codes = pd.read_csv(fields_csv, header=None)[0].tolist()

# 顧客データ読み込み
df = pd.read_csv(data_csv)

# 最大件数（Kintoneの制限）
MAX_RECORDS_PER_REQUEST = 100

# レコード作成関数
def build_record(row):
    record = {}
    table_values = {}

    for col in df.columns:
        if col in field_codes:
            if '.' in col:
                table_name, field_inside = col.split('.', 1)
                if table_name not in table_values:
                    table_values[table_name] = {}
                table_values[table_name][field_inside] = {"value": row[col] if pd.notna(row[col]) else ""}
            else:
                record[col] = {"value": row[col] if pd.notna(row[col]) else ""}

    for table_name, fields in table_values.items():
        record[table_name] = {"value": [{"value": fields}]}

    return record

# API送信関数
def post_records(records):
    url = f"https://{DOMAIN}/k/v1/records.json"
    headers = {
        "X-Cybozu-API-Token": API_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "app": APP_ID,
        "records": records
    }
    response = requests.post(url, headers=headers, json=payload)
    print(response.status_code, response.json())
    return response

# バッチ処理
all_records = [build_record(row) for _, row in df.iterrows()]
for i in range(0, len(all_records), MAX_RECORDS_PER_REQUEST):
    batch = all_records[i:i + MAX_RECORDS_PER_REQUEST]
    print(f"Uploading records {i + 1} to {i + len(batch)}...")
    res = post_records(batch)
    time.sleep(3)  # 過負荷対策
