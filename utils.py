import hashlib
import re
import logging
import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from config import Config

# Setup logging
logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    return hashlib.sha256((password + Config.PASSWORD_SALT).encode()).hexdigest()

def validate_email(email: str) -> bool:
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    pattern = r'^\+?1?\d{9,15}$'
    return bool(re.match(pattern, phone))

def validate_isbn(isbn: str) -> bool:
    isbn = isbn.replace('-', '').replace(' ', '')
    if len(isbn) == 10:
        # ISBN-10 validation logic
        total = sum((10 - i) * int(num) for i, num in enumerate(isbn[:-1]))
        check = 11 - (total % 11)
        check = 'X' if check == 10 else str(check % 11)
        return isbn[-1] == check
    elif len(isbn) == 13:
        # ISBN-13 validation logic
        total = sum((1 if i % 2 == 0 else 3) * int(num) for i, num in enumerate(isbn[:-1]))
        check = (10 - (total % 10)) % 10
        return isbn[-1] == str(check)
    else:
        return False

def create_loading_indicator(parent: tk.Widget) -> ttk.Label:
    """Create an animated loading indicator"""
    loading_frame = ttk.Frame(parent)
    loading_frame.pack(pady=20)
    
    dots = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    label = ttk.Label(loading_frame, 
                     text=dots[0],
                     font=('Segoe UI', 24))
    label.pack()
    
    def animate():
        current = label.cget("text")
        next_dot = dots[(dots.index(current) + 1) % len(dots)]
        label.configure(text=next_dot)
        parent.after(100, animate)
    
    animate()
    return loading_frame

def show_status_message(parent: tk.Widget, message: str, type_: str = "info") -> None:
    """Display improved status message with animation"""
    theme = Config.DARK_THEME if hasattr(parent, 'is_dark_mode') and parent.is_dark_mode.get() else Config.LIGHT_THEME
    
    # Create floating message frame
    frame = ttk.Frame(parent, style='Message.TFrame')
    frame.place(relx=1, rely=0, anchor='ne', x=-20, y=20)
    
    # Icon and color mapping
    icons = {
        "info": Config.ICONS['info'],
        "error": Config.ICONS['error'],
        "success": Config.ICONS['success'],
        "warning": Config.ICONS['warning']
    }
    
    colors = {
        "info": theme['button'],
        "error": Config.COLORS['error'],
        "success": Config.COLORS['success'],
        "warning": Config.COLORS['warning']
    }
    
    # Add icon
    ttk.Label(frame,
             text=icons.get(type_, icons['info']),
             font=('Segoe UI', 16)).pack(side=tk.LEFT, padx=5)
             
    # Add message text
    ttk.Label(frame,
             text=message,
             font=('Segoe UI', 11),
             foreground=colors.get(type_, theme['text'])).pack(side=tk.LEFT, padx=5)
    
    # Animation effect
    def fade_out():
        for alpha in range(100, 0, -2):
            frame.winfo_toplevel().attributes('-alpha', alpha/100)
            frame.update()
            frame.after(10)
        frame.destroy()
    
    # Fade out after 3 seconds
    parent.after(3000, fade_out)

def create_tooltip(widget: tk.Widget, text: str) -> None:
    """Create tooltip for widget"""
    tooltip = tk.Toplevel(widget)
    tooltip.withdraw()
    tooltip.overrideredirect(True)
    label = ttk.Label(tooltip, text=text, background="yellow", relief="solid", borderwidth=1)
    label.pack()

    def show_tooltip(event):
        tooltip.wm_geometry(f"+{event.x_root + 20}+{event.y_root}")
        tooltip.deiconify()

    def hide_tooltip(event):
        tooltip.withdraw()

    widget.bind("<Enter>", show_tooltip)
    widget.bind("<Leave>", hide_tooltip)

def create_table(parent: tk.Widget, data: List[Dict],
                 headers: Optional[List[str]] = None) -> ttk.Frame:
    """Create table to display data"""
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.BOTH, expand=True)

    if headers:
        for i, header in enumerate(headers):
            ttk.Label(frame, text=header, font=(Config.FONT_FAMILY, 10, "bold")).grid(row=0, column=i, padx=5, pady=5)
    for row_idx, row_data in enumerate(data, start=1):
        for col_idx, (key, value) in enumerate(row_data.items()):
            ttk.Label(frame, text=value).grid(row=row_idx, column=col_idx, padx=5, pady=5)

    return frame
