"""
Parser pro TTS parametry z Form dat
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException
from backend.config import (
    TTS_SPEED,
    TTS_TEMPERATURE,
    TTS_LENGTH_PENALTY,
    TTS_REPETITION_PENALTY,
    TTS_TOP_K,
    TTS_TOP_P,
    ENABLE_AUDIO_ENHANCEMENT,
)


def parse_bool_param(value: Optional[str], default: Optional[bool] = None) -> Optional[bool]:
    """Převede string "true"/"false" na boolean"""
    if value is None:
        return default
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def parse_float_param(value: Optional[Any], default: float, min_val: Optional[float] = None, max_val: Optional[float] = None, param_name: str = "") -> float:
    """Převede parametr na float s validací"""
    try:
        result = float(value) if value is not None else default
        if min_val is not None and result < min_val:
            raise HTTPException(status_code=400, detail=f"{param_name} musí být >= {min_val}")
        if max_val is not None and result > max_val:
            raise HTTPException(status_code=400, detail=f"{param_name} musí být <= {max_val}")
        return result
    except (ValueError, TypeError):
        return default


def parse_int_param(value: Optional[Any], default: int, min_val: Optional[int] = None, param_name: str = "") -> int:
    """Převede parametr na int s validací"""
    try:
        result = int(value) if value is not None else default
        if min_val is not None and result < min_val:
            raise HTTPException(status_code=400, detail=f"{param_name} musí být >= {min_val}")
        return result
    except (ValueError, TypeError):
        return default


def parse_optional_float_param(
    value: Optional[str],
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    param_name: str = ""
) -> Optional[float]:
    """Převede volitelný parametr na float s validací"""
    if value is None:
        return None
    try:
        result = float(value)
        if min_val is not None and result < min_val:
            raise HTTPException(status_code=400, detail=f"{param_name} musí být >= {min_val}")
        if max_val is not None and result > max_val:
            raise HTTPException(status_code=400, detail=f"{param_name} musí být <= {max_val}")
        return result
    except (ValueError, TypeError):
        return None


class TTSParamsParser:
    """Parser pro TTS parametry"""

    @staticmethod
    def parse_basic_params(
        speed: Optional[str] = None,
        temperature: Optional[float] = None,
        length_penalty: Optional[float] = None,
        repetition_penalty: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Parsuje základní TTS parametry"""
        tts_speed = parse_float_param(speed, TTS_SPEED, 0.5, 2.0, "Speed")
        tts_temperature = parse_float_param(temperature, TTS_TEMPERATURE, 0.0, 1.0, "Temperature")
        tts_length_penalty = parse_float_param(length_penalty, TTS_LENGTH_PENALTY, param_name="Length penalty")
        tts_repetition_penalty = parse_float_param(repetition_penalty, TTS_REPETITION_PENALTY, param_name="Repetition penalty")
        tts_top_k = parse_int_param(top_k, TTS_TOP_K, 1, "top_k")
        tts_top_p = parse_float_param(top_p, TTS_TOP_P, 0.0, 1.0, "top_p")

        return {
            "speed": tts_speed,
            "temperature": tts_temperature,
            "length_penalty": tts_length_penalty,
            "repetition_penalty": tts_repetition_penalty,
            "top_k": tts_top_k,
            "top_p": tts_top_p,
            "seed": seed,
        }

    @staticmethod
    def parse_enhancement_params(
        enable_enhancement: Optional[str] = None,
        enable_vad: Optional[str] = None,
        enable_batch: Optional[str] = None,
        enable_normalization: Optional[str] = None,
        enable_denoiser: Optional[str] = None,
        enable_compressor: Optional[str] = None,
        enable_deesser: Optional[str] = None,
        enable_eq: Optional[str] = None,
        enable_trim: Optional[str] = None,
        use_hifigan: Optional[str] = None,
    ) -> Dict[str, Optional[bool]]:
        """Parsuje enhancement parametry"""
        return {
            "enable_enhancement": parse_bool_param(enable_enhancement, ENABLE_AUDIO_ENHANCEMENT),
            "enable_vad": parse_bool_param(enable_vad),
            "enable_batch": parse_bool_param(enable_batch),
            "enable_normalization": parse_bool_param(enable_normalization),
            "enable_denoiser": parse_bool_param(enable_denoiser),
            "enable_compressor": parse_bool_param(enable_compressor),
            "enable_deesser": parse_bool_param(enable_deesser),
            "enable_eq": parse_bool_param(enable_eq),
            "enable_trim": parse_bool_param(enable_trim),
            "use_hifigan": parse_bool_param(use_hifigan, False),
        }

    @staticmethod
    def parse_hifigan_params(
        hifigan_refinement_intensity: Optional[str] = None,
        hifigan_normalize_output: Optional[str] = None,
        hifigan_normalize_gain: Optional[str] = None,
    ) -> Dict[str, Optional[Any]]:
        """Parsuje HiFi-GAN parametry"""
        return {
            "hifigan_refinement_intensity": parse_optional_float_param(
                hifigan_refinement_intensity, 0.0, 1.0, "hifigan_refinement_intensity"
            ),
            "hifigan_normalize_output": parse_bool_param(hifigan_normalize_output),
            "hifigan_normalize_gain": parse_optional_float_param(
                hifigan_normalize_gain, 0.0, 1.0, "hifigan_normalize_gain"
            ),
        }

    @staticmethod
    def parse_dialect_params(
        enable_dialect_conversion: Optional[str] = None,
        dialect_code: Optional[str] = None,
        dialect_intensity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Parsuje dialect parametry"""
        use_dialect = parse_bool_param(enable_dialect_conversion, False)
        dialect_code_value = dialect_code if dialect_code and dialect_code != "standardni" else None
        try:
            dialect_intensity_value = float(dialect_intensity) if dialect_intensity else 1.0
        except (ValueError, TypeError):
            dialect_intensity_value = 1.0

        return {
            "enable_dialect_conversion": use_dialect,
            "dialect_code": dialect_code_value,
            "dialect_intensity": dialect_intensity_value,
        }

    @staticmethod
    def parse_whisper_params(
        enable_whisper: Optional[str] = None,
        whisper_intensity: Optional[str] = None,
    ) -> Dict[str, Optional[Any]]:
        """Parsuje whisper parametry"""
        return {
            "enable_whisper": parse_bool_param(enable_whisper),
            "whisper_intensity": parse_optional_float_param(whisper_intensity, 0.0, 1.0, "whisper_intensity"),
        }

    @staticmethod
    def parse_headroom_param(target_headroom_db: Optional[str] = None) -> Optional[float]:
        """Parsuje headroom parametr"""
        return parse_optional_float_param(target_headroom_db, -128.0, 0.0, "target_headroom_db")

    @staticmethod
    def parse_multi_pass_params(
        multi_pass: Optional[str] = None,
        multi_pass_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Parsuje multi-pass parametry"""
        use_multi_pass = parse_bool_param(multi_pass, False)
        multi_pass_count_value = parse_int_param(multi_pass_count, 3, 1, "multi_pass_count")
        return {
            "multi_pass": use_multi_pass,
            "multi_pass_count": multi_pass_count_value,
        }

    @staticmethod
    def parse_all_params(**kwargs) -> Dict[str, Any]:
        """Parsuje všechny TTS parametry"""
        basic = TTSParamsParser.parse_basic_params(
            speed=kwargs.get("speed"),
            temperature=kwargs.get("temperature"),
            length_penalty=kwargs.get("length_penalty"),
            repetition_penalty=kwargs.get("repetition_penalty"),
            top_k=kwargs.get("top_k"),
            top_p=kwargs.get("top_p"),
            seed=kwargs.get("seed"),
        )
        enhancement = TTSParamsParser.parse_enhancement_params(
            enable_enhancement=kwargs.get("enable_enhancement"),
            enable_vad=kwargs.get("enable_vad"),
            enable_batch=kwargs.get("enable_batch"),
            enable_normalization=kwargs.get("enable_normalization"),
            enable_denoiser=kwargs.get("enable_denoiser"),
            enable_compressor=kwargs.get("enable_compressor"),
            enable_deesser=kwargs.get("enable_deesser"),
            enable_eq=kwargs.get("enable_eq"),
            enable_trim=kwargs.get("enable_trim"),
            use_hifigan=kwargs.get("use_hifigan"),
        )
        hifigan = TTSParamsParser.parse_hifigan_params(
            hifigan_refinement_intensity=kwargs.get("hifigan_refinement_intensity"),
            hifigan_normalize_output=kwargs.get("hifigan_normalize_output"),
            hifigan_normalize_gain=kwargs.get("hifigan_normalize_gain"),
        )
        dialect = TTSParamsParser.parse_dialect_params(
            enable_dialect_conversion=kwargs.get("enable_dialect_conversion"),
            dialect_code=kwargs.get("dialect_code"),
            dialect_intensity=kwargs.get("dialect_intensity"),
        )
        whisper = TTSParamsParser.parse_whisper_params(
            enable_whisper=kwargs.get("enable_whisper"),
            whisper_intensity=kwargs.get("whisper_intensity"),
        )
        multi_pass = TTSParamsParser.parse_multi_pass_params(
            multi_pass=kwargs.get("multi_pass"),
            multi_pass_count=kwargs.get("multi_pass_count"),
        )

        return {
            **basic,
            **enhancement,
            **hifigan,
            **dialect,
            **whisper,
            **multi_pass,
            "target_headroom_db": TTSParamsParser.parse_headroom_param(kwargs.get("target_headroom_db")),
            "quality_mode": kwargs.get("quality_mode"),
            "enhancement_preset": kwargs.get("enhancement_preset"),
        }

