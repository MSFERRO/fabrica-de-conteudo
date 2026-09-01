# 🏭 GUIA DE OPERAÇÃO E ESCALA — FÁBRICA DE CONTEÚDO AUTOMATIZADO

Este documento foi elaborado para guiar o **Miguel** na operação diária, manutenção, deploy em nuvem 24/7 e expansão da **Fábrica de Conteúdo Automatizado (YouTube Shorts)**.

---

## 🎯 1. Visão Geral do Sistema

A fábrica é um pipeline 100% autônomo e assíncrono projetado para operar sem intervenção humana:
1. **Caça de Tendências Virais**: O **GPT-4o** analisa o algoritmo e gera temas de alta retenção baseados em *curiosity gaps*, psicologia e ciência.
2. **Roteirização Inteligente**: O **GPT-4o** redige roteiros magnéticos de 130 a 150 palavras (45 a 60 segundos), com validação automática de regras (sem emojis, sem markdown).
3. **Narração Neural**: A voz neural da Microsoft (`pt-BR-FranciscaNeural` / `pt-BR-AntonioNeural`) sintetiza áudio cristalino de estúdio via **Edge-TTS**.
4. **Download de Mídia 4K/HD**: Integração com a API do **Pexels** para buscar vídeos verticais e cinemáticos correspondentes às palavras-chave.
5. **Edição e Renderização Profissional (FFmpeg + Faster-Whisper)**:
   - Transcrição de áudio por inteligência artificial local (**Faster-Whisper** na CPU).
   - Legendas dinâmicas estilo **MrBeast / Alex Hormozi** (Amarelo Ouro `#FFE600`, negrito com contorno preto 3D espesso `3.5px`).
   - Color grading cinematográfico com realce de saturação e contraste (`contrast=1.12:saturation=1.3`).
   - Sincronização e loop automático de vídeo de fundo e trilha sonora via `-stream_loop -1`.
   - Exportação em Full HD vertical estrito **1080x1920 (9:16)**.
6. **Upload e Agendamento Automático no YouTube**:
   - Envio via **YouTube Data API v3** com distribuição inteligente de cota diária (10.000 unidades por credencial).
   - Agendamento espaçado (ex: a cada 4 horas) para evitar penalidades de spam e maximizar o alcance do algoritmo.
7. **Monitoramento e Alertas em Tempo Real**:
   - Bot do Telegram enviando logs de início, erros e os links diretos dos vídeos postados.

---

## 📁 2. Estrutura de Diretórios e Arquivos-Chave

```text
content_factory/
├── config/
│   ├── .env                       # Chaves de API (OpenAI, Pexels, Telegram)
│   ├── settings.py                # Configurações globais e detecção de FFmpeg
│   ├── client_secrets_1.json      # OAuth do Google Cloud - Canal 1
│   ├── client_secrets_2.json      # OAuth do Google Cloud - Canal 2
│   ├── youtube_credentials_1.json # Tokens autenticados do Canal 1 (@CuriosidadeAutomáticasMSF)
│   ├── youtube_credentials_2.json # Tokens autenticados do Canal 2 (@MSFBot2)
│   └── prompts/                   # Prompts do GPT-4o para customização de nichos
├── src/
│   ├── api/
│   │   ├── openai_client.py       # Chamadas ao GPT-4o (temas, roteiros, validação)
│   │   ├── pexels_client.py       # Busca e download de vídeos HD/4K
│   │   └── youtube_client.py      # Upload resumable e agendamento no YouTube
│   ├── core/
│   │   ├── trend_hunter.py        # Caçador autônomo de temas virais
│   │   ├── script_writer.py       # Validador e criador de roteiros
│   │   ├── tts_engine.py          # Motor de narração neural
│   │   ├── asset_downloader.py    # Gerenciador de downloads e loops
│   │   ├── video_renderer.py      # Motor de renderização FFmpeg + Whisper
│   │   ├── quota_manager.py       # Gerenciador de cotas de múltiplos canais
│   │   └── youtube_auth.py        # Servidor local para autorização OAuth2
│   ├── utils/
│   │   ├── alert_bot.py           # Notificações do Telegram
│   │   ├── db.py                  # Banco SQLite assíncrono (content_factory.db)
│   │   ├── logger.py              # Log estruturado em arquivo e console
│   │   └── validators.py          # Validador de qualidade (1080x1920, duração, áudio)
│   └── main.py                    # Loop orquestrador 24/7 da fábrica
├── assets/
│   ├── backgrounds/               # Vídeos de fundo baixados e loops locais
│   └── music/                     # Trilhas sonoras de fundo (lo-fi, suspense, épica)
├── output/                        # Vídeos finais gerados em 1080x1920 prontos
├── logs/
│   └── system.log                 # Histórico completo de execução e auditoria
├── run.bat                        # Inicializador rápido para Windows
└── requirements.txt               # Dependências Python do projeto
```

---

