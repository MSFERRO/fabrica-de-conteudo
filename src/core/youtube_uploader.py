import logging
from typing import Dict, Any, List, Optional
from src.core.quota_manager import QuotaManager
from src.utils.alert_bot import send_alert

logger = logging.getLogger("content_factory.youtube_uploader")

# Custo de upload na YouTube Data API v3 é 1600 unidades
UPLOAD_QUOTA_COST = 1600

class YouTubeUploader:
    def __init__(self, quota_manager: QuotaManager):
        self.quota_manager = quota_manager

    async def upload_video_to_shorts(self, video_path: str, topic: str, script: str, 
                                     keywords: List[str], publish_at: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Orquestra o upload do vídeo de Shorts para o YouTube.
        1. Verifica e rotaciona chaves de cota do YouTube.
        2. Formata metadados virais.
        3. Realiza o upload resumível.
        4. Registra consumo de cota no banco se der certo.
        """
        logger.info(f"Iniciando processo de upload para Shorts do vídeo: {video_path}")

        # Verifica se há cota disponível em alguma credencial
        quota_available = await self.quota_manager.check_and_rotate_quota(UPLOAD_QUOTA_COST)
        if not quota_available:
            logger.error("Upload abortado devido a falta de cota disponível em todas as contas.")
            await send_alert("❌ *Falha no Upload*: Sem cotas de API do YouTube disponíveis hoje.")
            return None

        # Obtém o cliente do YouTube com a credencial ativa
        youtube_client = self.quota_manager.get_active_client()

        # Formata o título (limite de 100 caracteres para o YouTube)
        title = f"{topic[:85]} #shorts #curiosidades"
        
        # Formata a descrição (limite de 5000 caracteres)
        # Inclui o próprio roteiro do vídeo e hashtags estruturadas
        hashtags = " ".join([f"#{kw.replace(' ', '')}" for kw in keywords[:5]])
        description = (
            f"{script}\n\n"
            f"---\n"
            f"Curta e se inscreva para mais vídeos diários sobre ciência e curiosidades!\n\n"
            f"#shorts #curiosidades #fatos #ciência #conhecimento {hashtags}"
        )

        # Formata Tags
        tags = ["shorts", "curiosidades", "fatos", "educação", "conhecimento"]
        tags.extend(keywords)
        tags = [t[:30] for t in tags[:15]]  # Limita tamanho e quantidade

        # Monta payload de metadados
        metadata = {
            "title": title,
            "description": description,
            "tags": tags,
            "category_id": "27",  # 27 = Education
            "privacy_status": "private"  # Obrigatoriamente privado se for agendado
        }

        if publish_at:
            metadata["publish_at"] = publish_at
            logger.info(f"O Short será agendado para publicação automática em: {publish_at}")
        else:
            # Se não houver agendamento, posta direto como público
            metadata["privacy_status"] = "public"
            logger.info("O Short será publicado imediatamente como público.")

        # Executa o upload
        result = await youtube_client.upload_short(video_path, metadata)

        if result and result.get("video_id"):
            logger.info(f"Upload bem-sucedido! ID: {result['video_id']}. Link: {result['url']}")
            # Registra consumo de cota
            await self.quota_manager.record_quota_consumption(UPLOAD_QUOTA_COST)
            return result
        else:
            logger.error("Upload falhou no YouTubeClient.")
            return None
