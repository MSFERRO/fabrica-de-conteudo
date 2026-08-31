import os
import logging
import edge_tts
from config import settings

logger = logging.getLogger("content_factory.tts_engine")

class TTSEngine:
    def __init__(self):
        self.voice = settings.EDGE_TTS_VOICE

    async def generate_narration(self, text: str, job_id: int) -> str:
        """
        Gera o áudio de narração (.mp3) usando a biblioteca edge-tts (Microsoft Neural Voices).
        Retorna o caminho completo do arquivo gerado.
        """
        filename = f"narration_{job_id}.mp3"
        output_path = str(settings.ASSETS_DIR / filename)
        
        logger.info(f"Gerando áudio via edge-tts (Voz: {self.voice}) para o Job {job_id}...")
        try:
            # O edge-tts usa um fluxo assíncrono para obter e salvar o áudio
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(output_path)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"Áudio de narração salvo com sucesso em: {output_path}")
                return output_path
            else:
                raise RuntimeError("O arquivo de áudio gerado pelo edge-tts está vazio ou não existe.")
        except Exception as e:
            logger.error(f"Erro ao gerar áudio com edge-tts no Job {job_id}: {e}")
            raise e
