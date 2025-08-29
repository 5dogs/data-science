(() => {
  'use strict';

  // === プロセス管理のアクション実行前イベント ===
  // kintoneのプロセス管理で「売掛登録」という名前のアクションボタンがクリックされた時に発火します
  kintone.events.on('app.record.detail.show', (event) => {
    console.log('[INFO] レコード詳細画面表示イベント発生');
    const record = event.record;
    
    const buttonId = 'custom_button_call_cf_urikake'; // ボタン要素のID（ユニークなもの）

    // ボタンが既に存在する場合は追加しない (画面表示が更新される場合などの二重描画防止)
    if (document.getElementById(buttonId)) {
      return event;
    }
    
    console.log("!record.仕訳帳リンク.value:001 ", !record.仕訳帳リンク.value)
    console.log("!record.仕訳帳リンク.value:002 ", record.仕訳帳リンク.valu!="")
    console.log("!record.仕訳帳リンク.value:002 ", record.仕訳帳リンク.value==="")
    console.log("!record.仕訳帳リンク.value:003 ", record.仕訳帳リンク.valu)
    console.log("仕訳帳リンク: ", record.仕訳帳リンク.value)
    if (record.仕訳帳リンク.value) {
      return event
    }
    

    // ボタン要素を作成
    const myButton = document.createElement('button');
    myButton.id = buttonId;
    myButton.innerText = '売掛登録実行'; // ボタンに表示されるテキスト
    myButton.classList.add('kintoneplugin-button-normal');
    
    
    // クリックされたアクション名が「売掛登録」の場合のみAPI呼び出しを実行
    // --- ボタンクリック時の処理 ---
    myButton.onclick = async () => {
      console.log('[INFO] 「売掛登録実行」ボタンがクリックされました。');
      if (!confirm('売掛登録処理を開始します。よろしいですか？')) {
        console.log('[INFO] 処理がキャンセルされました。');
        return;
      }
      alert('処理を開始します。APIを呼び出します...');

      myButton.disabled = true;
      myButton.innerText = '処理中...';

      // レコードデータを取得
      // event.record にはプロセス実行"前"のデータが含まれます。
      // 通常はこのデータで十分ですが、もし実行前の画面上の最新データが必要な場合は
      // const currentRecord = kintone.app.record.get().record; を使ってください。
      const record = event.record;
      const recordId = record.$id.value; // レコードIDは $id から取得します

      console.log("[DEBUG] 使用するレコードデータ:", record);

      // --- freee API に送信するデータを抽出 ---
      // フィールドコードが正しいか確認してください
      const invoiceDate = record.請求日.value;
      const notes = record.備考.value;
      const dueDate = record.最終入金予定日.value;
      const companyName = record.事業所名.value;
      const partnerName = record.請求先.value || ''; // 請求先（取引先名）
      const totalAmount = record.料金_税込.value || ''; // 金額

      // 抽出したデータを確認（ログ出力）
      console.log("【API送信用データ】");
      console.log("Kintone Record ID:", recordId);
      console.log("入金予定日:", dueDate);
      console.log("事業所名:", companyName);
      console.log("請求日:", invoiceDate);
      console.log("請求先:", partnerName);
      console.log("請求金額合計:", totalAmount);
      console.log("備考:", notes);
      // --- データ抽出ここまで ---

      // --- 入力データ検証 (簡易) ---
      if (!invoiceDate || !partnerName || !totalAmount || !dueDate || !companyName) {
          console.error("[ERROR] API呼び出しに必要なデータがKintoneレコードに不足しています。");
          event.error = 'API呼び出しに必要なデータ（請求日、入金予定日、事業所名、請求先、料金）がレコードに設定されていません。確認してください。';
          alert(event.error);
          return event; // エラーメッセージを表示し、プロセスを中断
      }
      // --- 検証ここまで ---

      // APIに送信するデータオブジェクトを作成
      const postData = {
        recordId: String(recordId), // レコードIDは文字列にするのが無難
        invoiceDate,
        dueDate,
        partnerName,
        companyName,
        notes,
        totalAmount: String(totalAmount), // 金額も文字列にするのが無難
      };
      console.log("[DEBUG] 外部APIへの送信データ:", postData);

      try {
        console.log('[INFO] 外部API (Cloud Function) 呼び出し開始...');
        // 外部API (Cloud Function) にデータ送信
        const proxyResponse = await kintone.proxy(
          'https://freee-api-2-kintone-907975870833.asia-northeast1.run.app/invoices', // Cloud FunctionのエンドポイントURL
          'POST',
          { 'Content-Type': 'application/json' },
          postData // オブジェクトを直接渡す (kintone.proxyが内部でJSON文字列化します)
        );

        console.log('[DEBUG] 外部API Raw Response:', proxyResponse); // [body, status, headers] の配列

        // レスポンスを分割して取得
        const [body, status, headers] = proxyResponse;
        console.log(`[INFO] 外部API Response Status: ${status}`);
        console.log(`[DEBUG] 外部API Response Body: ${body}`);

        // 外部API呼び出しが成功したか (HTTPステータスコード 2xx) を確認
        if (status >= 200 && status < 300) {
          // API呼び出し成功
          console.log('[INFO] 外部API呼び出し成功。');
          alert('売掛登録が完了しました。ステータスが更新されます。');
          location.reload()
          // ★★★ ここでKintoneのプロセスを続行させるため、eventをそのまま返す ★★★
          // Kintoneが自動的にステータスを次の段階に進めます
          return event;

        } else {
          // API呼び出し失敗 (ステータスコードが2xx以外)
          console.error(`[ERROR] 外部API呼び出し失敗。Status: ${status}`);
          // Kintoneプロセスを中断し、エラーメッセージを表示
          event.error = `売掛登録APIの呼び出しに失敗しました (Status: ${status})。`;
          // レスポンスボディからエラー詳細を取得試行
          try {
              const errorBody = JSON.parse(body);
              event.error += `\n詳細: ${errorBody.error || errorBody.message || body}`;
          } catch (parseError) {
              event.error += `\n詳細: ${body}`; // JSONでなければそのまま表示
          }
          alert(event.error);
          return event; // event.error を設定して event を返すとプロセスが中断される
        }

      } catch (error) {
        // kintone.proxy 自体のエラー（ネットワークエラー、URL間違いなど）
        console.error('[ERROR] kintone.proxy 呼び出し中にエラー:', error);
        event.error = '売掛登録APIへの接続中にエラーが発生しました。';
        // エラーオブジェクトに message があれば詳細に追加
        if (error && error.message) {
            event.error += `\n詳細: ${error.message}`;
        }
        alert(event.error);
        return event; // プロセスを中断
      }

    }

    // ボタンをヘッダーメニュースペースに追加
    const headerMenuSpace = kintone.app.record.getHeaderMenuSpaceElement();
    if (headerMenuSpace) {
      headerMenuSpace.appendChild(myButton);
    } else {
      console.warn('[WARN] ヘッダーメニューのスペース要素が取得できませんでした。ボタンは追加されません。');
    }
    return event;
  });

})();