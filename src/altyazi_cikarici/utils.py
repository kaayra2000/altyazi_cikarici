"""
Utility functions for parsing filenames, extracting dates/years,
and calculating lesson indices chronologically.
"""

import os
import re
from datetime import datetime
from typing import Optional, Tuple

from altyazi_cikarici.constants import (
    BACKUP_YEAR_PATTERN,
    DATE_NOT_FOUND_DIRECTORY,
    DATE_PATTERN,
    DAYS_IN_WEEK,
    YEAR_PATTERN,
)


def extract_date(filename: str) -> Optional[datetime]:
    """
    Extracts a date from the filename in d-m-yyyy or dd-mm-yyyy format.
    Returns a datetime object or None if no valid date is found.
    """
    match = re.search(DATE_PATTERN, filename)
    if not match:
        return None

    day_str, month_str, year_str = match.groups()
    try:
        return datetime(int(year_str), int(month_str), int(day_str))
    except ValueError:
        return None


def extract_date_and_time(filename: str) -> Tuple[Optional[datetime], Optional[float]]:
    """
    Extracts a datetime and duration (in minutes) from a filename.
    Filename is expected to contain: start_date_start_time_end_date_end_time
    e.g., BLM2512 - 1_7-10-2020_13-00_7-10-2020_14-50_...
    Returns (start_datetime, duration_mins).
    If start/end times are not present or cannot be parsed, falls back to
    extract_date and returns (date_obj, None).
    """
    date_obj = extract_date(filename)
    if not date_obj:
        return None, None

    pattern = r"(\d{1,2}-\d{1,2}-\d{4})_(\d{2}-\d{2})_(\d{1,2}-\d{1,2}-\d{4})_(\d{2}-\d{2})"
    match = re.search(pattern, filename)
    duration_mins = None
    if match:
        start_date_str, start_time_str, end_date_str, end_time_str = match.groups()
        try:
            start_dt = datetime.strptime(f"{start_date_str}_{start_time_str}", "%d-%m-%Y_%H-%M")
            end_dt = datetime.strptime(f"{end_date_str}_{end_time_str}", "%d-%m-%Y_%H-%M")
            duration_mins = (end_dt - start_dt).total_seconds() / 60
            date_obj = start_dt
        except ValueError:
            pass
    return date_obj, duration_mins



def extract_year(filename: str) -> Optional[str]:
    """
    Extracts a 4-digit year from the filename.
    First tries to find a full date, then falls back to a 4-digit year pattern.
    """
    date_obj = extract_date(filename)
    if date_obj:
        return str(date_obj.year)

    # Fallback to word-bounded 4-digit year starting with 20
    year_match = re.search(YEAR_PATTERN, filename)
    if year_match:
        return year_match.group(1)

    # Fallback to any 20xx in the filename
    backup_match = re.search(BACKUP_YEAR_PATTERN, filename)
    if backup_match:
        return backup_match.group(1)

    return None


def determine_year_folder(filenames: list[str]) -> str:
    """
    Determines the year folder name based on the earliest video date in the list.
    If no dates are found, falls back to the earliest year.
    If no years are found, returns DATE_NOT_FOUND_DIRECTORY.
    """
    valid_dates: list[datetime] = []
    valid_years: list[str] = []

    for name in filenames:
        date_obj = extract_date(name)
        if date_obj:
            valid_dates.append(date_obj)
        else:
            year_str = extract_year(name)
            if year_str:
                valid_years.append(year_str)

    if valid_dates:
        earliest_date = min(valid_dates)
        return str(earliest_date.year)

    if valid_years:
        return min(valid_years)

    return DATE_NOT_FOUND_DIRECTORY


def calculate_lesson_indices(dates: list[datetime]) -> list[int]:
    """
    Calculates 1-based chronological lesson indices with gap detection.
    If gap between consecutive dates is > 1 week, skips indices proportionally.
    """
    if not dates:
        return []

    indices = [1]
    for i in range(1, len(dates)):
        gap_days = (dates[i] - dates[i - 1]).days
        step = max(1, round(gap_days / DAYS_IN_WEEK))
        indices.append(indices[-1] + step)

    return indices


def get_basename_without_extension(filename: str) -> str:
    """
    Returns the base filename without extension.
    """
    base = os.path.basename(filename)
    return os.path.splitext(base)[0]


def clean_course_name(name: str) -> str:
    """
    Cleans the course name by removing parenthetical explanations.
    E.g. "Veri Yapıları ve Algo (tek sayılı dersler uygulama ve lab)" -> "Veri Yapıları ve Algo"
    """
    cleaned = re.sub(r"\(.*?\)", "", name)
    return cleaned.strip()

