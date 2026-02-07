"""GUI entry point for speakpy application.

This script provides a Windows GUI interface for the audio recording
and transcription workflow using tkinter.
"""

import tkinter as tk
from tkinter import ttk
import sys
import logging
from pathlib import Path
import threading
from typing import Optional
import queue
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.audio_recorder import AudioRecorder
from src.audio_compressor import AudioCompressor
from src.api_client import SpeachesClient
from src.utils import setup_logging, get_temp_audio_file, cleanup_file
from src.vad_processor import VADProcessor, StreamingVAD
from src.gui import SpeakPyGUI
from src.single_instance import SingleInstance


def create_tray_icon():
    """Create a simple tray icon image dynamically.
    
    Returns:
        PIL.Image: 16x16 microphone icon
    """
    from PIL import Image, ImageDraw
    
    # Create a 16x16 image with transparent background
    img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a simple microphone icon (circle with line)
    # Microphone body (circle)
    draw.ellipse([5, 2, 11, 10], fill=(70, 130, 180), outline=(50, 100, 150))
    # Microphone stand
    draw.rectangle([7, 10, 9, 14], fill=(70, 130, 180))
    # Microphone base
    draw.rectangle([5, 14, 11, 15], fill=(70, 130, 180))
    
    return img


logger = logging.getLogger(__name__)


