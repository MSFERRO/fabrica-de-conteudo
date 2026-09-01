import os
import sys
import asyncio
import logging
import subprocess
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from src.api.openai_client import OpenAIClient
from src.api.tts_engine import TTSEngine
from src.api.pexels_client import PexelsClient
from src.core.quota_manager import QuotaManager
from src.core.trend_hunter import TrendHunter
from src.core.script_writer import ScriptWriter
from src.core.asset_downloader import AssetDownloader
from src.core.video_renderer import VideoRenderer
from src.utils.db import (
    init_db, get_next_job_to_process, update_job_status,
    add_video_job
)
from src.utils.validators import validate_video
from src.utils.logger import log_event
from src.utils.alert_bot import send_alert

logger = logging.getLogger("content_factory.main")

def verify_system_dependencies() -> bool:
    """Verifica se o FFmpeg e o FFprobe estão instalados e acessíveis no PATH."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info("FFmpeg e FFprobe detectados com sucesso no sistema.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.critical("FFmpeg e/ou FFprobe não encontrados no PATH do sistema. O renderizador não funcionará!")
        return False

async def calculate_next_publish_time(channel: str) -> str:
    """
    Calcula o próximo horário de publicação no formato ISO 8601 UTC para um canal específico.
    Garante que os vídeos fiquem espaçados pelo intervalo configurado em settings.SCHEDULE_INTERVAL.
    """
    now = datetime.utcnow()
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT scheduled_time FROM video_jobs 
            WHERE status = 'uploaded' AND channel = ? AND scheduled_time IS NOT NULL 
            ORDER BY scheduled_time DESC LIMIT 1
        """, (channel,)) as cursor:
            row = await cursor.fetchone()

    if row and row["scheduled_time"]:
        try:
            last_schedule = datetime.fromisoformat(row["scheduled_time"].replace("Z", ""))
            if last_schedule > now:
                next_time = last_schedule + timedelta(hours=settings.SCHEDULE_INTERVAL)
            else:
                next_time = now + timedelta(hours=settings.SCHEDULE_INTERVAL)
        except Exception:
            next_time = now + timedelta(hours=settings.SCHEDULE_INTERVAL)
    else:
        # Se for o primeiro vídeo do canal, agenda para dali a 1 hora
        next_time = now + timedelta(hours=1)

    return next_time.strftime("%Y-%m-%dT%H:%M:%SZ")

async def run_pipeline_step(job: dict, trend_hunter: TrendHunter, script_writer: ScriptWriter, 
                            tts_engine: TTSEngine, downloader: AssetDownloader, 
                            renderer: VideoRenderer, quota_manager: QuotaManager) -> bool:
    """
    Executa a próxima etapa necessária para o job fornecido com base no seu status atual.
    Retorna True se o job avançou de status, False se ocorreu algum erro ou se parou.
    """
    job_id = job["id"]
    topic = job["topic"]
    keywords = job["keywords"].split(",") if job["keywords"] else ["curiosidades"]
    status = job["status"]
    channel_name = job.get("channel") or "Cosmos Oculto"
    ch_info = quota_manager.get_channel_info(channel_name)

    start_time = datetime.utcnow()
    logger.info(f"Processando Job {job_id} | Canal: '{channel_name}' | Tema: '{topic}' | Status Atual: {status}")

    try:
        # ETAPA 1: Geração de Roteiro (OpenAI GPT-4o)
        if status == "pending":
            # Executado em threadpool pois faz requisição síncrona usando a SDK oficial
            script = await asyncio.to_thread(script_writer.write_script, topic, settings.VIDEO_DURATION)
            await update_job_status(job_id, "script_generated", script=script)
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            log_event("script_writer", "generate_script", "success", topic, duration_ms)
            return True

        # ETAPA 2: Conversão de Texto para Fala (Edge-TTS com voz personalizada por canal)
        elif status == "script_generated":
            channel_voice = ch_info.get("voice", "pt-BR-FranciscaNeural")
            audio_path = await tts_engine.generate_narration(job["script"], job_id, voice=channel_voice)
            await update_job_status(job_id, "audio_generated", audio_path=audio_path)
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            log_event("tts_engine", "generate_audio", "success", topic, duration_ms)
            return True

        # ETAPA 3: Download do Vídeo de Fundo (Pexels)
        elif status == "audio_generated":
            video_path, needs_crop = await downloader.download_background_video(keywords, job_id)
            await update_job_status(job_id, "downloaded", video_path=video_path)
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            log_event("asset_downloader", "download_video", "success", topic, duration_ms)
            return True

        # ETAPA 4: Edição/Renderização com FFmpeg, Legendas e Paleta do Canal
        elif status == "downloaded":
            sub_color = ch_info.get("subtitle_color", "&H0000FFFF")
            final_video_path = await renderer.render_video(
                job["video_path"], job["audio_path"], job_id, subtitle_color=sub_color
            )
            
            is_valid, reason = await validate_video(final_video_path)
            if not is_valid:
                raise ValueError(f"Vídeo renderizado reprovou na validação de qualidade: {reason}")
                
            await update_job_status(job_id, "rendered", final_video_path=final_video_path)
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            log_event("video_renderer", "render_video", "success", topic, duration_ms)
            return True

        # ETAPA 5: Upload e Agendamento para o YouTube (YouTube Data API v3 com gerenciamento de cota)
        elif status == "rendered":
            channel = job["channel"] or ch_info.get("channel_name", "@CuriosidadeAutomáticasMSF")
            # Verifica se há cota disponível no canal específico (custo: 1600 unidades)
            quota_available = await quota_manager.check_quota_for_channel(channel, 1600)
            if not quota_available:
                raise RuntimeError(f"Não há cotas de API do YouTube disponíveis para o canal '{channel}'.")

            youtube_client = quota_manager.get_client_for_channel(channel)

            # Formatação de metadados virais
            title = f"{topic[:85]} #shorts #curiosidades"
            hashtags = " ".join([f"#{kw.replace(' ', '')}" for kw in keywords[:5]])
            description = (
                f"{job['script']}\n\n"
                f"---\n"
                f"Curta e se inscreva para mais vídeos diários no canal {channel}!\n\n"
                f"#shorts #curiosidades #fatos #ciência #conhecimento {hashtags}"
            )
            tags = ["shorts", "curiosidades", "fatos", "educação"] + keywords
            tags = [t[:30] for t in tags[:15]]

            publish_time = await calculate_next_publish_time(channel)

            metadata = {
                "title": title,
                "description": description,
                "tags": tags,
                "category_id": "27",  # Education
                "privacy_status": "private",
                "publish_at": publish_time
            }

            upload_result = await youtube_client.upload_short(job["final_video_path"], metadata)
            
            if upload_result and upload_result.get("video_id"):
                video_id = upload_result["video_id"]
                url = upload_result["url"]
                
                await update_job_status(job_id, "uploaded", video_id=video_id, scheduled_time=publish_time)
                await quota_manager.record_quota_consumption(channel, 1600)
                
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                log_event("youtube_client", "upload_video", "success", topic, duration_ms, video_id)
                
                # Envia alerta Telegram
                await send_alert(
                    f"🚀 *Short Agendado com Sucesso!*\n"
                    f"▪️ *Canal*: {channel}\n"
                    f"▪️ *Tema*: {topic}\n"
                    f"▪️ *Publicação (UTC)*: {publish_time}\n"
                    f"▪️ *Link*: [Ver no YouTube]({url})"
                )
                
                # Limpa arquivos temporários gerados
                for path_key in ["audio_path", "video_path", "final_video_path"]:
                    if job.get(path_key) and os.path.exists(job[path_key]):
                        try:
                            os.remove(job[path_key])
                        except Exception:
                            pass
                return True
            else:
                raise RuntimeError("Falha ao subir vídeo para o YouTube no cliente do YouTube.")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Erro no pipeline do Job {job_id}: {error_msg}")
        await update_job_status(job_id, "failed", error_message=error_msg)
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        log_event(status, "pipeline_execution", "failed", topic, duration_ms, error_message=error_msg)
        
        await send_alert(
            f"❌ *Erro no Pipeline do Job {job_id}*\n"
            f"▪️ *Tema*: {topic}\n"
            f"▪️ *Etapa Falha*: {status}\n"
            f"▪️ *Detalhe*: {error_msg}"
        )
        return False

    return False

