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
    
    def record_until_stopped(
        self, 
        device: Optional[int] = None,
        vad_processor=None
    ) -> np.ndarray:
        """Record audio continuously until interrupted.
        
        Args:
            device: Device index to record from (None for default)
            vad_processor: Optional StreamingVAD instance for voice activity detection
            
        Returns:
            NumPy array containing audio data (only speech if VAD enabled)
            
        Raises:
            RuntimeError: If recording fails
            KeyboardInterrupt: When user interrupts recording
        """
        try:
            logger.info("Starting continuous recording...")
            
            if device is not None:
                logger.info(f"Using device index: {device}")
            
            # Storage for audio chunks
            recorded_chunks = []
            last_speech_state = False
            
            def audio_callback(indata, frames, time, status):
                """Callback for audio stream."""
                if status:
                    logger.warning(f"Audio callback status: {status}")
                
                # Copy audio data to our buffer
                audio_data = indata.copy()
                
                if vad_processor:
                    # Process through VAD
                    is_speech, speech_prob = vad_processor.process_chunk(audio_data)
                    
                    # Only store if speech detected OR we're in a speech segment
                    # (StreamingVAD handles buffering internally)
                    nonlocal last_speech_state
                    if is_speech != last_speech_state:
                        # State changed, print feedback
                        if is_speech:
                            print("🎤 Speech detected...", end='\r', flush=True)
                        else:
                            print("⏸️  Silence...        ", end='\r', flush=True)
                        last_speech_state = is_speech
                else:
                    # No VAD, record everything
                    recorded_chunks.append(audio_data)
            
            # Start recording stream
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=device,
                dtype='float32',
                callback=audio_callback
            ):
                logger.info("Recording started. Press CTRL+C to stop...")
                # Keep the stream open until interrupted
                while True:
                    sd.sleep(100)  # Sleep in small chunks to be responsive
            
        except KeyboardInterrupt:
            # This is expected when user wants to stop recording
            logger.info("Recording interrupted by user")
            
            if vad_processor:
                # Get speech audio from VAD processor
                recording = vad_processor.get_speech_audio()
                if recording is None or len(recording) == 0:
                    raise RuntimeError("No speech detected during recording")
                
                # Print statistics
                stats = vad_processor.get_statistics()
                logger.info(
                    f"VAD Statistics: {stats['speech_chunks']}/{stats['total_chunks']} "
                    f"chunks contained speech ({stats['speech_ratio']*100:.1f}%)"
                )
            else:
                # No VAD, use regular chunks
                if not recorded_chunks:
                    raise RuntimeError("No audio data recorded")
                recording = np.concatenate(recorded_chunks, axis=0)
            
            logger.info(f"Recording completed successfully ({len(recording) / self.sample_rate:.2f} seconds)")
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
