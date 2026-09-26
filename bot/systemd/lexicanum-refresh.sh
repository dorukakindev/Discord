#!/usr/bin/env bash
# Gece tazeleme: repo'yu main'e çeker, index + FTS gövde indeksini
# yeniden üretir, botu restart eder. systemd lexicanum-refresh.service
# üzerinden root koşar; veri dosyaları lexicanum kullanıcısıyla yazılır.
# Kod deploy'u kasıtlı yapılmaz — README'deki elle güncelleme akışı korunur.
set -u
REPO=/opt/lexicanum-repo
BOT=/opt/lexicanum

echo "== $(date -Is) refresh başladı"

if cd "$REPO"; then
    runuser -u ubuntu -- git fetch origin main &&
        runuser -u ubuntu -- git reset --hard FETCH_HEAD ||
        echo "!! git güncelleme başarısız — eski tree ile devam"
else
    echo "!! $REPO yok — index yine de denenecek"
fi

cd "$BOT" || exit 1

if runuser -u lexicanum -- python3 "$BOT/build_index.py"; then
    echo "index güncellendi"
else
    echo "!! build_index başarısız — eski index korunuyor"
fi
if runuser -u lexicanum -- env DISCORD_REPO="$REPO" python3 "$BOT/build_fts.py"; then
    echo "fts güncellendi"
else
    echo "!! build_fts başarısız"
fi

systemctl restart lexicanum
echo "== $(date -Is) bitti"
