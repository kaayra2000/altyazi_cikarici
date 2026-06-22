"""
Constants for the alt_yazi_cikarici package.
Centralized configuration values, regex patterns, and default paths.
"""

# ==============================================================================
# Domain & Technical Constants
# ==============================================================================
DEFAULT_WHISPER_MODEL: str = "medium"
DEFAULT_DEVICE: str = "cpu"
DEFAULT_COMPUTE_TYPE: str = "int8"
BEAM_SIZE: int = 5
VAD_FILTER: bool = True
DAYS_IN_WEEK: float = 7.0

# ==============================================================================
# File & Folder Constants
# ==============================================================================
DEFAULT_OUTPUT_DIRECTORY: str = "videolar"
DEFAULT_JSON_SOURCE: str = "dersler.json"
DATE_NOT_FOUND_DIRECTORY: str = "TARIH_BULUNAMADI"
SUBTITLE_EXTENSION: str = ".srt"
VIDEO_EXTENSIONS: tuple[str, ...] = (".mp4", ".avi", ".mkv", ".mov", ".MP4")

# ==============================================================================
# Regex Patterns
# ==============================================================================
# Matches dd-mm-yyyy or d-m-yyyy format in filenames
DATE_PATTERN: str = r"(\d{1,2})-(\d{1,2})-(\d{4})"
# Matches 4-digit years starting with 20 (e.g. 2020, 2021)
YEAR_PATTERN: str = r"\b(20\d{2})\b"
# Backup pattern to match any 20xx year in the filename
BACKUP_YEAR_PATTERN: str = r"(20\d{2})"
