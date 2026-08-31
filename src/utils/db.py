import aiosqlite
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from config import settings

logger = logging.getLogger("content_factory.db")

async def init_db():
    """Cria as tabelas necessárias se elas não existirem (assíncrono)."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        # Tabela de fila de Jobs de Vídeo
        await db.execute("""
        CREATE TABLE IF NOT EXISTS video_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            keywords TEXT,
            viral_score INTEGER,
            script TEXT,
            audio_path TEXT,
            video_path TEXT,
            final_video_path TEXT,
            status TEXT,
            video_id TEXT,
            channel TEXT,
            scheduled_time TEXT,
            error_message TEXT,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(topic, channel)
        )
        """)

        # Tabela de consumo de cota da API do YouTube
        await db.execute("""
        CREATE TABLE IF NOT EXISTS quota_usage (
            date_str TEXT,
            active_index INTEGER,
            used_quota INTEGER,
            PRIMARY KEY (date_str, active_index)
        )
        """)
        await db.commit()
    logger.info("Banco de dados SQLite inicializado com sucesso.")

# Funções auxiliares para cotas
async def get_quota_info(date_str: str, active_index: int) -> int:
    """Retorna a cota usada para uma determinada data e credencial."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT used_quota FROM quota_usage 
            WHERE date_str = ? AND active_index = ?
        """, (date_str, active_index)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row["used_quota"]
    return 0

async def save_quota_info(date_str: str, active_index: int, used_quota: int):
    """Insere ou atualiza o consumo de cota para a data e credencial especificada."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("""
        INSERT INTO quota_usage (date_str, active_index, used_quota) 
        VALUES (?, ?, ?)
        ON CONFLICT(date_str, active_index) DO UPDATE SET used_quota = excluded.used_quota
        """, (date_str, active_index, used_quota))
        await db.commit()

# Funções auxiliares para gerenciamento de Jobs
async def add_video_job(topic: str, keywords: List[str], viral_score: int, channel: str) -> bool:
    """Adiciona um novo job na fila com status 'pending' para um canal específico."""
    now = datetime.utcnow().isoformat()
    keywords_str = ",".join(keywords)
    try:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            await db.execute("""
            INSERT INTO video_jobs (topic, keywords, viral_score, status, channel, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (topic, keywords_str, viral_score, "pending", channel, now, now))
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        # Tópico duplicado para este canal, ignora silenciosamente
        return False

async def update_job_status(job_id: int, status: str, **kwargs):
    """Atualiza o status e outros atributos opcionais de um job."""
    now = datetime.utcnow().isoformat()
    fields = ["status = ?", "updated_at = ?"]
    values = [status, now]

    for key, val in kwargs.items():
        fields.append(f"{key} = ?")
        values.append(val)

    values.append(job_id)
    query = f"UPDATE video_jobs SET {', '.join(fields)} WHERE id = ?"

    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(query, tuple(values))
        await db.commit()

async def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    """Busca as informações de um job de vídeo pelo ID."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM video_jobs WHERE id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_jobs_by_status(status: str) -> List[Dict[str, Any]]:
    """Retorna todos os jobs com um determinado status."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM video_jobs WHERE status = ? ORDER BY id ASC", (status,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_next_job_to_process() -> Optional[Dict[str, Any]]:
    """Busca o próximo job que ainda não está finalizado e não falhou."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
        SELECT * FROM video_jobs 
        WHERE status IN ('pending', 'script_generated', 'audio_generated', 'downloaded', 'rendered') 
        ORDER BY id ASC LIMIT 1
        """) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
