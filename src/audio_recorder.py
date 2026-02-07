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
        
        Uses sounddevice's built-in filtering to get input devices.
        
        Returns:
            List of device information dictionaries
        """
        # Get only input devices
        input_devices = sd.query_devices(kind='input')
        
        # Convert to list if single device
        if isinstance(input_devices, dict):
            input_devices = [input_devices]
        
        # Format devices with required fields
        return [{
            'index': device['index'],
            'name': device['name'].strip(),
            'channels': device['max_input_channels'],
            'sample_rate': device['default_samplerate']
        } for device in input_devices]
    

    

    
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
