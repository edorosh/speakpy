# Dynamic VAD Toggle Feature

I have added a dynamic Voice Activity Detection (VAD) toggle to the SpeakPy GUI, allowing you to enable/disable silence filtering and adjust sensitivity on the fly.

## Changes

### GUI Enhancements
- **VAD Checkbox**: Added "Enable VAD Filtering" checkbox to the control panel.
- **VAD Threshold Slider**: Added a slider to adjust VAD sensitivity (0.0 to 1.0) with a live value display.
- **Dynamic State**: VAD settings are read from the GUI each time you start recording.

### Application Logic updates
- **On-Demand Initialization**: VAD is no longer initialized at startup. It is initialized only when you enable it and start recording.
- **Resource Management**: VAD resources are properly managed and released when switching between VAD and non-VAD modes.

## How to Use

1. **Launch the Application**:
   ```powershell
   python speakpy_gui.py
   ```
   (You can still use `--vad` flag to set the default state to enabled)

2. **Enable VAD**:
   - Check the **"Enable VAD Filtering"** box.
   - Adjust the **"VAD Threshold"** slider if needed (default is 0.5).
     - **Lower values (e.g., 0.3)**: More sensitive, captures quieter speech.
     - **Higher values (e.g., 0.8)**: Stricter, filters more noise/silence.

3. **Start Recording**:
   - Click **"Start Recording"** or press `Ctrl+Shift+;`.
   - If VAD is enabled, the console (and logs) will show "🎤 Recording with VAD filtering...".
   - If disabled, it will record everything continuously.

## Verification Results

Verified the logic with a test script:
- [x] When VAD is **disabled**: Recording starts immediately without initializing VAD processor.
- [x] When VAD is **enabled**: VAD processor detects speech based on the selected threshold.
- [x] **Switching**: You can toggle VAD on/off between recordings without restarting the app.
