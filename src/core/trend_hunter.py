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
        Gera tendências virais e de alta retenção diretamente com GPT-4o.
        Caso haja falha de conexão com a OpenAI, ativa os tópicos evergreen de segurança.
        """
        logger.info(f"Caçando temas virais de alta retenção com GPT-4o para o nicho '{niche}'...")
        try:
            trends = await asyncio.to_thread(
                self.openai_client.generate_viral_trends,
                niche,
                5
            )
            if not trends:
                raise ValueError("A resposta do OpenAI não retornou tópicos válidos.")
                
            logger.info(f"GPT-4o gerou {len(trends)} novos temas virais com sucesso.")
            return trends

        except Exception as e:
            logger.warning(f"Aviso na geração de tendências pela OpenAI: {e}. Utilizando lista de segurança.")
            return EVERGREEN_TOPICS
