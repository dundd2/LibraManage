import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import List, Dict, Any, Optional
from config import Config
from database import DatabaseHandler 
from session import Session
from ui import LoginWindow
import sys

# Setup logging
logger = logging.getLogger(__name__)

# Handle optional dependencies
HAS_TTKTHEMES = False
try:
    from ttkthemes import ThemedTk
    HAS_TTKTHEMES = True
except ImportError:
    print("ttkthemes not installed")
    HAS_TTKTHEMES = False

def create_window() -> tk.Tk:
    """Create main window with fallback options and enhanced error handling
    
    Returns:
        tk.Tk: The created window instance
    
    Raises:
        RuntimeError: If window creation completely fails
    """
    root = None
    
    try:
        if HAS_TTKTHEMES:
            root = ThemedTk()
            try:
                root.set_theme("breeze")
                logger.info("Successfully created ThemedTk window")
            except Exception as theme_error:
                logger.warning(f"Theme setting failed: {theme_error}, using default theme")
    except Exception as e:
        logger.warning(f"ThemedTk error: {e}, falling back to Tk")
    
    if root is None:
        try:
            # Fallback to regular Tk
            root = tk.Tk()
            style = ttk.Style()
            style.theme_use('default')
        except Exception as tk_error:
            logger.error(f"Failed to create Tk window: {tk_error}")
            raise RuntimeError("Could not create application window") from tk_error
    
    if not isinstance(root, (tk.Tk, ThemedTk)):
        raise RuntimeError("Invalid window instance created")
        
    return root

def center_window(window: tk.Tk) -> None:
    """Center the window on screen with validation
    
    Args:
        window: The window to center
    """
    if not isinstance(window, tk.Tk):
        raise TypeError("Window must be a Tk instance")
        
    window.update_idletasks()
    width = max(min(window.winfo_width(), window.winfo_screenwidth()), 100)
    height = max(min(window.winfo_height(), window.winfo_screenheight()), 100)
    
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    if screen_width <= 0 or screen_height <= 0:
        logger.warning("Invalid screen dimensions detected")
        x, y = 0, 0
    else:
        x = max(0, (screen_width // 2) - (width // 2))
        y = max(0, (screen_height // 2) - (height // 2))
    
    window.geometry(f'+{x}+{y}')

def main() -> None:
    root = None
    db = None
    
    try:
        Config.setup_logging()
        root = create_window()
        
        # Initialize database with connection check
        db = DatabaseHandler()
        if not db.test_connection():
            raise RuntimeError("Database connection test failed")
        
        app = LoginWindow(root, db)
        center_window(root)
        
        def on_closing() -> None:
            if messagebox.askokcancel("Quit", "Do you want to quit?"):
                try:
                    if db is not None:
                        db.close()
                    root.quit()
                except Exception as e:
                    logger.error(f"Error during shutdown: {e}")
                    root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
        
    except Exception as e:
        logger.error(f"Program startup error: {e}")
        messagebox.showerror("Error", "Program startup failed, please check the log file")
        if db is not None:
            try:
                db.close()
            except Exception as close_error:
                logger.error(f"Error closing database: {close_error}")
        if root is not None:
            root.destroy()
        sys.exit(1)

if __name__ == "__main__":
    main()



