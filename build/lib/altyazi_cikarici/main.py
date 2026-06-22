"""
Main orchestration module for downloading and transcribing course videos.
"""

import json
import os
import sys
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
    determine_year_folder,
    extract_date,
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
    with_date: List[Tuple[str, datetime]] = []
    without_date: List[str] = []

    for path in video_paths:
        filename = os.path.basename(path)
        date_obj = extract_date(filename)
        if date_obj:
            with_date.append((path, date_obj))
        else:
            without_date.append(path)

    # 1. Process files with dates (rename to ders_X.srt based on gaps)
    if with_date:
        # Sort chronologically by date
        with_date.sort(key=lambda x: x[1])
        sorted_paths = [x[0] for x in with_date]
        sorted_dates = [x[1] for x in with_date]
        indices = calculate_lesson_indices(sorted_dates)

        for path, idx in zip(sorted_paths, indices):
            mappings[path] = os.path.join(
                target_dir, f"ders_{idx}{SUBTITLE_EXTENSION}"
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
                print(f"\n--- Course: {course_name} ---")
                if not args.transcribe_only:
                    downloader.download_course(course_name, urls)

                if not args.download_only and transcriber:
                    course_dir = os.path.join(args.output_dir, course_name)
                    video_files = find_video_files(course_dir)
                    if video_files:
                        mappings = get_transcription_mappings(
                            video_files, naming_style=args.naming_style
                        )
                        transcribe_videos(mappings, transcriber)
                    else:
                        print(f"No videos downloaded/found for {course_name}")
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
