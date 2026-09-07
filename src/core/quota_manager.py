import os
import glob
import logging
from datetime import datetime
from typing import List, Optional
from config import settings
from src.utils.db import get_quota_info, save_quota_info
from src.utils.alert_bot import send_alert
from src.api.youtube_client import YouTubeClient

logger = logging.getLogger("content_factory.quota_manager")

# O limite máximo diário por projeto é 10.000 unidades
MAX_DAILY_QUOTA = 10000

class QuotaManager:
    def __init__(self):
        self.credentials_files = self._discover_credentials()
        self.active_index = 0
        logger.info(f"Gerenciador de Cota inicializado. {len(self.credentials_files)} arquivo(s) de credenciais encontrado(s).")

    def _discover_credentials(self) -> List[str]:
        """
        Descobre todos os arquivos de credenciais do YouTube no diretório de configurações.
        Busca por youtube_credentials_*.json e depois youtube_credentials.json.
        """
        config_dir = settings.CONFIG_DIR
        files = glob.glob(str(config_dir / "youtube_credentials_*.json"))
        files.sort()
        
        default_file = config_dir / "youtube_credentials.json"
        if not files and default_file.exists():
            files.append(str(default_file))
            
        if not files:
            files.append(str(default_file))
            
        return files

    def _get_today_str(self) -> str:
        """Retorna a data atual como string YYYY-MM-DD."""
        return datetime.utcnow().strftime("%Y-%m-%d")

    def get_channels_config(self) -> List[dict]:
        """Lê os perfis dos canais configurados em channels.json."""
        import json
        channels_file = settings.CONFIG_DIR / "channels.json"
        if channels_file.exists():
            try:
                with open(channels_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao ler channels.json: {e}")
        return []

    def get_channel_info(self, channel: str) -> dict:
        """Retorna o dicionário de configurações para um canal específico."""
        configs = self.get_channels_config()
        for c in configs:
            if (c.get("channel_name") == channel or 
                c.get("handle") == channel or 
                c.get("channel_id") == channel or
                channel in c.get("channel_name", "") or
                channel in c.get("handle", "")):
                return c
        return configs[0] if configs else {}

    def get_index_for_channel(self, channel: str) -> int:
        """
        Retorna o índice correspondente ao canal.
        """
        info = self.get_channel_info(channel)
        cred_file = info.get("credentials_file", "")
        if "2" in cred_file or "Mente Curiosa" in channel or "MSFBot2" in channel:
            return 1
        return 0

    def get_credentials_file_for_channel(self, channel: str) -> str:
        """Retorna o caminho do arquivo de credenciais associado ao canal."""
        info = self.get_channel_info(channel)
        cred_filename = info.get("credentials_file")
        if cred_filename:
            target = settings.CONFIG_DIR / cred_filename
            if target.exists():
                return str(target)
                
        idx = self.get_index_for_channel(channel)
        if 0 <= idx < len(self.credentials_files):
            return self.credentials_files[idx]
        return self.credentials_files[0]

    async def get_quota_used_today(self, index: int) -> int:
        """Consulta no banco de dados (assincronamente) o consumo de cota atual para um índice de credencial."""
        today = self._get_today_str()
        return await get_quota_info(today, index)

    def get_client_for_channel(self, channel: str) -> YouTubeClient:
        """
        Retorna uma instância do YouTubeClient configurada com o arquivo de credenciais do canal.
        """
        cred_file = self.get_credentials_file_for_channel(channel)
        idx = self.get_index_for_channel(channel)
        logger.info(f"Obtendo cliente para canal '{channel}' usando credenciais: {os.path.basename(cred_file)} (Índice: {idx})")
        return YouTubeClient(credentials_path=cred_file)

    async def check_quota_for_channel(self, channel: str, estimated_cost: int) -> bool:
        """
        Verifica se o canal específico possui cota suficiente para realizar o upload.
        """
        idx = self.get_index_for_channel(channel)
        if idx >= len(self.credentials_files):
            idx = 0
            
        used = await self.get_quota_used_today(idx)
        logger.info(f"Canal '{channel}' (Índice {idx}) -> Cota gasta hoje: {used}/{MAX_DAILY_QUOTA}")
        
        if used + estimated_cost <= MAX_DAILY_QUOTA:
            return True
            
        msg = f"⚠️ ALERTA: Cota diária do YouTube esgotada para o canal '{channel}' (Índice {idx})!"
        logger.error(msg)
        await send_alert(msg)
        return False

    async def record_quota_consumption(self, channel: str, cost: int):
        """
        Registra o consumo de cota de forma assíncrona no banco de dados para o canal específico.
        """
        idx = self.get_index_for_channel(channel)
        if idx >= len(self.credentials_files):
            idx = 0
            
        today = self._get_today_str()
        current_used = await self.get_quota_used_today(idx)
        new_used = current_used + cost
        
        await save_quota_info(today, idx, new_used)
        logger.info(f"Consumo de cota registrado (+{cost} unidades) para canal '{channel}'. Novo total (Índice {idx}): {new_used}/{MAX_DAILY_QUOTA}")
        
        if new_used >= 9500:
            await send_alert(
                f"ℹ️ Canal '{channel}' (Índice {idx}) atingiu {new_used} unidades de cota hoje."
            )
