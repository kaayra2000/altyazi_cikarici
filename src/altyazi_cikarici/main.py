"""
Main orchestration module for downloading and transcribing course videos.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

from altyazi_cikarici.cli import parse_arguments
from altyazi_cikarici.constants import (
    SUBTITLE_EXTENSION,
    VIDEO_EXTENSIONS,
)
from altyazi_cikarici.downloader import VideoDownloader
from altyazi_cikarici.transcriber import VideoTranscriber
from altyazi_cikarici.utils import (
    calculate_lesson_indices,
    clean_course_name,
    determine_year_folder,
    extract_date,
    extract_date_and_time,
    get_basename_without_extension,
)


def find_video_files(dir_path: str) -> List[str]:
    """
    Finds video files directly in the specified directory.
    """
    if not os.path.exists(dir_path):
        return []

    video_files = []
    for entry in os.scandir(dir_path):
        if entry.is_file() and entry.name.endswith(VIDEO_EXTENSIONS):
            video_files.append(entry.path)
    return video_files


def find_all_video_dirs(root_dir: str) -> List[str]:
    """
    Recursively finds all directories containing at least one video file.
    """
    video_dirs = []
    for dirpath, _, filenames in os.walk(root_dir):
        # Check if current directory has any video files
        has_video = any(name.endswith(VIDEO_EXTENSIONS) for name in filenames)
        if has_video:
            video_dirs.append(dirpath)
    return video_dirs


def get_transcription_mappings(
    video_paths: List[str], naming_style: str
) -> Dict[str, str]:
    """
    Generates target SRT file paths for a list of video paths in a single folder.
    Returns a dictionary mapping video_path -> srt_path.
    """
    if not video_paths:
        return {}

    filenames = [os.path.basename(p) for p in video_paths]
    year_folder = determine_year_folder(filenames)
    parent_dir = os.path.dirname(video_paths[0])
    target_dir = os.path.join(parent_dir, year_folder)

    mappings: Dict[str, str] = {}

    if naming_style == "original":
        # Keep original filename
        for path in video_paths:
            base_name = get_basename_without_extension(path)
            mappings[path] = os.path.join(
                target_dir, f"{base_name}{SUBTITLE_EXTENSION}"
            )
        return mappings

    # Group into with and without dates
    with_date: List[Dict] = []
    without_date: List[str] = []

    for path in video_paths:
        filename = os.path.basename(path)
        date_obj, duration = extract_date_and_time(filename)
        if date_obj:
            with_date.append({
                "path": path,
                "date": date_obj,
                "duration": duration,
                "filename": filename
            })
        else:
            without_date.append(path)

    # 1. Process files with dates
    if with_date:
        # Sort chronologically by date
        with_date.sort(key=lambda x: x["date"])

        # Calculate weeks
        weeks = [1]
        for i in range(1, len(with_date)):
            prev_v = with_date[i-1]
            curr_v = with_date[i]
            gap_days = (curr_v["date"].date() - prev_v["date"].date()).days

            # Same week if gap < 5 days and weekday is increasing or equal (e.g. same day)
            if gap_days < 5 and curr_v["date"].weekday() >= prev_v["date"].weekday():
                weeks.append(weeks[-1])
            else:
                step = max(1, round(gap_days / 7.0))
                weeks.append(weeks[-1] + step)

        for item, w in zip(with_date, weeks):
            item["week"] = w

        # Group by week index
        weeks_dict: Dict[int, List[Dict]] = {}
        for item in with_date:
            weeks_dict.setdefault(item["week"], []).append(item)

        # Determine regular weekday of the course
        weekday_counts: Dict[int, int] = {}
        for w_idx, items in weeks_dict.items():
            if len(items) == 1:
                wd = items[0]["date"].weekday()
                weekday_counts[wd] = weekday_counts.get(wd, 0) + 1

        if weekday_counts:
            regular_weekday = max(weekday_counts, key=weekday_counts.get)
        else:
            all_weekday_counts = {}
            for item in with_date:
                wd = item["date"].weekday()
                all_weekday_counts[wd] = all_weekday_counts.get(wd, 0) + 1
            if all_weekday_counts:
                regular_weekday = max(all_weekday_counts, key=all_weekday_counts.get)
            else:
                regular_weekday = with_date[0]["date"].weekday()

        # Classify each video within its week as "ders" or "lab"
        for w_idx, items in weeks_dict.items():
            # Group items in this week by unique day of the week (using date.date())
            days_in_week = {}
            for it in items:
                days_in_week.setdefault(it["date"].date(), []).append(it)

            if len(days_in_week) == 1:
                # All videos are on the same day -> all are "ders"
                for it in items:
                    it["type"] = "ders"
            else:
                # Multiple days in the week -> determine which day is "ders" and which is "lab"
                day_durations = {}
                for day, it_list in days_in_week.items():
                    durs = [it["duration"] for it in it_list]
                    if all(d is not None for d in durs):
                        day_durations[day] = sum(durs)
                    else:
                        day_durations[day] = None

                all_have_duration = all(d is not None for d in day_durations.values())
                unique_durations = set(d for d in day_durations.values() if d is not None)

                if all_have_duration and len(unique_durations) > 1:
                    # Durations are different -> day with max duration is "ders", others are "lab"
                    max_day = max(day_durations, key=day_durations.get)
                    for day, it_list in days_in_week.items():
                        for it in it_list:
                            it["type"] = "ders" if day == max_day else "lab"
                else:
                    # Try file sizes on disk as proxy
                    day_sizes = {}
                    for day, it_list in days_in_week.items():
                        sizes = []
                        for it in it_list:
                            if os.path.exists(it["path"]):
                                sizes.append(os.path.getsize(it["path"]))
                        if sizes:
                            day_sizes[day] = sum(sizes)
                        else:
                            day_sizes[day] = 0

                    unique_sizes = set(day_sizes.values())
                    if len(unique_sizes) > 1:
                        max_day = max(day_sizes, key=day_sizes.get)
                        for day, it_list in days_in_week.items():
                            for it in it_list:
                                it["type"] = "ders" if day == max_day else "lab"
                    else:
                        # Fallback to regular weekday
                        found_regular = False
                        # Sort days so regular weekday is checked first
                        sorted_days = sorted(days_in_week.keys(), key=lambda d: 0 if d.weekday() == regular_weekday else 1)
                        for day in sorted_days:
                            it_list = days_in_week[day]
                            if day.weekday() == regular_weekday and not found_regular:
                                for it in it_list:
                                    it["type"] = "ders"
                                found_regular = True
                            else:
                                for it in it_list:
                                    it["type"] = "lab"
                        if not found_regular:
                            earliest_day = min(days_in_week.keys())
                            for day, it_list in days_in_week.items():
                                for it in it_list:
                                    it["type"] = "ders" if day == earliest_day else "lab"

        # Generate target paths based on naming style
        name_counts = {}
        for item in with_date:
            w = item["week"]
            t = item["type"]
            path = item["path"]

            if naming_style == "lesson-lab":
                if t == "ders":
                    base_name = f"ders_{w}"
                else:
                    base_name = f"ders_{w}_lab"
            else:
                base_name = f"ders_{w}"

            if base_name not in name_counts:
                name_counts[base_name] = 0
                name = base_name
            else:
                name_counts[base_name] += 1
                name = f"{base_name}_{name_counts[base_name]}"

            mappings[path] = os.path.join(
                target_dir, f"{name}{SUBTITLE_EXTENSION}"
            )

    # 2. Process files without dates (keep original name)
    for path in without_date:
        base_name = get_basename_without_extension(path)
        mappings[path] = os.path.join(
            target_dir, f"{base_name}{SUBTITLE_EXTENSION}"
        )

    return mappings


def transcribe_videos(mappings: Dict[str, str], transcriber: VideoTranscriber) -> None:
    """
    Transcribes videos using mappings and a transcriber instance.
    """
    for video_path, srt_path in mappings.items():
        if os.path.exists(srt_path):
            print(f"Subtitle already exists, skipping: {srt_path}")
            continue

        success = transcriber.transcribe(video_path, srt_path)
        if not success:
            print(f"Transcription failed for: {video_path}")


def process_directory(dir_path: str, transcriber: VideoTranscriber) -> None:
    """
    Processes all videos in a single directory.
    Uses default 'lesson' naming style unless overridden by config.
    """
    print(f"Processing directory: {dir_path}")
    video_files = find_video_files(dir_path)
    if not video_files:
        print(f"No video files found in {dir_path}")
        return

    # Use naming_style='lesson' by default, or get from context/args
    mappings = get_transcription_mappings(video_files, naming_style="lesson")
    transcribe_videos(mappings, transcriber)


def process_recursive(root_dir: str, transcriber: VideoTranscriber) -> None:
    """
    Recursively scans and transcribes videos under root_dir.
    """
    print(f"Recursively scanning: {root_dir}")
    video_dirs = find_all_video_dirs(root_dir)
    if not video_dirs:
        print(f"No directories with video files found under {root_dir}")
        return

    # Sort to process in a clean order
    video_dirs.sort()
    for v_dir in video_dirs:
        # Note: If it's a recursively scanned directory, we follow the
        # user's layout structure which maps original names, but we default to
        # 'original' style for recursively traversed folders to preserve
        # context as shown in the diagram, or we can use 'lesson' if preferred.
        # Let's use 'original' for recursive mode to match the diagram,
        # unless the user overrides it. Let's make it configurable in run.
        # Actually, let's pass a tuple/object if we need more options, but for
        # now let's just generate the mappings using 'original' naming style
        # if the directory contains structures like week folders, or 'lesson' if not.
        # To be safe and highly customizable, we will check if the user wanted 'original'.
        # We can pass naming_style as an attribute of the transcriber or retrieve it.
        # Let's keep it simple: we can configure the default naming style.
        pass


def run_pipeline(source: str, output_dir: str) -> None:
    """
    Runs the pipeline with source and output directory.
    """
    # This is a helper that we will invoke from the CLI entrypoint.
    pass


def main() -> None:
    """
    CLI Entrypoint.
    """
    args = parse_arguments()

    # Determine if source is JSON or directory
    is_json = os.path.isfile(args.source) and args.source.endswith(".json")

    # Initialize transcriber if we are transcribing
    transcriber = None
    if not args.download_only:
        transcriber = VideoTranscriber(
            model_name=args.model,
            device=args.device,
        )

    if is_json:
        print(f"Loading courses from JSON: {args.source}")
        with open(args.source, "r", encoding="utf-8") as f:
            courses = json.load(f)

        downloader = VideoDownloader(output_dir=args.output_dir)

        for course_entry in courses:
            for course_name, urls in course_entry.items():
                cleaned_name = clean_course_name(course_name)
                print(f"\n--- Course: {cleaned_name} ---")
                if not args.transcribe_only:
                    downloader.download_course(cleaned_name, urls)

                if not args.download_only and transcriber:
                    course_dir = os.path.join(args.output_dir, cleaned_name)
                    video_files = find_video_files(course_dir)
                    if video_files:
                        mappings = get_transcription_mappings(
                            video_files, naming_style=args.naming_style
                        )
                        transcribe_videos(mappings, transcriber)
                    else:
                        print(f"No videos downloaded/found for {cleaned_name}")
    else:
        # Source is a directory
        if not os.path.exists(args.source):
            print(f"Source path does not exist: {args.source}")
            sys.exit(1)

        if args.download_only:
            print("Error: --download-only requires a JSON source file.")
            sys.exit(1)

        print(f"Processing local directory: {args.source}")
        video_dirs = find_all_video_dirs(args.source)
        if not video_dirs:
            print(f"No videos found in {args.source}")
            sys.exit(0)

        # For directory source, process folder by folder
        for v_dir in video_dirs:
            print(f"\nProcessing folder: {v_dir}")
            video_files = find_video_files(v_dir)
            if video_files and transcriber:
                # Use the configured naming style
                mappings = get_transcription_mappings(
                    video_files, naming_style=args.naming_style
                )
                transcribe_videos(mappings, transcriber)


if __name__ == "__main__":
    main()