## 🚀 3. Como Rodar Localmente (Windows)

1. **Abrir a pasta do projeto** no terminal:
   ```cmd
   cd "C:\Users\USUARIO\Documents\PROJETOS\FABRICA DE AUTOMAÇÃO\content_factory"
   ```
2. **Iniciar o ambiente**:
   ```cmd
   run.bat
   ```
   *Ou diretamente pelo Python:*
   ```cmd
   venv\Scripts\python.exe src/main.py
   ```
3. **Acompanhar**: O terminal mostrará o progresso em tempo real e o bot do Telegram alertará a cada vídeo renderizado e postado.

---

## ☁️ 4. Como Fazer Deploy 24/7 na Nuvem (VPS Linux / Ubuntu)

Para manter a fábrica operando 24 horas por dia sem depender do notebook:

### Passo 1: Criar uma VPS
- **Recomendação**: VPS Ubuntu 22.04 ou 24.04 (DigitalOcean, AWS EC2, Hetzner ou Hostinger).
- **Configuração mínima**: 2 vCPUs, 4GB RAM, 40GB SSD (Custo médio: $6 a $10/mês).

### Passo 2: Instalar Dependências no Servidor
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip ffmpeg git
```

### Passo 3: Clonar o Repositório do GitHub
```bash
git clone https://github.com/MSFERRO/fabrica-de-conteudo.git
cd fabrica-de-conteudo/content_factory
```

### Passo 4: Criar o Ambiente Virtual e Instalar Pacotes
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Passo 5: Configurar as Variáveis e Credenciais
Crie o arquivo `config/.env` e copie as chaves:
```env
OPENAI_API_KEY=sua_chave_openai
PEXELS_API_KEY=sua_chave_pexels
TELEGRAM_BOT_TOKEN=seu_token_telegram
TELEGRAM_CHAT_ID=seu_chat_id
SCHEDULE_INTERVAL=4
```
Transfira os arquivos `client_secrets_*.json` e `youtube_credentials_*.json` para a pasta `config/`.

### Passo 6: Rodar em Segundo Plano com `pm2` ou `systemd`
```bash
# Instalar PM2
sudo apt install -y nodejs npm
sudo npm install -g pm2

# Iniciar a fábrica com reinício automático em caso de reboot
pm2 start "venv/bin/python src/main.py" --name "fabrica-shorts"
pm2 save
pm2 startup
```

---

## 🔑 5. Como Adicionar Novos Canais (Canal 3, Canal 4...)

A fábrica foi arquitetada para escalar para dezenas de canais:

1. **No Google Cloud Console**:
   - Crie um novo projeto ou adicione um novo OAuth 2.0 Client ID.
   - Baixe o JSON e salve em `config/client_secrets_3.json`.
2. **Autorizar a Conta**:
   Execute o assistente interativo de autenticação:
   ```cmd
   venv\Scripts\python.exe -c "import asyncio; from src.core.youtube_auth import authenticate_channel; asyncio.run(authenticate_channel('config/client_secrets_3.json', 'config/youtube_credentials_3.json'))"
   ```
   - Faça login na conta do canal no navegador e autorize.
   - O arquivo `config/youtube_credentials_3.json` será gerado automaticamente.
3. **Pronto!** O `quota_manager.py` detectará a nova credencial automaticamente na próxima inicialização e incluirá o novo canal no rodízio de postagens.

---

## 📊 6. Estratégias de Otimização e Escala

1. **Alteração de Nicho / Tópicos**:
   - Para mudar o estilo de vídeos de um canal (ex: focar em *Finanças*, *Tecnologia*, *História Antiga*), basta editar os prompts em `config/prompts/` ou passar o parâmetro de nicho no `trend_hunter.py`.
2. **Trilhas Sonoras Personalizadas**:
   - Adicione arquivos de áudio `.mp3` sem direitos autorais na pasta `assets/music/`. O sistema selecionará faixas aleatórias e fará o *ducking* automático de volume durante a narração.
3. **Distribuição Multi-Plataforma (TikTok / Instagram Reels / Kwai)**:
   - Todos os vídeos gerados ficam preservados em `output/final_X.mp4`.
   - O Miguel pode usar esses mesmos vídeos verticais prontos em Full HD para postar no TikTok e Instagram Reels, triplicando o alcance sem nenhum custo extra de produção.

---

## 🛠️ 7. Comandos de Diagnóstico e Manutenção

- **Verificar logs ao vivo:**
  ```cmd
  Get-Content logs/system.log -Wait -Tail 30
  ```
- **Limpar fila do banco de dados (Resetar para novo ciclo):**
  ```cmd
  del content_factory.db
  ```
- **Executar bateria de testes automatizados:**
  ```cmd
  venv\Scripts\pytest.exe tests/
  ```

---
*Fábrica de Conteúdo Automatizado — Desenvolvida com arquitetura de alta resiliência, automação assíncrona e inteligência artificial de ponta.*
