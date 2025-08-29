import pandas as pd
import requests


# 入力ファイル
fields_csv = 'kintone_fields_break_kokyaku.csv'
data_csv = '顧客リストテスト.csv'

# アプリ設定（あとで置き換えてください）
API_TOKEN = 'nC1nrNfzEV6RpnfWUMjfbiiGqzKJ8RGJ0I4fkxk8'
APP_ID = '9'
DOMAIN = 'break-c.cybozu.com'  # 例: 'xxxx.cybozu.com'

# フィールドコード一覧を取得（1列目）
field_codes = pd.read_csv(fields_csv, header=None)[0].tolist()

# 顧客データ読み込み
df = pd.read_csv(data_csv)




# レコード作成
records = []
for _, row in df.iterrows():
    record = {}
    table_values = {}

    for col in df.columns:
        if col in field_codes:
            if '.' in col:
                table_name, field_inside = col.split('.', 1)                # テーブル形式（例: ヒアリングシート.卒業後の希望）
                if table_name not in table_values:
                    table_values[table_name] = {}
                table_values[table_name][field_inside] = {"value": row[col] if pd.notna(row[col]) else ""}
            else:
                # 通常フィールド
                record[col] = {"value": row[col] if pd.notna(row[col]) else ""}

    # サブテーブル構造を構築
    for table_name, fields in table_values.items():
        record[table_name] = {
            "value": [
                {
                    "value": fields  # 1行分のデータ
                }
            ]
        }

    records.append(record)


# 送信用に整形
payload = {
    "app": APP_ID,
    "records": records
}

# API送信
url = f"https://{DOMAIN}/k/v1/records.json"
headers = {
    "X-Cybozu-API-Token": API_TOKEN,
    "Content-Type": "application/json"
}

res = requests.post(url, headers=headers, json=payload)

print(res.status_code)
print(res.json())
