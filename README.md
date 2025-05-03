# Discord AI Bot

Bot Discord yang menggunakan teknologi AI untuk berinteraksi dengan pengguna. Bot ini dirancang untuk memberikan respons yang cerdas dan kontekstual menggunakan berbagai model AI dan tools.

## Tool yang dapat digunakan

- get-set Knowledge
- task management
- issue management
- create issue channel
- web search

## Teknologi yang Digunakan

- **Discord.py**: Framework utama untuk bot Discord
- **LangChain**: Framework untuk pengembangan aplikasi berbasis LLM
- **Groq**: Provider LLM untuk generasi teks
- **Transformers**: Embedding untuk RAG
- **Supabase**: Database
- **DuckDuckGo Search**: Untuk pencarian informasi real-time

## Struktur Proyek

```
.
├── src/
│   ├── agent/          # Komponen AI agent
│   ├── config/         # Konfigurasi aplikasi
│   ├── data/           # Data dan resources
│   ├── services/       # Layanan utama
│   ├── utils/          # Utilitas dan helper
│   └── app.py          # Entry point aplikasi
├── logs/               # File log
├── Dockerfile          # Konfigurasi Docker
├── Architecture.drawio # Diagram Arsitektur
└── requirements.txt    # Dependensi Python
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

## Lisensi

[MIT License](LICENSE)
