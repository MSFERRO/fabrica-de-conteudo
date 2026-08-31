import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.trend_hunter import TrendHunter, EVERGREEN_TOPICS

@pytest.mark.asyncio
async def test_trend_hunter_fallback_on_exception():
    # Mock do cliente OpenAI
    mock_openai = MagicMock()
    hunter = TrendHunter(openai_client=mock_openai)
    
    # Simula um erro de conexão remota remendando as funções internas de fetch
    with patch.object(hunter, "_fetch_google_trends", side_effect=Exception("Erro de Rede")):
        with patch.object(hunter, "_fetch_reddit_hot", side_effect=Exception("Erro de Rede")):
            # Deve retornar os tópicos evergreen salvando a execução de crashs
            result = await hunter.hunt_trends()
            assert result == EVERGREEN_TOPICS

@pytest.mark.asyncio
async def test_trend_hunter_curates_successfully():
    mock_openai = MagicMock()
    # Simula o retorno curado do OpenAI
    curated_mock = [
        {"topic": "Mistérios Espaciais", "keywords": ["espaço", "nasa"], "viral_score": 98}
    ]
    mock_openai.curate_trends.return_value = curated_mock

    hunter = TrendHunter(openai_client=mock_openai)

    # Simula retorno de dados brutos
    with patch.object(hunter, "_fetch_google_trends", return_value=["Busca 1", "Busca 2"]):
        with patch.object(hunter, "_fetch_reddit_hot", return_value=["Post 1", "Post 2"]):
            result = await hunter.hunt_trends()
            assert result == curated_mock
            mock_openai.curate_trends.assert_called_once()
            # Verifica se agregou as linhas dos dados brutos
            raw_arg = mock_openai.curate_trends.call_args[0][0]
            assert "GOOGLE TRENDS" in raw_arg
            assert "REDDIT" in raw_arg
