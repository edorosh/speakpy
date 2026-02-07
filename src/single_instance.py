"""Single instance application lock using Windows Named Mutex.

This module provides a mechanism to ensure only one instance of the application
can run at a time. It uses Windows Named Mutex which doesn't require admin rights.
"""

import sys
import logging

logger = logging.getLogger(__name__)


class SingleInstance:
    """Ensures only one instance of the application runs at a time.
    
    Uses Windows Named Mutex to create a system-wide lock. The mutex
    is automatically released when the application exits.
    
    Usage:
        # Method 1: Context manager (recommended)
        with SingleInstance():
            # Your application code here
            pass
        
        # Method 2: Manual management
        lock = SingleInstance()
        try:
            # Your application code here
            pass
        finally:
            lock.close()
    
    Raises:
        RuntimeError: If another instance is already running
    """
    
    def __init__(self, mutex_name: str = "Global\\SpeakPy_SingleInstance"):
        """Initialize the single instance lock.
        
        Args:
            mutex_name: Name of the mutex (default: Global\\SpeakPy_SingleInstance)
        
        Raises:
            RuntimeError: If another instance is already running
        """
        self.mutex_name = mutex_name
        self.mutex = None
        
        # Only available on Windows
        if sys.platform != 'win32':
            logger.warning("Single instance check is only supported on Windows")
            return
        
        try:
            import win32event
            import win32api
            import winerror
            
            # Try to create a named mutex
            self.mutex = win32event.CreateMutex(None, False, self.mutex_name)
            last_error = win32api.GetLastError()
            
            # Check if mutex already exists
            if last_error == winerror.ERROR_ALREADY_EXISTS:
                # Another instance is running
                logger.error("Another instance of SpeakPy is already running")
                if self.mutex:
                    win32api.CloseHandle(self.mutex)
                    self.mutex = None
                raise RuntimeError(
                    "Another instance of SpeakPy is already running.\n"
                    "Please close the existing instance before starting a new one.\n"
                    "Check your system tray for the running instance."
                )
            
            logger.info(f"Single instance lock acquired: {self.mutex_name}")
            
        except ImportError:
            logger.warning(
                "pywin32 not installed - single instance check disabled. "
                "Install with: pip install pywin32"
            )
        except Exception as e:
            logger.error(f"Failed to create single instance lock: {e}")
            raise
    
    def close(self):
        """Release the mutex lock."""
        if self.mutex:
            try:
                import win32api
                win32api.CloseHandle(self.mutex)
                logger.info("Single instance lock released")
            except Exception as e:
                logger.warning(f"Failed to release mutex: {e}")
            finally:
                self.mutex = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - release the mutex."""
        self.close()
        return False
    
    def __del__(self):
        """Destructor - ensure mutex is released."""
        self.close()
