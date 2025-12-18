"""
YouTube audio downloader pro XTTS-v2 Demo
"""
import re
import subprocess
import uuid
from pathlib import Path
from typing import Tuple, Optional
from backend.config import (
    TARGET_SAMPLE_RATE,
    TARGET_CHANNELS,
    MIN_VOICE_DURATION,
    DEMO_VOICES_DIR
)
from backend.audio_processor import AudioProcessor


def validate_youtube_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validuje YouTube URL

    Args:
        url: YouTube URL k validaci

    Returns:
        (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL je prázdná"

    # YouTube URL patterns - podporuje více formátů
    patterns = [
        r'(?:https?://)?(?:www\.)?(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?.*[&?]v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return True, None

    return False, "Neplatná YouTube URL. Použijte formát: https://www.youtube.com/watch?v=VIDEO_ID nebo https://youtu.be/VIDEO_ID"


def extract_video_id(url: str) -> Optional[str]:
    """
    Extrahuje video ID z YouTube URL
    Ignoruje parametry playlistu a další parametry - najde video ID i v URL s parametry

    Args:
        url: YouTube URL (může obsahovat parametry jako &list=, &index=, atd.)

    Returns:
        Video ID nebo None
    """
    patterns = [
        # Standardní formát: ?v=VIDEO_ID nebo &v=VIDEO_ID (i s dalšími parametry)
        r'[?&]v=([a-zA-Z0-9_-]{11})',
        # youtu.be formát: /VIDEO_ID
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        # Embed formát: /embed/VIDEO_ID
        r'/embed/([a-zA-Z0-9_-]{11})',
        # Starý formát: /v/VIDEO_ID
        r'/v/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            # Ověření, že video ID má správnou délku (11 znaků)
            if len(video_id) == 11:
                return video_id

    return None


def get_video_info(url: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Získá informace o videu pomocí yt-dlp

    Args:
        url: YouTube URL

    Returns:
        (video_info, error_message)
    """
    try:
        import yt_dlp

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            return {
                'id': info.get('id'),
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
            }, None

    except ImportError:
        return None, "yt-dlp není nainstalován. Nainstalujte pomocí: pip install yt-dlp"
    except Exception as e:
        error_msg = str(e)
        # Lepší error messages
        if "Private video" in error_msg or "Video unavailable" in error_msg:
            return None, "Video není dostupné (soukromé nebo smazané)"
        elif "HTTP Error 403" in error_msg or "HTTP Error 404" in error_msg:
            return None, "Video není dostupné nebo bylo smazáno"
        else:
            return None, f"Chyba při získávání informací o videu: {error_msg[:200]}"


def download_youtube_audio(
    url: str,
    output_path: str,
    start_time: Optional[float] = None,
    duration: Optional[float] = None
) -> Tuple[bool, Optional[str]]:
    """
    Stáhne audio z YouTube a uloží jako WAV

    Args:
        url: YouTube URL
        output_path: Cesta k výstupnímu souboru
        start_time: Začátek ořezu v sekundách (volitelné)
        duration: Délka ořezu v sekundách (volitelné)

    Returns:
        (success, error_message)
    """
    try:
        import yt_dlp

        # Validace URL
        is_valid, error = validate_youtube_url(url)
        if not is_valid:
            return False, error

        # Vytvoření dočasného souboru
        temp_dir = Path(output_path).parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / f"youtube_{uuid.uuid4()}.%(ext)s"

        # Extrahování video ID z URL
        expected_video_id = extract_video_id(url)
        if not expected_video_id:
            return False, "Nelze extrahovat video ID z URL"

        # Vytvoření čisté URL pouze s video ID (bez parametrů playlistu)
        # Tím zajistíme, že se stáhne správné video, ne jiné z playlistu
        clean_url = f"https://www.youtube.com/watch?v={expected_video_id}"

        # yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(temp_file),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'quiet': True,  # Tichý režim
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': True,  # Ignorovat playlisty, stáhnout jen video
        }

        # Stáhnutí audio s ověřením video ID
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Nejdřív získáme informace o videu pomocí čisté URL, abychom ověřili ID
                info = ydl.extract_info(clean_url, download=False)
                actual_video_id = info.get('id')

                # Ověření, že se stahuje správné video
                if actual_video_id != expected_video_id:
                    return False, f"Chyba: Očekáváno video ID '{expected_video_id}', ale yt-dlp našlo '{actual_video_id}'. Video může být nedostupné nebo bylo přesměrováno."

                print(f"✅ Ověřeno: Stahuje se správné video ID: {actual_video_id}")
                print(f"📹 Název videa: {info.get('title', 'Unknown')}")

                # Nyní stáhneme audio pomocí čisté URL
                ydl.download([clean_url])
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "Private video" in error_msg:
                return False, "Video je soukromé a není dostupné"
            elif "Video unavailable" in error_msg:
                return False, "Video není dostupné nebo bylo smazáno"
            elif "Sign in to confirm your age" in error_msg:
                return False, "Video vyžaduje přihlášení nebo potvrzení věku"
            else:
                return False, f"Chyba při stahování: {error_msg[:200]}"

        # Najít stažený soubor (yt-dlp přidá .wav příponu)
        downloaded_files = list(temp_dir.glob("youtube_*.wav"))
        if not downloaded_files:
            # Zkus najít jakýkoliv audio soubor
            downloaded_files = list(temp_dir.glob("youtube_*.*"))
            if not downloaded_files:
                return False, "Stažený soubor nebyl nalezen. Zkontrolujte, zda je video dostupné."

        downloaded_file = downloaded_files[0]

        # Ořez časového úseku pokud je zadán
        if start_time is not None or duration is not None:
            trimmed_file = temp_dir / f"trimmed_{uuid.uuid4()}.wav"
            success, error = _trim_audio(
                str(downloaded_file),
                str(trimmed_file),
                start_time,
                duration
            )
            if not success:
                # Smazat dočasný soubor
                downloaded_file.unlink(missing_ok=True)
                return False, error

            downloaded_file = trimmed_file

        # Zpracování pomocí AudioProcessor (44100 Hz, mono - CD kvalita)
        # Vypnuto pokročilé zpracování - způsobovalo flanger efekt a pumpování
        success, error = AudioProcessor.convert_audio(
            str(downloaded_file),
            output_path,
            apply_advanced_processing=False
        )

        # Smazat dočasné soubory
        downloaded_file.unlink(missing_ok=True)
        if start_time is not None or duration is not None:
            trimmed_file.unlink(missing_ok=True)

        if not success:
            return False, error

        # Validace výstupního souboru
        is_valid, error = AudioProcessor.validate_audio_file(output_path)
        if not is_valid:
            return False, error

        return True, None

    except ImportError as e:
        return False, "yt-dlp není nainstalován. Nainstalujte pomocí: pip install yt-dlp"
    except Exception as e:
        error_msg = str(e)
        # Lepší error messages pro běžné chyby
        if "Private video" in error_msg or "Video unavailable" in error_msg:
            return False, "Video není dostupné (soukromé nebo smazané)"
        elif "Sign in to confirm your age" in error_msg:
            return False, "Video vyžaduje přihlášení nebo potvrzení věku"
        elif "HTTP Error 403" in error_msg or "HTTP Error 404" in error_msg:
            return False, "Video není dostupné nebo bylo smazáno"
        else:
            return False, f"Chyba při stahování z YouTube: {error_msg[:200]}"


def _trim_audio(
    input_path: str,
    output_path: str,
    start_time: Optional[float] = None,
    duration: Optional[float] = None
) -> Tuple[bool, Optional[str]]:
    """
    Ořízne audio na zadaný časový úsek

    Args:
        input_path: Cesta k vstupnímu souboru
        output_path: Cesta k výstupnímu souboru
        start_time: Začátek ořezu v sekundách
        duration: Délka ořezu v sekundách

    Returns:
        (success, error_message)
    """
    # Zkus FFmpeg nejprve (rychlejší)
    # Kontrola FFmpeg dostupnosti
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        ffmpeg_available = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        ffmpeg_available = False

    if ffmpeg_available:
        try:
            cmd = ["ffmpeg", "-i", str(input_path), "-y"]

            if start_time is not None:
                cmd.extend(["-ss", str(start_time)])

            if duration is not None:
                cmd.extend(["-t", str(duration)])

            cmd.append(str(output_path))

            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )

            return True, None

        except subprocess.CalledProcessError as e:
            # Fallback na librosa
            pass

    # Fallback na librosa
    try:
        import librosa
        import soundfile as sf

        # Načtení audio
        audio, sr = librosa.load(
            input_path,
            offset=start_time if start_time else 0,
            duration=duration if duration else None,
            sr=None  # Ponechat původní sample rate
        )

        # Uložení
        sf.write(output_path, audio, sr)

        return True, None

    except Exception as e:
        return False, f"Chyba při ořezu audio: {str(e)}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitizuje název souboru (odstraní nebezpečné znaky)

    Args:
        filename: Původní název souboru

    Returns:
        Sanitizovaný název souboru
    """
    # Odstranění přípony pokud existuje
    filename = Path(filename).stem

    # Povolené znaky: písmena, čísla, podtržítko, pomlčka
    filename = re.sub(r'[^a-zA-Z0-9_-]', '_', filename)

    # Omezení délky
    filename = filename[:50]

    # Zajištění, že není prázdný
    if not filename:
        filename = "youtube_audio"

    return filename

