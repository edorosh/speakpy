"""Main script for audio recording to speech-to-text conversion.

This script records audio from an input device, compresses it using ffmpeg,
and sends it to a speaches.ai API for transcription.
"""

import argparse
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.audio_recorder import AudioRecorder
from src.audio_compressor import AudioCompressor
from src.api_client import SpeachesClient
from src.utils import setup_logging, get_temp_audio_file, cleanup_file


logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Record audio and transcribe using speaches.ai API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available audio devices
  python speakpy.py --list-devices
  
  # Record from default device (press CTRL+C to stop)
  python speakpy.py
  
  # Record from specific device
  python speakpy.py --device 1
  
  # Use custom API endpoint
  python speakpy.py --api-url http://192.168.1.100:8000
  
  # Specify language
  python speakpy.py --language en
        """
    )
    
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit"
    )
    
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Audio input device index (use --list-devices to see options)"
    )
    
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="Speaches.ai API base URL (default: http://localhost:8000)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="Systran/faster-distil-whisper-large-v3",
        help="Model to use for transcription"
    )
    
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code for transcription (e.g., 'en', 'es')"
    )
    
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=44100,
        help="Recording sample rate in Hz (default: 44100)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Keep temporary audio files (for debugging)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    # List devices if requested
    if args.list_devices:
        AudioRecorder.print_devices()
        return 0
    
    # Check if ffmpeg is available
    compressor = AudioCompressor()
    if not compressor.is_available():
        logger.error("FFmpeg is not available")
        AudioCompressor.print_installation_instructions()
        return 1
    
    # Initialize components
    recorder = AudioRecorder(sample_rate=args.sample_rate, channels=1)
    client = SpeachesClient(base_url=args.api_url, model=args.model)
    
    # Check API health
    logger.info("Checking speaches.ai API availability...")
    if not client.check_health():
        logger.warning(
            f"Could not verify API at {args.api_url}. "
            "Proceeding anyway, but transcription may fail."
        )
    else:
        logger.info("API is available ✓")
    
    temp_wav = None
    temp_opus = None
    interrupt_count = [0]  # Use list to allow modification in nested function
    recording_active = [False]  # Track if we're in recording phase
    
    def signal_handler(sig, frame):
        """Handle CTRL+C interrupts."""
        interrupt_count[0] += 1
        if not recording_active[0]:
            # Not recording, exit immediately
            print("\n\n❌ Exiting application")
            logger.info("Application interrupted by user")
            sys.exit(130)
        elif interrupt_count[0] >= 2:
            # Second CTRL+C during or after recording, exit
            print("\n\n❌ Exiting application (CTRL+C pressed twice)")
            logger.info("Application interrupted by user (double CTRL+C)")
            sys.exit(130)
        else:
            # First CTRL+C during recording - let it propagate to stop recording
            raise KeyboardInterrupt
    
    # Set up signal handler
    import signal
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Record audio
        print("\n🎤 Recording... Press CTRL+C once to stop recording, twice to exit.")
        print("Speak now!\n")
        
        recording_active[0] = True
        audio_data = recorder.record_until_stopped(device=args.device)
        recording_active[0] = False
        print("\n✓ Recording complete\n")
        
        # Save to temporary WAV file
        temp_wav = get_temp_audio_file(".wav")
        recorder.save_wav(audio_data, temp_wav)
        
        # Compress audio
        print("🔄 Compressing audio with ffmpeg...")
        temp_opus = get_temp_audio_file(".opus")
        compressor.compress(temp_wav, temp_opus)
        print("✓ Compression complete\n")
        
        # Transcribe
        print("🌐 Sending to speaches.ai for transcription...")
        result = client.transcribe(
            temp_opus,
            language=args.language,
            response_format="json"
        )
        
        print("✓ Transcription complete\n")
        
        # Display result
        print("=" * 70)
        print("TRANSCRIPTION RESULT")
        print("=" * 70)
        
        if "text" in result:
            print(f"\n{result['text']}\n")
        else:
            print(f"\n{result}\n")
        
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"\n❌ Error: {e}\n", file=sys.stderr)
        return 1
        
    finally:
        # Cleanup temporary files
        if not args.keep_files:
            if temp_wav:
                cleanup_file(temp_wav)
            if temp_opus:
                cleanup_file(temp_opus)
        else:
            if temp_wav:
                logger.info(f"Kept temporary WAV file: {temp_wav}")
            if temp_opus:
                logger.info(f"Kept temporary Opus file: {temp_opus}")


if __name__ == "__main__":
    sys.exit(main())
