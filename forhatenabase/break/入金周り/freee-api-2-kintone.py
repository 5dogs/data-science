import functions_framework
import os
import requests
import json
import uuid
import random
from flask import request

# --- 環境変数 ---
kintone_base_url = os.getenv("KINTONE_BASE_URL")
invoices_post_api_token = os.getenv("INVOICE_API_TOKEN")
token_endpoint = os.getenv("TOKEN_ENDPOINT")

# --- Kintone アプリID ---
# 入金管理または請求管理アプリにテーブル形式で入金履歴を記録する場合はpayment_history_app=payment_manage_appと設定する
payment_manage_app = 11    # 入金管理アプリ or 請求管理アプリ (旧 App ID 11)
payment_history_app = payment_manage_app  # 入金履歴アプリ (旧 App ID 132)

# --- Kintone フィールドコード定義 ---
# 入金管理アプリ (payment_manage_app)
FIELD_DEAL_ID = "取引ID"
FIELD_OFFICE_ID = "事業所ID"
FIELD_PAYMENT_STATUS = "入金ステータス"
# (create_dealで使われるが、Kintone JS側から渡される想定のフィールドはここでは定義不要)
# FIELD_COMPANY_NAME = "事業所名"
# FIELD_PARTNER_NAME = "請求先"
# FIELD_NOTES = "備考"
# FIELD_TOTAL_AMOUNT = "料金_税込"
FIELD_RECORD_NUMBER = "レコード番号" # Kintone標準のレコード番号フィールド
FIELD_ISSUE_DATE = "請求日"
FIELD_DUE_DATE = "入金予定日"
FIELD_PAYMENT_TABLE = "入金履歴テーブル" # テーブルのフィールドコード

# 入金履歴テーブル内のフィールドコード
FIELD_TABLE_ISSUE_DATE = "請求日_入金履歴"
FIELD_TABLE_DUE_DATE = "入金予定日_入金履歴"
FIELD_TABLE_PAYMENT_AMOUNT = "入金額_入金履歴"
FIELD_TABLE_PAYMENT_DATE = "入金日_入金履歴"
FIELD_TABLE_PAYMENT_ID = "支払いID_入金履歴"
FIELD_TABLE_PAYMENT_TYPE = "種別_入金履歴"


def api_request(method, url, token, json_data=None):
    headers = {"X-Cybozu-API-Token": token, "Content-Type": "application/json"}
    response = requests.request(method, url, headers=headers, json=json_data)
    if response.status_code != 200:
        print(f"Failed request ({method}): {response.status_code}")
        print(response.text)
    return response.json() if response.status_code == 200 else None


