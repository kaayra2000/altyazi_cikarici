"""
Transcriber module using faster-whisper to extract subtitles from videos.
"""

import os
import time
import unicodedata
from typing import Iterable, List, Optional, Tuple
from faster_whisper import WhisperModel

from altyazi_cikarici.constants import (
    BEAM_SIZE,
    DEFAULT_COMPUTE_TYPE,
    DEFAULT_DEVICE,
    DEFAULT_WHISPER_MODEL,
    VAD_FILTER,
)


SUPPORTED_TRANSCRIPTION_LANGUAGES = {
    "tr": "Turkish",
    "en": "English",
}
MIN_LANGUAGE_PROBABILITY = 0.50
LANGUAGE_DETECTION_SEGMENTS = 3


def format_srt_time(seconds: float) -> str:
    """
    Formats a time in seconds to SRT time format: HH:MM:SS,mmm.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def _normalize_language(language: Optional[str]) -> Optional[str]:
    """
    Normalizes Whisper language codes for the supported prompt choices.
    """
    if not language:
        return None

    value = unicodedata.normalize("NFKD", language.strip().lower())
    value = value.encode("ascii", "ignore").decode("ascii")
    aliases = {
        "turkish": "tr",
        "turkce": "tr",
        "english": "en",
        "ingilizce": "en",
    }
    return aliases.get(value, value)


def _language_label(language: Optional[str]) -> str:
    """
    Returns a human-readable label for a language code.
    """
    if not language:
        return "unknown"
    return SUPPORTED_TRANSCRIPTION_LANGUAGES.get(language, language)


def _format_probability(probability: Optional[float]) -> str:
    """
    Formats a language probability when Whisper provides one.
    """
    return f" (olasilik: {probability:.2f})" if probability is not None else ""


def _prompt_for_language(
    detected_language: Optional[str],
    probability: Optional[float],
    context: str,
    allow_accept: bool = False,
) -> Optional[str]:
    """
    Asks the user which supported language to use when detection is inconclusive.
    """
    probability_text = _format_probability(probability)
    if allow_accept and detected_language in SUPPORTED_TRANSCRIPTION_LANGUAGES:
        print("Enter ile kabul edin, degistirmek icin 'tr'/'en' yazin.")
    elif detected_language:
        print(
            f"{context} dili Ingilizce veya Turkce olarak dogrulanamadi. "
            f"Tespit edilen dil: {detected_language}{probability_text}."
        )
    else:
        print(f"{context} dili tespit edilemedi.")

    while True:
        try:
            choices = "[enter/tr/en/skip]" if allow_accept else "[tr/en/skip]"
            print(
                f"Bu {context.lower()} icin altyazi dili secin {choices}:",
                flush=True,
            )
            answer = input().strip()
        except EOFError:
            print(f"Dil secimi alinamadi, {context.lower()} atlaniyor.")
            return None

        if allow_accept and not answer:
            return detected_language

        language = _normalize_language(answer)
        if language in SUPPORTED_TRANSCRIPTION_LANGUAGES:
            return language
        if language in {"", "skip", "s", "atla"}:
            print(f"{context} atlaniyor.")
            return None
        print("Lutfen 'tr', 'en' veya 'skip' girin.")


def _prompt_to_confirm_general_language(
    detected_language: Optional[str],
    probability: Optional[float],
    ask_uncertain_language: bool,
) -> Optional[str]:
    """
    Returns a confident overall language guess, otherwise asks the user.
    """
    if (
        detected_language in SUPPORTED_TRANSCRIPTION_LANGUAGES
        and probability is not None
        and probability >= MIN_LANGUAGE_PROBABILITY
    ):
        print(
            "Genel video dili tahmini: "
            f"{_language_label(detected_language)} "
            f"({detected_language}){_format_probability(probability)}. "
            "Otomatik kabul edildi."
        )
        return detected_language

    if ask_uncertain_language:
        return _prompt_for_language(detected_language, probability, context="Video")

    print(
        "Genel video dili Turkce/Ingilizce olarak guvenle tespit edilemedi; "
        "video atlaniyor."
    )
    return None


def _sort_segments(segments: Iterable[object]) -> List[object]:
    """
    Returns segments ordered by timestamp.
    """
    return sorted(segments, key=lambda segment: (segment.start, segment.end))


class VideoTranscriber:
    """
    Handles loading the Whisper model and transcribing video files to SRT subtitles.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_WHISPER_MODEL,
        device: str = DEFAULT_DEVICE,
        compute_type: str = DEFAULT_COMPUTE_TYPE,
        language: str = "auto",
        segment_language_detection: bool = False,
        ask_uncertain_language: bool = False,
        ask_uncertain_segments: bool = False,
    ):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = _normalize_language(language) or "auto"
        if self.language not in {"auto", *SUPPORTED_TRANSCRIPTION_LANGUAGES}:
            raise ValueError("language must be one of: auto, tr, en")
        self.segment_language_detection = segment_language_detection
        self.ask_uncertain_language = ask_uncertain_language
        self.ask_uncertain_segments = ask_uncertain_segments
        self._model: Optional[WhisperModel] = None

    def _load_model(self) -> WhisperModel:
        """
        Loads the Whisper model lazily when needed.
        """
        if self._model is None:
            print(f"Loading Whisper model '{self.model_name}' on {self.device}...")
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def _resolve_clip_language(
        self,
        info: object,
        context: str,
        fallback_language: str,
    ) -> Optional[str]:
        """
        Returns a confident segment language, or falls back to the overall language.
        """
        detected_language = _normalize_language(
            getattr(info, "language", None)
        )
        probability = getattr(info, "language_probability", None)

        if (
            detected_language in SUPPORTED_TRANSCRIPTION_LANGUAGES
            and probability is not None
            and probability >= MIN_LANGUAGE_PROBABILITY
        ):
            print(
                f"{context} language: "
                f"{_language_label(detected_language)} "
                f"({detected_language}, probability: {probability:.2f})"
            )
            return detected_language

        if self.ask_uncertain_segments:
            return _prompt_for_language(detected_language, probability, context=context)

        print(
            f"{context} dili guvenle tespit edilemedi; "
            f"genel dil kullaniliyor: {fallback_language}."
        )
        return fallback_language

    def _detect_general_language(
        self,
        model: WhisperModel,
        video_path: str,
    ) -> Optional[str]:
        """
        Resolves the overall video language from manual config or detection.
        """
        if self.language in SUPPORTED_TRANSCRIPTION_LANGUAGES:
            print(
                "Altyazi dili elle secildi: "
                f"{_language_label(self.language)} ({self.language})."
            )
            return self.language

        _, info = model.transcribe(
            video_path,
            vad_filter=VAD_FILTER,
            beam_size=BEAM_SIZE,
            language_detection_segments=LANGUAGE_DETECTION_SEGMENTS,
        )
        detected_language = _normalize_language(
            getattr(info, "language", None)
        )
        probability = getattr(info, "language_probability", None)
        return _prompt_to_confirm_general_language(
            detected_language,
            probability,
            self.ask_uncertain_language,
        )

    def _transcribe_clip(
        self,
        model: WhisperModel,
        video_path: str,
        start: float,
        end: float,
        fallback_language: str,
    ) -> Tuple[List[object], Optional[str]]:
        """
        Transcribes a time range after detecting a supported language for it.
        """
        clip_timestamps = f"{start:.3f},{end:.3f}"
        segments, info = model.transcribe(
            video_path,
            clip_timestamps=clip_timestamps,
            vad_filter=False,
            beam_size=BEAM_SIZE,
            language_detection_segments=1,
        )
        language = self._resolve_clip_language(
            info,
            context=f"Parca {start:.2f}-{end:.2f}",
            fallback_language=fallback_language,
        )
        if language is None:
            return [], None

        detected_language = _normalize_language(
            getattr(info, "language", None)
        )
        probability = getattr(info, "language_probability", None)
        should_rerun = (
            detected_language != language
            or probability is None
            or probability < MIN_LANGUAGE_PROBABILITY
        )
        if should_rerun:
            segments, _ = model.transcribe(
                video_path,
                language=language or fallback_language,
                clip_timestamps=clip_timestamps,
                vad_filter=False,
                beam_size=BEAM_SIZE,
            )

        return _sort_segments(list(segments)), language

    def transcribe(self, video_path: str, srt_path: str) -> Optional[bool]:
        """
        Transcribes the video at video_path and writes the subtitles to srt_path.
        Returns True if successful, False if failed, or None if skipped.
        """
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return False

        # Ensure output directory exists
        os.makedirs(os.path.dirname(srt_path), exist_ok=True)

        start_time = time.time()
        print(f"Starting transcription for: {os.path.basename(video_path)}")

        try:
            model = self._load_model()
            general_language = self._detect_general_language(model, video_path)
            if general_language is None:
                return None

            segment_list = []
            if not self.segment_language_detection:
                print(f"Video genel diliyle yaziliyor: {general_language}.")
                segments, _ = model.transcribe(
                    video_path,
                    language=general_language,
                    vad_filter=VAD_FILTER,
                    beam_size=BEAM_SIZE,
                )
                segment_list = _sort_segments(list(segments))
            else:
                print(
                    "Parca parca dil algilama basliyor "
                    "(yalnizca Turkce/Ingilizce kabul edilecek)."
                )
                base_segments, _ = model.transcribe(
                    video_path,
                    language=general_language,
                    multilingual=True,
                    vad_filter=VAD_FILTER,
                    beam_size=BEAM_SIZE,
                )
                for segment in _sort_segments(list(base_segments)):
                    if not segment.text.strip() or segment.end <= segment.start:
                        continue
                    clip_segments, clip_language = self._transcribe_clip(
                        model,
                        video_path,
                        max(0.0, segment.start),
                        segment.end,
                        fallback_language=general_language,
                    )
                    if clip_language:
                        print(
                            f"Parca yazildi: {segment.start:.2f}-{segment.end:.2f} "
                            f"{clip_language}"
                        )
                    segment_list.extend(clip_segments)
                segment_list = _sort_segments(segment_list)

            with open(srt_path, "w", encoding="utf-8") as f:
                for idx, seg in enumerate(segment_list, 1):
                    f.write(f"{idx}\n")
                    f.write(
                        f"{format_srt_time(seg.start)} --> {format_srt_time(seg.end)}\n"
                    )
                    f.write(f"{seg.text.strip()}\n\n")

            duration = time.time() - start_time
            video_len = segment_list[-1].end if segment_list else 0.0

            print(f"Successfully transcribed: {os.path.basename(video_path)}")
            print(f"Video Duration: {video_len / 60:.2f} mins")
            print(f"Processing Time: {duration / 60:.2f} mins")
            if duration > 0:
                print(f"Speed: {video_len / duration:.2f}x real-time")
            return True

        except Exception as e:
            print(f"Error transcribing {video_path}: {e}")
            if os.path.exists(srt_path):
                os.remove(srt_path)
            return False
        return True