class SpeakPyApplication:
    """Main application class that manages recording workflow."""
    
    def __init__(self, 
                 api_url: str = "http://localhost:8000",
                 model: str = "Systran/faster-distil-whisper-large-v3",
                 sample_rate: int = 44100,
                 device: int | None = None,
                 language: str | None = None,
                 use_vad: bool = False,
                 vad_threshold: float = 0.5,
                 keep_files: bool = False,
                 gui_toggle_callback: Optional[callable] = None):
        """Initialize the application.
        
        Args:
            api_url: Speaches.ai API base URL
            model: Model to use for transcription
            sample_rate: Recording sample rate in Hz
            device: Audio input device index
            language: Language code for transcription
            use_vad: Enable Voice Activity Detection
            vad_threshold: VAD sensitivity threshold
            keep_files: Keep temporary audio files
        """
        self.api_url = api_url
        self.model = model
        self.sample_rate = sample_rate
        self.device = device
        self.language = language
        self.use_vad = use_vad
        self.vad_threshold = vad_threshold
        self.keep_files = keep_files
        self.gui_toggle_callback = gui_toggle_callback
        
        # Recording state
        self.recording_active = False
        self.stop_event = threading.Event()
        self.audio_data = None
        self.temp_wav = None
        self.temp_opus = None
        
        # Hotkey support
        self.hotkey_listener = None
        self.hotkey_queue = queue.Queue()
        
        # Initialize components
        self.recorder = AudioRecorder(sample_rate=sample_rate, channels=1)
        self.compressor = AudioCompressor()
        self.client = SpeachesClient(base_url=api_url, model=model)
        self.vad_streaming = None
        
        # Check components
        self._check_components()
        
        # Start global hotkey listener
        self._start_hotkey_listener()
    
    def _check_components(self):
        """Check if required components are available."""
        # Check ffmpeg
        if not self.compressor.is_available():
            logger.error("FFmpeg is not available")
            AudioCompressor.print_installation_instructions()
            raise RuntimeError("FFmpeg is required but not available")
        
        # Skip API health check at startup - connection will drop anyway
        # We do a warmup right before transcription instead
        logger.info(f"API configured: {self.api_url}")
        
        # Initialize VAD if requested
        if self.use_vad:
            try:
                logger.info("Initializing Voice Activity Detection...")
                vad = VADProcessor(
                    sample_rate=16000,
                    threshold=self.vad_threshold
                )
                if not vad.is_available():
                    logger.error("VAD is not available")
                    VADProcessor.print_installation_instructions()
                    raise RuntimeError("VAD is required but not available")
                
                self.vad_streaming = StreamingVAD(
                    vad_processor=vad,
                    original_sample_rate=self.sample_rate
                )
                logger.info(f"VAD enabled (threshold: {self.vad_threshold})")
            except Exception as e:
                logger.error(f"Failed to initialize VAD: {e}")
                raise RuntimeError(f"Failed to initialize VAD: {e}")
    
    def start_recording(self, device_index: Optional[int] = None, model: Optional[str] = None) -> dict:
        """Start recording and process the audio.
        
        Args:
            device_index: Audio device index to use (None for default)
            model: Model to use for transcription (None to use default)
        
        Returns:
            Dictionary containing transcription result
        """
        self.stop_event.clear()
        self.recording_active = True
        
        # Update model if specified
        if model and model != self.model:
            self.model = model
            # Recreate client with new model
            self.client = SpeachesClient(base_url=self.api_url, model=model)
            logger.info(f"Using model: {model}")
        
        # Update device if specified
        if device_index is not None:
            self.device = device_index
            logger.info(f"Using audio device index: {device_index}")
        
        result = {}
        
        try:
            # Record audio
            vad_status = " with VAD filtering" if self.use_vad else ""
            logger.info(f"Recording{vad_status}...")
            print(f"🎤 Recording{vad_status}... Speak now!")
            
            if self.use_vad:
                print("VAD will detect and record only when you speak.")
            
            # Record with custom stop check
            self.audio_data = self._record_with_stop_check()
            
            if self.audio_data is None or len(self.audio_data) == 0:
                logger.warning("Recording was cancelled or no audio captured")
                return {"text": "Recording cancelled or no audio captured"}
            
            print("✓ Recording complete")
            logger.info("Recording complete")
            
            # Save to temporary WAV file
            self.temp_wav = get_temp_audio_file(".wav")
            self.recorder.save_wav(self.audio_data, self.temp_wav)
            
            # Compress audio
            print("🔄 Compressing audio with ffmpeg...")
            logger.info("Compressing audio...")
            self.temp_opus = get_temp_audio_file(".opus")
            self.compressor.compress(self.temp_wav, self.temp_opus)
            print("✓ Compression complete")
            logger.info("Compression complete")
            
            # Transcribe
            print("🌐 Sending to speaches.ai for transcription...")
            logger.info("Sending to API for transcription...")
            
            # Warm up connection right before transcription to avoid dropped connections
            logger.debug("Warming up connection...")
            self.client.check_health()
            
            result = self.client.transcribe(
                self.temp_opus,
                language=self.language,
                response_format="json"
            )
            
            print("✓ Transcription complete")
            logger.info("Transcription complete")
            
        except Exception as e:
            logger.error(f"Error during recording/transcription: {e}")
            result = {"error": str(e)}
            raise
        
        finally:
            self.recording_active = False
            # Cleanup temporary files
            self._cleanup_files()
        
        return result
    
    def _record_with_stop_check(self):
        """Record audio with periodic stop event checking.
        
        Returns:
            Audio data as numpy array
        """
        import numpy as np
        import sounddevice as sd
        
        recorded_chunks = []
        last_speech_state = False
        
        def audio_callback(indata, frames, time, status):
            """Callback for audio stream."""
            if status:
                logger.warning(f"Audio callback status: {status}")
            
            # Check if we should stop
            if self.stop_event.is_set():
                raise sd.CallbackStop()
            
            audio_data = indata.copy()
            
            # Apply VAD if enabled
            if self.vad_streaming:
                nonlocal last_speech_state
                is_speech, speech_prob = self.vad_streaming.process_chunk(audio_data)
                
                # Log state changes
                if is_speech != last_speech_state:
                    if is_speech:
                        print("🎤 Speech detected...")
                    else:
                        print("⏸️ Silence...")
                    last_speech_state = is_speech
            else:
                # No VAD, record everything
                recorded_chunks.append(audio_data)
        
        # Start recording
        try:
            with sd.InputStream(
                callback=audio_callback,
                device=self.device,
                channels=self.recorder.channels,
                samplerate=self.recorder.sample_rate,
                dtype='float32'
            ):
                # Wait for stop event
                self.stop_event.wait()
                
        except sd.CallbackStop:
            pass
        except Exception as e:
            logger.error(f"Recording error: {e}")
            raise
        
        # Get final audio data
        if self.vad_streaming:
            # Get speech audio from VAD processor
            recording = self.vad_streaming.get_speech_audio()
            if recording is None or len(recording) == 0:
                logger.warning("No speech detected during recording")
                return None
            
            # Print statistics
            stats = self.vad_streaming.get_statistics()
            logger.info(
                f"VAD Statistics: {stats['speech_chunks']}/{stats['total_chunks']} "
                f"chunks contained speech ({stats['speech_ratio']*100:.1f}%)"
            )
            return recording
        else:
            # No VAD, concatenate chunks
            if recorded_chunks:
                return np.concatenate(recorded_chunks, axis=0)
            return None
    
    def stop_recording(self):
        """Stop the current recording."""
        logger.info("Stop recording requested")
        self.stop_event.set()
    
    def _cleanup_files(self):
        """Clean up temporary files."""
        if not self.keep_files:
            if self.temp_wav:
                cleanup_file(self.temp_wav)
                self.temp_wav = None
            if self.temp_opus:
                cleanup_file(self.temp_opus)
                self.temp_opus = None
        else:
            if self.temp_wav:
                logger.info(f"Kept temporary WAV file: {self.temp_wav}")
            if self.temp_opus:
                logger.info(f"Kept temporary Opus file: {self.temp_opus}")
    
    def _start_hotkey_listener(self):
        """Start the global hotkey listener."""
        try:
            from pynput import keyboard
            
            def on_hotkey():
                """Handle hotkey press."""
                self.hotkey_queue.put('toggle')
                logger.debug("Global hotkey pressed (Ctrl+Shift+;)")
            
            # Create hotkey listener (Ctrl+Shift+;)
            self.hotkey_listener = keyboard.GlobalHotKeys({
                '<ctrl>+<shift>+;': on_hotkey
            })
            self.hotkey_listener.start()
            logger.info("Global hotkey registered: Ctrl+Shift+;")
        except Exception as e:
            logger.warning(f"Failed to register global hotkey: {e}")
    
    def check_hotkey_queue(self):
        """Check and process hotkey queue (called from GUI main thread)."""
        try:
            while True:
                action = self.hotkey_queue.get_nowait()
                if action == 'toggle' and self.gui_toggle_callback:
                    self.gui_toggle_callback()
        except queue.Empty:
            pass
    
    def cleanup(self):
        """Clean up resources."""
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            logger.info("Global hotkey listener stopped")


