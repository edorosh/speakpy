"""Voice Activity Detection (VAD) module using Silero VAD."""

import logging
import numpy as np
import torch
from typing import Optional, Tuple


logger = logging.getLogger(__name__)


class VADProcessor:
    """Voice Activity Detection processor using Silero VAD model."""
    
    def __init__(
        self, 
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100,
        speech_pad_ms: int = 30
    ):
        """Initialize the VAD processor.
        
        Args:
            sample_rate: Sample rate for VAD processing (8000 or 16000 Hz)
            threshold: Speech probability threshold (0.0 to 1.0)
            min_speech_duration_ms: Minimum speech duration to keep (milliseconds)
            min_silence_duration_ms: Minimum silence to split speech (milliseconds)
            speech_pad_ms: Padding to add around speech segments (milliseconds)
        """
        if sample_rate not in [8000, 16000]:
            logger.warning(
                f"Silero VAD works best with 8000 or 16000 Hz. "
                f"Got {sample_rate} Hz. Audio will be resampled."
            )
        
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms
        
        # Calculate frame sizes
        self.min_speech_samples = int(sample_rate * min_speech_duration_ms / 1000)
        self.min_silence_samples = int(sample_rate * min_silence_duration_ms / 1000)
        self.speech_pad_samples = int(sample_rate * speech_pad_ms / 1000)
        
        # State tracking
        self.is_speaking = False
        self.speech_buffer = []
        self.silence_counter = 0
        
        # Load model
        self.model = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the Silero VAD model."""
        try:
            logger.info("Loading Silero VAD model...")
            self.model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            self.model.eval()
            logger.info("Silero VAD model loaded successfully")
            
            # Extract utility functions
            (self.get_speech_timestamps,
             self.save_audio,
             self.read_audio,
             self.VADIterator,
             self.collect_chunks) = utils
             
        except Exception as e:
            logger.error(f"Failed to load Silero VAD model: {e}")
            raise RuntimeError(f"Could not load VAD model: {e}")
    
    def is_available(self) -> bool:
        """Check if VAD model is available.
        
        Returns:
            True if model is loaded and ready
        """
        return self.model is not None
    
    def resample_audio(
        self, 
        audio: np.ndarray, 
        original_rate: int
    ) -> np.ndarray:
        """Resample audio to VAD sample rate if needed.
        
        Args:
            audio: Audio data (float32)
            original_rate: Original sample rate
            
        Returns:
            Resampled audio at self.sample_rate
        """
        if original_rate == self.sample_rate:
            return audio
        
        # Simple linear interpolation resampling
        # For production, consider using librosa or torchaudio for better quality
        duration = len(audio) / original_rate
        new_length = int(duration * self.sample_rate)
        
        indices = np.linspace(0, len(audio) - 1, new_length)
        resampled = np.interp(indices, np.arange(len(audio)), audio.flatten())
        
        return resampled.astype(np.float32)
    
    def process_chunk(
        self, 
        audio_chunk: np.ndarray,
        original_rate: int = None
    ) -> Tuple[bool, Optional[np.ndarray]]:
        """Process an audio chunk and detect speech.
        
        Args:
            audio_chunk: Audio data as numpy array (float32)
            original_rate: Original sample rate (if different from VAD rate)
            
        Returns:
            Tuple of (is_speech, audio_to_keep)
            - is_speech: True if speech detected in this chunk
            - audio_to_keep: Audio data to save (None if silence)
        """
        if self.model is None:
            raise RuntimeError("VAD model not loaded")
        
        # Resample if needed
        if original_rate and original_rate != self.sample_rate:
            processed_chunk = self.resample_audio(audio_chunk, original_rate)
        else:
            processed_chunk = audio_chunk.flatten()
        
        # Convert to torch tensor
        audio_tensor = torch.from_numpy(processed_chunk)
        
        # Get speech probability
        with torch.no_grad():
            speech_prob = self.model(audio_tensor, self.sample_rate).item()
        
        is_speech = speech_prob >= self.threshold
        
        return is_speech, speech_prob
    
    def reset(self) -> None:
        """Reset the VAD state."""
        self.is_speaking = False
        self.speech_buffer = []
        self.silence_counter = 0
        logger.debug("VAD state reset")
    
    @staticmethod
    def print_installation_instructions() -> None:
        """Print instructions for installing VAD dependencies."""
        print("\n" + "=" * 70)
        print("VAD (Voice Activity Detection) requires PyTorch")
        print("=" * 70)
        print("\nTo install PyTorch:")
        print("\n  uv pip install torch")
        print("\nOr for CPU-only version (smaller download):")
        print("\n  uv pip install torch --index-url https://download.pytorch.org/whl/cpu")
        print("\n" + "=" * 70 + "\n")


class StreamingVAD:
    """Streaming VAD processor that maintains state across chunks."""
    
    def __init__(
        self,
        vad_processor: VADProcessor,
        original_sample_rate: int,
        chunk_duration_ms: int = 30
    ):
        """Initialize streaming VAD.
        
        Args:
            vad_processor: VAD processor instance
            original_sample_rate: Original audio sample rate
            chunk_duration_ms: Process audio in chunks of this duration
        """
        self.vad = vad_processor
        self.original_rate = original_sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        
        # Minimum chunk size for Silero VAD (512 samples at 16kHz = 32ms)
        # We need to buffer chunks to reach this minimum
        self.min_chunk_samples = 512
        self.buffer = []
        self.buffer_size = 0
        
        # Calculate target buffer size in original sample rate
        # We want at least min_chunk_samples at VAD sample rate
        vad_duration = self.min_chunk_samples / self.vad.sample_rate
        self.target_buffer_samples = int(vad_duration * original_sample_rate)
        
        # For collecting speech segments
        self.current_speech = []
        self.is_in_speech = False
        self.silence_duration = 0
        
        # Statistics
        self.total_chunks = 0
        self.speech_chunks = 0
    
    def process_chunk(
        self, 
        audio_chunk: np.ndarray
    ) -> Tuple[bool, Optional[float]]:
        """Process a streaming audio chunk.
        
        Args:
            audio_chunk: Audio chunk from recording stream
            
        Returns:
            Tuple of (is_speech, speech_prob)
            - is_speech: True if speech detected (from last processed buffer)
            - speech_prob: Speech probability (average if multiple chunks processed)
        """
        # Add chunk to buffer
        self.buffer.append(audio_chunk)
        self.buffer_size += len(audio_chunk)
        
        # Only process when we have enough samples
        if self.buffer_size < self.target_buffer_samples:
            # Not enough data yet, return last known state
            return self.is_in_speech, 0.0
        
        # Concatenate buffer
        buffered_audio = np.concatenate(self.buffer, axis=0)
        
        # Clear buffer
        self.buffer = []
        self.buffer_size = 0
        
        # Resample to VAD sample rate
        resampled = self.vad.resample_audio(buffered_audio, self.original_rate)
        
        # Silero VAD requires EXACTLY 512 samples at 16kHz (or 256 at 8kHz)
        required_samples = 512 if self.vad.sample_rate == 16000 else 256
        
        # Split into exact-sized chunks and process each
        num_full_chunks = len(resampled) // required_samples
        speech_probs = []
        
        for i in range(num_full_chunks):
            start = i * required_samples
            end = start + required_samples
            chunk = resampled[start:end]
            
            # Process through VAD
            try:
                # Convert to torch tensor
                audio_tensor = torch.from_numpy(chunk)
                
                # Get speech probability
                with torch.no_grad():
                    speech_prob = self.vad.model(audio_tensor, self.vad.sample_rate).item()
                
                speech_probs.append(speech_prob)
                
            except Exception as e:
                # Log error but don't crash - just treat as silence
                logger.warning(f"VAD processing error: {e}")
                speech_probs.append(0.0)
        
        # If we had any chunks to process
        if speech_probs:
            self.total_chunks += num_full_chunks
            
            # Use average speech probability
            avg_speech_prob = sum(speech_probs) / len(speech_probs)
            is_speech = avg_speech_prob >= self.vad.threshold
            
            if is_speech:
                self.speech_chunks += num_full_chunks
                if not self.is_in_speech:
                    # Starting new speech segment
                    self.is_in_speech = True
                    logger.debug("Speech started")
                
                # Add to current speech buffer (original audio, not resampled)
                self.current_speech.append(buffered_audio)
                self.silence_duration = 0
                
            else:
                # Not speech
                if self.is_in_speech:
                    # We're in a speech segment but this chunk is silence
                    self.silence_duration += len(buffered_audio) / self.original_rate * 1000
                    
                    # Still add to buffer (don't cut off speech abruptly)
                    self.current_speech.append(buffered_audio)
                    
                    # If silence is long enough, end the speech segment
                    if self.silence_duration >= self.vad.min_silence_duration_ms:
                        self.is_in_speech = False
                        self.silence_duration = 0
                        logger.debug("Speech ended")
                # else: we're not in speech and this is silence - ignore
            
            return is_speech, avg_speech_prob
        else:
            # No full chunks to process, return current state
            return self.is_in_speech, 0.0
    
    def get_speech_audio(self) -> Optional[np.ndarray]:
        """Get all collected speech audio.
        
        Returns:
            Concatenated speech segments or None if no speech
        """
        if not self.current_speech:
            return None
        
        return np.concatenate(self.current_speech, axis=0)
    
    def get_statistics(self) -> dict:
        """Get VAD statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        return {
            'total_chunks': self.total_chunks,
            'speech_chunks': self.speech_chunks,
            'speech_ratio': self.speech_chunks / self.total_chunks if self.total_chunks > 0 else 0
        }
