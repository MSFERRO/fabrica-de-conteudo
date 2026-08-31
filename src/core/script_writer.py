import logging
from src.api.openai_client import OpenAIClient
from src.utils.validators import validate_script
from config import settings

logger = logging.getLogger("content_factory.script_writer")

class ScriptWriter:
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client

    def write_script(self, topic: str, duration_seconds: int = 60) -> str:
        """
        Gera e valida o roteiro usando a OpenAI.
        Se a validação falhar, tenta regenerar o roteiro com avisos específicos, respeitando o limite de retentativas.
        """
        attempts = settings.RETRY_ATTEMPTS
        logger.info(f"Iniciando escrita do roteiro sobre: '{topic}'")

        for attempt in range(1, attempts + 1):
            try:
                script = self.openai_client.generate_script(topic, duration_seconds)
                
                is_valid, reason = validate_script(script)
                if is_valid:
                    logger.info(f"Roteiro aprovado na tentativa {attempt}!")
                    return script
                
                logger.warning(f"Roteiro inválido na tentativa {attempt}: {reason}. Solicitando correção...")
                topic = f"{topic} (LEMBRETE: evite emojis, formate texto corrido puramente em português brasileiro com 130 a 150 palavras, sem asteriscos ou hashtags)"
                
            except Exception as e:
                logger.error(f"Erro ao chamar a OpenAI para gerar roteiro (tentativa {attempt}): {e}")
                
        raise ValueError(f"Não foi possível gerar um roteiro em conformidade após {attempts} tentativas.")
