import os
import asyncio
import logging
from typing import Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger("content_factory.youtube_client")

class YouTubeClient:
    def __init__(self, credentials_path: str):
        """
        Inicializa o cliente do YouTube com base em um arquivo específico de credenciais.
        Isso permite alternar credenciais para contornar limites de cota.
        """
        self.credentials_path = credentials_path
        self.credentials: Optional[Credentials] = None
        self.service = None

    def _load_credentials(self) -> bool:
        """
        Carrega as credenciais salvas em disco e as atualiza (refresh) se estiverem expiradas.
        """
        if not os.path.exists(self.credentials_path):
            logger.error(f"Arquivo de credenciais do YouTube não encontrado: {self.credentials_path}")
            return False

        try:
            self.credentials = Credentials.from_authorized_user_file(
                self.credentials_path,
                scopes=[
                    "https://www.googleapis.com/auth/youtube.upload",
                    "https://www.googleapis.com/auth/youtube"
                ]
            )
            
            # Se as credenciais estiverem expiradas, realiza o refresh usando o refresh_token
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                logger.info(f"Atualizando token expirado para credenciais em {self.credentials_path}...")
                self.credentials.refresh(Request())
                
                # Salva o novo access token de volta no arquivo
                with open(self.credentials_path, "w") as f:
                    f.write(self.credentials.to_json())
                    
            self.service = build("youtube", "v3", credentials=self.credentials)
            return True
        except Exception as e:
            logger.error(f"Erro ao carregar/atualizar credenciais do YouTube: {e}")
            return False

    def _execute_upload(self, video_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa o upload resumível síncrono. Deve ser rodado em thread separada.
        """
        if not self.service:
            if not self._load_credentials():
                raise ValueError("Serviço do YouTube não inicializado. Verifique as credenciais.")

        body = {
            "snippet": {
                "title": metadata.get("title", "Video Curto"),
                "description": metadata.get("description", ""),
                "tags": metadata.get("tags", []),
                "categoryId": metadata.get("category_id", "27")  # 27 = Education, 24 = Entertainment
            },
            "status": {
                "privacyStatus": metadata.get("privacy_status", "private"), # public, private, unlisted
            }
        }

        # Se houver agendamento de data (deve estar em formato ISO 8601: YYYY-MM-DDThh:mm:ss.sZ)
        publish_at = metadata.get("publish_at")
        if publish_at and metadata.get("privacy_status") == "private":
            body["status"]["publishAt"] = publish_at

        # Define o arquivo de mídia e chunk_size (ex: 10MB)
        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            chunksize=10 * 1024 * 1024,
            resumable=True
        )

        request = self.service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        logger.info(f"Iniciando envio do arquivo {video_path}...")
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Progresso do upload: {int(status.progress() * 100)}%")

        logger.info(f"Upload concluído! Video ID: {response['id']}")
        return {
            "video_id": response["id"],
            "url": f"https://youtu.be/{response['id']}"
        }

    async def upload_short(self, video_path: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Invoca o upload síncrono em um threadpool assíncrono para evitar travar o event loop.
        """
        if not os.path.exists(video_path):
            logger.error(f"Arquivo de vídeo não encontrado para upload: {video_path}")
            return None

        try:
            # Executa a função síncrona em uma thread separada gerenciada pelo asyncio
            result = await asyncio.to_thread(self._execute_upload, video_path, metadata)
            return result
        except HttpError as e:
            logger.error(f"Erro HTTP da API do YouTube: {e.resp.status} - {e.content}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado durante o upload para o YouTube: {e}")
            return None
