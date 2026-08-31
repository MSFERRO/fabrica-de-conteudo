import os
import httpx
import logging
from typing import Dict, Any, Optional
from config import settings

logger = logging.getLogger("content_factory.pexels")

class PexelsClient:
    def __init__(self):
        if not settings.PEXELS_API_KEY:
            raise ValueError("PEXELS_API_KEY não encontrada nas configurações. Verifique o arquivo config/.env")
        self.api_key = settings.PEXELS_API_KEY
        self.base_url = "https://api.pexels.com/videos"

    async def search_videos(self, query: str, orientation: str = "portrait", per_page: int = 5) -> Optional[Dict[str, Any]]:
        """
        Busca vídeos no Pexels com base em uma query e orientação (portrait ou landscape).
        """
        url = f"{self.base_url}/search"
        headers = {
            "Authorization": self.api_key
        }
        params = {
            "query": query,
            "orientation": orientation,
            "per_page": per_page
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                logger.info(f"Buscando vídeos no Pexels para: '{query}' (Orientação: {orientation})")
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    return response.json()
                
                logger.error(f"Falha na busca do Pexels. Status: {response.status_code}. Resposta: {response.text}")
                return None
            except httpx.RequestError as exc:
                logger.error(f"Erro de rede ao conectar à API do Pexels: {exc}")
                return None

    async def download_video(self, download_url: str, output_path: str) -> bool:
        """
        Baixa o vídeo a partir de uma URL direta em blocos (streaming) para evitar sobrecarga de memória.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                logger.info(f"Iniciando download do vídeo de: {download_url}")
                async with client.stream("GET", download_url, follow_redirects=True) as response:
                    if response.status_code != 200:
                        logger.error(f"Falha no download do vídeo. Status: {response.status_code}")
                        return False
                    
                    with open(output_path, "wb") as f:
                        async for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            
                logger.info(f"Vídeo baixado com sucesso em: {output_path}")
                return True
            except httpx.RequestError as exc:
                logger.error(f"Erro ao baixar vídeo da URL {download_url}: {exc}")
                return False
