import os
import asyncio
import httpx
import logging
from typing import Optional
from config import settings

logger = logging.getLogger("content_factory.elevenlabs")

class ElevenLabsClient:
    def __init__(self):
        if not settings.ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY não encontrada nas configurações. Verifique o arquivo config/.env")
        self.api_key = settings.ELEVENLABS_API_KEY
        self.voice_id = settings.ELEVENLABS_VOICE_ID
        self.base_url = "https://api.elevenlabs.io/v1"

    async def text_to_speech(self, text: str, output_path: str) -> bool:
        """
        Converte texto em fala (.mp3) usando a API ElevenLabs.
        Implementa retentativa automática com backoff exponencial.
        """
        url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        # Cria a pasta pai do arquivo de saída se não existir
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        attempts = settings.RETRY_ATTEMPTS
        delay = 2.0  # Tempo inicial de espera em segundos

        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(1, attempts + 1):
                try:
                    logger.info(f"Gerando áudio (tentativa {attempt}/{attempts}) para o roteiro...")
                    response = await client.post(url, json=data, headers=headers)

                    if response.status_code == 200:
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                        logger.info(f"Áudio gerado com sucesso e salvo em: {output_path}")
                        return True
                    
                    # Trata limites de requisição (HTTP 429) ou outros erros de servidor
                    logger.warning(
                        f"Falha na API ElevenLabs. Status: {response.status_code}. Resposta: {response.text[:200]}"
                    )
                    
                    if response.status_code == 429:
                        logger.info("Limite de requisições atingido. Aguardando para tentar novamente...")

                except httpx.RequestError as exc:
                    logger.error(f"Erro de conexão com ElevenLabs na tentativa {attempt}: {exc}")

                if attempt < attempts:
                    logger.info(f"Aguardando {delay} segundos antes de tentar novamente...")
                    await asyncio.sleep(delay)
                    delay *= 2.0  # Backoff exponencial

            logger.error("Falha ao gerar áudio com ElevenLabs após todas as tentativas.")
            return False
