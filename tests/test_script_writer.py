import pytest
from unittest.mock import MagicMock
from src.core.script_writer import ScriptWriter
from src.utils.validators import validate_script

def test_validate_script_success():
    # Roteiro válido com cerca de 135 palavras, sem emojis e sem markdown
    valid_script = " ".join(["palavra"] * 135)
    is_valid, reason = validate_script(valid_script)
    assert is_valid is True
    assert "Roteiro válido" in reason

def test_validate_script_too_short():
    # Roteiro muito curto (10 palavras)
    short_script = "Um roteiro muito curto que não atende as diretrizes básicas do sistema."
    is_valid, reason = validate_script(short_script)
    assert is_valid is False
    assert "Tamanho incorreto" in reason

def test_validate_script_has_emojis():
    # Contém emojis
    emoji_script = " ".join(["palavra"] * 130) + " 😊🚀"
    is_valid, reason = validate_script(emoji_script)
    assert is_valid is False
    assert "emojis" in reason

def test_validate_script_has_markdown():
    # Contém markdown **negrito**
    markdown_script = " ".join(["palavra"] * 130) + " **negrito**"
    is_valid, reason = validate_script(markdown_script)
    assert is_valid is False
    assert "Markdown" in reason

def test_script_writer_retry_on_invalid_script():
    # Mock do cliente OpenAI que retorna primeiro um roteiro inválido (curto) 
    # e depois um válido na segunda tentativa.
    mock_client = MagicMock()
    mock_client.generate_script.side_effect = [
        "Curto demais.",
        " ".join(["palavra"] * 135)
    ]

    writer = ScriptWriter(openai_client=mock_client)
    result = writer.write_script("Nicho Espacial")
    
    assert len(result.split()) == 135
    assert mock_client.generate_script.call_count == 2
