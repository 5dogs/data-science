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
        "app": 900,
        "record": {
            "会社名_マスタ登録なし": {"value": form_values[0]},
            "お名前_2_マスタ登録なし": {"value": form_values[1]},
            "メールアドレス_マスタ登録なし": {"value": form_values[2]},
            "コンサル予約時の質問": {"value": form_values[3]},
            "受付日時": {"value": created_at},
            "予約開始時刻": {"value": start_datetime},
            "予約終了時刻": {"value": end_datetime},
            "管理用ID": {"value": event_id}
        }
    }
    api_request("POST", URL_RECORD, ADMIN_API_TOKEN, record_data)

# 顧客マスタを取得し、該当のメールアドレスが存在するか確認
def fetch_customer_master(form_values, event_id, start_datetime, end_datetime, created_at):
    params = {"app": 929, "fields": ["メールアドレス"]}
    data = api_request("GET", URL_RECORDS, CUSTOMER_LIST_API_TOKEN, params)
    
    if data:
        email_list = [record['メールアドレス']['value'] for record in data['records']]
        if form_values[2] in email_list:
            print(f"{form_values[2]} はリストにあります。処理をスキップします。")
        else:
            register_not_found_customer(form_values, event_id, start_datetime, end_datetime, created_at)



# 新規ミーティングを登録
def register_new_meeting(request_json):
    event = request_json["event"]
    form_values = [field["value"] for field in event["form"]]
    fetch_customer_master(form_values, event["id"], event["local_start_datetime"], event["local_end_datetime"], event["created_at"])

    record_data = {
        "app": 900,
        "record": {
            "受講者番号": {"value": form_values[2]},
            "コンサル予約時の質問": {"value": form_values[3]},
            "受付日時": {"value": event["created_at"]},
            "予約開始時刻": {"value": event["local_start_datetime"]},
            "予約終了時刻": {"value": event["local_end_datetime"]},
            "管理用ID": {"value": event["id"]}
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
            "app": 900,
            "id": delete_id,
            "record": {
                "キャンセル日時": {"value": cancel_date},
                "面談予約状況": {"value": "キャンセル"}
            }
        }
        api_request("PUT", URL_RECORD, ADMIN_API_TOKEN, update_data)

# 削除対象のレコード番号を取得
def fetch_delete_record(delete_record_id):
    params = {
        "app": 900,
        "query": f'管理用ID = "{delete_record_id}"',
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