async def main():
    logger.info("Iniciando Fábrica de Conteúdo Automatizado (Versão 4)...")
    
    # 1. Inicializa o Banco de Dados SQLite (aiosqlite)
    await init_db()

    # 2. Verifica dependências do sistema operacional (FFmpeg)
    if not verify_system_dependencies():
        print("Erro: FFmpeg ou FFprobe ausentes no PATH.")
        sys.exit(1)

    # 3. Inicializa Clientes e Motores
    try:
        openai_client = OpenAIClient()
        tts_engine = TTSEngine()
        pexels_client = PexelsClient()
        quota_manager = QuotaManager()

        trend_hunter = TrendHunter(openai_client)
        script_writer = ScriptWriter(openai_client)
        downloader = AssetDownloader(pexels_client)
        renderer = VideoRenderer(openai_client)
    except Exception as e:
        logger.critical(f"Falha ao carregar chaves de API e inicializar clientes: {e}")
        sys.exit(1)

    await send_alert("🟢 *Fábrica de Conteúdo v4 iniciada com sucesso!* Monitoramento ativo 24/7.")

    # 4. Loop Infinito do Orquestrador
    while True:
        try:
            job = await get_next_job_to_process()
            
            if job:
                await run_pipeline_step(
                    job, trend_hunter, script_writer, tts_engine, 
                    downloader, renderer, quota_manager
                )
            else:
                logger.info("Fila de processamento vazia. Buscando novas tendências para os canais...")
                channels_config = quota_manager.get_channels_config()
                if not channels_config:
                    channels_config = [
                        {"channel_name": "Cosmos Oculto", "niche": "Astronomia e Mistérios do Universo"},
                        {"channel_name": "Mente Sombria", "niche": "Psicologia Oculta e Segredos da Mente"}
                    ]
                
                added_count = 0
                for ch in channels_config:
                    niche = ch.get("niche", "curiosidades e ciência")
                    ch_name = ch.get("channel_name", ch.get("handle"))
                    logger.info(f"Buscando temas virais para o canal '{ch_name}' no nicho: '{niche}'...")
                    trends = await trend_hunter.hunt_trends(niche=niche)
                    for item in trends:
                        success = await add_video_job(
                            topic=item["topic"],
                            keywords=item["keywords"],
                            viral_score=item["viral_score"],
                            channel=ch_name
                        )
                        if success:
                            added_count += 1
                
                if added_count > 0:
                    logger.info(f"Novas tendências adicionadas à fila: {added_count} novos tópicos distintos.")
                else:
                    logger.info("Nenhum tópico novo adicionado nesta rodada. Aguardando...")
            
            await asyncio.sleep(15)

        except KeyboardInterrupt:
            logger.info("Encerrando fábrica de conteúdo...")
            await send_alert("🔴 *Fábrica de Conteúdo finalizada pelo operador.*")
            break
        except Exception as e:
            logger.error(f"Erro inesperado no loop principal: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
