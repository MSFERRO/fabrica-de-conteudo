import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.script_writer import ScriptWriter
from src.core.trend_hunter import TrendHunter, EVERGREEN_TOPICS
from src.core.quota_manager import QuotaManager
from src.core.asset_downloader import AssetDownloader
from src.api.tts_engine import TTSEngine
from src.utils.validators import validate_script

def test_validate_script_constraints():
    # Roteiro válido (130 palavras, sem emojis, sem markdown)
    valid_script = " ".join(["fato"] * 135)
    is_valid, reason = validate_script(valid_script)
    assert is_valid is True

    # Roteiro muito curto (10 palavras)
    short_script = "Um roteiro curto demais que deve ser invalidado."
    is_valid, reason = validate_script(short_script)
    assert is_valid is False
    assert "Tamanho incorreto" in reason

    # Presença de Emojis
    emoji_script = " ".join(["fato"] * 130) + " 🚀😊"
    is_valid, reason = validate_script(emoji_script)
    assert is_valid is False
    assert "emojis" in reason

@pytest.mark.asyncio
async def test_trend_hunter_fallback():
    mock_openai = MagicMock()
    hunter = TrendHunter(openai_client=mock_openai)
    
    # Simula erro de conexão nas buscas
    with patch.object(hunter, "_fetch_google_trends", side_effect=Exception("Timeout")):
        with patch.object(hunter, "_fetch_reddit_hot", side_effect=Exception("403 Forbidden")):
            # Deve disparar o fallback e retornar tópicos evergreen
            result = await hunter.hunt_trends()
            assert result == EVERGREEN_TOPICS

@pytest.mark.asyncio
async def test_tts_engine_generation(tmp_path):
    # Mock do edge_tts Communicate
    tts_engine = TTSEngine()
    
    mock_communicate = MagicMock()
    mock_communicate.save = AsyncMock()
    
    # Criamos um arquivo falso no diretório temporário para simular sucesso
    dummy_audio = tmp_path / "narration_99.mp3"
    
    with patch("edge_tts.Communicate", return_value=mock_communicate):
        with patch("config.settings.ASSETS_DIR", tmp_path):
            # Escrevemos conteúdo de teste para simular que o arquivo foi gerado
            with open(dummy_audio, "w") as f:
                f.write("dummy audio content")
                
            result = await tts_engine.generate_narration("Texto de roteiro para o Shorts", job_id=99)
            assert result == str(dummy_audio)
            mock_communicate.save.assert_called_once_with(str(dummy_audio))

@pytest.mark.asyncio
async def test_asset_downloader_local_fallback(tmp_path):
    mock_pexels = MagicMock()
    downloader = AssetDownloader(pexels_client=mock_pexels)
    
    # Simula pasta de loops com um arquivo de vídeo
    loops_dir = tmp_path / "loops"
    bg_dir = tmp_path / "backgrounds"
    loops_dir.mkdir(parents=True)
    bg_dir.mkdir(parents=True)
    
    dummy_fallback_video = loops_dir / "fallback_1.mp4"
    with open(dummy_fallback_video, "w") as f:
        f.write("dummy video data")

    with patch("config.settings.FALLBACK_DIR", loops_dir):
        with patch("config.settings.BACKGROUNDS_DIR", bg_dir):
            # Força erro na chamada da API para ativar o fallback local
            mock_pexels.search_videos = AsyncMock(side_effect=Exception("API Error"))
            
            result_path, needs_crop = await downloader.download_background_video(["espaço"], job_id=5)
            
            assert os.path.exists(result_path)
            assert "bg_5.mp4" in result_path
            assert needs_crop is False
