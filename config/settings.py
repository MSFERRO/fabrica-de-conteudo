import os
from pathlib import Path
from dotenv import load_dotenv

# Encontra a raiz do projeto (content_factory)
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega as variáveis de ambiente
ENV_PATH = BASE_DIR / "config" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Configurações de API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# Configuração de Voz (edge-tts)
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "pt-BR-FranciscaNeural")

# Telegram Bot Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configurações do Sistema
SUBTITLE_GENERATION_METHOD = os.getenv("SUBTITLE_GENERATION_METHOD", "local_whisper").lower()
VIDEO_DURATION = int(os.getenv("VIDEO_DURATION", 60))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))
PARALLEL_JOBS = int(os.getenv("PARALLEL_JOBS", 3))
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 3))
SCHEDULE_INTERVAL = int(os.getenv("SCHEDULE_INTERVAL", 4))
QUALITY_THRESHOLD = float(os.getenv("QUALITY_THRESHOLD", 0.8))

# Diretórios do Sistema
ASSETS_DIR = BASE_DIR / "assets"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"
FALLBACK_DIR = BACKGROUNDS_DIR / "loops"
MUSIC_DIR = ASSETS_DIR / "music"
FONTS_DIR = ASSETS_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

# Certifica que todos os diretórios necessários existem
for directory in [ASSETS_DIR, BACKGROUNDS_DIR, FALLBACK_DIR, MUSIC_DIR, FONTS_DIR, OUTPUT_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Banco de Dados
DB_PATH = BASE_DIR / "content_factory.db"
