"""
Transcriber module using faster-whisper to extract subtitles from videos.
"""

import os
import time
import unicodedata
from typing import Optional
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


def _prompt_for_language(
    detected_language: Optional[str],
    probability: Optional[float],
) -> Optional[str]:
    """
    Asks the user which supported language to use when detection is inconclusive.
    """
    probability_text = (
        f" (olasilik: {probability:.2f})" if probability is not None else ""
    )
    if detected_language:
        print(
            "Video dili Ingilizce veya Turkce olarak dogrulanamadi. "
            f"Tespit edilen dil: {detected_language}{probability_text}."
        )
    else:
        print("Video dili tespit edilemedi.")

    while True:
        try:
            print("Bu video icin altyazi dili secin [tr/en/skip]:", flush=True)
            answer = input().strip()
        except EOFError:
            print("Dil secimi alinamadi, video atlaniyor.")
            return None

        language = _normalize_language(answer)
        if language in SUPPORTED_TRANSCRIPTION_LANGUAGES:
            return language
        if language in {"", "skip", "s", "atla"}:
            print("Video atlaniyor.")
            return None
        print("Lutfen 'tr', 'en' veya 'skip' girin.")


class VideoTranscriber:
    """
    Handles loading the Whisper model and transcribing video files to SRT subtitles.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_WHISPER_MODEL,
        device: str = DEFAULT_DEVICE,
        compute_type: str = DEFAULT_COMPUTE_TYPE,
    ):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
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

    def _resolve_language(self, info: object) -> Optional[str]:
        """
        Returns 'tr'/'en' when Whisper confidently detects a supported language.
        Otherwise asks the user which supported language to use, or skips.
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
                "Detected language: "
                f"{SUPPORTED_TRANSCRIPTION_LANGUAGES[detected_language]} "
                f"({detected_language}, probability: {probability:.2f})"
            )
            return detected_language

        return _prompt_for_language(detected_language, probability)

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
            segments, info = model.transcribe(
                video_path,
                vad_filter=VAD_FILTER,
                beam_size=BEAM_SIZE,
            )
            language = self._resolve_language(info)
            if language is None:
                return None

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
                    language=language,
                    vad_filter=VAD_FILTER,
                    beam_size=BEAM_SIZE,
                )

            # Resolve segments generator to list
            segment_list = list(segments)

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
