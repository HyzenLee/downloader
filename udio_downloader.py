#!/usr/bin/env python3
"""
Standalone Udio Song Downloader
Downloads songs from Udio.com without requiring a web interface.

Usage:
    python udio_downloader.py <udio_song_url> [output_directory]

Example:
    python udio_downloader.py https://www.udio.com/songs/abc123
    python udio_downloader.py https://www.udio.com/songs/abc123 ./downloads
"""

import requests
import re
import os
import sys
from urllib.parse import urlparse


def is_valid_udio_url(url):
    """Validate that URL is actually from udio.com"""
    try:
        parsed = urlparse(url)
        return parsed.netloc == 'www.udio.com' and '/songs/' in parsed.path
    except:
        return False


def extract_audio_url(udio_url):
    """
    Extract MP3 URL and song title from a Udio song page.

    Args:
        udio_url: The Udio song page URL

    Returns:
        tuple: (audio_url, song_title) or (None, None) if extraction fails
    """
    print(f"[1/3] Fetching Udio page: {udio_url}")

    try:
        # Fetch the page
        response = requests.get(udio_url, timeout=10)
        response.raise_for_status()

        # Find all MP3 URLs in the page
        all_mp3_urls = re.findall(r'https://storage\.googleapis\.com/[^"]+\.mp3', response.text)

        if not all_mp3_urls:
            print("ERROR: Could not find audio file on this page")
            return None, None

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in all_mp3_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        print(f"      Found {len(unique_urls)} unique MP3 URL(s)")

        # Try to find a working URL by checking if it's accessible
        audio_url = None
        for i, url in enumerate(unique_urls, 1):
            try:
                print(f"      Testing URL {i}/{len(unique_urls)}...", end=" ")
                head_response = requests.head(url, timeout=5)
                if head_response.status_code == 200:
                    audio_url = url
                    print("✓ Working")
                    break
                else:
                    print(f"✗ Status {head_response.status_code}")
            except Exception as e:
                print(f"✗ Failed ({e})")
                continue

        if not audio_url:
            # If none work, use the first URL anyway (fallback)
            print("      No working URL found, using first URL as fallback")
            audio_url = unique_urls[0]

        # Extract song title from page
        title_match = re.search(r'<title>([^<]+)</title>', response.text)
        song_title = 'udio_song'
        if title_match:
            title_text = title_match.group(1)
            # Extract just the song name part (before " | Udio")
            if ' - ' in title_text:
                song_title = title_text.split(' - ')[1].split(' | ')[0].strip()
            # Sanitize filename
            song_title = re.sub(r'[^\w\s-]', '', song_title).strip().replace(' ', '_')

        print(f"      Song title: {song_title}")
        return audio_url, song_title

    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch URL: {e}")
        return None, None
    except Exception as e:
        print(f"ERROR: An error occurred: {e}")
        return None, None


def download_audio(audio_url, output_path):
    """
    Download audio file from the given URL.

    Args:
        audio_url: The direct MP3 URL
        output_path: The file path to save the MP3

    Returns:
        bool: True if download succeeded, False otherwise
    """
    print(f"[2/3] Downloading audio file...")

    try:
        audio_response = requests.get(audio_url, stream=True, timeout=30)
        audio_response.raise_for_status()

        # Get file size if available
        file_size = audio_response.headers.get('Content-Length')
        if file_size:
            file_size_mb = int(file_size) / (1024 * 1024)
            print(f"      File size: {file_size_mb:.2f} MB")

        # Download in chunks
        downloaded = 0
        with open(output_path, 'wb') as f:
            for chunk in audio_response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if file_size:
                    progress = (downloaded / int(file_size)) * 100
                    print(f"\r      Progress: {progress:.1f}%", end="", flush=True)

        if file_size:
            print()  # New line after progress

        print(f"[3/3] Successfully saved to: {output_path}")
        return True

    except Exception as e:
        print(f"ERROR: Download failed: {e}")
        return False


def main():
    """Main function to handle CLI usage"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nERROR: Please provide a Udio song URL")
        sys.exit(1)

    udio_url = sys.argv[1].strip()
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'

    # Validate URL
    if not is_valid_udio_url(udio_url):
        print("ERROR: Invalid Udio song URL. Must be from www.udio.com with /songs/ path")
        print("Example: https://www.udio.com/songs/abc123")
        sys.exit(1)

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # Extract audio URL and title
    audio_url, song_title = extract_audio_url(udio_url)

    if not audio_url:
        print("\nFailed to extract audio URL")
        sys.exit(1)

    # Prepare output path
    output_path = os.path.join(output_dir, f"{song_title}.mp3")

    # Download the audio
    success = download_audio(audio_url, output_path)

    if not success:
        print("\nDownload failed")
        sys.exit(1)

    print("\n✓ Download complete!")
    print(f"  File: {os.path.abspath(output_path)}")


if __name__ == '__main__':
    main()
