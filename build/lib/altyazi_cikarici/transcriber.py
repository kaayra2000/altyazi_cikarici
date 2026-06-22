"""
Transcriber module using faster-whisper to extract subtitles from videos.
"""

import os
import time
from typing import Optional
from faster_whisper import WhisperModel

from altyazi_cikarici.constants import (
    BEAM_SIZE,
    DEFAULT_COMPUTE_TYPE,
    DEFAULT_DEVICE,
    DEFAULT_WHISPER_MODEL,
    VAD_FILTER,
)


def format_srt_time(seconds: float) -> str:
    """
    Formats a time in seconds to SRT time format: HH:MM:SS,mmm.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


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

    def transcribe(self, video_path: str, srt_path: str) -> bool:
        """
        Transcribes the video at video_path and writes the subtitles to srt_path.
        Returns True if successful, False otherwise.
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
                language="tr",
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
