# 🤖 BNB Sentinel Bot (Serverless Edition)

Un bot financiero para Telegram diseñado para ejecutarse 100% de manera gratuita en la nube usando una arquitectura orientada a eventos (Serverless). Monitorea precios de criptomonedas, aperturas de mercados globales y filtra noticias RSS de alto impacto.

## 🏗 Arquitectura

El bot ha sido refactorizado para abandonar el polling tradicional y operar bajo:

- **Vercel (Compute):** Funciones Serverless en Python para manejar los comandos de los usuarios vía Webhooks y un Cron Job automático.
- **Supabase (PostgreSQL):** Base de datos en la nube para persistir los usuarios suscritos y mantener un caché de las noticias enviadas, evitando mensajes duplicados.

## 🚀 Guía de Configuración Rápida

Para desplegar tu propio bot gratis, sigue estos pasos:

### 1. Configurar Supabase (Base de Datos)

1. Crea un proyecto gratuito en [Supabase](https://supabase.com/).
2. Ve a la sección **SQL Editor** y ejecuta este snippet para crear las tablas necesarias:

```sql
CREATE TABLE users (
    chat_id BIGINT PRIMARY KEY,
    news_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE sent_news (
    news_hash TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE command_log (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    command TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE bot_health (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    last_cron_at TIMESTAMPTZ DEFAULT now(),
    last_cron_status TEXT DEFAULT 'ok',
    updated_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO bot_health (id, last_cron_at, last_cron_status)
VALUES (1, now(), 'ok') ON CONFLICT DO NOTHING;
```

3. Ve a `Project Settings -> API` y guarda tu **URL** y tu **anon/public KEY**.

### 2. Configurar Variables de Entorno (Local y Vercel)

Crea un archivo `.env` en la raíz de este proyecto (solo para desarrollo local) y asegúrate de agregar estas mismas variables en el panel de **Vercel** (`Settings -> Environment Variables`):

```env
TELEGRAM_TOKEN=tu_token_de_botfather
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_key_anon_de_supabase
ADMIN_CHAT_ID=tu_id_de_telegram
```

### 3. Despliegue en Vercel

1. Sube este repositorio a tu cuenta de GitHub.
2. Inicia sesión en [Vercel](https://vercel.com/), haz clic en "Add New Project" e importa tu repositorio.
3. Asegúrate de añadir las 3 variables de entorno antes de darle a "Deploy".
4. Vercel te dará una URL (ej. `https://mi-bot-financiero.vercel.app`).

### 4. Conectar Telegram (Webhook)

Telegram necesita saber a dónde enviar los mensajes. Abre tu navegador y pega esta URL (reemplazando con tus datos reales):

```
https://api.telegram.org/bot<TU_TELEGRAM_TOKEN>/setWebhook?url=https://<TU_DOMINIO_VERCEL>/api/webhook
```

Si todo sale bien, verás un JSON diciendo `"Webhook was set"`.

## 📂 Estructura del Proyecto

- `api/webhook.py`: El punto de entrada que Telegram llama cuando alguien escribe un comando.
- `api/cron.py`: El script que Vercel llama automáticamente cada 15 min. para buscar noticias.
- `api/stats.py`: Endpoint para el dashboard público de estadísticas.
- `bot/services.py`: Contiene la lógica pura (cálculos, APIs externas, RSS).
- `bot/db.py`: Funciones auxiliares para interactuar con Supabase.
- `public/index.html`: Dashboard público de analíticas y estado del bot.

## ⏰ Configuración del Monitor (Cada 15 min)

Debido a que Vercel Hobby limita los Crons nativos a una vez al día, hemos implementado un **Trigger Externo** usando GitHub Actions:

1. El archivo `.github/workflows/cron.yml` ya está configurado.
2. Cada 15 minutos, GitHub lanzará un pequeño proceso que llamará a tu URL de Vercel para activar la búsqueda de noticias.
3. Asegúrate de que tu URL en `.github/workflows/cron.yml` sea la correcta (reemplaza `telegram-bot-news.vercel.app` por tu dominio real si es diferente).

## 🚀 Notificaciones de Release

Tenemos un GitHub Action configurado para notificarte automáticamente en Telegram cada vez que publiques un Release. Para que esto funcione, **debes configurar dos Secrets en tu repositorio de GitHub**:

1. Ve a `Settings` > `Secrets and variables` > `Actions` > `New repository secret`.
2. Agrega `TELEGRAM_TOKEN` (tu token de BotFather).
3. Agrega `ADMIN_CHAT_ID` (tu ID de Telegram).
Si no agregas estos Secrets, el Action de notificación simplemente fallará y no enviará el mensaje (pero el resto del bot seguirá funcionando).

## 🛠 Comandos Disponibles en Telegram

- `/start` - Inicia el bot y suscribe al usuario a alertas (o muestra su estado).
- `/subscribe` - Activa las noticias automáticas.
- `/unsubscribe` - Desactiva las noticias automáticas.
- `/prices` - Devuelve el precio actual de BTC, ETH y BNB.
- `/mercados` - Informa qué bolsas mundiales están abiertas en este momento.
- `/noticias` - Top 3 noticias de impacto en demanda.

### 👑 Comandos de Administrador

*(Requieren que tu Chat ID coincida con la variable de entorno `ADMIN_CHAT_ID` configurada en Vercel)*

> [!IMPORTANT]
> **Sobre `ADMIN_CHAT_ID` en Vercel:** Es obligatorio agregar esta variable en tu panel de Vercel (`Settings -> Environment Variables`) con tu ID de Telegram. Si no lo haces, el bot asumirá que tu ID es `0` y te denegará el acceso a estos comandos, respondiendo con un mensaje de error de permisos.

- `/stats` - Muestra estadísticas de usuarios (totales, suscritos, desuscritos).
- `/broadcast <mensaje>` - Envía un mensaje masivo a todos los usuarios. (También puedes responder a un mensaje con `/broadcast` para reenviarlo).
- `/ban <chat_id>` - Elimina un usuario de la base de datos.
