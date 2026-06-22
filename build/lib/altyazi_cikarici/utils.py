"""
Utility functions for parsing filenames, extracting dates/years,
and calculating lesson indices chronologically.
"""

import os
import re
from datetime import datetime
from typing import Optional

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
