import httpx
import logging
from typing import Optional
from config import settings

logger = logging.getLogger("content_factory.alert_bot")

class TelegramAlertBot:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

    async def send_message(self, text: str) -> bool:
        """
        Envia uma mensagem de texto formatada em Markdown para o chat do Telegram configurado.
        Falha de forma silenciosa para não travar a fábrica caso ocorra erro de conexão.
        """
        if not self.base_url or not self.chat_id:
            logger.warning("Telegram Bot não configurado. Defina TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID em config/.env")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    logger.info("Alerta enviado com sucesso para o Telegram.")
                    return True
                else:
                    logger.error(f"Erro ao enviar alerta ao Telegram. Status: {response.status_code}. Detalhe: {response.text}")
                    return False
            except Exception as e:
                logger.error(f"Exceção ao conectar à API do Telegram para enviar alerta: {e}")
                return False

# Instância unificada
alert_bot = TelegramAlertBot()

async def send_alert(text: str) -> bool:
    return await alert_bot.send_message(text)
