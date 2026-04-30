-- ========================================
-- Migración: Dashboard de Stats del Bot
-- Ejecutar en Supabase SQL Editor
-- ========================================

-- Tabla para loguear cada comando ejecutado
CREATE TABLE IF NOT EXISTS command_log (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    command TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Índice para consultas por fecha (dashboard)
CREATE INDEX IF NOT EXISTS idx_command_log_created_at ON command_log(created_at);

-- Tabla para trackear health del bot (última ejecución exitosa del cron)
CREATE TABLE IF NOT EXISTS bot_health (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    last_cron_at TIMESTAMPTZ DEFAULT now(),
    last_cron_status TEXT DEFAULT 'ok',
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Insertar fila inicial de bot_health si no existe
INSERT INTO bot_health (id, last_cron_at, last_cron_status)
VALUES (1, now(), 'ok')
ON CONFLICT (id) DO NOTHING;