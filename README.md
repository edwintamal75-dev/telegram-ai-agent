# Telegram AI Agent

Proyek awal untuk membuat AI agent yang bisa menjadi admin grup Telegram, membalas pesan, membuat caption, menjadwalkan konten, dan memposting ke channel Telegram. Integrasi X dan Instagram disiapkan sebagai tahap lanjutan lewat modul placeholder.

## Fitur Tahap 1

- Bot Telegram untuk grup dan channel.
- Balasan otomatis dengan AI.
- Perintah membuat caption konten.
- Draft posting ke database SQLite.
- Approval posting sebelum dikirim.
- Jadwal posting otomatis.
- Mode `DRY_RUN` untuk mencoba tanpa mengirim ke Telegram/OpenAI.

## Struktur

```text
telegram-ai-agent/
  .env.example
  requirements.txt
  src/
    agent/
      config.py
      database.py
      llm.py
      scheduler.py
      telegram_bot.py
      main.py
```

## Cara Menjalankan

1. Buat bot lewat `@BotFather` di Telegram.
2. Masukkan bot ke grup atau channel.
3. Jadikan bot sebagai admin.
4. Salin konfigurasi:

```powershell
Copy-Item .env.example .env
```

5. Isi nilai di `.env`:

```env
TELEGRAM_BOT_TOKEN=isi_token_bot
TELEGRAM_CHANNEL_ID=@nama_channel_atau_chat_id
OPENAI_API_KEY=isi_openai_api_key
```

6. Jalankan bot:

```powershell
python -m src.agent.main
```

Jika perintah `python` di Windows belum terbaca, pakai path Python langsung:

```powershell
& "C:\Users\User\AppData\Local\Python\bin\python.exe" -m src.agent.main
```

## Perintah Bot

- `/start` menampilkan status bot.
- `/caption topik konten` membuat caption dengan AI.
- `/post isi konten` membuat draft posting.
- `/xpost isi konten` membuat draft posting ke X.
- `/postall isi konten` membuat draft posting ke Telegram dan X.
- `/photo URL_GAMBAR caption` membuat draft posting dengan gambar.
- `/pending` melihat draft yang belum dikirim.
- `/approve ID` mengirim draft ke channel.
- `/schedule YYYY-MM-DD HH:MM isi konten` menjadwalkan posting.
- `/schedulephoto YYYY-MM-DD HH:MM URL_GAMBAR caption` menjadwalkan posting gambar.
- `/cancel ID` membatalkan draft.

## Auto Posting Harian

Bot bisa posting otomatis beberapa kali sehari jika variable ini diaktifkan di Railway:

```env
AUTO_DAILY_ENABLED=true
AUTO_DAILY_TIMES=08:00,15:00,20:00
```

Slot default:

- `08:00` konten pembuka/jadwal/topik bola hari ini.
- `15:00` transfer, berita klub, atau opini singkat.
- `20:00` big match, prediksi, atau pertanyaan diskusi.

Bot membuat teks dengan AI. Untuk berita atau skor aktual, tetap sebaiknya dicek dulu sebelum diposting agar tidak keliru.

## Catatan Instalasi

Versi awal ini tidak membutuhkan `pip install`. Integrasi Telegram dan OpenAI dipanggil langsung memakai standard library Python.

## Deploy ke Railway

1. Buat project baru di Railway.
2. Pilih **Deploy from GitHub repo** jika proyek sudah di-upload ke GitHub.
3. Jika belum pakai GitHub, upload folder `telegram-ai-agent` ke repo GitHub dulu.
4. Di Railway, buka tab **Variables**.
5. Tambahkan variable berikut:

```env
DRY_RUN=false
TELEGRAM_BOT_TOKEN=isi_token_bot_dari_botfather
TELEGRAM_CHANNEL_ID=@matchdayai
OPENAI_API_KEY=isi_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
DEFAULT_TIMEZONE=Asia/Bangkok
AUTO_REPLY_ENABLED=true
AUTO_DAILY_ENABLED=false
AUTO_DAILY_TIMES=08:00,15:00,20:00
DATABASE_PATH=data/agent.sqlite3
X_ENABLED=false
X_API_KEY=
X_API_KEY_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=
```

## Posting ke X

Aktifkan variable berikut di Railway jika ingin bot bisa posting ke akun X:

```env
X_ENABLED=true
X_API_KEY=consumer_key
X_API_KEY_SECRET=consumer_secret
X_ACCESS_TOKEN=access_token
X_ACCESS_TOKEN_SECRET=access_token_secret
```

Perintah:

```text
/xpost teks untuk X saja
/postall teks untuk Telegram dan X
```

Setelah draft dibuat, kirim `/approve ID`.

6. Railway akan membaca `Procfile` dan menjalankan:

```text
python -m src.agent.main
```

Gunakan service bertipe worker/background process, bukan website statis.

## Catatan API

- Telegram adalah integrasi pertama yang paling mudah dan realistis.
- X butuh X API resmi.
- Instagram butuh akun Professional/Business yang terhubung ke Facebook Page dan Instagram Graph API.
- Jangan membagikan token API ke orang lain atau memasukkannya ke Git.
