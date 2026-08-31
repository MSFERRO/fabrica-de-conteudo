import os
import shutil
import random
import logging
from typing import List, Tuple, Optional, Dict, Any
from src.api.pexels_client import PexelsClient
from config import settings
from src.utils.alert_bot import send_alert

logger = logging.getLogger("content_factory.asset_downloader")

DEFAULT_FALLBACK_QUERY = "abstract background loop"

class AssetDownloader:
    def __init__(self, pexels_client: PexelsClient):
        self.pexels_client = pexels_client

    def _get_best_video_file(self, video_data: Dict[str, Any]) -> Optional[str]:
        """
        Analisa os arquivos de vídeo do Pexels e retorna a URL de download da melhor qualidade.
        """
        video_files = video_data.get("video_files", [])
        if not video_files:
            return None

        mp4_files = [f for f in video_files if f.get("file_type") == "video/mp4"]
        if not mp4_files:
            mp4_files = video_files

        best_file = None
        for f in mp4_files:
            width = f.get("width", 0)
            height = f.get("height", 0)
            quality = f.get("quality", "")
            
            if quality == "hd" and (width == 1920 or height == 1920 or width == 1080 or height == 1080):
                return f.get("link")
            
            if quality == "hd":
                best_file = f.get("link")
                
        return best_file or mp4_files[0].get("link")

    def _select_candidate_video(self, videos: List[Dict[str, Any]], min_duration: int = 40) -> Optional[Dict[str, Any]]:
        """
        Seleciona um vídeo candidato que atenda à duração mínima.
        """
        for v in videos:
            duration = v.get("duration", 0)
            if duration >= min_duration:
                return v
        return None

    def _get_local_fallback_video(self, job_id: int) -> Tuple[str, bool]:
        """
        Tenta localizar um vídeo de fallback local no diretório loops/.
        """
        if not settings.FALLBACK_DIR.exists():
            settings.FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
            
        fallback_files = [
            f for f in os.listdir(settings.FALLBACK_DIR) 
            if f.lower().endswith((".mp4", ".mov", ".mkv"))
        ]
        
        if fallback_files:
            selected_file = random.choice(fallback_files)
            source_path = settings.FALLBACK_DIR / selected_file
            dest_filename = f"bg_{job_id}.mp4"
            dest_path = settings.BACKGROUNDS_DIR / dest_filename
            
            shutil.copy(str(source_path), str(dest_path))
            logger.info(f"Usando vídeo de fallback local: {selected_file} -> {dest_path}")
            return str(dest_path), False
            
        raise FileNotFoundError("Nenhum vídeo de fallback local encontrado na pasta assets/backgrounds/loops/.")

    async def _download_fallback_from_pexels(self, job_id: int) -> Tuple[str, bool]:
        """
        Busca e baixa um vídeo abstrato genérico do Pexels caso o local esteja vazio.
        """
        logger.info("Buscando vídeo de fallback abstrato no Pexels...")
        search_result = await self.pexels_client.search_videos(DEFAULT_FALLBACK_QUERY, orientation="portrait", per_page=5)
        
        if search_result and search_result.get("videos"):
            candidate = self._select_candidate_video(search_result["videos"], min_duration=30)
            if candidate:
                download_url = self._get_best_video_file(candidate)
                if download_url:
                    dest_filename = f"bg_{job_id}.mp4"
                    dest_path = str(settings.BACKGROUNDS_DIR / dest_filename)
                    success = await self.pexels_client.download_video(download_url, dest_path)
                    if success:
                        return dest_path, False
                        
        raise RuntimeError("Falha total: Não foi possível obter vídeo nem da API nem do fallback local.")

    async def download_background_video(self, keywords: List[str], job_id: int) -> Tuple[str, bool]:
        """
        Busca e baixa um vídeo de fundo adequado do Pexels.
        """
        query = " ".join(keywords[:2])
        dest_filename = f"bg_{job_id}.mp4"
        dest_path = str(settings.BACKGROUNDS_DIR / dest_filename)

        try:
            # 1. Tentativa: Vídeo Vertical específico
            logger.info(f"Tentativa 1: Buscando vídeo vertical no Pexels para '{query}'")
            search_result = await self.pexels_client.search_videos(query, orientation="portrait", per_page=10)
            if search_result and search_result.get("videos"):
                candidate = self._select_candidate_video(search_result["videos"], min_duration=40)
                if candidate:
                    download_url = self._get_best_video_file(candidate)
                    if download_url:
                        success = await self.pexels_client.download_video(download_url, dest_path)
                        if success:
                            return dest_path, False
            
            # 2. Tentativa: Vídeo Horizontal específico (exige Crop)
            logger.info(f"Tentativa 2: Vídeo vertical não encontrado. Buscando vídeo horizontal para '{query}'...")
            search_result = await self.pexels_client.search_videos(query, orientation="landscape", per_page=10)
            if search_result and search_result.get("videos"):
                candidate = self._select_candidate_video(search_result["videos"], min_duration=40)
                if candidate:
                    download_url = self._get_best_video_file(candidate)
                    if download_url:
                        success = await self.pexels_client.download_video(download_url, dest_path)
                        if success:
                            logger.info(f"Vídeo horizontal baixado. Necessita de corte 9:16.")
                            return dest_path, True

            logger.warning(f"Sem resultados para '{query}' no Pexels. Iniciando cascata de fallback...")
            
        except Exception as e:
            logger.error(f"Erro ao interagir com Pexels para baixar vídeo: {e}")

        # 3. Tentativa: Vídeo de Fallback Local
        try:
            return self._get_local_fallback_video(job_id)
        except Exception as e:
            logger.warning(f"Falha ao usar fallback local: {e}")

        # 4. Tentativa: Busca Genérica no Pexels
        try:
            return await self._download_fallback_from_pexels(job_id)
        except Exception as e:
            logger.error(f"Falha crítica no download de backgrounds: {e}")
            await send_alert(
                f"⚠️ *Erro Crítico de Download*: Não foi possível obter background para o Job {job_id}. Falha total."
            )
            raise e
