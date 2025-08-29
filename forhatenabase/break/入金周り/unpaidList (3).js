(() => {
    'use strict';

    // レコード一覧の表示後イベント
    kintone.events.on('app.record.index.show', (event) => {
        // 現在のビューIDを取得

        // 指定したビューID（8425183）以外では処理を行わない
        if (event.viewId !== 8425183) {
            return event; // ビューIDが一致しない場合は何もしない
        }
        // 増殖バグを防ぐ
        if (document.getElementById('menu_button2') !== null) {
            return event; // 重複ボタンを作成しない
        }

        // ボタンを作成
        const menuButton = document.createElement('button');
        menuButton.id = 'menu_button2';
        menuButton.innerText = 'ステータスを更新する';

        // ボタンクリック時の処理
        menuButton.onclick = async () => {
          window.alert('ステータス更新APIを呼び出します');
            try {
                // 必要なフィールドの値を取得
                console.log("kintone.app.getFieldElements('事業所ID'): ", kintone.app.getFieldElements('事業所ID'))
                console.log("kintone.app.getFieldElements('仕訳帳リンク'): ", kintone.app.getFieldElements('仕訳帳リンク'))
                const companyIdList = Array.from(kintone.app.getFieldElements('事業所ID')).map((element) => element.innerText.trim());
                const dealIdList = Array.from(kintone.app.getFieldElements('仕訳帳リンク')).map((element) => {
                    const match = element.innerText.match(/deal_id=(\d+)/);
                    return match ? match[1] : null;
                }).filter((dealId) => dealId !== null);
                const recordNumberList = Array.from(kintone.app.getFieldElements('レコード番号')).map((element) => element.innerText.trim());
      
                // 必要なデータが不足している場合、警告を表示
                if (!companyIdList.length || !dealIdList.length || !recordNumberList.length) {
                    window.alert('必要なデータが不足しています');
                    return;
                }

                // 一致しない長さのリストに対してエラーチェック
                // if (companyIdList.length !== dealIdList.length || companyIdList.length !== recordNumberList.length) {
                //     window.alert('事業所ID、dealId、レコード番号の数が一致しません');
                //     return;
                // }

                // 事業所ID、dealId、レコード番号の辞書を作成
                const companyDealDict = companyIdList.map((companyId, index) => ({
                    companyId,
                    dealId: dealIdList[index],
                    recordNumber: recordNumberList[index]
                }));

                console.log('送信データ:', companyDealDict);

                // 外部APIにデータ送信
                const postData = { records: companyDealDict };
                const proxyResponse = await kintone.proxy(
                    'https://freee-api-2-kintone-907975870833.asia-northeast1.run.app/dealStatus', 'POST', 
                    { 'Content-Type': 'application/json' },
                    JSON.stringify(postData)
                );

                // APIレスポンスのログ
                console.log('APIレスポンス:', proxyResponse);
                console.log('APIレスポンス0:', proxyResponse[0]);
                console.log('APIレスポンス1:', proxyResponse[1]);
                console.log('APIレスポンス2:', proxyResponse[2]);
                

                // if (proxyResponse[1] !== 200) {
                //     window.alert('更新できるレコードがありません。');
                //     return;
                // }


                // 完了メッセージを表示
                window.alert('API送信とステータス更新データの処理が完了しました');
                location.reload(); // 成功時にページをリロード
            } catch (error) {
                console.error('エラーが発生しました:', error);
                window.alert('エラーが発生しました。コンソールを確認してください。');
            }
        };

        // レコード一覧のメニューにボタンを追加
        const headerMenuSpace = kintone.app.getHeaderMenuSpaceElement();
        headerMenuSpace.appendChild(menuButton);

        return event;
    });
})();
