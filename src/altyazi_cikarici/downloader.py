"""
Downloader module for fetching course videos from URLs.
"""

import os
import urllib.parse
from typing import List
import httpx
from tqdm import tqdm

from altyazi_cikarici.constants import DEFAULT_OUTPUT_DIRECTORY


class VideoDownloader:
    """
    Handles downloading videos from URLs into appropriate course folders.
    """

    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIRECTORY):
        self.output_dir = output_dir

    def download_file(self, url: str, target_path: str) -> bool:
        """
        Downloads a single file from url to target_path with a progress bar.
        Returns True if successful, False otherwise.
        """
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        if os.path.exists(target_path):
            print(f"Already exists: {os.path.basename(target_path)}")
            return True

        temp_path = target_path + ".tmp"
        print(f"Downloading: {url} -> {target_path}")

        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as r:
                r.raise_for_status()
                total_size = int(r.headers.get("content-length", 0))

                desc_name = os.path.basename(target_path)
                if len(desc_name) > 30:
                    desc_name = desc_name[:27] + "..."
                with open(temp_path, "wb") as f, tqdm(
                    desc=desc_name,
                    total=total_size,
                    unit="iB",
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar:
                    for chunk in r.iter_bytes(chunk_size=8192):
                        size = f.write(chunk)
                        bar.update(size)

            os.replace(temp_path, target_path)
            return True
        except BaseException as e:
            if not isinstance(e, KeyboardInterrupt):
                print(f"Failed to download {url}: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            if isinstance(e, KeyboardInterrupt):
                raise e
            return False

    def download_course(self, course_name: str, urls: List[str]) -> List[str]:
        """
        Downloads all videos for a given course name.
        Returns the list of downloaded file paths.
        """
        downloaded_paths: List[str] = []
        course_dir = os.path.join(self.output_dir, course_name)

        for url in urls:
            # Parse the filename from the URL path
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename:
                continue

            # Unquote filename (e.g. %20 -> space)
            filename = urllib.parse.unquote(filename)
            target_path = os.path.join(course_dir, filename)

            success = self.download_file(url, target_path)
            if success:
                downloaded_paths.append(target_path)

        return downloaded_paths
