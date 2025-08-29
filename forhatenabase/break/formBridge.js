const KINTONE_SUBDOMAIN = "break-c";  // APIトークン（各アプリ用に設定）
const API_TOKEN_FORM = "Zk7LxahaKZeU4n1fNUcyOtLinUtu3zEWpTUOhFNf";  // フォーム流入履歴アプリのAPIトークン
const API_TOKEN_FRONT = "cESdRDPcYd13Hg0IG2dILuT0sHabSVmjzdeZ4FBD"; // フロントセミナーアプリのAPIトークン

const FORM_HISTORY_APP_ID = 147; // フォーム流入履歴アプリID
const FRONT_SEMINAR_APP_ID = 152; // フロントセミナーアプリID

// フォーム流入履歴アプリIDのレコード追加イベントを監視
kintone.events.on(["app.record.create.submit.success"], async (event) => {
    const record = event.record;
    const email = record.メールアドレス.value;
    const formName = record.フォーム識別コード.value;
    const entryDate = record.流入日.value;

    try {
        const existingRecord = await getFrontSeminarRecord(email);

        if (existingRecord) {
            // 既存レコードがあれば更新
            await updateFrontSeminarRecord(existingRecord.id, formName, entryDate);
        } else {
            // 既存レコードがなければ新規作成
            await createFrontSeminarRecord(email, formName, entryDate);
        }
    } catch (error) {
        console.error("エラー:", error);
    }

    return event;
});

async function getFrontSeminarRecord(email) {
    const query = `email="${encodeURIComponent(email)}"`;
    const url = `https://${KINTONE_SUBDOMAIN}.cybozu.com/k/v1/records.json?app=${FRONT_SEMINAR_APP_ID}&query=${query}`;

    try {
        const response = await fetch(url, {
            method: "GET",
            headers: {
                "X-Cybozu-API-Token": API_TOKEN_FRONT,
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`APIエラー: ${response.statusText}`);
        }

        const data = await response.json();
        return data.records.length > 0 ? data.records[0] : null;
    } catch (error) {
        console.error("レコード取得エラー:", error);
        throw error;
    }
}

async function updateFrontSeminarRecord(recordId, formName, entryDate) {
    const url = `https://${KINTONE_SUBDOMAIN}.cybozu.com/k/v1/record.json`;

    const body = {
        app: FRONT_SEMINAR_APP_ID,
        id: recordId,  // idを使用
        record: {
            formName: { value: formName },
            entryDate: { value: entryDate }
        }
    };

    try {
        await fetch(url, {
            method: "PUT",
            headers: {
                "X-Cybozu-API-Token": API_TOKEN_FRONT,
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body)
        });
    } catch (error) {
        console.error("レコード更新エラー:", error);
        throw error;
    }
}

async function createFrontSeminarRecord(email, formName, entryDate) {
    const url = `https://${KINTONE_SUBDOMAIN}.cybozu.com/k/v1/record.json`;

    const body = {
        app: FRONT_SEMINAR_APP_ID,
        record: {
            email: { value: email },
            formName: { value: formName },
            entryDate: { value: entryDate }
        }
    };

    try {
        await fetch(url, {
            method: "POST",
            headers: {
                "X-Cybozu-API-Token": API_TOKEN_FRONT,
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body)
        });
    } catch (error) {
        console.error("レコード作成エラー:", error);
        throw error;
    }
}
