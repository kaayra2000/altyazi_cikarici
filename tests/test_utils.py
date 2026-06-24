"""
Unit tests for altyazi_cikarici.utils.
"""

from datetime import datetime
from altyazi_cikarici.utils import (
    extract_date,
    extract_date_and_time,
    extract_year,
    determine_year_folder,
    calculate_lesson_indices,
    clean_course_name,
)
from altyazi_cikarici.cli import parse_arguments


def test_extract_date_and_time():
    """
    Test extracting start datetime and duration from filenames.
    """
    filename = "BLM2512 - 1_7-10-2020_13-00_7-10-2020_14-50_a7f6.mp4"
    dt, dur = extract_date_and_time(filename)
    assert dt == datetime(2020, 10, 7, 13, 0)
    assert dur == 110.0

    filename_no_time = "BLM2021_1-2-2020.mp4"
    dt, dur = extract_date_and_time(filename_no_time)
    assert dt == datetime(2020, 2, 1)
    assert dur is None


def test_extract_date_valid():
    """
    Test extracting valid dates from filenames.
    """
    filename = "BLM2021 - 2_7-01-2021_09-00_7-01-2021_11-50_609fa2f1-74c8-4cd2-877c-5d3fcf252276.mp4"
    date_obj = extract_date(filename)
    assert date_obj == datetime(2021, 1, 7)



def test_extract_date_single_digit():
    """
    Test extracting dates with single digit day/month.
    """
    filename = "BLM2021_1-2-2020_12-00.mp4"
    date_obj = extract_date(filename)
    assert date_obj == datetime(2020, 2, 1)


def test_extract_date_invalid():
    """
    Test that invalid dates return None.
    """
    filename = "BLM2021_no_date_here.mp4"
    assert extract_date(filename) is None

    # Invalid day/month combinations
    filename_invalid = "BLM2021_32-13-2020.mp4"
    assert extract_date(filename_invalid) is None


def test_extract_year_from_date():
    """
    Test extracting year when full date is present.
    """
    filename = "BLM2021 - 2_7-01-2021_09-00.mp4"
    assert extract_year(filename) == "2021"


def test_extract_year_fallback():
    """
    Test extracting year when only year is present.
    """
    filename = "BLM2020 - Lecture 1.mp4"
    assert extract_year(filename) == "2020"

    filename_backup = "BLM_lecture_2022_extra.mp4"
    assert extract_year(filename_backup) == "2022"


def test_determine_year_folder_from_dates():
    """
    Test determining year folder from a list of files with dates.
    """
    filenames = [
        "BLM2021_7-01-2021_09-00.mp4",
        "BLM2021_14-01-2021_09-00.mp4",
        "BLM2021_18-12-2020_09-00.mp4",
    ]
    # Earliest date is 18-12-2020, so year should be 2020
    assert determine_year_folder(filenames) == "2020"


def test_determine_year_folder_fallback_to_years():
    """
    Test determining year folder when only year is present.
    """
    filenames = [
        "BLM2022_lecture.mp4",
        "BLM2021_lecture.mp4",
    ]
    assert determine_year_folder(filenames) == "2021"


def test_determine_year_folder_not_found():
    """
    Test fallback to TARIH_BULUNAMADI.
    """
    filenames = [
        "BLM_lecture_no_date.mp4",
        "some_other_video.mp4",
    ]
    assert determine_year_folder(filenames) == "TARIH_BULUNAMADI"


def test_calculate_lesson_indices_weekly():
    """
    Test calculating lesson indices with standard 1-week gaps.
    """
    dates = [
        datetime(2021, 1, 7),   # ders 1
        datetime(2021, 1, 14),  # ders 2
        datetime(2021, 1, 21),  # ders 3
    ]
    assert calculate_lesson_indices(dates) == [1, 2, 3]


def test_calculate_lesson_indices_with_skips():
    """
    Test calculating lesson indices when weeks are skipped.
    """
    dates = [
        datetime(2021, 1, 7),   # ders 1
        datetime(2021, 1, 14),  # ders 2 (1 week gap -> +1)
        datetime(2021, 1, 28),  # ders 4 (2 week gap -> +2)
        datetime(2021, 2, 11),  # ders 6 (2 week gap -> +2)
    ]
    assert calculate_lesson_indices(dates) == [1, 2, 4, 6]


