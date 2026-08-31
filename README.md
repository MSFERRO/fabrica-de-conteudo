# Fábrica de Conteúdo Automatizado v4 (YouTube Shorts) 🚀

Sistema de produção e automação de vídeo curto para o YouTube Shorts, operando 24/7 de forma totalmente assíncrona (`asyncio` + `aiosqlite`), utilizando **voz neural gratuita** (`edge-tts`) e **crop centralizado dinâmico** no FFmpeg.

---

## 📂 Estrutura de Diretórios Criada

```
/content_factory/
├── config/
│   ├── .env.example                 # Exemplo de variáveis de ambiente
│   └── settings.py                  # Definição de caminhos e parâmetros globais
├── assets/
│   └── backgrounds/
│       └── loops/                   # Vídeos de fallback locais (.mp4)
├── output/                          # Vídeos prontos (1080x1920)
├── logs/                            # Logs estruturados (events.json e system.log)
├── src/
│   ├── api/
│   │   ├── openai_client.py         # GPT-4o e Whisper
│   │   ├── tts_engine.py            # edge-tts (Microsoft Neural Voices)
│   │   ├── pexels_client.py         # Cliente assíncrono do Pexels
│   │   └── youtube_client.py        # Upload resumível via threadpool
│   ├── core/
│   │   ├── trend_hunter.py          # Curadoria OpenAI + fallback evergreen
│   │   ├── script_writer.py         # Escrita e validação de roteiros
│   │   ├── asset_downloader.py      # Lógica de fallback em cascata
│   │   ├── video_renderer.py        # FFmpeg + transcrição local faster-whisper
│   │   ├── quota_manager.py         # Gestão de cotas com aiosqlite
│   │   └── youtube_auth.py          # Autenticação OAuth2 via CLI
│   └── utils/
│       ├── alert_bot.py             # Alertas assíncronos no Telegram
│       ├── logger.py                # Logger JSON e System
│       └── validators.py            # probe do FFmpeg para validação
├── tests/
│   └── test_core_pipeline.py        # Testes de unidade e integração
├── requirements.txt
└── README.md
```

---

## 🛠️ Tecnologias e Configurações Chave (v4)

1. **Voz Neural Gratuita (`edge-tts`)**: Gera narrações dinâmicas sem depender de créditos da ElevenLabs. Usa a API de vozes do Microsoft Edge (Exemplo: `pt-BR-FranciscaNeural`).
2. **SQLite Assíncrono (`aiosqlite`)**: Evita travamento do Loop de Eventos principal durante a checagem ou incremento de cotas no banco local.
3. **Múltiplas Chaves do YouTube**: Rotação transparente no `quota_manager.py` para canais que excedem o limite de upload de cota (1600 por post).

---

## ⚙️ Instalação e Execução

### 1. Requisitos Prévios
Certifique-se de que o **Python 3.11+** e o **FFmpeg** (incluindo `ffprobe`) estejam instalados e configurados no PATH do sistema.

### 2. Configurando o Ambiente
- **Windows**: Dê dois cliques em `install.bat`.
- **Linux/Mac**: Rode `chmod +x install.sh && ./install.sh`.

Isso gerará o arquivo `config/.env`. Preencha os dados:
- `OPENAI_API_KEY`: Chave da OpenAI.
- `PEXELS_API_KEY`: Chave do Pexels.
- `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`: Dados do BotFather do Telegram para notificações.
- `EDGE_TTS_VOICE`: `pt-BR-FranciscaNeural` (ou outra de sua preferência).

### 3. Autenticação das Contas do YouTube (OAuth)
1. Salve o arquivo JSON das credenciais do GCP em `config/client_secrets.json` (ou `client_secrets_1.json`, `client_secrets_2.json`, se usar múltiplas chaves).
2. Execute o CLI de autenticação:
   ```bash
   python src/core/youtube_auth.py
   ```
   *Pressione Enter para autenticar no arquivo padrão ou digite o número do índice (ex: 1, 2).*

### 4. Executando a Fábrica 24/7
- **Windows**: Dê dois cliques em `run.bat`.
- **Linux/Mac**: Execute `./run.sh`.

O loop analisará as tendências, fará a curadoria com IA, criará áudio, baixará vídeos, renderizará com legendas e agendará posts automaticamente.

---

## 🧪 Rodando Testes Unitários
Para verificar a integridade dos motores locais, execute na raiz do projeto:
```bash
pytest
```
*Os testes usam mocks e não cobram saldo ou créditos das APIs externas.*
