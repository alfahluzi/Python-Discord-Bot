# Discord AI Bot

Bot Discord yang menggunakan teknologi AI untuk berinteraksi dengan pengguna. Bot ini dirancang untuk memberikan respons yang cerdas dan kontekstual menggunakan berbagai model AI dan tools.

## Fitur Utama

- Integrasi dengan Discord menggunakan discord.py
- Hot-reload untuk pengembangan yang lebih cepat
- Sistem logging yang komprehensif
- Arsitektur modular dan terstruktur
- Dukungan untuk berbagai model AI dan tools

## Teknologi yang Digunakan

- **Discord.py**: Framework utama untuk bot Discord
- **LangChain**: Framework untuk pengembangan aplikasi berbasis LLM
- **Groq**: Provider LLM untuk generasi teks
- **Transformers**: Untuk pemrosesan bahasa alami
- **Supabase**: Database dan backend services
- **DuckDuckGo Search**: Untuk pencarian informasi real-time
- **Watchdog**: Untuk hot-reload selama pengembangan

## Struktur Proyek

```
.
├── src/
│   ├── agent/         # Komponen AI agent
│   ├── config/        # Konfigurasi aplikasi
│   ├── data/          # Data dan resources
│   ├── services/      # Layanan utama
│   ├── utils/         # Utilitas dan helper
│   └── app.py         # Entry point aplikasi
├── logs/              # File log
├── Dockerfile         # Konfigurasi Docker
└── requirements.txt   # Dependensi Python
```

## Cara Penggunaan

1. Clone repositori ini
2. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```
3. Setup environment variables (lihat `.env.example`)
4. Jalankan bot:
   ```bash
   python src/app.py
   ```

## Perintah Bot

- `!ai [pertanyaan]`: Mengajukan pertanyaan ke AI bot

## Pengembangan

Proyek ini mendukung hot-reload, sehingga perubahan kode akan otomatis me-reload bot tanpa perlu restart manual.

## Lisensi

[MIT License](LICENSE)
