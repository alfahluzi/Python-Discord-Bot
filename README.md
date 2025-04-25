# Discord Bot dengan Hot Reload

Bot Discord dengan fitur hot reload untuk development yang lebih efisien.

## Penggunaan dengan Docker

### Build Image

```bash
docker build -t discord-bot:latest .
```

### Menjalankan Container

```bash
docker run -d \
  --name discord-bot \
  -e DISCORD_TOKEN=your_token_here \
  discord-bot:latest
```

### Environment Variables

- `DISCORD_TOKEN`: Token Discord bot Anda (wajib)
- `LOG_LEVEL`: Level logging (opsional, default: INFO)

## Development

### Menjalankan Locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Jalankan bot:

```bash
python src/app.py
```

## Fitur

- Hot reload untuk development
- Command prefix: `ai`
- Logging otomatis
