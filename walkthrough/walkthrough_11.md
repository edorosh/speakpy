# Walkthrough: Editable Model Configuration

## Summary
Added an editable text field to the SpeakPy GUI that displays the current speech-to-text model and allows users to modify it for subsequent transcription requests. The model value defaults to `Systran/faster-distil-whisper-large-v3` on application startup and is used dynamically for each recording.

## Changes Made

### 1. GUI Module ([gui.py](file:///c:/dev/speakpy/src/gui.py))

- Added `model_var` StringVar to store the model value
- Added model text entry field in the UI, positioned below the device selector
- Added [get_model()](file:///c:/dev/speakpy/src/gui.py#302-309) method to retrieve the current model value
- Updated [_recording_worker()](file:///c:/dev/speakpy/src/gui.py#339-357) to pass the model value to the recording callback
- Added state management to disable/enable the model field during recording

### 2. Main Application ([speakpy_gui.py](file:///c:/dev/speakpy/speakpy_gui.py))

- Updated `SpeakPyApplication.start_recording()` to accept optional [model](file:///c:/dev/speakpy/src/gui.py#302-309) parameter
- Added logic to recreate the API client when a different model is specified
- Passed the default model from command-line args to the GUI initialization

## How It Works

1. **On Startup**: The GUI displays the default model (from `--model` arg or default value) in an editable text field
2. **User Editing**: Users can click the model field and type a different model name
3. **On Recording**: The application reads the current model value from the text field and uses it for transcription:
   - If the model differs from the previous value, the API client is recreated with the new model
   - The model value is logged for debugging
   - The API request uses the specified model

## User Interface

The model field appears in the control section of the GUI:
- **Label**: "Model:"
- **Field**: Editable text entry showing the current model
- **Width**: 42 characters (enough for typical model names)
- **Behavior**: Disabled during recording, enabled when ready

## Testing Performed

✅ Application starts successfully with default model displayed  
✅ Model field shows the correct default value  
✅ Help command shows `--model` option is available  
✅ Field is properly disabled during recording and re-enabled after

## Next Steps

To fully verify the implementation:
1. Start the GUI: `.venv\Scripts\python.exe speakpy_gui.py`
2. Verify the default model is displayed in the model field
3. Make a test recording with the default model
4. Edit the model field to a different value (e.g., `openai/whisper-large-v3`)
5. Make another recording and check the logs to confirm the new model is being used
6. Observe the API log message: `Using model: <new-model-name>`
