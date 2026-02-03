"""Utility functions for the speakpy application."""

import logging
import tempfile
import os
from pathlib import Path
from typing import Optional


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the application.
    
    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def get_temp_audio_file(suffix: str = ".wav") -> str:
    """Create a temporary file for audio data.
    
    Args:
        suffix: File extension for the temp file
        
    Returns:
        Path to the temporary file
    """
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="speakpy_")
    os.close(fd)  # Close file descriptor, we just need the path
    return path


def cleanup_file(filepath: str) -> None:
    """Safely remove a file if it exists.
    
    Args:
        filepath: Path to file to remove
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logging.debug(f"Cleaned up file: {filepath}")
    except Exception as e:
        logging.warning(f"Failed to clean up file {filepath}: {e}")


def ensure_directory(dirpath: str) -> None:
    """Ensure a directory exists, creating it if necessary.
    
    Args:
        dirpath: Path to directory
    """
    Path(dirpath).mkdir(parents=True, exist_ok=True)