def test_calculate_lesson_indices_same_day():
    """
    Test calculating lesson indices when multiple videos are on the same day.
    """
    dates = [
        datetime(2021, 1, 7),   # ders 1
        datetime(2021, 1, 7),   # ders 2 (0 day gap -> +1)
        datetime(2021, 1, 14),  # ders 3 (1 week gap -> +1)
    ]
    assert calculate_lesson_indices(dates) == [1, 2, 3]


def test_get_transcription_mappings_naming_styles():
    """
    Test that get_transcription_mappings correctly maps naming styles
    including original, lesson, and lesson-lab.
    """
    from altyazi_cikarici.main import get_transcription_mappings
    
    video_paths = [
        "videolar/Alt Seviye/BLM2021_7-01-2021.mp4",
        "videolar/Alt Seviye/BLM2021_11-01-2021.mp4",
        "videolar/Alt Seviye/BLM2021_14-01-2021.mp4",
        "videolar/Alt Seviye/BLM2021_21-01-2021.mp4",
        "videolar/Alt Seviye/BLM2021_25-01-2021.mp4",
        "videolar/Alt Seviye/BLM2021_28-01-2021.mp4",
    ]
    
    # 1. Test original
    mappings_orig = get_transcription_mappings(video_paths, naming_style="original")
    assert mappings_orig["videolar/Alt Seviye/BLM2021_7-01-2021.mp4"] == "videolar/Alt Seviye/2021/BLM2021_7-01-2021.srt"
    
    # 2. Test lesson
    mappings_lesson = get_transcription_mappings(video_paths, naming_style="lesson")
    assert mappings_lesson["videolar/Alt Seviye/BLM2021_7-01-2021.mp4"] == "videolar/Alt Seviye/2021/ders_1.srt"
    assert mappings_lesson["videolar/Alt Seviye/BLM2021_11-01-2021.mp4"] == "videolar/Alt Seviye/2021/ders_2.srt"
    assert mappings_lesson["videolar/Alt Seviye/BLM2021_14-01-2021.mp4"] == "videolar/Alt Seviye/2021/ders_2_1.srt"

    # 3. Test lesson-lab
    mappings_lab = get_transcription_mappings(video_paths, naming_style="lesson-lab")
    assert mappings_lab["videolar/Alt Seviye/BLM2021_7-01-2021.mp4"] == "videolar/Alt Seviye/2021/ders_1.srt"
    assert mappings_lab["videolar/Alt Seviye/BLM2021_11-01-2021.mp4"] == "videolar/Alt Seviye/2021/ders_2_lab.srt"
    assert mappings_lab["videolar/Alt Seviye/BLM2021_14-01-2021.mp4"] == "videolar/Alt Seviye/2021/ders_2.srt"
    assert mappings_lab["videolar/Alt Seviye/BLM2021_21-01-2021.mp4"] == "videolar/Alt Seviye/2021/ders_3.srt"
    assert mappings_lab["videolar/Alt Seviye/BLM2021_25-01-2021.mp4"] == "videolar/Alt Seviye/2021/ders_4_lab.srt"
    assert mappings_lab["videolar/Alt Seviye/BLM2021_28-01-2021.mp4"] == "videolar/Alt Seviye/2021/ders_4.srt"


def test_get_transcription_mappings_detects_same_day_lab():
    """
    Test that a shorter same-day session is marked as lab.
    """
    from altyazi_cikarici.main import get_transcription_mappings

    video_paths = [
        "videolar/Alt Seviye/BLM2021_7-01-2021_09-00_7-01-2021_11-50.mp4",
        "videolar/Alt Seviye/BLM2021_7-01-2021_13-00_7-01-2021_13-50.mp4",
    ]

    mappings = get_transcription_mappings(video_paths, naming_style="lesson-lab")

    assert mappings[video_paths[0]] == "videolar/Alt Seviye/2021/ders_1.srt"
    assert mappings[video_paths[1]] == "videolar/Alt Seviye/2021/ders_1_lab.srt"


def test_parse_arguments_defaults_to_lesson_lab():
    """
    Test that CLI defaults to lab-aware naming.
    """
    args = parse_arguments([])
    assert args.naming_style == "lesson-lab"



def test_clean_course_name():
    """
    Test cleaning of course names.
    """
    assert clean_course_name("Veri Yapıları ve Algo (tek sayılı dersler uygulama ve lab)") == "Veri Yapıları ve Algo"
    assert clean_course_name("İşletim Sistemleri (çift sayılı dersler uygulama ve lab)") == "İşletim Sistemleri"
    assert clean_course_name("Veritabanı Yönetimi(tek sayılı dersler lab)") == "Veritabanı Yönetimi"
    assert clean_course_name("Normal Ders") == "Normal Ders"

