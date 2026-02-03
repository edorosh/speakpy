# SpeakPy

Audio recording to speech-to-text script using speaches.ai API. Record audio from your microphone, compress it with ffmpeg, and get instant transcriptions using a local speaches.ai instance.

## Features

- 🎤 **Audio Recording**: Record from any audio input device using sounddevice
- 🗜️ **Smart Compression**: Automatic silence removal and Opus encoding with ffmpeg
- 🚀 **Fast Transcription**: Uses speaches.ai (OpenAI-compatible API) with faster-whisper
- 💻 **Windows Compatible**: Works on Windows 11 without admin rights
- 📦 **Easy Management**: Uses modern `uv` package manager

## Requirements

- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- ffmpeg (installation instructions below)
- speaches.ai running locally (Docker)

## Installation

### 1. Install uv (if not already installed)

```powershell
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### 2. Clone/Download this project

```powershell
cd c:\dev\speakpy
```

### 3. Create virtual environment and install dependencies

```powershell
uv venv
.venv\Scripts\activate
uv pip install -e .
```

### 4. Install ffmpeg

**Option A: System Installation**
1. Download ffmpeg from [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
2. Choose "ffmpeg-release-essentials.zip"
3. Extract the archive
4. Add the `bin` folder to your system PATH

**Option B: Portable (No Admin Required)**
1. Download ffmpeg from the link above
2. Extract the archive
3. Create a `ffmpeg` folder in the project directory
4. Copy the `bin` folder into it
5. Your structure should be: `c:\dev\speakpy\ffmpeg\bin\ffmpeg.exe`

### 5. Start speaches.ai

Make sure your speaches.ai Docker container is running:

```powershell
docker run -d -p 8000:8000 ghcr.io/speaches-ai/speaches:latest
```

## Usage

### List Available Audio Devices

```powershell
python speakpy.py --list-devices
```

### Basic Recording and Transcription

```powershell
# Record from default microphone (press CTRL+C to stop)
python speakpy.py

# Record from specific device (use device index from --list-devices)
python speakpy.py --device 1
```

**Recording Control:**
- Press **CTRL+C once** to stop recording and proceed to transcription
- Press **CTRL+C twice** to exit the application immediately

### Advanced Options

```powershell
# Specify language for better accuracy
python speakpy.py --language en

# Use custom API endpoint
python speakpy.py --api-url http://192.168.1.100:8000

# Use different model
python speakpy.py --model "Systran/faster-whisper-medium"

# Enable verbose logging
python speakpy.py --verbose

# Keep temporary audio files for debugging
python speakpy.py --keep-files
```

### Full Command Reference

```
usage: speakpy.py [-h] [--list-devices] [--device DEVICE]
                  [--api-url API_URL] [--model MODEL] [--language LANGUAGE]
                  [--sample-rate SAMPLE_RATE] [--verbose] [--keep-files]

Arguments:
  --list-devices          List available audio input devices and exit
  --device DEVICE         Audio input device index
  --api-url API_URL       Speaches.ai API base URL (default: http://localhost:8000)
  --model MODEL           Model to use for transcription
  --language LANGUAGE     Language code (e.g., 'en', 'es')
  --sample-rate RATE      Recording sample rate in Hz (default: 44100)
  --verbose               Enable verbose logging
  --keep-files            Keep temporary audio files for debugging
```

## How It Works

1. **Recording**: Captures audio from your microphone using the sounddevice library
2. **Compression**: Processes audio with ffmpeg:
   - Removes silence at the beginning
   - Converts to 16kHz mono
   - Encodes with Opus codec at 32kbps for minimal file size
3. **Transcription**: Sends compressed audio to speaches.ai API
4. **Results**: Displays the transcription in your console

## Troubleshooting

### "ffmpeg is not available"
- Make sure ffmpeg is installed and in your PATH
- Or place ffmpeg in the `ffmpeg/bin/` directory within the project
- Run `ffmpeg -version` to verify installation

### "Could not connect to speaches.ai"
- Check if Docker container is running: `docker ps`
- Verify port 8000 is accessible: `curl http://localhost:8000/docs`
- Make sure you're using the correct API URL

### "No input devices found"
- Check if your microphone is connected and enabled
- Try listing devices: `python speakpy.py --list-devices`
- Check Windows sound settings

### Poor transcription quality
- Ensure good microphone quality and minimal background noise
- Try specifying the language: `--language en`
- Record for longer (speak more before pressing CTRL+C) for better context
- Check if the correct audio device is selected

## Project Structure

```
speakpy/
├── speakpy.py              # Main CLI script
├── pyproject.toml          # Project configuration
├── README.md               # This file
├── src/
│   ├── __init__.py
│   ├── audio_recorder.py   # Audio recording with sounddevice
│   ├── audio_compressor.py # FFmpeg compression
│   ├── api_client.py       # Speaches.ai API client
│   └── utils.py            # Helper functions
└── ffmpeg/                 # Optional: portable ffmpeg
    └── bin/
        └── ffmpeg.exe
```

## Credits

- [speaches.ai](https://github.com/speaches-ai/speaches) - OpenAI-compatible STT/TTS server
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Fast transcription engine
- [sounddevice](https://python-sounddevice.readthedocs.io/) - Audio I/O library
- Compression technique inspired by [Epicenter](https://github.com/EpicenterHQ/epicenter)

## License

This project is free to use and modify.
