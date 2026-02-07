# Single Instance Check Implementation

Successfully implemented single instance checking to prevent multiple SpeakPy application instances from running simultaneously, eliminating duplicate system tray icons.

## Changes Made

### New Module: [single_instance.py](file:///c:/dev/speakpy/src/single_instance.py)

Created a robust single instance lock mechanism using Windows Named Mutex:

- **Technology**: Uses `pywin32` library for Windows Native API access
- **Mutex name**: `Global\SpeakPy_SingleInstance` (system-wide scope)
- **No admin rights required**: Named mutex operates at user level
- **Auto-cleanup**: Implements context manager protocol and destructor for automatic mutex release
- **Error handling**: Provides clear error messages when second instance is attempted

Key features:
- Detects `ERROR_ALREADY_EXISTS` error code (183) when mutex already exists
- Raises `RuntimeError` with user-friendly message
- Automatically releases mutex on application exit
- Supports both context manager and manual usage patterns

### Updated: [pyproject.toml](file:///c:/dev/speakpy/pyproject.toml)

Added `pywin32>=306` dependency for Windows mutex support.

### Updated: [speakpy_gui.py](file:///c:/dev/speakpy/speakpy_gui.py)

Integrated single instance check into the main entry point:

- **Import**: Added [SingleInstance](file:///c:/dev/speakpy/src/single_instance.py#13-111) class import
- **Early check**: Single instance check executes before any GUI initialization
- **Error handling**: Catches `RuntimeError` and displays clear error message to stderr
- **Exit code**: Returns exit code 1 when second instance is detected
- **Cleanup**: Properly releases mutex in finally block when application exits

## Verification Results

### ✅ Test 1: First Instance Launch

**Command**: `uv run speakpy_gui.py --tray`

**Result**: SUCCESS
- Application launched successfully
- System tray icon appeared
- Mutex acquired without errors
- Log message: "Single instance lock acquired"

### ✅ Test 2: Second Instance Prevention

**Command**: `uv run speakpy_gui.py` (while first instance running)

**Result**: SUCCESS - Second instance was blocked
- Second instance detected existing mutex
- Clear error message displayed:
  ```
  ❌ Error: Another instance of SpeakPy is already running.
  Please close the existing instance before starting a new one.
  Check your system tray for the running instance.
  ```
- Second instance exited with code 1
- Only ONE system tray icon remained visible
- First instance continued running normally

### ✅ Test 3: Mutex Cleanup and Restart

**Steps**:
1. Terminated first instance
2. Waited for cleanup
3. Launched new instance: `uv run speakpy_gui.py --tray`

**Result**: SUCCESS
- First instance released mutex on exit
- Log message: "Single instance lock released"
- New instance started successfully
- No "already running" error
- Mutex was properly cleaned up

## Technical Details

### Implementation Approach

The implementation uses Windows Named Mutex, which provides:

1. **System-wide locking**: Prevents instances across all processes
2. **No admin rights**: Operates at user privilege level
3. **Automatic cleanup**: OS releases mutex when process terminates
4. **Race condition safety**: Atomic mutex creation check

### Error Detection

```python
mutex = win32event.CreateMutex(None, False, mutex_name)
last_error = win32api.GetLastError()

if last_error == winerror.ERROR_ALREADY_EXISTS:
    # Another instance is running
    raise RuntimeError("Another instance is already running")
```

### Cleanup Strategy

Multiple cleanup mechanisms ensure mutex is always released:

1. **Explicit cleanup**: `instance_lock.close()` in finally block
2. **Context manager**: [__exit__](file:///c:/dev/speakpy/src/single_instance.py#103-107) method
3. **Destructor**: [__del__](file:///c:/dev/speakpy/src/single_instance.py#108-111) method as final safety net
4. **OS cleanup**: Windows automatically releases on process termination

## Summary

The single instance check is fully functional and working as expected:

- ✅ Prevents multiple instances from running
- ✅ No admin rights required
- ✅ Clear error messaging for users
- ✅ Proper mutex cleanup on exit
- ✅ Allows restart after previous instance exits
- ✅ No duplicate system tray icons possible
