"""
CLI module for alt_yazi_cikarici.
"""

import argparse
from typing import List, Optional

from altyazi_cikarici.constants import (
    DEFAULT_DEVICE,
    DEFAULT_JSON_SOURCE,
    DEFAULT_OUTPUT_DIRECTORY,
    DEFAULT_WHISPER_MODEL,
)


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parses CLI arguments.
    """
    parser = argparse.ArgumentParser(
        description="Download course videos and transcribe them using faster-whisper."
    )

    parser.add_argument(
        "-s",
        "--source",
        default=DEFAULT_JSON_SOURCE,
        help=f"Source JSON file (e.g. {DEFAULT_JSON_SOURCE}) or a directory containing videos.",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        default=DEFAULT_OUTPUT_DIRECTORY,
        help=f"Directory to save downloaded videos (default: {DEFAULT_OUTPUT_DIRECTORY}).",
    )

    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_WHISPER_MODEL,
        help=f"Whisper model to use (default: {DEFAULT_WHISPER_MODEL}).",
    )

    parser.add_argument(
        "-d",
        "--device",
        default=DEFAULT_DEVICE,
        help=f"Compute device for Whisper (e.g. cpu, cuda) (default: {DEFAULT_DEVICE}).",
    )

    parser.add_argument(
        "--naming-style",
        choices=["lesson", "original", "lesson-lab"],
        default="lesson-lab",
        help="Subtitle naming convention: 'lesson-lab' (default, detects lab sessions), 'lesson' (e.g., ders_1.srt), or 'original' (keeps video name).",
    )
    parser.add_argument(
        "--language",
        choices=["auto", "tr", "en"],
        default="auto",
        help="Subtitle language: 'tr' or 'en' to skip language detection, 'auto' to detect the overall video language (default).",
    )
    parser.add_argument(
        "--segment-language-detection",
        action="store_true",
        help="Detect Turkish/English per segment. Slower than overall video language detection.",
    )
    parser.add_argument(
        "--ask-uncertain-language",
        action="store_true",
        help="Ask what to do when the overall video language is not confidently Turkish or English. By default, the video is skipped.",
    )
    parser.add_argument(
        "--ask-uncertain-segments",
        action="store_true",
        help="Ask what to do when a video segment language is not confidently Turkish or English. By default, uncertain segments use the overall video language.",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--download-only",
        action="store_true",
        help="Only download the videos from the JSON file, do not transcribe.",
    )
    group.add_argument(
        "--transcribe-only",
        action="store_true",
        help="Only run transcription, do not download videos.",
    )

    return parser.parse_args(args)
