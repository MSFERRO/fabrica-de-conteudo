import os
import logging
from src.api.elevenlabs_client import ElevenLabsClient
from config import settings

logger = logging.getLogger("content_factory.tts_engine")

class TTSEngine:
    def __init__(self, elevenlabs_client: ElevenLabsClient):
        self.elevenlabs_client = elevenlabs_client

    async def generate_narration(self, text: str, job_id: int) -> str:
        """
        Gera o arquivo de áudio para narração com base no texto.
        Salva o arquivo com o ID do job para evitar conflitos de nomes na geração concorrente.
        Retorna o caminho completo do arquivo de áudio gerado se for bem-sucedido.
        """
        # Define o nome do arquivo de áudio final da narração
        filename = f"narration_{job_id}.mp3"
        output_path = str(settings.ASSETS_DIR / filename)
        
        logger.info(f"Iniciando conversão de texto para fala do Job {job_id}...")
        success = await self.elevenlabs_client.text_to_speech(text, output_path)
        
        if success and os.path.exists(output_path):
            logger.info(f"Áudio de narração gerado com sucesso em: {output_path}")
            return output_path
        else:
            raise RuntimeError(f"Falha ao gerar áudio de narração via ElevenLabs para o Job {job_id}.")
