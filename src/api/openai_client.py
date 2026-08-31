import os
import json
import re
from openai import OpenAI
from typing import List, Dict, Any
from config import settings

class OpenAIClient:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não encontrada nas configurações. Verifique o arquivo config/.env")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def _load_prompt_template(self, filename: str) -> str:
        """Carrega um arquivo de prompt a partir da pasta de prompts."""
        path = settings.CONFIG_DIR / "prompts" / filename
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def curate_trends(self, raw_data: str, niche: str = "ciência e curiosidades") -> List[Dict[str, Any]]:
        """Usa GPT-4o para transformar dados brutos em tópicos virais estruturados."""
        template = self._load_prompt_template("trend_prompt.txt")
        
        if template:
            prompt = template.format(niche=niche, raw_data=raw_data)
        else:
            prompt = f"""
            Você é um especialista em algoritmos de YouTube Shorts. 
            Analise os seguintes dados brutos de tendências e selecione os 5 melhores tópicos para o nicho: "{niche}".
            
            Dados brutos:
            {raw_data}
            
            Regras de saída ESTRITAS:
            1. Retorne APENAS um array JSON válido.
            2. NÃO use markdown (```json), NÃO escreva texto antes ou depois.
            3. Formato exato: [{{"topic": "Título chamativo em PT-BR", "keywords": ["kw1", "kw2"], "viral_score": 95}}]
            4. viral_score deve ser um inteiro entre 1 e 100.
            """
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Limpeza robusta de blocos de código markdown ```json ou ```
        content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Falha ao decodificar JSON da resposta do OpenAI. Resposta: {content}") from e

    def generate_script(self, topic: str, duration_seconds: int = 60) -> str:
        """Gera o roteiro final baseado no tópico aprovado."""
        template = self._load_prompt_template("script_template.txt")
        
        if template:
            prompt = template.format(topic=topic, duration=duration_seconds)
        else:
            prompt = f"""
            Crie um roteiro de vídeo curto (YouTube Shorts) extremamente engajador sobre o tema: "{topic}".
            Regras:
            - Português brasileiro, tom envolvente e simples.
            - Comece com um gancho impactante (ex: "Você sabia que...?").
            - Inclua 2 ou 3 fatos reais e surpreendentes.
            - Termine com uma pergunta ou call-to-action curta.
            - NÃO use emojis, NÃO use markdown, NÃO use aspas no texto final.
            - Tamanho: aproximadamente 130 a 150 palavras.
            Retorne APENAS o texto do roteiro.
            """
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        script = response.choices[0].message.content.strip()
        return script.replace('"', '').replace("'", "")

    def transcribe_audio_to_srt(self, audio_file_path: str) -> str:
        """Transcreve áudio para formato SRT usando a API do Whisper da OpenAI."""
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Arquivo de áudio não encontrado para transcrição: {audio_file_path}")
            
        with open(audio_file_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="srt"
            )
        return transcript
