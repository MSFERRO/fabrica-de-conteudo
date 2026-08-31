import os
import json
import logging
from datetime import datetime
from config import settings

class JSONFormatter(logging.Formatter):
    """
    Formatador personalizado para converter registros de log no formato JSON estruturado.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": getattr(record, "module_name", record.module),
            "action": getattr(record, "action", record.funcName),
            "topic": getattr(record, "topic", None),
            "status": getattr(record, "status", "success" if record.levelno < logging.WARNING else "failed"),
            "duration_ms": getattr(record, "duration_ms", 0),
            "video_id": getattr(record, "video_id", None),
            "error_message": getattr(record, "error_message", record.message if record.levelno >= logging.WARNING else None)
        }
        return json.dumps(log_data)

def setup_logger():
    """
    Configura os handlers de log para Console, Arquivo JSON e Arquivo de texto comum.
    """
    logger = logging.getLogger("content_factory")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    os.makedirs(settings.LOGS_DIR, exist_ok=True)

    # 1. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s]: %(message)s", 
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 2. JSON File Handler
    json_path = settings.LOGS_DIR / "events.json"
    json_handler = logging.FileHandler(json_path, encoding="utf-8")
    json_handler.setLevel(logging.INFO)
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)

    # 3. System Log File Handler
    sys_log_path = settings.LOGS_DIR / "system.log"
    sys_handler = logging.FileHandler(sys_log_path, encoding="utf-8")
    sys_handler.setLevel(logging.INFO)
    sys_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d]: %(message)s"
    )
    sys_handler.setFormatter(sys_formatter)
    logger.addHandler(sys_handler)

    return logger

logger = setup_logger()

def log_event(module_name: str, action: str, status: str, topic: str = None, 
              duration_ms: int = 0, video_id: str = None, error_message: str = None):
    """
    Registra um evento formatado em log de forma estruturada.
    """
    extra = {
        "module_name": module_name,
        "action": action,
        "status": status,
        "topic": topic,
        "duration_ms": duration_ms,
        "video_id": video_id,
        "error_message": error_message
    }
    
    msg = f"Modulo: {module_name} | Acao: {action} | Status: {status}"
    if topic:
        msg += f" | Tema: {topic}"
    if error_message:
        msg += f" | Erro: {error_message}"
        logger.error(msg, extra=extra)
    else:
        logger.info(msg, extra=extra)
