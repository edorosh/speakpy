"""API client for speaches.ai speech-to-text service."""

import logging
import requests
from typing import Optional, Dict, Any
from pathlib import Path


logger = logging.getLogger(__name__)


class SpeachesClient:
    """Client for interacting with speaches.ai API."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        model: str = "Systran/faster-distil-whisper-large-v3"
    ):
        """Initialize the speaches.ai API client.
        
        Args:
            base_url: Base URL of the speaches.ai server
            model: Model name to use for transcription
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.transcription_endpoint = f"{self.base_url}/v1/audio/transcriptions"
    
    def transcribe(
        self,
        audio_file_path: str,
        language: Optional[str] = None,
        response_format: str = "json"
    ) -> Dict[str, Any]:
        """Transcribe an audio file using the speaches.ai API.
        
        Args:
            audio_file_path: Path to the audio file to transcribe
            language: Optional language code (e.g., 'en', 'es')
            response_format: Response format ('json', 'text', 'srt', 'vtt')
            
        Returns:
            Dictionary containing transcription results
            
        Raises:
            RuntimeError: If the API request fails
        """
        try:
            logger.info(f"Sending audio to speaches.ai API: {self.transcription_endpoint}")
            logger.debug(f"Using model: {self.model}")
            
            # Prepare the multipart form data
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': (Path(audio_file_path).name, audio_file, 'audio/opus')
                }
                
                data = {
                    'model': self.model,
                    'response_format': response_format
                }
                
                if language:
                    data['language'] = language
                
                # Make the API request
                response = requests.post(
                    self.transcription_endpoint,
                    files=files,
                    data=data,
                    timeout=30
                )
            
            # Check response status
            if response.status_code != 200:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                raise RuntimeError(
                    f"API request failed with status {response.status_code}: {response.text}"
                )
            
            # Parse response
            if response_format == "json":
                result = response.json()
                logger.info("Transcription completed successfully")
                return result
            else:
                # For text/srt/vtt formats, return as text
                return {"text": response.text}
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to speaches.ai API: {e}")
            raise RuntimeError(
                f"Could not connect to speaches.ai at {self.base_url}. "
                "Please ensure the Docker container is running on port 8000."
            )
        except requests.exceptions.Timeout as e:
            logger.error(f"API request timed out: {e}")
            raise RuntimeError("API request timed out. The audio file may be too large.")
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            raise RuntimeError(f"Transcription failed: {e}")
    
    def check_health(self) -> bool:
        """Check if the speaches.ai API is available.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Try to reach the base URL
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            try:
                # Fallback: try the docs endpoint
                response = requests.get(f"{self.base_url}/docs", timeout=5)
                return response.status_code == 200
            except:
                return False