class FreeeAPIClient:
    def __init__(self, token_endpoint):
        """
        コンストラクタでアクセストークン取得用エンドポイントを設定
        """
        self.token_endpoint = token_endpoint
        self.freee_api_token = None
        self.base_url = "https://api.freee.co.jp/api/v1"

    def fetch_access_token(self):
        """
        アクセストークンを取得する関数
        """
        # 開発中は固定のアクセストークンを使用
        # self.freee_api_token = tmp_access_token
        # print(f"アクセストークン (固定): {self.freee_api_token}")
        try:
            response = requests.get(self.token_endpoint)
            if response.status_code == 200:
                response_json = response.json()
                # レスポンスが {"message": "Token processing succeeded.", "status": "success", "access_token": "hoge"}
                # のような形式であることを想定
                if response_json.get("status") == "success" and "access_token" in response_json:
                    self.freee_api_token = response_json["access_token"]
                    print(f"取得したアクセストークン: {self.freee_api_token}")
                    return self.freee_api_token
                else:
                    print("レスポンスからアクセストークンを取得できませんでした。")
                    return None
            else:
                print(f"トークンエンドポイントへのリクエストに失敗しました: {response.status_code}")
                return None
        except Exception as e:
            print(f"アクセストークン取得中にエラーが発生しました: {e}")
            return None


    def fetch_data(self, api_type, company_id=None, year=None, month=None, employee_id=None, limit=50, offset=0, with_no_payroll_calculation=False, update_data=None, date=None, id=None):
        """
        APIタイプに応じて異なるデータを取得または更新する関数

        - dealStatus: 入金管理アプリで入金ステータスの更新
        - checkPayments: 入金履歴アプリにデータの作成
        """
        if not self.freee_api_token:
            print("アクセストークンが設定されていません。fetch_access_token を先に呼び出してください。")
            return {}

        # 事業所IDをどうとるか確認する
        # company_id = 11628732
    
        # APIタイプごとに適切な関数を呼び出す
        if api_type == "invoices":
            return self.create_deal()
        elif api_type == "dealStatus":
            return self.process_deals()
        elif api_type == "checkPayments":
            deal_list = self.fetch_all_deal_ids()
            results = []
            for deal_id, company_id in deal_list:
                if company_id:
                    result = self.check_and_update_payments(deal_id, company_id)
                    results.append({"deal_id": deal_id, "company_id": company_id, "payment_status": result})
            return results
        else:
            print("無効なAPIタイプまたは必要なIDが指定されていません。")
            return {}


    def create_deal(self):
        """
        指定した事業所の取引（収入・支出）を作成する

        Args:
            deal_data (Dict[str, Any]): 作成する取引データ

        Returns:
            Optional[Dict[str, Any]]: 作成された取引情報。失敗した場合は None。
        """
        print("[INFO] create_deal called.")
        post_data = request.json
        record_id = post_data.get('recordId')
        invoice_date = post_data.get('invoiceDate')  # 請求日
        due_date = post_data.get('dueDate')  # 決済期日
        company_name = post_data.get('companyName')  # 事業所名
        notes = post_data.get('notes') # 摘要
        partner_name = post_data.get('partnerName') # 取引先
        amount = post_data.get('totalAmount')  # 合計金額
        print("post_data", post_data)

        # --- 入力チェック ---
        # required_fields = {
        #     "recordId": record_id, "invoiceDate": invoice_date, "dueDate": due_date,
        #     "companyName": company_name, "partnerName": partner_name, "totalAmount": amount
        # }
        # missing = [k for k, v in required_fields.items() if v is None]
        # if missing:
        #     error_msg = f"Missing required fields in request data: {', '.join(missing)}"
        #     print(f"[ERROR] {error_msg}")
        #     return {"error": error_msg}, 400
        # try:
        #     amount_int = int(amount) # 金額を整数に変換（API仕様確認）
        # except (ValueError, TypeError):
        #     error_msg = f"Invalid totalAmount: {amount}. Must be an integer."
        #     print(f"[ERROR] {error_msg}")
        #     return {"error": error_msg}, 400
        # --- 入力チェックここまで ---

        print("[INFO] Fetching company ID from freee...")
        companies_dict = self.fetch_company_id()
        if companies_dict is None:
            return {"error": "Failed to fetch company info from freee"}, 500        
        company_id = companies_dict[company_name]
        if not company_id:
            error_msg = f"Company ID not found for company name: {company_name}"
            print(f"[ERROR] {error_msg}")
            return {"error": error_msg}, 400 # Kintone側のデータ不備の可能性
        print(f"[INFO] Found company ID: {company_id} for name: {company_name}")

        # --- パートナーIDの取得または作成 ---
        print(f"[INFO] Getting or creating partner ID for: {partner_name}")
        partner_id = self.get_partners_id(company_id, partner_name)
        print(f"[INFO] partner_id: {partner_id}")

        if partner_id is None: # パートナーが存在しない場合
            partner_id = self.create_partner(company_id, partner_name)
            if partner_id is None: # パートナー作成に失敗した場合
                    error_msg = f"Failed to get or create partner ID for '{partner_name}'. Aborting deal creation."
                    print(f"[ERROR] {error_msg}")
                    # 失敗したことを示すレスポンスを返す
                    return {"error": error_msg, "details": "Partner creation failed in freee"}, 500

        print(f"[INFO] Using Partner ID: {partner_id}")
        # --- パートナーIDの取得または作成ここまで ---

        url = f"https://api.freee.co.jp/api/1/deals"
        headers = {
            "Authorization": f"Bearer {self.freee_api_token}",
            "Content-Type": "application/json",
            "X-Api-Version": "2020-06-15"
        }

        deal_data = {
            "issue_date": invoice_date,
            "type": "income",  # 収入か支出
            "company_id": company_id,
            "due_date": due_date,
            "partner_id": partner_id,
            "ref_number": "1",
            "details": [
                {
                    "tax_code": 1,
                    "account_item_id": 877419104,
                    "amount": amount,
                    "description": notes,
                    "vat": 800
                }
            ]
        }
        print("deal_data", deal_data)

        response = requests.post(url, headers=headers, json=deal_data)
        response_data = response.json()
        print("respose_data", response_data)
        deal_id = response_data["deal"]["id"]

        put_to_kintone(payment_manage_app, company_id, record_id, deal_id)

        if response.status_code != 201:
            print(f"Failed to create deal. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return None

        return response.json()


    def get_partners_id(self, company_id, partner_name):
        """
        Freee APIからパートナー情報を取得し、name: id形式の辞書を作成する。

        Args:
            api_token (str): Freee APIの認証トークン
            company_id (int): 対象となる事業所のID

        Returns:
            dict: nameをキー、idを値とした辞書
        """
        print(f"[INFO] get_partners_id called for company_id: {company_id}, partner_name: '{partner_name}'")

        url = "https://api.freee.co.jp/api/1/partners"
        headers = {
            "Authorization": f"Bearer {self.freee_api_token}",
            "accept": "application/json",
            "X-Api-Version": "2020-06-15"
        }
        params = {"company_id": company_id}
        try:

            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                print(f"Failed to retrieve partners. Status Code: {response.status_code}")
                print(f"Response: {response.text}")
                return {}

            partners_data = response.json()
            partners = partners_data.get("partners", [])
            print(f"[INFO] Partners list '{partners}'")
            # 名前でIDを検索
            for partner in partners:
                if partner.get("name") == partner_name:
                    partner_id = partner.get("id")
                    print(f"[INFO] Found existing partner '{partner_name}' with ID: {partner_id}")
                    return partner_id

            # name_id_dict = {partner["name"]: partner["id"] for partner in partners if "name" in partner and "id" in partner}
            # print("name_id_dict: ", name_id_dict)
            # partner_id = name_id_dict[partner_name]
            print(f"[INFO] Partner '{partner_name}' not found in existing partners.")
            return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to retrieve partners. Status: {e.response.status_code if e.response else 'N/A'}, Error: {e}")
            if e.response is not None:
                print(f"[ERROR] Response Body: {e.response.text}")
            return None # エラー時はNoneを返す

    def create_partner(self, company_id, partner_name):
        """
        freeeに新しいパートナーを作成し、そのIDを返す。失敗した場合は None を返す。
        """
        print(f"[INFO] Attempting to create new partner '{partner_name}' for company ID {company_id}...")
        url = f"https://api.freee.co.jp/api/1/partners"
        headers = {
            "Authorization": f"Bearer {self.freee_api_token}",
            "Content-Type": "application/json",
            "X-Api-Version": "2020-06-15"
        }
        # freee APIのパートナー作成に必要な最小限のデータ
        # partner_code = str(uuid.uuid4()).replace('-', '')[:6]
        # random_code_int = random.randint(1, 99999999)
        # 文字列に変換 (APIの仕様に合わせて)
        # partner_code = str(random_code_int)        
        payload = {
            "company_id": company_id,
            "name": partner_name
        }
        print(f"[DEBUG] Create Partner URL: {url}")
        print(f"[DEBUG] Create Partner Payload: {json.dumps(payload)}")

        try:
            response = requests.post(url, headers=headers, json=payload)
            print(f"[DEBUG] Create Partner Response Status: {response.status_code}")
            response.raise_for_status() # 201以外でもエラーを発生させる

            response_data = response.json()
            print(f"[DEBUG] Create Partner Response JSON: {response_data}")
            new_partner_id = response_data.get("partner", {}).get("id")

            if new_partner_id:
                print(f"[INFO] Successfully created partner '{partner_name}' with ID: {new_partner_id}")
                return new_partner_id
            else:
                # 201 OKでもIDが返らないケースは通常ないはずだが念のため
                print("[ERROR] Partner created response received, but ID not found in response.")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to create partner '{partner_name}'. Status: {e.response.status_code if e.response else 'N/A'}, Error: {e}")
            if e.response is not None:
                print(f"[ERROR] Response Body: {e.response.text}")
            return None # 作成失敗
        
    def fetch_company_id(self):
        """
        事業所情報を取得し、{ 事業所名 : 事業所ID} の辞書を返す
        """
        url = f"https://api.freee.co.jp/api/1/companies"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.freee_api_token}",
            "X-Api-Version": "2020-06-15"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            companies = response.json().get("companies", [])
            companies_dict = {data["display_name"]: data["id"] for data in companies}
            return companies_dict
        else:
            print(f"事業所情報の取得に失敗しました: {response.status_code}")
            print(response.text)
            return None  


    def check_payments(self, deal_id, company_id):
        """
        Freee APIを叩いて、指定した取引IDのpaymentsが存在するか確認する。
        あれば支払い済み、なければ未支払
    
        Args:
            deal_id (int): 確認対象の取引ID
            company_id (int): 事業所ID
    
        Returns:
            bool: paymentsが存在すればTrue、なければFalse
        """
        url = f"https://api.freee.co.jp/api/1/deals/{deal_id}"
        headers = {
            "Authorization": f"Bearer {self.freee_api_token}",
            "accept": "application/json",
            "X-Api-Version": "2020-06-15"
        }
        params = {"company_id": company_id}
    
        response = requests.get(url, headers=headers, params=params)
    
        if response.status_code != 200:
            print(f"Failed to retrieve deal. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return False  # APIエラー時はFalseを返す
    
        deal_data = response.json()
        payments = deal_data.get("deal", {}).get("payments", [])
        
        return bool(payments) 
    

    def process_deals(self):
        """
        複数のdealを処理し、paymentsがあればkintoneにPUTする。
        つまり入金消し込み状況を連携する

        Returns:
            dict: 処理結果の詳細を含むJSONオブジェクト
        """
        deal_dict = request.json
        print("deal_dict", deal_dict)

        results = []  # 処理結果を格納するリスト

        for deal in deal_dict["records"]:
            record_id = deal["recordNumber"]
            company_id = deal["companyId"]
            deal_id = deal["dealId"]
            self.check_and_update_payments(deal_id, company_id)
    
            try:
                if self.check_payments(deal_id, company_id):
                    print(f"Payments found for deal_id {deal_id}. Updating kintone...")
                    update_deal_kintone(payment_manage_app, record_id)
                    results.append({
                        "recordNumber": record_id,
                        "dealId": deal_id,
                        "status": "Payment found and updated in Kintone"
                    })
                else:
                    print(f"No payments found for deal_id {deal_id}. Skipping...")
                    results.append({
                        "recordNumber": record_id,
                        "dealId": deal_id,
                        "status": "No payments found"
                    })
            except Exception as e:
                print(f"Error processing deal_id {deal_id}: {e}")
                results.append({
                    "recordNumber": record_id,
                    "dealId": deal_id,
                    "status": f"Error occurred: {str(e)}"
                })
    
        # 全処理の結果をJSON形式でまとめて返す
        response_json = {
            "status": "completed",
            "results": results
        }
        print("Process results:", json.dumps(response_json, indent=4, ensure_ascii=False))
        return response_json


    def fetch_all_deal_ids(self):
        get_url = "https://break-c.cybozu.com/k/v1/records.json"
        params = {
            "app": payment_manage_app,
            "fields": [FIELD_DEAL_ID, FIELD_OFFICE_ID]
        }
        data = api_request("GET", get_url, invoices_post_api_token, params)
        deal_list = [
            (record[FIELD_DEAL_ID]['value'], record[FIELD_OFFICE_ID]['value']) 
            for record in data['records'] if record[FIELD_DEAL_ID]['value']
        ]
        return deal_list


    def check_and_update_payments(self, deal_id, company_id):
        """
        Freee APIを叩いて、指定した取引IDのpaymentsが存在するか確認する。
        あれば支払い済み、なければ未支払

        Args:
            deal_id (int): 確認対象の取引ID
            company_id (int): 事業所ID

        Returns:
            bool: paymentsが存在すればTrue、なければFalse
        """
        url = f"https://api.freee.co.jp/api/1/deals/{deal_id}"
        headers = {
            "Authorization": f"Bearer {self.freee_api_token}",
            "accept": "application/json",
            "X-Api-Version": "2020-06-15"
        }
        params = {"company_id": company_id}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Failed to retrieve deal. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

        deal_data = response.json()
        payments = deal_data.get("deal", {}).get("payments", [])
        issue_date = deal_data.get("deal", {}).get("issue_date", [])
        due_date = deal_data.get("deal", {}).get("due_date", [])
        deal_id = deal_data.get("deal", {}).get("id",[])

        query_url = f'https://break-c.cybozu.com/k/v1/records.json'
        headers = {
            "X-Cybozu-API-Token": invoices_post_api_token,
            "Content-Type": "application/json"
        }
        # 入金履歴アプリのレコード番号と取引IDの辞書を作成する(どのレコードに書き込むか取りたいため)
        params = {"app": payment_history_app, "fields": [FIELD_RECORD_NUMBER, FIELD_DEAL_ID]}
        data = api_request("GET", query_url, invoices_post_api_token, params)
        id_to_record_dict = {
            record[FIELD_DEAL_ID]['value']: record[FIELD_RECORD_NUMBER]['value']
            for record in data.get('records', [])
        }

        record_id = id_to_record_dict.get(str(deal_id))
        if not record_id:
            record_id = self.create_record(payment_history_app, deal_id, issue_date, due_date)  # 新規作成しrecord_idを取得
            if not record_id:
                print("Failed to create new record in Kintone.")
                return False

        for payment in payments:
            payment_date = payment["date"]
            payment_amount = payment["amount"]
            payment_id = payment["id"]
            from_walletable_type = payment["from_walletable_type"]
            payment_type = self.get_walletable_type_label(from_walletable_type)

            payments_data_put_to_kintone(payment_history_app, record_id, issue_date, due_date, payment_date, payment_amount, payment_id, payment_type)

        return {
            "deal_id": deal_id,
            "company_id": company_id,
            "status": "paid" if payments else "unpaid",
            "payments": payments
        }


    def get_walletable_type_label(self, from_walletable_type):
        """
        from_walletable_type の値に基づき、対応する名称を取得する。

        Args:
            from_walletable_type (str): freee API から取得した from_walletable_type の値

        Returns:
            str: 対応する名称
        """
        walletable_type_mapping = {
            "bank_account": "銀行口座",
            "credit_card": "クレジットカード",
            "wallet": "現金",
            "private_account_item": "プライベート資金"
        }

        return walletable_type_mapping.get(from_walletable_type, "不明")


    def create_record(self, app_id, deal_id, issue_date, due_date):
        """
        Kintoneに新規レコードを作成し、作成したレコードのIDを返す。

        Args:
            app_id (int): KintoneアプリID
            deal_id (str): 取引ID
            issue_date (str): 請求日
            due_date (str): 入金予定日

        Returns:
            int: 作成されたレコードのID (失敗した場合は None)
        """
        url = "https://break-c.cybozu.com/k/v1/record.json"
        payload = {
            "app": app_id,
            "record": {
                FIELD_DEAL_ID: {"value": deal_id},
                FIELD_ISSUE_DATE: {"value": issue_date},
                FIELD_DUE_DATE: {"value": due_date}
            }
        }

        response = api_request("POST", url, invoices_post_api_token, json_data=payload)

        if not response or "id" not in response:
            print(f"Failed to create record: {response}")
            return None

        return response["id"]



def put_to_kintone(app_id, company_id, record_id, deal_id):
    """
    Kintone API を使用してデータを投稿
    Args:
        app_id (int): Kintone アプリの ID
        company_id: 事業所ID
        record_id (int): レコードID
        deal_id (int): 請求書ID
    """
    url = f"{kintone_base_url}/k/v1/record.json"
    payload = {
        "app": app_id,
        "id": record_id,
        "record": {
            FIELD_DEAL_ID: {"value": deal_id},
            FIELD_OFFICE_ID: {"value": company_id},
        }
    }
    headers = {
        "X-Cybozu-API-Token": invoices_post_api_token,
        "Content-Type": "application/json"
    }
    response = requests.put(url, json=payload, headers=headers)
    if response.status_code == 200:
        print("Kintone に正常に投稿されました")
    else:
        print(f"Kintone への投稿に失敗しました: {response.status_code}")
        print(response.text)


def payments_data_put_to_kintone(app_id, record_id, issue_date, due_date, payment_date, payment_amount, payment_id, payment_type):
    """
    Kintoneのテーブルに支払いデータを新しい行として追加。ただし、同じ支払いIDが既に存在する場合は更新をスキップ。

    Args:
        app_id (int): KintoneアプリID
        record_id (int): レコードID
        payment_date (str): 支払い日
        payment_amount (int): 支払い金額
        payment_id (int): 支払いID
    """
    # 既存のテーブルデータを取得
    get_url = "https://break-c.cybozu.com/k/v1/record.json"
    params = {
        "app": app_id,
        "id": record_id
    }

    # GETリクエストでデータ取得
    response_get = api_request("GET", get_url, invoices_post_api_token, json_data=params)
    print("payments_data_put_to_kintone >> response_get: ", response_get)

    # エラーチェック
    if not response_get:
        print("Failed to retrieve record: Response is None")
        return

    # レスポンスデータからレコードを取得
    record = response_get.get("record", {})
    print("payments_data_put_to_kintone >> record: ", record)
    if not record:
        print("No record found in the response.")
        return

    # テーブルデータを取得
    table_data = record.get(FIELD_PAYMENT_TABLE, {}).get("value", [])
    print("payments_data_put_to_kintone >> table_data: ", table_data)
    print(f"Current table data: {table_data}")

    # 支払いIDの重複を確認
    for row in table_data:
        existing_payment_id = row.get("value", {}).get(FIELD_TABLE_PAYMENT_ID, {}).get("value")
        if existing_payment_id == str(payment_id):
            print(f"Payment ID {payment_id} already exists. Skipping update.")
            return

    # 新しい行を追加
    new_row = {
        "value": {
            FIELD_TABLE_ISSUE_DATE: {"value": issue_date},
            FIELD_TABLE_DUE_DATE: {"value": due_date},
            FIELD_TABLE_PAYMENT_AMOUNT: {"value": payment_amount},
            FIELD_TABLE_PAYMENT_DATE: {"value": payment_date},
            FIELD_TABLE_PAYMENT_ID: {"value": payment_id},
            FIELD_TABLE_PAYMENT_TYPE: {"value": payment_type},
        }
    }
    table_data.append(new_row)

    # テーブル全体を更新
    update_url = "https://break-c.cybozu.com/k/v1/record.json"
    payload = {
        "app": app_id,
        "id": record_id,
        "record": {
            FIELD_PAYMENT_TABLE: {"value": table_data}
        }
    }

    response_put = api_request("PUT", update_url, invoices_post_api_token, json_data=payload)

    if not response_put:
        print("Failed to update record.")
    else:
        print("新しい支払いデータがKintoneに追加されました。")


def update_deal_kintone(app_id, record_id):
    """
    Kintone API を使用してデータを投稿
    Args:
        app_id (int): Kintone アプリの ID
        record_id (int): レコードID
        deal_id (int): 請求書ID
    """
    url = f"{kintone_base_url}/k/v1/record.json"
    payload = {
        "app": app_id,
        "id": record_id,
        "record": {
            FIELD_PAYMENT_STATUS: {"value": "入金済み"},
        }
    }
    headers = {
        "X-Cybozu-API-Token": invoices_post_api_token,
        "Content-Type": "application/json"
    }
    response = requests.put(url, json=payload, headers=headers)
    if response.status_code == 200:
        print("Kintone に正常に投稿されました")
    else:
        print(f"Kintone への投稿に失敗しました: {response.status_code}")
        print(response.text)


@functions_framework.http
def freee_api(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
    Returns:
        The response text.
    """
    # リクエスト URL の最後の部分
    last_segment = request.path.split('/')[-1]
    print(last_segment)

    client = FreeeAPIClient(token_endpoint)
    access_token = client.fetch_access_token()

    if access_token:
        employee_data = client.fetch_data(api_type=last_segment)

        return employee_data
    else:
        print("アクセストークンの取得に失敗しました。")
        return {}, 401 
