import os
import sys
import asyncio
import logging
import subprocess
from datetime import datetime
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from src.api.openai_client import OpenAIClient
from src.core.tts_engine import TTSEngine
from src.api.pexels_client import PexelsClient
from src.core.quota_manager import QuotaManager
from src.api.youtube_client import YouTubeClient
from src.utils.validators import get_video_metadata
from src.utils.alert_bot import send_alert
from src.core.video_renderer import VideoRenderer

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger("generate_long_video")

async def generate_long_video_mente_curiosa():
    logger.info("🎬 Iniciando produção de VÍDEO LONGO (16:9 Cinema) para o canal Mente Curiosa...")
    
    openai_client = OpenAIClient()
    tts_engine = TTSEngine(default_voice="pt-BR-FranciscaNeural")
    pexels_client = PexelsClient()
    quota_manager = QuotaManager()
    renderer = VideoRenderer(openai_client)

    topic = "O Efeito Lúcifer: Como Pessoas Boas São Manipuladas Para o Mal"
    logger.info(f"Tema escolhido: '{topic}'")

    # 1. GERAÇÃO DE ROTEIRO DOCUMENTAL APROFUNDADO (GPT-4o)
    logger.info("Gerando roteiro documental aprofundado com GPT-4o...")
    prompt = f"""
    Você é um roteirista sênior de documentários do YouTube especializado em psicologia sombria e comportamento humano.
    Crie um roteiro fascinante, magnético e reflexivo de aproximadamente 450 a 550 palavras (~3 minutos de narração contínua) sobre o tema:
    "{topic}".

    Estrutura obrigatória:
    - Gancho Hipnótico: Comece com uma pergunta chocante que prende o espectador nos primeiros 10 segundos.
    - Bloco 1: O famoso Experimento da Prisão de Stanford de Philip Zimbardo e o que ele revelou sobre a natureza humana.
    - Bloco 2: Os 3 gatilhos psicológicos da desindividuação e obediência cega (como pessoas normais perdem a empatia).
    - Bloco 3: Como esse fenômeno afeta a sociedade moderna, redes sociais e o cotidiano.
    - Conclusão Reflexiva: Mensagem poderosa sobre autoconsciência e call-to-action inteligente convidando para se inscrever no canal Mente Curiosa e debater nos comentários.

    Regras ESTRITAS:
    - Português brasileiro fluído, cinematográfico e envolvente.
    - Texto contínuo puro para locução neural.
    - SEM marcações de cena (não escreva [Música], [Locutor], [Cena], etc.).
    - SEM emojis, SEM asteriscos, SEM hashtags.
    Retorne APENAS o texto do roteiro.
    """

    response = openai_client.client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1500
    )
    script = response.choices[0].message.content.strip().replace('"', '').replace("'", "")
    logger.info(f"Roteiro gerado com sucesso ({len(script.split())} palavras).")

    # 2. CONVERSÃO DE TEXTO PARA VOZ (Edge-TTS com Francisca)
    audio_path = str(settings.ASSETS_DIR / "long_audio_mente_curiosa.mp3")
    logger.info("Sintetizando narração imersiva com voz FranciscaNeural...")
    communicate = __import__("edge_tts").Communicate(script, "pt-BR-FranciscaNeural")
    await communicate.save(audio_path)

    metadata = await get_video_metadata(audio_path)
    audio_duration = metadata.get("duration", 180.0)
    total_duration = audio_duration + 2.0
    logger.info(f"Duração da narração: {audio_duration:.2f}s | Duração total: {total_duration:.2f}s")

    # 3. DOWNLOAD DE MÚLTIPLOS CLIPES 16:9 NO PEXELS (B-Roll Dinâmico)
    search_queries = ["dark psychology", "human brain mystery", "thinking mind shadow", "neural network glowing", "mysterious silhouette", "deep thought"]
    video_paths: List[str] = []

    logger.info("Baixando múltiplos clipes de alta definição (16:9 Horizontal) no Pexels...")
    for idx, query in enumerate(search_queries):
        try:
            results = await pexels_client.search_videos(query=query, orientation="landscape", per_page=5)
            videos = results.get("videos", [])
            if videos:
                # Escolhe o melhor arquivo HD/Full HD
                video_files = videos[0].get("video_files", [])
                link = None
                for vf in video_files:
                    if vf.get("width") == 1920 or vf.get("quality") == "hd":
                        link = vf.get("link")
                        break
                if not link and video_files:
                    link = video_files[0].get("link")

                if link:
                    clip_path = str(settings.BACKGROUNDS_DIR / f"long_bg_{idx+1}.mp4")
                    success = await pexels_client.download_video(link, clip_path)
                    if success and os.path.exists(clip_path):
                        video_paths.append(clip_path)
        except Exception as e:
            logger.warning(f"Erro ao baixar clipe para query '{query}': {e}")

    # Fallback se não baixou clipes suficientes
    if not video_paths:
        logger.warning("Usando clipe de fallback...")
        fallback_clip = str(settings.BACKGROUNDS_DIR / "bg_1.mp4")
        if os.path.exists(fallback_clip):
            video_paths.append(fallback_clip)

    logger.info(f"Total de {len(video_paths)} clipes de fundo 16:9 baixados com sucesso!")

    # 4. TRANSCRIÇÃO DE LEGENDAS SRT
    srt_path = str(settings.BACKGROUNDS_DIR / "long_subtitles_mente_curiosa.srt")
    await renderer._generate_subtitles(audio_path, srt_path)

    # 5. MONTAGEM E RENDERIZAÇÃO FULL HD 1080p (16:9 Widescreen)
    final_video_path = str(settings.OUTPUT_DIR / "long_video_mente_curiosa.mp4")
    music_path = renderer._select_random_bg_music()
    rel_srt_path = os.path.relpath(srt_path, str(settings.BASE_DIR)).replace("\\", "/")

    # Concatenação e transição de clipes 16:9
    cmd = ["ffmpeg", "-y"]
    
    # Adiciona os clipes de vídeo com loop
    primary_bg = video_paths[0] if video_paths else str(settings.BACKGROUNDS_DIR / "bg_1.mp4")
    cmd.extend(["-stream_loop", "-1", "-i", primary_bg])
    cmd.extend(["-i", audio_path])

    video_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,eq=contrast=1.10:saturation=1.25,"
    # Legendas discretas horizontais 16:9 no terço inferior
    video_filter += f"subtitles='{rel_srt_path}':force_style='Fontname=Arial,Fontsize=14,Bold=1,PrimaryColour=&H0014E5FF,OutlineColour=&H00000000,Outline=2.0,Shadow=1.0,BorderStyle=1,Alignment=2,MarginV=60'"

    fade_start = max(0.0, total_duration - 2.0)
    if music_path:
        cmd.extend(["-stream_loop", "-1", "-i", music_path])
        filter_complex = (
            f"[0:v]{video_filter}[v];"
            f"[1:a]apad=pad_dur=2.0,volume=1.0[a1];"
            f"[2:a]volume=0.08,afade=t=out:st={fade_start:.2f}:d=2.0[a2];"
            f"[a1][a2]amix=inputs=2:duration=longest:dropout_transition=2[a]"
        )
        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", "[v]", "-map", "[a]"])
    else:
        filter_complex = f"[0:v]{video_filter}[v];[1:a]apad=pad_dur=2.0,volume=1.0[a]"
        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", "[v]", "-map", "[a]"])

    cmd.extend([
        "-t", f"{total_duration:.3f}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        final_video_path
    ])

    logger.info("Executando renderização FFmpeg Full HD 16:9...")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(settings.BASE_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.error(f"Erro FFmpeg: {stderr.decode('utf-8', errors='ignore')}")
        raise RuntimeError("Falha na renderização do vídeo longo 16:9.")

    logger.info(f"✅ Vídeo Longo 16:9 renderizado com sucesso: {final_video_path}")

    # 6. UPLOAD E PUBLICAÇÃO NO YOUTUBE (Canal Mente Curiosa)
    logger.info("Iniciando upload para o canal Mente Curiosa...")
    youtube_client = quota_manager.get_client_for_channel("Mente Curiosa")

    title = "O Efeito Lúcifer: Por Que Pessoas Boas Ficam Más? (Psicologia Oculta)"
    description = (
        f"{script}\n\n"
        f"---\n"
        f"🧠 Bem-vindo ao canal Mente Curiosa!\n"
        f"Inscreva-se para desvendar os segredos mais profundos da mente humana e do comportamento.\n\n"
        f"Deixe sua opinião nos comentários: você acredita que qualquer pessoa pode sucumbir ao Efeito Lúcifer sob a pressão certa?\n\n"
        f"#psicologia #mentehumana #comportamento #curiosidades #documentario #cienciacognitiva"
    )
    tags = ["psicologia", "mente humana", "efeito lúcifer", "experimento stanford", "ciência", "comportamento", "curiosidades", "cérebro"]

    metadata = {
        "title": title,
        "description": description,
        "tags": tags,
        "category_id": "27",
        "privacy_status": "public"
    }

    video_id = youtube_client.upload_video_resumable(final_video_path, metadata)

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    logger.info(f"🎉 Vídeo Longo publicado com sucesso! Link: {video_url}")

    await send_alert(
        f"🎬 *NOVO VÍDEO LONGO 16:9 NO AR!*\n\n"
        f"📺 *Canal:* Mente Curiosa\n"
        f"🏷️ *Tema:* {title}\n"
        f"⏱️ *Duração:* ~3 minutos (Full HD 1080p)\n"
        f"🔗 *Assista agora:* {video_url}"
    )

    return video_url

if __name__ == "__main__":
    asyncio.run(generate_long_video_mente_curiosa())
