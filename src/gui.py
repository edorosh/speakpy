"""GUI module for speakpy application using tkinter."""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import logging
import queue
from typing import Optional, Callable
import sys


class TextHandler(logging.Handler):
    """Custom logging handler that redirects logs to a text widget."""
    
    def __init__(self, text_widget):
        """Initialize the handler.
        
        Args:
            text_widget: tkinter Text widget to write logs to
        """
        super().__init__()
        self.text_widget = text_widget
        self.queue = queue.Queue()
        
    def emit(self, record):
        """Emit a log record to the queue."""
        msg = self.format(record)
        self.queue.put(msg)


class SpeakPyGUI:
    """Main GUI application for SpeakPy."""
    
    def __init__(self, root: tk.Tk, recording_callback: Callable, stop_callback: Callable, devices: list, start_in_tray: bool = False):
        """Initialize the GUI.
        
        Args:
            root: tkinter root window
            recording_callback: Function to call when starting recording
            stop_callback: Function to call when stopping recording
            devices: List of available audio input devices
            start_in_tray: Start minimized to system tray
        """
        self.root = root
        self.recording_callback = recording_callback
        self.stop_callback = stop_callback
        self.is_recording = False
        self.recording_thread: Optional[threading.Thread] = None
        self.auto_copy = tk.BooleanVar(value=False)
        self.devices = devices
        self.device_var = tk.StringVar()
        self.start_in_tray = start_in_tray
        self.tray_icon = None
        self.is_visible = not start_in_tray
        
        # Configure root window
        self.root.title("SpeakPy - Voice Recorder & Transcription")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Setup GUI components
        self._setup_ui()
        
        # Setup logging redirection
        self._setup_logging()
        
        # Start queue polling
        self._poll_log_queue()
        
        # Setup system tray
        self._setup_tray()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Start hidden if requested
        if self.start_in_tray:
            self.root.withdraw()
            self.is_visible = False
    
    def _setup_ui(self):
        """Setup all UI components."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=2)  # Log area
        main_frame.rowconfigure(3, weight=3)  # Transcription area
        
        # Title and status
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        title_frame.columnconfigure(1, weight=1)
        
        title_label = ttk.Label(
            title_frame,
            text="🎤 SpeakPy Voice Recorder",
            font=("Segoe UI", 14, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Hotkey hint
        hotkey_label = ttk.Label(
            title_frame,
            text="Hotkey: Ctrl+Shift+;",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        hotkey_label.grid(row=1, column=0, sticky=tk.W)
        
        self.status_label = ttk.Label(
            title_frame,
            text="Ready",
            font=("Segoe UI", 10),
            foreground="green"
        )
        self.status_label.grid(row=0, column=1, sticky=tk.E)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=0, column=0, sticky=tk.E, pady=(0, 10))
        
        self.record_button = ttk.Button(
            button_frame,
            text="▶ Start Recording",
            command=self._toggle_recording,
            width=20
        )
        self.record_button.grid(row=0, column=0, padx=5)
        
        # Device selector
        device_label = ttk.Label(button_frame, text="Input Device:")
        device_label.grid(row=0, column=1, padx=(15, 5))
        
        # Populate device dropdown
        device_names = []
        default_index = 0
        for i, device in enumerate(self.devices):
            device_names.append(device['name'])
            if device.get('is_default', False):
                default_index = i
        
        self.device_dropdown = ttk.Combobox(
            button_frame,
            textvariable=self.device_var,
            values=device_names,
            state='readonly',
            width=40
        )
        self.device_dropdown.grid(row=0, column=2, padx=5)
        
        # Set default device
        if device_names:
            self.device_dropdown.current(default_index)
        
        # Log section
        log_label = ttk.Label(main_frame, text="Activity Log:", font=("Segoe UI", 10, "bold"))
        log_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 2))
        
        # Log text widget with scrollbar
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=8,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Transcription section
        transcription_label = ttk.Label(
            main_frame,
            text="Transcription Result:",
            font=("Segoe UI", 10, "bold")
        )
        transcription_label.grid(row=3, column=0, sticky=tk.W, pady=(5, 2))
        
        # Transcription text widget with scrollbar
        transcription_frame = ttk.Frame(main_frame)
        transcription_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        transcription_frame.columnconfigure(0, weight=1)
        transcription_frame.rowconfigure(0, weight=1)
        
        self.transcription_text = scrolledtext.ScrolledText(
            transcription_frame,
            height=10,
            wrap=tk.WORD,
            font=("Segoe UI", 11)
        )
        self.transcription_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Copy button
        button_bottom_frame = ttk.Frame(main_frame)
        button_bottom_frame.grid(row=5, column=0, sticky=tk.E)
        
        self.copy_button = ttk.Button(
            button_bottom_frame,
            text="📋 Copy to Clipboard",
            command=self._copy_to_clipboard,
            state=tk.DISABLED
        )
        self.copy_button.grid(row=0, column=0, padx=5)
        
        self.clear_button = ttk.Button(
            button_bottom_frame,
            text="🗑 Clear",
            command=self._clear_transcription
        )
        self.clear_button.grid(row=0, column=1, padx=5)
        
        self.auto_copy_checkbox = ttk.Checkbutton(
            button_bottom_frame,
            text="Auto copy to clipboard",
            variable=self.auto_copy
        )
        self.auto_copy_checkbox.grid(row=0, column=2, padx=5)
    
    def _setup_logging(self):
        """Setup logging to redirect to GUI text widget."""
        # Create custom handler
        self.text_handler = TextHandler(self.log_text)
        self.text_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')
        )
        
        # Add handler to root logger
        logging.getLogger().addHandler(self.text_handler)
        
        # Redirect stdout to log widget (for print statements)
        sys.stdout = LogRedirector(self.log_text, self.text_handler.queue)
    
    def _poll_log_queue(self):
        """Poll the log queue and update the text widget."""
        while True:
            try:
                msg = self.text_handler.queue.get_nowait()
                self._append_log(msg)
            except queue.Empty:
                break
        
        # Schedule next poll
        self.root.after(100, self._poll_log_queue)
    
    def _append_log(self, message: str):
        """Append a message to the log text widget.
        
        Args:
            message: Message to append
        """
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _toggle_recording(self):
        """Toggle between start and stop recording."""
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()
    
    def get_selected_device_index(self) -> Optional[int]:
        """Get the index of the selected device.
        
        Returns:
            Device index or None if default should be used
        """
        try:
            device_name = self.device_var.get()
            for device in self.devices:
                if device['name'] == device_name:
                    return device['index']
        except Exception as e:
            logger.error(f"Error getting device index: {e}")
        return None
    
    def _start_recording(self):
        """Start recording in a separate thread."""
        self.is_recording = True
        self.record_button.config(text="⏹ Stop Recording", style="Accent.TButton")
        self.status_label.config(text="Recording...", foreground="red")
        self.copy_button.config(state=tk.DISABLED)
        self.device_dropdown.config(state=tk.DISABLED)
        
        # Clear previous transcription
        self.transcription_text.delete(1.0, tk.END)
        
        # Show toast notification
        self._show_notification("Recording Started", "Speak now to record audio")
        
        # Start recording in separate thread
        self.recording_thread = threading.Thread(
            target=self._recording_worker,
            daemon=True
        )
        self.recording_thread.start()
    
    def _stop_recording(self):
        """Stop the current recording."""
        if self.is_recording and self.stop_callback:
            self.status_label.config(text="Stopping...", foreground="orange")
            self._show_notification("Recording Stopped", "Processing audio...")
            self.stop_callback()
    
    def _recording_worker(self):
        """Worker function that runs in the recording thread."""
        try:
            # Get selected device
            device_index = self.get_selected_device_index()
            
            # Call the recording callback with device
            result = self.recording_callback(device_index)
            
            # Update UI on main thread
            self.root.after(0, self._recording_complete, result)
            
        except Exception as e:
            logging.error(f"Recording error: {e}")
            self.root.after(0, self._recording_error, str(e))
    
    def _recording_complete(self, result: dict):
        """Handle recording completion.
        
        Args:
            result: Transcription result dictionary
        """
        self.is_recording = False
        self.record_button.config(text="▶ Start Recording", style="")
        self.status_label.config(text="Ready", foreground="green")
        self.device_dropdown.config(state='readonly')
        
        # Display transcription
        if result and "text" in result:
            self.transcription_text.delete(1.0, tk.END)
            self.transcription_text.insert(1.0, result["text"])
            self.copy_button.config(state=tk.NORMAL)
            
            # Show notification with preview
            preview = result["text"][:100] + "..." if len(result["text"]) > 100 else result["text"]
            self._show_notification("Transcription Complete", preview)
            
            # Auto-copy if enabled
            if self.auto_copy.get():
                self._copy_to_clipboard()
        elif result:
            self.transcription_text.delete(1.0, tk.END)
            self.transcription_text.insert(1.0, str(result))
            self.copy_button.config(state=tk.NORMAL)
            # Auto-copy if enabled
            if self.auto_copy.get():
                self._copy_to_clipboard()
    
    def _recording_error(self, error_msg: str):
        """Handle recording error.
        
        Args:
            error_msg: Error message to display
        """
        self.is_recording = False
        self.record_button.config(text="▶ Start Recording", style="")
        self.status_label.config(text="Error", foreground="red")
        self.device_dropdown.config(state='readonly')
        messagebox.showerror("Recording Error", f"An error occurred:\n{error_msg}")
    
    def _copy_to_clipboard(self):
        """Copy transcription text to clipboard."""
        text = self.transcription_text.get(1.0, tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            
            # Auto-paste if enabled
            if self.auto_copy.get():
                self.status_label.config(text="Copied and pasting...", foreground="blue")
                # Delay paste slightly to ensure clipboard is ready
                self.root.after(150, self._auto_paste)
            else:
                self.status_label.config(text="Copied to clipboard!", foreground="blue")
                self.root.after(2000, lambda: self.status_label.config(text="Ready", foreground="green"))
    
    def _auto_paste(self):
        """Automatically paste the clipboard content using keyboard simulation.
        
        This simulates Ctrl+V keypress to paste into the currently focused application.
        Works without admin rights on Windows.
        """
        try:
            from pynput.keyboard import Controller, Key
            
            # Create keyboard controller
            keyboard = Controller()
            
            # Simulate Ctrl+V
            keyboard.press(Key.ctrl)
            keyboard.press('v')
            keyboard.release('v')
            keyboard.release(Key.ctrl)
            
            # Update status
            self.status_label.config(text="Copied and pasted!", foreground="blue")
            self.root.after(2000, lambda: self.status_label.config(text="Ready", foreground="green"))
            
            logging.debug("Auto-paste completed successfully")
            
        except Exception as e:
            logging.error(f"Auto-paste failed: {e}")
            self.status_label.config(text="Copied (paste failed)", foreground="orange")
            self.root.after(2000, lambda: self.status_label.config(text="Ready", foreground="green"))
    
    def _clear_transcription(self):
        """Clear the transcription text area."""
        self.transcription_text.delete(1.0, tk.END)
        self.copy_button.config(state=tk.DISABLED)
    
    def _setup_tray(self):
        """Setup system tray icon."""
        try:
            import pystray
            
            # Get icon from speakpy_gui module
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            import speakpy_gui
            
            # Create icon dynamically
            icon_image = speakpy_gui.create_tray_icon()
            
            # Create menu
            menu = pystray.Menu(
                pystray.MenuItem("Show Window", self._show_window, default=True),
                pystray.MenuItem("Start Recording", self._tray_toggle_recording),
                pystray.MenuItem("Exit", self._tray_exit)
            )
            
            # Create tray icon
            self.tray_icon = pystray.Icon(
                "SpeakPy",
                icon_image,
                "SpeakPy Voice Recorder",
                menu
            )
            
            # Start tray in separate thread
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            
        except Exception as e:
            logging.error(f"Failed to setup system tray: {e}")
    
    def _show_window(self, icon=None, item=None):
        """Show the main window (thread-safe)."""
        self.root.after(0, self._do_show_window)
    
    def _do_show_window(self):
        """Actually show the window (must run in main thread)."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.is_visible = True
    
    def _hide_window(self):
        """Hide window to tray."""
        self.root.withdraw()
        self.is_visible = False
    
    def _tray_toggle_recording(self, icon=None, item=None):
        """Toggle recording from tray menu (thread-safe)."""
        self.root.after(0, self._toggle_recording)
    
    def _tray_exit(self, icon=None, item=None):
        """Exit application from tray."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)
    
    def _on_closing(self):
        """Handle window close event."""
        if self.is_recording:
            if messagebox.askokcancel("Quit", "Recording in progress. Do you want to quit?"):
                self._stop_recording()
                self._hide_window()
        else:
            # Minimize to tray instead of closing
            self._hide_window()
    
    def _show_notification(self, title: str, message: str):
        """Show a Windows toast notification.
        
        Args:
            title: Notification title
            message: Notification message
        """
        try:
            from winotify import Notification
            
            toast = Notification(
                app_id="SpeakPy",
                title=title,
                msg=message,
                duration="short"
            )
            toast.show()
        except Exception as e:
            logging.debug(f"Failed to show notification: {e}")
    
    def run(self):
        """Start the GUI main loop."""
        self.root.mainloop()


class LogRedirector:
    """Redirect stdout/stderr to log queue."""
    
    def __init__(self, text_widget, log_queue):
        """Initialize the redirector.
        
        Args:
            text_widget: tkinter Text widget
            log_queue: Queue to write messages to
        """
        self.text_widget = text_widget
        self.log_queue = log_queue
        self.buffer = ""
    
    def write(self, message):
        """Write message to queue."""
        if message and message.strip():
            # Clean up emoji-based messages for better log appearance
            clean_msg = message.strip()
            self.log_queue.put(clean_msg)
    
    def flush(self):
        """Flush buffer (required for file-like objects)."""
        pass
