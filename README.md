# Discord Music Bot

Un bot de música para Discord interactivo y moderno, escrito en Python utilizando discord.py y yt-dlp. Cuenta con soporte para YouTube (búsquedas, canciones y listas de reproducción), Spotify (canciones, álbumes y playlists) y un panel de control interactivo con botones.

---

## Características
- **Panel de control con botones:** Controla la reproducción, volumen, bucles, mezclas y cola de reproducción directamente desde el chat de Discord.
- **Soporte de Spotify:** Pega enlaces de canciones, álbumes o playlists de Spotify para cargarlas automáticamente.
- **Soporte de YouTube:** Reproduce enlaces directos, listas de reproducción o realiza búsquedas por nombre de canción.
- **Controles avanzados:** Bucle (Loop), mezcla de cola (Shuffle), historial de canciones (Back) y reproducción automática (AutoPlay).

---

## Requisitos Previos

Antes de ejecutar el bot, asegúrate de tener instalado lo siguiente:

1. **Python 3.8+**
2. **FFmpeg** (Debe estar instalado en el sistema y agregado a las variables de entorno / PATH).
   - Windows: Puedes descargarlo desde [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) o instalarlo vía Chocolatey/Scoop: `choco install ffmpeg` o `scoop install ffmpeg`.
   - Linux (Ubuntu/Debian): `sudo apt update && sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`

---

## Instalación y Configuración

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/GermanSmigoski/discord-bot.git
   cd discord-bot
   ```

2. **Instalar dependencias:**
   Puedes instalar las dependencias necesarias ejecutando:
   ```bash
   pip install -r requirements.txt
   ```
   (Las dependencias principales son `discord.py`, `yt-dlp`, `python-dotenv` y `requests`).

3. **Configurar las variables de entorno:**
   Crea un archivo llamado `.env` en la raíz del proyecto (este archivo está ignorado en git por seguridad) y añade tu token de Discord Bot:
   ```env
   DISCORD_TOKEN=TuTokenDeDiscordAqui
   ```
   > **Nota:** Recuerda activar el **Message Content Intent** en el portal de desarrolladores de Discord (Discord Developer Portal -> Bot -> Privileged Gateway Intents).

---

## Comandos de Texto

El prefijo por defecto es `!`. Los comandos disponibles en el chat son:

- **`!play <nombre o URL>`**: Conecta el bot a tu canal de voz y reproduce la canción o lista especificada.
- **`!pause`**: Alterna entre pausar y reanudar la reproducción actual.
- **`!skip`**: Salta la canción en reproducción.
- **`!stop`**: Detiene la reproducción, vacía la cola y desconecta al bot del canal de voz.

---

## Panel de Control Interactivo

Cuando reproduces una canción, el bot enviará un panel interactivo con los siguientes controles mediante botones:

### Fila 1 (Controles de reproducción):
- `🔉` **Down**: Baja el volumen del bot.
- `⏮️` **Back**: Vuelve a reproducir la canción anterior desde el historial.
- `⏯️` **Resume**: Pausa o reanuda la música.
- `⏭️` **Skip**: Salta a la siguiente canción en la cola.
- `🔊` **Up**: Sube el volumen del bot.

### Fila 2 (Controles de Cola y Modos):
- `🔀` **Shuffle**: Mezcla aleatoriamente el orden de las canciones en la cola.
- `🔁` **Loop**: Repite la canción actual en bucle.
- `⏹️` **Stop**: Detiene la música, vacía la cola y desconecta el bot.
- `🔄` **AutoPlay**: Continúa reproduciendo música automáticamente.
- `📑` **Playlist**: Muestra una ventana efímera con las próximas 10 canciones en la cola.

### Fila 3 (Gestión de Cola):
- `🗑️` **Vaciar Lista**: Elimina todas las canciones de la lista de reproducción de forma rápida.
