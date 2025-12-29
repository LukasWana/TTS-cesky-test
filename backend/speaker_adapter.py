"""
Speaker Adaptation modul pro caching a optimalizaci speaker embeddingů
"""
import hashlib
import pickle
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from backend.config import ENABLE_SPEAKER_CACHE, SPEAKER_CACHE_DIR
import torch


class SpeakerAdapter:
    """Třída pro caching a optimalizaci speaker embeddingů"""

    def __init__(self):
        self.cache_dir = SPEAKER_CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        self.enabled = ENABLE_SPEAKER_CACHE

    def _get_cache_key(self, speaker_wav_path: str) -> str:
        """
        Vytvoří cache klíč z cesty k audio souboru

        Args:
            speaker_wav_path: Cesta k speaker audio souboru

        Returns:
            Cache klíč (hash)
        """
        # Použij hash cesty a velikosti souboru pro jedinečnost
        path_str = str(Path(speaker_wav_path).resolve())
        try:
            file_size = Path(speaker_wav_path).stat().st_size
            key_data = f"{path_str}:{file_size}"
        except:
            key_data = path_str

        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """
        Vrátí cestu k cache souboru

        Args:
            cache_key: Cache klíč

        Returns:
            Cesta k cache souboru
        """
        return self.cache_dir / f"{cache_key}.pkl"

    def get_speaker_embedding(
        self,
        speaker_wav_path: str,
        tts_model
    ) -> Optional[torch.Tensor]:
        """
        Získá speaker embedding z cache nebo extrahuje z audio

        Args:
            speaker_wav_path: Cesta k speaker audio souboru
            tts_model: TTS model instance

        Returns:
            Speaker embedding tensor nebo None
        """
        if not self.enabled:
            return None

        cache_key = self._get_cache_key(speaker_wav_path)
        cache_path = self._get_cache_path(cache_key)

        # Zkus načíst z cache
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    cached_data = pickle.load(f)
                    print(f"✅ Speaker embedding načten z cache: {cache_key[:8]}...")
                    return cached_data
            except Exception as e:
                print(f"Warning: Failed to load speaker cache: {e}")

        # Pokud není v cache, extrahuj z modelu
        try:
            embedding = self._extract_embedding(speaker_wav_path, tts_model)
            if embedding is not None:
                # Ulož do cache
                try:
                    with open(cache_path, 'wb') as f:
                        # Ukládej na CPU (bez vazby na konkrétní device)
                        pickle.dump(embedding.detach().cpu(), f)
                    print(f"💾 Speaker embedding uložen do cache: {cache_key[:8]}...")
                except Exception as e:
                    print(f"Warning: Failed to save speaker cache: {e}")

            return embedding
        except Exception as e:
            print(f"Warning: Failed to extract speaker embedding: {e}")
            return None

    def get_conditioning_latents(
        self,
        speaker_wav_path: str,
        tts_model
    ) -> Optional[Tuple[torch.Tensor, torch.Tensor]]:
        """
        Vrátí (gpt_cond_latent, speaker_embedding) z cache nebo je spočítá.
        Pokud verze TTS neumožňuje extrakci, vrátí None.
        """
        if not self.enabled:
            return None

        cache_key = self._get_cache_key(speaker_wav_path)
        cache_path = self._get_cache_path(f"cond_{cache_key}")

        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    data = pickle.load(f)
                gpt = data.get("gpt_cond_latent")
                emb = data.get("speaker_embedding")
                if gpt is not None and emb is not None:
                    print(f"✅ Conditioning latents načteny z cache: {cache_key[:8]}...")
                    return gpt, emb
            except Exception as e:
                print(f"Warning: Failed to load conditioning cache: {e}")

        try:
            gpt, emb = self._extract_conditioning_latents(speaker_wav_path, tts_model)
            if gpt is None or emb is None:
                return None
            try:
                with open(cache_path, "wb") as f:
                    pickle.dump(
                        {
                            "gpt_cond_latent": gpt.detach().cpu(),
                            "speaker_embedding": emb.detach().cpu(),
                        },
                        f,
                    )
                print(f"💾 Conditioning latents uloženy do cache: {cache_key[:8]}...")
            except Exception as e:
                print(f"Warning: Failed to save conditioning cache: {e}")
            return gpt, emb
        except Exception as e:
            print(f"Warning: Failed to extract conditioning latents: {e}")
            return None

    def _extract_embedding(
        self,
        speaker_wav_path: str,
        tts_model
    ) -> Optional[torch.Tensor]:
        """
        Extrahuje speaker embedding z audio pomocí TTS modelu

        Args:
            speaker_wav_path: Cesta k speaker audio souboru
            tts_model: TTS model instance

        Returns:
            Speaker embedding tensor nebo None
        """
        try:
            # XTTS model má metodu pro extrakci speaker embeddingu
            # Zkus různé možné metody podle verze TTS
            if hasattr(tts_model, 'synthesizer'):
                synthesizer = tts_model.synthesizer
                if hasattr(synthesizer, 'get_conditioning_latents'):
                    # XTTS-v2 metoda
                    gpt_cond_latent, speaker_embedding, _ = synthesizer.get_conditioning_latents(
                        audio_path=speaker_wav_path
                    )
                    return speaker_embedding
                elif hasattr(synthesizer, 'compute_speaker_embedding'):
                    # Alternativní metoda
                    return synthesizer.compute_speaker_embedding(speaker_wav_path)
            elif hasattr(tts_model, 'get_speaker_embedding'):
                return tts_model.get_speaker_embedding(speaker_wav_path)

            # Pokud žádná metoda nefunguje, vrať None
            print("Warning: Speaker embedding extraction not available in this TTS version")
            return None

        except Exception as e:
            print(f"Error extracting speaker embedding: {e}")
            return None

    def _extract_conditioning_latents(
        self,
        speaker_wav_path: str,
        tts_model
    ) -> Tuple[Optional[torch.Tensor], Optional[torch.Tensor]]:
        """
        Pokusí se vytáhnout conditioning latents ze synthesizeru (XTTS-v2).
        """
        try:
            if hasattr(tts_model, "synthesizer"):
                synthesizer = tts_model.synthesizer
                if hasattr(synthesizer, "get_conditioning_latents"):
                    gpt_cond_latent, speaker_embedding, _ = synthesizer.get_conditioning_latents(
                        audio_path=speaker_wav_path
                    )
                    return gpt_cond_latent, speaker_embedding
            return None, None
        except Exception as e:
            print(f"Error extracting conditioning latents: {e}")
            return None, None

    def clear_cache(self, speaker_wav_path: Optional[str] = None) -> int:
        """
        Vymaže cache pro konkrétní speaker nebo celou cache

        Args:
            speaker_wav_path: Cesta k speaker audio (None = vymaže vše)

        Returns:
            Počet smazaných souborů
        """
        if speaker_wav_path:
            cache_key = self._get_cache_key(speaker_wav_path)
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                cache_path.unlink()
                return 1
            return 0
        else:
            # Vymaž celou cache
            count = 0
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
                count += 1
            return count

    def get_cache_size(self) -> int:
        """
        Vrátí počet položek v cache

        Returns:
            Počet cache souborů
        """
        return len(list(self.cache_dir.glob("*.pkl")))


# Globální instance
_speaker_adapter = None


def get_speaker_adapter() -> SpeakerAdapter:
    """Vrátí globální instanci speaker adapteru"""
    global _speaker_adapter
    if _speaker_adapter is None:
        _speaker_adapter = SpeakerAdapter()
    return _speaker_adapter




















