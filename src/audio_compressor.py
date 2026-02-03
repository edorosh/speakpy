"""Audio compression module using ffmpeg."""

import logging
import subprocess
import shutil
import os
import sys
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


class AudioCompressor:
    """Compresses audio files using ffmpeg."""
    
    # FFmpeg compression arguments from Epicenter project
    FFMPEG_FILTERS = (
        "silenceremove=start_periods=1:start_duration=0.1:"
        "start_threshold=-50dB:detection=peak,"
        "aformat=sample_fmts=s16:sample_rates=16000:channel_layouts=mono"
    )
    
    FFMPEG_CODEC_ARGS = [
        "-c:a", "libopus",
        "-b:a", "32k",
        "-ar", "16000",
        "-ac", "1",
        "-compression_level", "10"
    ]
    
    def __init__(self):
        """Initialize the audio compressor."""
        self.ffmpeg_path = self._find_ffmpeg()
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Find ffmpeg binary in system PATH or local directory.
        
        Returns:
            Path to ffmpeg binary or None if not found
        """
        # Check system PATH
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            logger.info(f"Found ffmpeg in system PATH: {ffmpeg_path}")
            return ffmpeg_path
        
        # Check local directory
        local_ffmpeg = Path("ffmpeg") / "bin" / "ffmpeg.exe"
        if local_ffmpeg.exists():
            logger.info(f"Found local ffmpeg: {local_ffmpeg}")
            return str(local_ffmpeg)
        
        logger.warning("ffmpeg not found in PATH or local directory")
        return None
    
    def is_available(self) -> bool:
        """Check if ffmpeg is available.
        
        Returns:
            True if ffmpeg is available, False otherwise
        """
        return self.ffmpeg_path is not None
    
    def compress(self, input_path: str, output_path: str) -> None:
        """Compress audio file using ffmpeg.
        
        Args:
            input_path: Path to input audio file
            output_path: Path to output compressed file
            
        Raises:
            RuntimeError: If compression fails or ffmpeg is not available
        """
        if not self.is_available():
            raise RuntimeError(
                "ffmpeg is not available. Please install ffmpeg or download "
                "a portable version to the 'ffmpeg' directory.\n"
                "Download from: https://www.gyan.dev/ffmpeg/builds/"
            )
        
        try:
            logger.info(f"Compressing audio: {input_path} -> {output_path}")
            
            # Build ffmpeg command
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-af", self.FFMPEG_FILTERS,
                *self.FFMPEG_CODEC_ARGS,
                "-y",  # Overwrite output file if exists
                output_path
            ]
            
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            
            # Run ffmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg stderr: {result.stderr}")
                raise RuntimeError(f"FFmpeg compression failed: {result.stderr}")
            
            logger.info("Audio compression completed successfully")
            
            # Log file sizes
            input_size = os.path.getsize(input_path)
            output_size = os.path.getsize(output_path)
            compression_ratio = (1 - output_size / input_size) * 100
            
            logger.info(
                f"Compression stats: {input_size:,} bytes -> {output_size:,} bytes "
                f"({compression_ratio:.1f}% reduction)"
            )
            
        except Exception as e:
            logger.error(f"Failed to compress audio: {e}")
            raise RuntimeError(f"Audio compression failed: {e}")
    
    @staticmethod
    def print_installation_instructions() -> None:
        """Print instructions for installing ffmpeg."""
        print("\n" + "=" * 70)
        print("FFmpeg Installation Instructions")
        print("=" * 70)
        print("\nOption 1: Install to System PATH (Recommended)")
        print("  1. Download ffmpeg from: https://www.gyan.dev/ffmpeg/builds/")
        print("  2. Extract the ZIP file")
        print("  3. Add the 'bin' folder to your system PATH")
        print("  4. Restart your terminal")
        print("\nOption 2: Use Portable Version")
        print("  1. Download ffmpeg from: https://www.gyan.dev/ffmpeg/builds/")
        print("  2. Extract the ZIP file")
        print("  3. Create a 'ffmpeg' folder in this project directory")
        print("  4. Copy the extracted 'bin' folder into the 'ffmpeg' folder")
        print("  5. The structure should be: .\\ffmpeg\\bin\\ffmpeg.exe")
        print("=" * 70 + "\n")
