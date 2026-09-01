import os
import edge_tts
import logging
from typing import Optional
from config import settings

logger = logging.getLogger("content_factory.tts_engine")

class TTSEngine:
    def __init__(self, default_voice: str = "pt-BR-FranciscaNeural"):
        self.default_voice = default_voice

    async def generate_narration(self, text: str, job_id: int, voice: Optional[str] = None) -> str:
        """
        Gera o arquivo de áudio para narração com base no texto usando vozes neurais da Microsoft (Edge-TTS).
        Aceita voz personalizada por canal (ex: pt-BR-AntonioNeural ou pt-BR-FranciscaNeural).
        """
        selected_voice = voice or self.default_voice
        filename = f"narration_{job_id}.mp3"
        output_path = str(settings.ASSETS_DIR / filename)
        
        logger.info(f"Gerando áudio via edge-tts (Voz: {selected_voice}) para o Job {job_id}...")
        communicate = edge_tts.Communicate(text, selected_voice)
        await communicate.save(output_path)
        
        if os.path.exists(output_path):
            logger.info(f"Áudio de narração salvo com sucesso em: {output_path}")
            return output_path
        else:
            raise RuntimeError(f"Falha ao gerar áudio de narração para o Job {job_id}.")
