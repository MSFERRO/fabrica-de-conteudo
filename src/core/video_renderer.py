import os
import re
import random
import asyncio
import logging
from typing import Optional
from config import settings
from src.api.openai_client import OpenAIClient
from src.utils.validators import get_video_metadata

logger = logging.getLogger("content_factory.video_renderer")

def _format_time(seconds: float) -> str:
    """Formata segundos para o padrão SRT: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

class VideoRenderer:
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client

    def _generate_srt_locally(self, audio_path: str, srt_path: str):
        """
        Usa a biblioteca local faster-whisper na CPU para transcrever o áudio
        e gerar legendas curtas (máximo 3 palavras por cartão em caixa alta).
        """
        from faster_whisper import WhisperModel
        logger.info("Carregando modelo local Whisper (tiny na CPU)...")
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        
        segments, info = model.transcribe(audio_path, word_timestamps=True, beam_size=5)
        
        words_list = []
        for segment in segments:
            if segment.words:
                for word in segment.words:
                    words_list.append(word)

        if not words_list:
            logger.warning("Nenhuma palavra detectada na transcrição local. Gerando legenda em bloco simples...")
            segments, info = model.transcribe(audio_path, beam_size=5)
            with open(srt_path, "w", encoding="utf-8") as f:
                for idx, segment in enumerate(segments, start=1):
                    start = _format_time(segment.start)
                    end = _format_time(segment.end)
                    f.write(f"{idx}\n{start} --> {end}\n{segment.text.strip().upper()}\n\n")
            return

        chunks = []
        current_chunk = []
        for w in words_list:
            current_chunk.append(w)
            if len(current_chunk) >= 3:
                chunks.append(current_chunk)
                current_chunk = []
        if current_chunk:
            chunks.append(current_chunk)

        with open(srt_path, "w", encoding="utf-8") as f:
            for idx, chunk in enumerate(chunks, start=1):
                start = _format_time(chunk[0].start)
                end = _format_time(chunk[-1].end)
                text = " ".join([w.word.strip() for w in chunk])
                if text:
                    f.write(f"{idx}\n{start} --> {end}\n{text.upper()}\n\n")

        logger.info(f"Legendas locais salvas em SRT: {srt_path}")

    async def _generate_subtitles(self, audio_path: str, srt_path: str):
        """
        Orquestra a geração das legendas SRT (via nuvem da OpenAI ou local).
        """
        method = settings.SUBTITLE_GENERATION_METHOD
        logger.info(f"Gerando legendas usando o método: {method}")

        if method == "openai_api":
            try:
                srt_content = await asyncio.to_thread(
                    self.openai_client.transcribe_audio_to_srt, audio_path
                )
                srt_content = srt_content.upper()
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(srt_content)
                logger.info(f"Legendas da API do Whisper salvas em: {srt_path}")
            except Exception as e:
                logger.error(f"Falha ao usar a API do Whisper ({e}). Tentando fallback local...")
                await asyncio.to_thread(self._generate_srt_locally, audio_path, srt_path)
        else:
            await asyncio.to_thread(self._generate_srt_locally, audio_path, srt_path)

    def _select_random_bg_music(self) -> Optional[str]:
        """Seleciona aleatoriamente um arquivo de áudio mp3/wav na pasta assets/music/."""
        if not settings.MUSIC_DIR.exists():
            return None
        music_files = [
            f for f in os.listdir(settings.MUSIC_DIR) 
            if f.lower().endswith((".mp3", ".wav"))
        ]
        if music_files:
            selected = random.choice(music_files)
            return str(settings.MUSIC_DIR / selected)
        return None

    async def render_video(self, bg_video_path: str, audio_path: str, job_id: int, needs_crop: bool = False) -> str:
        """
        Orquestra o FFmpeg para juntar vídeo, áudio, música de fundo e queimar legendas.
        """
        srt_path = str(settings.BACKGROUNDS_DIR / f"subtitles_{job_id}.srt")
        output_filename = f"final_{job_id}.mp4"
        final_video_path = str(settings.OUTPUT_DIR / output_filename)

        # 1. Gera as legendas SRT
        await self._generate_subtitles(audio_path, srt_path)

        # Obtém a duração exata do áudio de narração
        metadata = await get_video_metadata(audio_path)
        duration = metadata.get("duration", 45.0)
        logger.info(f"Duração detectada para renderização: {duration:.2f} segundos")

        # Auto-detecção de orientação do vídeo de fundo
        bg_metadata = await get_video_metadata(bg_video_path)
        bg_w = bg_metadata.get("width", 0)
        bg_h = bg_metadata.get("height", 0)
        if bg_w > bg_h:
            needs_crop = True
            logger.info(f"Vídeo de fundo horizontal detectado ({bg_w}x{bg_h}). Ativando corte 9:16 automático.")

        music_path = self._select_random_bg_music()

        cmd = ["ffmpeg", "-y"]
        cmd.extend(["-i", bg_video_path])
        cmd.extend(["-i", audio_path])

        srt_filter_path = srt_path.replace("\\", "/").replace(":", "\\:")
        
        video_filter = ""
        if needs_crop:
            # Fórmula exata solicitada: crop centralizado 9:16
            video_filter += "crop=w=ih*(9/16):h=ih:x=(in_w-out_w)/2:y=0,"
        
        video_filter += f"subtitles={srt_filter_path}:force_style='Fontname=Arial,Fontsize=18,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2.5,BorderStyle=1,Alignment=2,MarginV=120'"

        if music_path:
            cmd.extend(["-i", music_path])
            filter_complex = (
                f"[0:v]{video_filter}[v];"
                f"[1:a]volume=1.0[a1];"
                f"[2:a]volume=0.15[a2];"
                f"[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[a]"
            )
            cmd.extend(["-filter_complex", filter_complex])
            cmd.extend(["-map", "[v]", "-map", "[a]"])
        else:
            filter_complex = f"[0:v]{video_filter}[v];[1:a]volume=1.0[a]"
            cmd.extend(["-filter_complex", filter_complex])
            cmd.extend(["-map", "[v]", "-map", "[a]"])

        cmd.extend([
            "-t", f"{duration:.3f}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            final_video_path
        ])

        logger.info(f"Executando renderização via FFmpeg do Job {job_id}...")
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()

        if os.path.exists(srt_path):
            try:
                os.remove(srt_path)
            except Exception:
                pass

        if proc.returncode == 0:
            logger.info(f"Renderização concluída com sucesso! Arquivo final: {final_video_path}")
            return final_video_path
        else:
            error_details = stderr.decode()
            logger.error(f"Erro na renderização do FFmpeg. Código: {proc.returncode}. Log:\n{error_details}")
            raise RuntimeError(f"FFmpeg falhou com código {proc.returncode}: {error_details}")
