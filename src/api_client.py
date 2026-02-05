"""API client for speaches.ai speech-to-text service."""

import logging
import requests
import time
from typing import Optional, Dict, Any
from pathlib import Path

# import http.client
# http.client.HTTPConnection.debuglevel = 1

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

        # You must initialize logging, otherwise you'll not see debug output.
        # logging.basicConfig()
        # logging.getLogger().setLevel(logging.DEBUG)
        # requests_log = logging.getLogger("requests.packages.urllib3")
        # requests_log.setLevel(logging.DEBUG)
        # requests_log.propagate = True

        self.base_url = base_url.rstrip('/')
        self.model = model
        self.transcription_endpoint = f"{self.base_url}/v1/audio/transcriptions"
        
        # Use persistent session for connection pooling
        self.session = requests.Session()
        
        # Add curl-like headers for better compatibility
        self.session.headers.update({
            'User-Agent': 'speakpy/1.0',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
    
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
            start_time = time.time()
            file_size = Path(audio_file_path).stat().st_size / 1024  # KB
            logger.info(f"Sending audio to speaches.ai API: {self.transcription_endpoint}")
            logger.info(f"File size: {file_size:.2f} KB")
            logger.debug(f"Using model: {self.model}")
            
            # Prepare the multipart form data
            upload_start = time.time()
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
                logger.debug(f"Upload prepared in {time.time() - upload_start:.2f}s")
                request_start = time.time()
                response = self.session.post(
                    self.transcription_endpoint,
                    files=files,
                    data=data,
                    # timeout=15
                )
            
            request_time = time.time() - request_start
            logger.debug(f"API request completed in {request_time:.2f}s")
            
            # Check response status
            if response.status_code != 200:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                raise RuntimeError(
                    f"API request failed with status {response.status_code}: {response.text}"
                )
            
            # Parse response
            if response_format == "json":
                result = response.json()
                total_time = time.time() - start_time
                logger.info(f"Transcription completed successfully (total: {total_time:.2f}s, request: {request_time:.2f}s)")
                return result
            else:
                # For text/srt/vtt formats, return as text
                total_time = time.time() - start_time
                logger.info(f"Transcription completed successfully (total: {total_time:.2f}s, request: {request_time:.2f}s)")
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
            response = self.session.get(f"{self.base_url}/health", timeout=1)
            return response.status_code == 200
        except:
            try:
                # Fallback: try the docs endpoint
                response = self.session.get(f"{self.base_url}/docs", timeout=1)
                return response.status_code == 200
            except:
                return False