def main():
    """Main entry point for the GUI application."""
    # Check for single instance before doing anything else
    try:
        instance_lock = SingleInstance()
    except RuntimeError as e:
        # Another instance is already running
        print(f"\n❌ Error: {e}\n", file=sys.stderr)
        return 1
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='SpeakPy GUI - Voice Recorder & Transcription')
    parser.add_argument('--tray', action='store_true', help='Start minimized to system tray')
    parser.add_argument('--api-url', default='http://localhost:8000', help='Speaches.ai API URL')
    parser.add_argument('--model', default='Systran/faster-distil-whisper-large-v3', help='Transcription model')
    parser.add_argument('--vad', action='store_true', help='Enable Voice Activity Detection')
    parser.add_argument('--vad-threshold', type=float, default=0.5, help='VAD sensitivity threshold')
    parser.add_argument('--keep-files', action='store_true', help='Keep temporary audio files')
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(logging.INFO)
    
    # Create root window first (needed for gui_toggle_callback)
    root = tk.Tk()
    
    # Get available audio devices
    import sounddevice as sd
    devices = AudioRecorder.list_devices()
    
    # Mark the default device
    default_device = sd.default.device[0]  # Input device index
    for device in devices:
        if device['index'] == default_device:
            device['is_default'] = True
        else:
            device['is_default'] = False
    
    if not devices:
        logger.error("No input devices found!")
        print("Error: No audio input devices found!")
        return 1
    
    # GUI toggle callback placeholder (will be set after GUI creation)
    gui_toggle_ref = {'callback': None}
    
    def gui_toggle_wrapper():
        if gui_toggle_ref['callback']:
            gui_toggle_ref['callback']()
    
    # Create application instance
    app = SpeakPyApplication(
        api_url=args.api_url,
        model=args.model,
        sample_rate=44100,
        device=None,  # Use default device
        language=None,  # Auto-detect
        use_vad=args.vad,
        vad_threshold=args.vad_threshold,
        keep_files=args.keep_files,
        gui_toggle_callback=gui_toggle_wrapper
    )
    
    # Create GUI
    gui = SpeakPyGUI(
        root=root,
        recording_callback=app.start_recording,
        stop_callback=app.stop_recording,
        devices=devices,
        default_model=args.model,
        start_in_tray=args.tray
    )
    
    # Set GUI toggle callback
    gui_toggle_ref['callback'] = gui._toggle_recording
    
    logger.info("SpeakPy GUI started")
    if not args.tray:
        print("SpeakPy GUI Ready! Click 'Start Recording' to begin.")
        print("Global hotkey: Ctrl+Shift+; to toggle recording")
    
    # Poll hotkey queue
    def poll_hotkey():
        app.check_hotkey_queue()
        root.after(100, poll_hotkey)
    
    poll_hotkey()
    
    # Run GUI
    try:
        gui.run()
    finally:
        app.cleanup()
        instance_lock.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
