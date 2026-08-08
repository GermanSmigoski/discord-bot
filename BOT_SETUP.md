# Configuracion del Bot en Discord

Esta guia explica paso a paso como crear un bot en el portal de desarrolladores de Discord, obtener el token y agregarlo a tu servidor con los permisos necesarios.

---

## Paso 1: Crear la Aplicacion en Discord

1. Ingresa al [Discord Developer Portal](https://discord.com/developers/applications).
2. Inicia sesion con tu cuenta de Discord.
3. Haz clic en el boton **New Application** (Nueva Aplicacion) en la esquina superior derecha.
4. Escribe un nombre para tu bot y acepta los terminos. Haz clic en **Create** (Crear).

---

## Paso 2: Crear el Bot y Obtener el Token

1. En el menu izquierdo de la aplicacion que acabas de crear, selecciona la opcion **Bot**.
2. En la seccion del nombre e icono del bot, haz clic en **Reset Token** (Restablecer Token) y confirma la accion.
3. Copia el token generado inmediatamente.
   - **Importante:** Este token es privado y no debes compartirlo. Debes pegarlo en tu archivo `.env` en el campo `DISCORD_TOKEN`.

---

## Paso 3: Activar los Intents Necesarios

Para que el bot pueda escuchar tus comandos de texto (como `!play`), es obligatorio activar los permisos de contenido de mensajes en el portal:

1. Permanece en la seccion **Bot** del menu izquierdo.
2. Desplazate hacia abajo hasta encontrar la seccion **Privileged Gateway Intents** (Intents de Gateway Privilegiados).
3. Activa la opcion **Message Content Intent** (Intent de Contenido de Mensajes).
4. Guarda los cambios haciendo clic en **Save Changes**.

---

## Paso 4: Invitar al Bot a tu Servidor

Para generar el enlace de invitacion con los permisos correctos para reproducir musica:

1. En el menu izquierdo, selecciona la opcion **OAuth2** y luego haz clic en **URL Generator**.
2. En la cuadricula de **Scopes** (Ambitos), selecciona la casilla:
   - `bot`
3. Al seleccionar `bot`, se abrira abajo una nueva cuadricula de **Bot Permissions** (Permisos del Bot). Selecciona los siguientes permisos:
   - **General Permissions:**
     - `Read Messages/View Channels` (Leer Mensajes/Ver Canales)
   - **Text Permissions:**
     - `Send Messages` (Enviar Mensajes)
     - `Embed Links` (Insertar Enlaces)
     - `Read Message History` (Leer el Historial de Mensajes)
   - **Voice Permissions:**
     - `Connect` (Conectarse)
     - `Speak` (Hablar)
     - `Use Voice Activity` (Usar Actividad de Voz)
4. Copia el enlace que se genera al final de la pagina en la seccion **Generated URL**.
5. Pega ese enlace en tu navegador web, selecciona tu servidor de Discord y haz clic en **Autorizar**.
