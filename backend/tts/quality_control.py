"""
Quality Control - kontrola kvality a nastavení presety
"""
from typing import Optional
from backend.config import (
    QUALITY_PRESETS,
    TTS_SPEED,
    TTS_TEMPERATURE,
    TTS_LENGTH_PENALTY,
    TTS_REPETITION_PENALTY,
    TTS_TOP_K,
    TTS_TOP_P,
    OUTPUT_HEADROOM_DB,
)


class QualityControl:
    """Třída pro správu quality presetů a efektivních nastavení"""

    def apply_quality_preset(self, preset: str) -> dict:
        """
        Aplikuje quality preset na TTS parametry

        Args:
            preset: Název presetu (high_quality, natural, fast, meditative, whisper)

        Returns:
            Slovník s TTS parametry
        """
        preset_config = QUALITY_PRESETS.get(preset, QUALITY_PRESETS["natural"])

        # Vrátit pouze TTS parametry (bez enhancement)
        tts_params = {
            "speed": preset_config.get("speed", 1.0),
            "temperature": preset_config.get("temperature", 0.7),
            "length_penalty": preset_config.get("length_penalty", 1.0),
            "repetition_penalty": preset_config.get("repetition_penalty", 2.0),
            "top_k": preset_config.get("top_k", 50),
            "top_p": preset_config.get("top_p", 0.85)
        }

        return tts_params

    def compute_effective_settings(
        self,
        quality_mode: Optional[str] = None,
        enhancement_preset: Optional[str] = None,
        speed: Optional[float] = None,
        temperature: Optional[float] = None,
        length_penalty: Optional[float] = None,
        repetition_penalty: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        enable_eq: Optional[bool] = None,
        enable_denoiser: Optional[bool] = None,
        enable_compressor: Optional[bool] = None,
        enable_deesser: Optional[bool] = None,
        enable_normalization: Optional[bool] = None,
        enable_trim: Optional[bool] = None,
        enable_whisper: Optional[bool] = None,
        whisper_intensity: Optional[float] = None,
        target_headroom_db: Optional[float] = None,
    ) -> dict:
        """
        Vypočítá efektivní nastavení kombinací quality_mode presetu, enhancement_preset a explicitních parametrů.

        Pravidla priority:
        1. Explicitní parametry (pokud zadány) mají přednost před presety
        2. quality_mode určuje TTS parametry a enhancement (pokud je quality preset)
        3. enhancement_preset určuje enhancement (pokud není quality_mode nebo quality_mode není quality preset)
        4. Výchozí hodnoty z configu pro neexplicitní parametry

        Pro speed: Pokud je quality_mode in {meditative, whisper} a speed není explicitně zadán,
        použije se speed z presetu. Jinak se zachová explicitní speed nebo výchozí.

        Returns:
            Dictionary s efektivními nastaveními:
            - tts: {speed, temperature, length_penalty, repetition_penalty, top_k, top_p}
            - enhancement: {enable_eq, enable_denoiser, enable_compressor, enable_deesser, enable_trim, enable_normalization}
            - whisper: {enable_whisper, whisper_intensity}
            - headroom: {target_headroom_db}
        """
        # Výchozí hodnoty z configu
        defaults = {
            "speed": TTS_SPEED,
            "temperature": TTS_TEMPERATURE,
            "length_penalty": TTS_LENGTH_PENALTY,
            "repetition_penalty": TTS_REPETITION_PENALTY,
            "top_k": TTS_TOP_K,
            "top_p": TTS_TOP_P,
            "enable_eq": True,
            "enable_denoiser": True,
            "enable_compressor": True,
            "enable_deesser": True,
            "enable_trim": True,
            "enable_normalization": True,
            "enable_whisper": False,
            "whisper_intensity": 1.0,
            "target_headroom_db": OUTPUT_HEADROOM_DB,
        }

        # Načti TTS parametry z quality_mode presetu (pokud existuje)
        preset_tts = {}
        preset_enhancement = {}
        if quality_mode and quality_mode in QUALITY_PRESETS:
            preset_config = QUALITY_PRESETS[quality_mode]
            preset_tts = self.apply_quality_preset(quality_mode)
            preset_enhancement = preset_config.get("enhancement", {})

        # Načti enhancement z enhancement_preset (pokud je to quality preset a quality_mode není nastaven)
        elif enhancement_preset and enhancement_preset in QUALITY_PRESETS:
            preset_config = QUALITY_PRESETS[enhancement_preset]
            preset_enhancement = preset_config.get("enhancement", {})

        # Sestav efektivní TTS parametry (explicitní > preset > výchozí)
        effective_tts = {
            "speed": speed if speed is not None else (preset_tts.get("speed") if preset_tts else defaults["speed"]),
            "temperature": temperature if temperature is not None else (preset_tts.get("temperature") if preset_tts else defaults["temperature"]),
            "length_penalty": length_penalty if length_penalty is not None else (preset_tts.get("length_penalty") if preset_tts else defaults["length_penalty"]),
            "repetition_penalty": repetition_penalty if repetition_penalty is not None else (preset_tts.get("repetition_penalty") if preset_tts else defaults["repetition_penalty"]),
            "top_k": top_k if top_k is not None else (preset_tts.get("top_k") if preset_tts else defaults["top_k"]),
            "top_p": top_p if top_p is not None else (preset_tts.get("top_p") if preset_tts else defaults["top_p"]),
        }

        # Speciální pravidlo pro speed: pokud je quality_mode meditative/whisper a speed není explicitně zadán,
        # použij speed z presetu (pro meditative/whisper je to důležité pro správný efekt)
        if quality_mode in ("meditative", "whisper") and speed is None:
            effective_tts["speed"] = preset_tts.get("speed", defaults["speed"])

        # Sestav efektivní enhancement parametry (explicitní > preset > výchozí)
        # Mapování názvů: enable_noise_reduction -> enable_denoiser, enable_compression -> enable_compressor
        effective_enhancement = {
            "enable_eq": enable_eq if enable_eq is not None else (preset_enhancement.get("enable_eq", defaults["enable_eq"])),
            "enable_denoiser": enable_denoiser if enable_denoiser is not None else (preset_enhancement.get("enable_noise_reduction", defaults["enable_denoiser"])),
            "enable_compressor": enable_compressor if enable_compressor is not None else (preset_enhancement.get("enable_compression", defaults["enable_compressor"])),
            "enable_deesser": enable_deesser if enable_deesser is not None else (preset_enhancement.get("enable_deesser", defaults["enable_deesser"])),
            "enable_trim": enable_trim if enable_trim is not None else defaults["enable_trim"],
            "enable_normalization": enable_normalization if enable_normalization is not None else (preset_enhancement.get("enable_normalization", defaults["enable_normalization"])),
        }

        # Whisper efekt (z presetu nebo explicitní)
        effective_whisper = {
            "enable_whisper": enable_whisper if enable_whisper is not None else (preset_enhancement.get("enable_whisper", defaults["enable_whisper"])),
            "whisper_intensity": whisper_intensity if whisper_intensity is not None else (preset_enhancement.get("whisper_intensity", defaults["whisper_intensity"])),
        }

        # Headroom (preset může mít target_headroom_db, jinak globální)
        effective_headroom = {
            "target_headroom_db": target_headroom_db if target_headroom_db is not None else (preset_enhancement.get("target_headroom_db", defaults["target_headroom_db"])),
        }

        return {
            "tts": effective_tts,
            "enhancement": effective_enhancement,
            "whisper": effective_whisper,
            "headroom": effective_headroom,
        }


