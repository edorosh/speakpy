# SpeakPy

Audio recording to speech-to-text script using speaches.ai API. Record audio from your microphone, compress it with ffmpeg, and get instant transcriptions using a local speaches.ai instance.

## Features

- 🎤 **Audio Recording**: Record from any audio input device using sounddevice
- 🖥️ **GUI & CLI Modes**: Choose between graphical interface or command-line interface
- 🎙️ **Voice Activity Detection (VAD)**: Optional filtering using Silero VAD with dynamic GUI controls
- 🗜️ **Smart Compression**: Automatic silence removal and Opus encoding with ffmpeg
- 🚀 **Fast Transcription**: Uses speaches.ai (OpenAI-compatible API) with faster-whisper
- 🎛️ **Editable Model Selection**: Change the transcription model on-the-fly in the GUI
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

### GUI Mode (Recommended for Windows)

Launch the graphical interface:

```powershell
# Start with visible window
python speakpy_gui.py

# Start minimized to system tray
python speakpy_gui.py --tray
```

The GUI provides:
- **Simple Interface**: Click "Start Recording" button to begin, "Stop Recording" to finish
- **Live Activity Log**: See real-time feedback about recording and processing status
- **Transcription Display**: View transcription results in a dedicated text area
- **Copy to Clipboard**: One-click button to copy transcription text
- **Auto-Paste**: Automatically paste transcribed text into other applications (no admin rights required)
- **System Tray Integration**: Minimize to tray, control from system tray icon
- **Global Hotkey**: Press Ctrl+Shift+; to toggle recording from anywhere
- **Status Indicators**: Visual feedback showing current application state (Ready/Recording/Processing)

**GUI Controls:**
- Click **Start Recording** to begin capturing audio
- Speak clearly into your microphone
- Click **Stop Recording** when finished
- Wait for processing and transcription to complete
- Use **Copy to Clipboard** to copy the transcription text
- Enable **Auto copy to clipboard** checkbox to automatically paste text into focused applications
- Use **Clear** to reset the transcription area
- **Model Selection**: Edit the model field to change the transcription model (takes effect on next recording)
- **Enable VAD Filtering**: Checkbox to toggle Voice Activity Detection (silence filtering) for the next recording
- **VAD Threshold**: Slider to adjust detection sensitivity (0.0-1.0) on-the-fly

**Window Management:**
- **Close (X) Button**: Exits the application completely
- **Minimize (-) Button**: Hides window to system tray (keeps running in background)
- **System Tray Icon**: Right-click for menu options:
  - Show Window: Restore the main window
  - Start Recording: Toggle recording from tray
  - Exit: Close the application
- **Global Hotkey**: Press **Ctrl+Shift+;** anywhere to toggle recording (even when minimized)

**Auto-Paste Feature:**
When the "Auto copy to clipboard" checkbox is enabled, transcribed text will automatically:
1. Copy to clipboard
2. Simulate Ctrl+V keypress after 150ms
3. Paste into whichever application has keyboard focus (e.g., Notepad, browser, Word)

This works **without admin rights** using standard keyboard input simulation.

### Command-Line Mode

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
# Enable Voice Activity Detection (only record speech, skip silence)
# In GUI mode, this sets the checkbox to Checked by default
python speakpy.py --vad

# Adjust VAD sensitivity (lower = more sensitive)
# In GUI mode, this sets the default slider position
python speakpy.py --vad --vad-threshold 0.3

# Specify language for better accuracy
python speakpy.py --language en

# Combine VAD with language specification
python speakpy.py --vad --language en

# Use custom API endpoint
python speakpy.py --api-url http://192.168.1.100:8000

# Use different model
python speakpy.py --model "Systran/faster-whisper-medium"

# Enable verbose logging
python speakpy.py --verbose

# Keep temporary audio files for debugging
python speakpy.py --keep-files
```

### Voice Activity Detection (VAD)

The `--vad` flag enables real-time voice activity detection to record only when you're speaking:

- **Automatic Silence Removal**: Skips silent segments during recording
- **Real-time Feedback**: Shows "🎤 Speech detected..." or "⏸️ Silence..." status
- **Smaller Files**: Output contains only speech, reducing file size
- **Adjustable Sensitivity**: Use `--vad-threshold` (0.0-1.0) to tune detection
  - Lower values (0.2-0.4): More sensitive, catches quieter speech
  - Default (0.5): Balanced for normal speaking
  - Higher values (0.6-0.8): Less sensitive, filters more aggressively

**Note**: VAD requires PyTorch (~200MB). Install with:
```powershell
uv pip install torch
```

### Full Command Reference

```
usage: speakpy.py [-h] [--list-devices] [--device DEVICE]
                  [--api-url API_URL] [--model MODEL] [--language LANGUAGE]
                  [--sample-rate SAMPLE_RATE] [--verbose] [--keep-files]
                  [--vad] [--vad-threshold VAD_THRESHOLD]

Arguments:
  --list-devices          List available audio input devices and exit
  --device DEVICE         Audio input device index
  --api-url API_URL       Speaches.ai API base URL (default: http://localhost:8000)
  --model MODEL           Model to use for transcription
  --language LANGUAGE     Language code (e.g., 'en', 'es')
  --sample-rate RATE      Recording sample rate in Hz (default: 44100)
  --verbose               Enable verbose logging
  --keep-files            Keep temporary audio files for debugging
  --vad                   Enable Voice Activity Detection
  --vad-threshold THRESH  VAD sensitivity 0.0-1.0 (default: 0.5)
```

## How It Works

1. **Recording**: Captures audio from your microphone using the sounddevice library
2. **VAD (Optional)**: Detects and filters voice activity in real-time using Silero VAD
3. **Compression**: Processes audio with ffmpeg:
   - Removes silence at the beginning
   - Converts to 16kHz mono
   - Encodes with Opus codec at 32kbps for minimal file size
4. **Transcription**: Sends compressed audio to speaches.ai API
5. **Results**: Displays the transcription in your console

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
├── speakpy_gui.py          # GUI entry point
├── pyproject.toml          # Project configuration
├── README.md               # This file
├── src/
│   ├── __init__.py
│   ├── audio_recorder.py   # Audio recording with sounddevice
│   ├── audio_compressor.py # FFmpeg compression
│   ├── api_client.py       # Speaches.ai API client
│   ├── vad_processor.py    # Voice Activity Detection (Silero VAD)
│   ├── gui.py              # GUI components (tkinter)
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
