(function() {
    'use strict';


    kintone.events.on('app.record.detail.show', function(event) {
        alert('レコード表示イベント発生');
        console.log(event);

        console.log('[INFO] レコード表示イベント発生');
        console.log('[DEBUG] レコードID:', event.record.$id.value);
        console.log('[DEBUG] レコードタイプ:', event.record.$recordType.value);
    });
})();
