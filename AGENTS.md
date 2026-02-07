# SpeakPy - AI Coding Agent Instructions

> **Prerequisites**: Before modifying this codebase, read [README.md](README.md) for project overview, installation, usage, and troubleshooting. This file contains **only agent-specific technical implementation details** not found in README or source code docstrings.

## Agent Guidelines

**DO NOT duplicate information that is:**
- Already documented in [README.md](README.md) (features, installation, usage)
- Available in source code docstrings and comments
- Basic Python or library usage patterns

**DO focus on:**
- Non-obvious design decisions and their rationale
- Critical implementation constraints that aren't immediately apparent
- Common pitfalls specific to this codebase's architecture
- Thread-safety and concurrency patterns unique to this project

---

## Critical Design Decisions

1. **Streaming VAD Architecture**: [StreamingVAD](src/vad_processor.py) class buffers audio chunks in real-time and filters out silence *during* recording (not post-processing). This reduces final file size before ffmpeg compression.

2. **FFmpeg Portable Support**: [AudioCompressor](src/audio_compressor.py) checks both system PATH and local `ffmpeg/bin/ffmpeg.exe` to work without admin rights on Windows. Always preserve this dual lookup in `_find_ffmpeg()`.

3. **Threading in GUI**: Recording runs in a separate thread ([speakpy_gui.py](speakpy_gui.py#L165)) to prevent UI freezing. Use `threading.Event` for stop signals, never block the main tkinter loop.

4. **API Health Checks**: [SpeachesClient.check_health()](src/api_client.py#L98) tries `/health` then falls back to `/docs`. Always verify API availability before recording to provide early user feedback.

5. **Single Instance Locking**: [SingleInstance](src/single_instance.py) uses a Windows Named Mutex (`Global\SpeakPy_SingleInstance`) to prevent multiple application instances. This avoids conflicts with audio devices and system tray icons. It's checked immediately in `main()` before GUI creation.

---

## Critical Implementation Constraints

### Audio Processing Pipeline

1. **Recording format**: Always 44100 Hz, float32, mono (converted to int16 for WAV)
2. **VAD requires 16000 Hz**: [VADProcessor](src/vad_processor.py#L16) resamples internally if needed
3. **FFmpeg compression params** (from Epicenter project):
   - Silence removal: `silenceremove=start_periods=1:start_duration=0.1:start_threshold=-50dB`
   - Output: Opus codec @ 32kbps, 16kHz mono
   - These are hardcoded in [FFMPEG_FILTERS](src/audio_compressor.py#L18) - only change with careful testing

### Error Handling Patterns

- **Raise RuntimeError** for user-facing errors (missing ffmpeg, API failures)
- **Graceful degradation**: If API health check fails, log warning but continue ([speakpy_gui.py](speakpy_gui.py#L71))

### GUI-Specific Patterns

- **Log redirection**: [TextHandler](src/gui.py#L13) uses a queue to safely write logs from worker threads to tkinter Text widget
- **State management**: `self.is_recording` flag prevents concurrent recordings; always check before starting new thread
- **Clipboard integration**: GUI provides one-click copy via `self.root.clipboard_clear()` + `clipboard_append()`

---

## Modification Guidelines

### Adding New Features

**To add a new transcription model:**

- Modify `--model` default in [speakpy_gui.py](speakpy_gui.py#L33)
- Update README examples

**To support new audio formats:**

- Extend [AudioCompressor.FFMPEG_CODEC_ARGS](src/audio_compressor.py#L22) for codec changes
- Test with different API file MIME types in [api_client.py](src/api_client.py#L48)

**To add GUI features:**

- Follow tkinter grid layout in [_setup_ui()](src/gui.py#L65) with proper weight configuration
- Always use thread-safe queue for logging, never direct writes to Text widgets from threads

**After implementing a new feature:**

- Write a walkthrough markdown file in the `walkthrough/` folder (e.g., `walkthrough_NN.md`) documenting the changes, usage instructions, and verification steps. Use the next sequential number for the filename.

---

## Development Workflow

### Virtual Environment

**CRITICAL**: Always initialize the virtual environment before running Python commands.

- **Windows**: `.venv\Scripts\Activate.ps1` (PowerShell) or `.venv\Scripts\activate.bat` (CMD)
- **Linux/macOS**: `source .venv/bin/activate`

This ensures:
1. Dependencies match the project's requirements.txt
2. No conflicts with system-wide Python packages
3. Consistent behavior across different development environments

**Before running any Python script** (speakpy_gui.py, tests), verify the virtual environment is active by checking for `(.venv)` prefix in your shell prompt.

---

## Common Pitfalls

1. **VAD sample rate mismatch**: VAD expects 16kHz but recorder uses 44.1kHz. [VADProcessor.resample_audio()](src/vad_processor.py#L88) handles this - don't bypass it.
2. **FFmpeg path on Windows**: Use `Path` objects and check both system PATH + local directory. Never assume ffmpeg.exe is in PATH.
3. **Empty recordings with VAD**: If no speech detected, [StreamingVAD.get_speech_audio()](src/vad_processor.py#L169) returns `None` - handle this in [record_until_stopped()](src/audio_recorder.py#L123).
4. **API timeout**: Default is commented out in [api_client.py](src/api_client.py#L54) to allow large files - re-enable carefully.

---

## Debugging Strategies

- Use `--verbose` flag to enable DEBUG logging for all modules
- Enable `--keep-files` to inspect intermediate WAV and Opus files in temp directory
- Check `docker logs <container_id>` for speaches.ai API errors
- GUI logs appear in Activity Log widget; console logs with timestamps

---

*For project overview, installation, and usage instructions, see [README.md](README.md).*
