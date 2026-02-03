"""Audio recording module using sounddevice."""

import logging
import sounddevice as sd
import numpy as np
from typing import Optional, Dict, List
import wave


logger = logging.getLogger(__name__)


class AudioRecorder:
    """Records audio from input devices using sounddevice."""
    
    def __init__(self, sample_rate: int = 44100, channels: int = 1):
        """Initialize the audio recorder.
        
        Args:
            sample_rate: Sample rate in Hz (default: 44100)
            channels: Number of audio channels (default: 1 for mono)
        """
        self.sample_rate = sample_rate
        self.channels = channels
    
    @staticmethod
    def list_devices() -> List[Dict]:
        """List all available audio input devices.
        
        Returns:
            List of device information dictionaries
        """
        devices = sd.query_devices()
        input_devices = []
        
        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    'index': idx,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })
        
        return input_devices
    
    @staticmethod
    def print_devices() -> None:
        """Print all available audio input devices to console."""
        devices = AudioRecorder.list_devices()
        
        if not devices:
            print("No input devices found!")
            return
        
        print("\nAvailable Audio Input Devices:")
        print("-" * 70)
        print(f"{'Index':<8} {'Name':<40} {'Channels':<10} {'Sample Rate'}")
        print("-" * 70)
        
        for device in devices:
            print(f"{device['index']:<8} {device['name']:<40} "
                  f"{device['channels']:<10} {device['sample_rate']:.0f} Hz")
        print("-" * 70)
    
    def record(self, duration: float, device: Optional[int] = None) -> np.ndarray:
        """Record audio from the specified device.
        
        Args:
            duration: Recording duration in seconds
            device: Device index to record from (None for default)
            
        Returns:
            NumPy array containing audio data
            
        Raises:
            RuntimeError: If recording fails
        """
        try:
            logger.info(f"Recording {duration} seconds of audio...")
            
            if device is not None:
                logger.info(f"Using device index: {device}")
            
            # Record audio
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                device=device,
                dtype='float32'
            )
            
            sd.wait()  # Wait until recording is finished
            
            logger.info("Recording completed successfully")
            return recording
            
        except Exception as e:
            logger.error(f"Failed to record audio: {e}")
            raise RuntimeError(f"Audio recording failed: {e}")
    
    def save_wav(self, audio_data: np.ndarray, filepath: str) -> None:
        """Save audio data to a WAV file.
        
        Args:
            audio_data: NumPy array containing audio data
            filepath: Output file path
            
        Raises:
            RuntimeError: If saving fails
        """
        try:
            logger.debug(f"Saving audio to {filepath}")
            
            # Convert float32 to int16
            audio_int16 = np.int16(audio_data * 32767)
            
            with wave.open(filepath, 'w') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 2 bytes for int16
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())
            
            logger.debug(f"Audio saved successfully to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            raise RuntimeError(f"Failed to save audio file: {e}")
