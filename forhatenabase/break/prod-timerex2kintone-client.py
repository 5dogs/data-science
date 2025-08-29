import functions_framework
import requests
import os
from flask import make_response, jsonify

# 環境変数からドメインとAPIトークンを取得
DOMAIN = os.getenv('DOMAIN')
ADMIN_API_TOKEN = os.getenv('ADMINISTRATION_API_TOKEN')
CUSTOMER_LIST_API_TOKEN = os.getenv('CUSTOMER_LIST_API_TOKEN')

# URL 定義
URL_RECORD = f"https://{DOMAIN}.cybozu.com/k/v1/record.json"
URL_RECORDS = f"https://{DOMAIN}.cybozu.com/k/v1/records.json"

# APIリクエストの共通関数
def api_request(method, url, token, json_data=None):
    headers = {"X-Cybozu-API-Token": token, "Content-Type": "application/json"}
    response = requests.request(method, url, headers=headers, json=json_data)
    if response.status_code != 200:
        print(f"Failed request ({method}): {response.status_code}")
        print(response.text)
    return response.json() if response.status_code == 200 else None

# マスタ未登録の顧客を登録する
def register_not_found_customer(form_values, event_id, start_datetime, end_datetime, created_at):
    record_data = {
        "app": 8,
        "record": {
            "会社名_マスタ登録なし": {"value": form_values[0]},
            "面談予約者_マスタ登録なし": {"value": form_values[1]},
            "ふりがな_マスタ登録なし": {"value": form_values[2]},
            "メールアドレス_マスタ登録なし": {"value": form_values[5]},
            "居住地": {"value": form_values[7]},
            "BMP講座受講をどのような形で検討されていますか": {"value": form_values[8] if isinstance(form_values[8], list) else [form_values[8]]},
            "PCを使った業務経験について教えてください": {"value": form_values[9]},
            "現在のご状況を教えてください": {"value": form_values[10]},
            "現在のお仕事の内容やこれから活かしたい過去の経歴をご自由にお書きください": {"value": form_values[11]},
            "Webマーケ習得の目的がございましたらご自由にお書きください": {"value": form_values[12]},
            "無料個別コンサル当日にご相談されたい内容などがございましたらご自由にお書きください": {"value": form_values[13]},
            "コンサル申込日時": {"value": created_at},
            "予約開始時刻": {"value": start_datetime},
            "予約終了時刻": {"value": end_datetime},
            "TimeRex管理用ID": {"value": event_id}
        }
    }
    print("recorddata", record_data)
    api_request("POST", URL_RECORD, ADMIN_API_TOKEN, record_data)


def fetch_customer_master(form_values, event_id, start_datetime, end_datetime, created_at):
    params = {"app": 9, "fields": ["メールアドレス", "レコード番号"]}
    data = api_request("GET", URL_RECORDS, CUSTOMER_LIST_API_TOKEN, params)
    
    if data:
        target_email = form_values[5]
        for record in data['records']:
            email = record.get('メールアドレス', {}).get('value')
            if email and email == target_email:
                record_number = record.get('レコード番号', {}).get('value')
                print(f"マッチしたメールアドレス: {email}, レコード番号: {record_number}")
                return record_number

    print("該当するメールアドレスが見つかりませんでした")
    return None

def register_new_meeting(request_json):
    event = request_json["event"]
    form_values = [field["value"] for field in event["form"]]
    record_number = fetch_customer_master(form_values, event["id"], event["local_start_datetime"], event["local_end_datetime"], event["created_at"])
    print("record_number", record_number)

    if record_number is None:
        print("顧客マスタに該当メールアドレスが見つからなかったため、新規登録を行います")
        register_not_found_customer(form_values, event["id"], event["local_start_datetime"], event["local_end_datetime"], event["created_at"])
        return  # 顧客マスタ未登録者用の処理で完了するため、以降の処理はスキップ

    # 顧客マスタに該当がある場合は、こちらの処理を行う
    record_data = {
        "app": 8,
        "record": {
            "BMP講座受講をどのような形で検討されていますか": {
                "value": form_values[8] if isinstance(form_values[8], list) else [form_values[8]]
            },
            "PCを使った業務経験について教えてください": {"value": form_values[9]},
            "現在のご状況を教えてください": {"value": form_values[10]},
            "現在のお仕事の内容やこれから活かしたい過去の経歴をご自由にお書きください": {"value": form_values[11]},
            "Webマーケ習得の目的がございましたらご自由にお書きください": {"value": form_values[12]},
            "無料個別コンサル当日にご相談されたい内容などがございましたらご自由にお書きください": {"value": form_values[13]},
            "コンサル申込日時": {"value": event["created_at"]},
            "予約開始時刻": {"value": event["local_start_datetime"]},
            "予約終了時刻": {"value": event["local_end_datetime"]},
            "TimeRex管理用ID": {"value": event["id"]},
            "顧客リストアプリレコード番号": {"value": record_number}
        }
    }
    api_request("POST", URL_RECORD, ADMIN_API_TOKEN, record_data)


# キャンセルされたミーティングを更新
def cancel_meeting(request_json):
    cancel_date = request_json["event"]["canceled_at"]
    delete_record_id = request_json["event"]["id"]
    delete_id = fetch_delete_record(delete_record_id)

    if delete_id:
        update_data = {
            "app": 8,
            "id": delete_id,
            "record": {
                "キャンセル日時": {"value": cancel_date},
                # "面談実施ステータス": {"value": "キャンセル"}
            }
        }
        api_request("PUT", URL_RECORD, ADMIN_API_TOKEN, update_data)

# 削除対象のレコード番号を取得
def fetch_delete_record(delete_record_id):
    params = {
        "app": 8,
        "query": f'TimeRex管理用ID = "{delete_record_id}"',
        "fields": ["レコード番号"]
    }
    data = api_request("GET", URL_RECORDS, ADMIN_API_TOKEN, params)
    return data['records'][0]['レコード番号']['value'] if data else None

# Webhook のエントリーポイント
@functions_framework.http
def timerex_to_kintone(request):
    request_json = request.get_json(silent=True)
    print("request_json:", request_json)

    if request_json:
        webhook_type = request_json.get("webhook_type")
        if webhook_type == "event_confirmed":
            register_new_meeting(request_json)
            print("Confirmed event processed.")
        elif webhook_type == "event_cancelled":
            cancel_meeting(request_json)
            print("Cancelled event processed.")
        return make_response(jsonify({"status": "success"}), 200)
    return make_response(jsonify({"status": "error", "message": "Invalid request"}), 400)
