FROM python:3.12-slim

# ffmpeg para reproducir el audio, libopus para la voz de discord.py
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libopus0 \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp necesita un runtime de JavaScript para extraer de YouTube; usa deno por defecto
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

WORKDIR /app

# requirements.txt trae discord.py[voice], que agrega PyNaCl y davey (necesarios para voz)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]
