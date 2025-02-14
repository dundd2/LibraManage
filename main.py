import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import List, Dict, Any
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

def create_window():
    """Create main window with fallback options"""
    try:
        if HAS_TTKTHEMES:
            root = ThemedTk()
            root.set_theme("breeze")
            logger.info("Successfully created ThemedTk window")
            return root
    except Exception as e:
        logger.warning(f"ThemedTk error: {e}, falling back to Tk")
    
    # Fallback to regular Tk
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('default')
    return root

def main():
    try:
        Config.setup_logging()
        
        # Create main window with better error handling
        root = create_window()
        
        # Initialize database connection
        db = DatabaseHandler()
        
        # Create and display login window
        app = LoginWindow(root, db)
        
        # Center the window
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'+{x}+{y}')
        
        # Setup clean shutdown
        def on_closing():
            if messagebox.askokcancel("Quit", "Do you want to quit?"):
                root.quit()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
        
    except Exception as e:
        logger.error(f"Program startup error: {e}")
        messagebox.showerror("Error", "Program startup failed, please check the log file")
        sys.exit(1)

if __name__ == "__main__":
    main()



