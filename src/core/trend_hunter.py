import xml.etree.ElementTree as ET
import httpx
import asyncio
import logging
from typing import List, Dict, Any
from src.api.openai_client import OpenAIClient
from src.utils.alert_bot import send_alert

logger = logging.getLogger("content_factory.trend_hunter")

EVERGREEN_TOPICS = [
    {
        "topic": "O mistério dos Buracos Negros no espaço profundo", 
        "keywords": ["espaço", "buraco negro", "universo", "astronomia"], 
        "viral_score": 95
    },
    {
        "topic": "Como o cérebro humano sabota suas próprias decisões", 
        "keywords": ["psicologia", "cérebro", "ciência", "mente"], 
        "viral_score": 92
    },
    {
        "topic": "3 Fatos inacreditáveis sobre as profundezas do oceano", 
        "keywords": ["oceano", "curiosidades", "animais marinhos", "natureza"], 
        "viral_score": 90
    },
    {
        "topic": "O manuscrito misterioso que ninguém consegue decifrar", 
        "keywords": ["história", "mistério", "arqueologia", "enigma"], 
        "viral_score": 88
    },
    {
        "topic": "O que aconteceria se a Terra parasse de girar por um segundo?", 
        "keywords": ["terra", "física", "ciência", "catástrofe"], 
        "viral_score": 94
    }
]

class TrendHunter:
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client

    async def _fetch_google_trends(self) -> List[str]:
        """Busca tendências diárias do Google Trends via RSS Feed do Brasil."""
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=BR"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.warning(f"Não foi possível obter Google Trends RSS. Status: {response.status_code}")
                return []
            
            root = ET.fromstring(response.content)
            titles = []
            for item in root.findall(".//item/title"):
                if item.text:
                    titles.append(item.text.strip())
            return titles

    async def _fetch_reddit_hot(self, subreddit: str) -> List[str]:
        """Busca posts populares de um determinado subreddit via JSON público."""
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=15"
        headers = {
            "User-Agent": "ContentFactoryBot/1.0 (Contact: marcelo@example.com)"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.warning(f"Não foi possível obter posts de r/{subreddit}. Status: {response.status_code}")
                return []
            
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            titles = []
            for post in posts:
                title = post.get("data", {}).get("title")
                if title:
                    titles.append(title.strip())
            return titles

    async def hunt_trends(self, niche: str = "ciência e curiosidades") -> List[Dict[str, Any]]:
        """
        Coleta dados do Google Trends e do Reddit, envia para curadoria da OpenAI.
        Se houver qualquer falha de rede ou parsing, ativa o fallback de temas evergreen.
        """
        logger.info("Iniciando caça por tendências...")
        try:
            google_task = self._fetch_google_trends()
            reddit_til_task = self._fetch_reddit_hot("todayilearned")
            reddit_space_task = self._fetch_reddit_hot("space")

            google_trends, reddit_til, reddit_space = await asyncio.gather(
                google_task, reddit_til_task, reddit_space_task,
                return_exceptions=True
            )

            google_trends = google_trends if not isinstance(google_trends, Exception) else []
            reddit_til = reddit_til if not isinstance(reddit_til, Exception) else []
            reddit_space = reddit_space if not isinstance(reddit_space, Exception) else []

            raw_lines = []
            if google_trends:
                raw_lines.append("=== GOOGLE TRENDS BRASIL ===")
                raw_lines.extend(google_trends[:15])
            if reddit_til:
                raw_lines.append("=== REDDIT r/todayilearned ===")
                raw_lines.extend(reddit_til[:10])
            if reddit_space:
                raw_lines.append("=== REDDIT r/space ===")
                raw_lines.extend(reddit_space[:10])

            if not raw_lines or len(raw_lines) < 5:
                raise ValueError("Pouco ou nenhum dado bruto pôde ser coletado das fontes primárias.")

            raw_data_str = "\n".join(raw_lines)
            logger.info("Dados brutos coletados. Enviando para OpenAI curar os melhores tópicos...")
            
            trends = self.openai_client.curate_trends(raw_data_str, niche=niche)
            
            if not trends:
                raise ValueError("A resposta de curadoria do OpenAI não retornou tópicos válidos.")
                
            logger.info(f"Caça de tendências finalizada com sucesso. {len(trends)} tópicos encontrados.")
            return trends

        except Exception as e:
            logger.error(f"Erro durante a caça de tendências: {e}. Ativando fallback de tópicos evergreen...")
            await send_alert(
                f"⚠️ *Alerta de Fallback*: Falha ao caçar tendências ({e}). Usando tópicos evergreen."
            )
            return EVERGREEN_TOPICS
