import os
import re
import json
import asyncio
import logging
from typing import Dict, Any, Tuple
from config import settings

logger = logging.getLogger("content_factory.validators")

def validate_script(script: str) -> Tuple[bool, str]:
    """
    Valida as regras de negócio do roteiro gerado:
    - 130 a 170 palavras (margem de tolerância).
    - Sem emojis.
    - Sem markdown (**negrito**, # título, etc.).
    """
    if not script:
        return False, "O roteiro está vazio."

    # Contagem de palavras
    word_count = len(script.split())
    if word_count < 110 or word_count > 180:
        return False, f"Tamanho incorreto: {word_count} palavras (esperado: 130-150)."

    # Verifica presença de emojis
    emoji_regex = re.compile(
        "["
        "\U00010000-\U0010ffff"
        "\u2600-\u27BF"
        "]+", 
        flags=re.UNICODE
    )
    if emoji_regex.search(script):
        return False, "O roteiro contém emojis não permitidos."

    # Verifica formatação markdown comum
    markdown_patterns = [r"\*\*.*?\*\*", r"\#+ ", r"\`+.*?\`+", r"\[.*?\]\(.*?\)", r"\-\-\-"]
    for pattern in markdown_patterns:
        if re.search(pattern, script):
            return False, f"O roteiro contém caracteres de formatação Markdown inválidos ({pattern})."

    return True, "Roteiro válido."

async def get_video_metadata(video_path: str) -> Dict[str, Any]:
    """
    Usa o ffprobe para extrair metadados exatos do arquivo de mídia (resolução, duração).
    Suporta tanto arquivos de vídeo (MP4) quanto de áudio (MP3, WAV).
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Arquivo não encontrado para inspeção: {video_path}")

    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-show_entries", "format=duration:stream=width,height,duration", 
        "-of", "json", 
        video_path
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.error(f"Erro no ffprobe: {stderr.decode()}")
            return {}

        data = json.loads(stdout.decode())
        result = {}
        
        # Extrai duração do formato geral (funciona para áudio e vídeo)
        format_info = data.get("format", {})
        if "duration" in format_info:
            try:
                result["duration"] = float(format_info["duration"])
            except (ValueError, TypeError):
                pass

        # Extrai resolução do stream de vídeo, se existir
        streams = data.get("streams", [])
        for stream in streams:
            if "width" in stream and "height" in stream:
                result["width"] = int(stream["width"])
                result["height"] = int(stream["height"])
                if "duration" in stream and "duration" not in result:
                    try:
                        result["duration"] = float(stream["duration"])
                    except (ValueError, TypeError):
                        pass
                break
                
        return result
    except Exception as e:
        logger.error(f"Falha ao rodar ffprobe no arquivo {video_path}: {e}")
        return {}

async def validate_video(video_path: str) -> Tuple[bool, str]:
    """
    Valida as regras de qualidade do vídeo gerado:
    - O arquivo precisa existir e ter tamanho > 1MB.
    - Duração deve ser entre 35s e 70s.
    - A resolução deve ser estritamente 1080x1920 (Vertical 9:16).
    """
    if not os.path.exists(video_path):
        return False, "Arquivo de vídeo não existe."

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    if file_size_mb < 0.5:
        return False, f"Arquivo de vídeo muito pequeno: {file_size_mb:.2f}MB (Provavelmente corrompido)."

    metadata = await get_video_metadata(video_path)
    if not metadata:
        return False, "Não foi possível extrair metadados do vídeo com o ffprobe."

    width = metadata.get("width", 0)
    height = metadata.get("height", 0)
    duration = metadata.get("duration", 0.0)

    if width != 1080 or height != 1920:
        return False, f"Dimensões incorretas: {width}x{height} (Esperado: 1080x1920)."

    if duration < 35.0 or duration > 70.0:
        return False, f"Duração fora dos limites: {duration:.2f}s (Esperado: 45-60s)."

    return True, f"Vídeo válido. Duração: {duration:.2f}s. Resolução: {width}x{height}."
