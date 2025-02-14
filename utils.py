import hashlib
import re
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict, Union
from datetime import datetime, timedelta
from config import Config
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, HashingError

# Setup logging
logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """Hash a password using Argon2"""
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    if not password:
        raise ValueError("Password cannot be empty")
        
    try:
        ph = PasswordHasher()
        return ph.hash(password)
    except HashingError as e:
        logger.error(f"Failed to hash password: {str(e)}")
        raise

def verify_password(password: str, hash: str) -> bool:
    """Verify a password against its hash"""
    if not isinstance(password, str) or not isinstance(hash, str):
        raise TypeError("Password and hash must be strings")
    if not password or not hash:
        raise ValueError("Password and hash cannot be empty")

    try:
        ph = PasswordHasher()
        return ph.verify(hash, password)
    except Exception as e:
        logger.error(f"Password verification failed: {str(e)}")
        return False

def validate_email(email: str) -> bool:
    if not isinstance(email, str):
        raise TypeError("Email must be a string")
    if not email:
        return False
    
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    if not isinstance(phone, str):
        raise TypeError("Phone must be a string")
    if not phone:
        return False
    
    pattern = r'^\+?1?\d{9,15}$'
    return bool(re.match(pattern, phone))

def validate_isbn(isbn: str) -> bool:
    if not isinstance(isbn, str):
        raise TypeError("ISBN must be a string")
    if not isbn:
        return False
    
    try:
        isbn = isbn.replace('-', '').replace(' ', '')
        if not isbn.replace('X', '').isdigit():
            return False
            
        if len(isbn) == 10:
            total = sum((10 - i) * int(num) for i, num in enumerate(isbn[:-1]))
            check = 11 - (total % 11)
            check = 'X' if check == 10 else str(check % 11)
            return isbn[-1] == check
        elif len(isbn) == 13:
            total = sum((1 if i % 2 == 0 else 3) * int(num) for i, num in enumerate(isbn[:-1]))
            check = (10 - (total % 10)) % 10
            return isbn[-1] == str(check)
        else:
            return False
    except Exception as e:
        logger.error(f"ISBN validation failed: {str(e)}")
        return False

def create_loading_indicator(parent: tk.Widget) -> ttk.Label:
    if not isinstance(parent, tk.Widget):
        raise TypeError("Parent must be a tkinter Widget")
        
    try:
        label = ttk.Label(parent, text="Loading...", font=('Segoe UI', 10))
        label.pack(pady=10)
        return label
    except Exception as e:
        logger.error(f"Failed to create loading indicator: {str(e)}")
        raise

def show_status_message(parent: Union[tk.Widget, tk.Tk, tk.Toplevel], 
                       message: str, type_: str = "info") -> None:
    if not isinstance(message, str):
        raise TypeError("Message must be a string")
    if not isinstance(type_, str):
        raise TypeError("Type must be a string")
    if type_ not in ["info", "error", "warning", "success"]:
        raise ValueError("Invalid message type")

    try:
        colors = {
            "info": "#3498db",
            "error": "#e74c3c",
            "warning": "#f39c12",
            "success": "#2ecc71"
        }
        
        msg = messagebox.showinfo if type_ == "info" else \
              messagebox.showerror if type_ == "error" else \
              messagebox.showwarning if type_ == "warning" else \
              messagebox.showinfo
        
        msg(type_.title(), message)
    except Exception as e:
        logger.error(f"Failed to show status message: {str(e)}")
        raise

def create_tooltip(widget: tk.Widget, text: str) -> None:
    if not isinstance(widget, tk.Widget):
        raise TypeError("Widget must be a tkinter Widget")
    if not isinstance(text, str):
        raise TypeError("Text must be a string")
    if not text:
        raise ValueError("Tooltip text cannot be empty")

    try:
        tooltip = tk.Toplevel()
        tooltip.withdraw()
        tooltip.overrideredirect(True)
        
        label = ttk.Label(tooltip, text=text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack()
        
        def enter(event):
            tooltip.deiconify()
            x = widget.winfo_rootx() + widget.winfo_width()
            y = widget.winfo_rooty()
            tooltip.geometry(f"+{x}+{y}")
            
        def leave(event):
            tooltip.withdraw()
            
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)
    except Exception as e:
        logger.error(f"Failed to create tooltip: {str(e)}")
        raise

def create_table(parent: tk.Widget, data: List[Dict],
                 headers: Optional[List[str]] = None) -> ttk.Frame:
    if not isinstance(parent, tk.Widget):
        raise TypeError("Parent must be a tkinter Widget")
    if not isinstance(data, list):
        raise TypeError("Data must be a list of dictionaries")
    if headers is not None and not isinstance(headers, list):
        raise TypeError("Headers must be a list of strings")
    if not data:
        raise ValueError("Data cannot be empty")
    if headers and not all(isinstance(h, str) for h in headers):
        raise TypeError("All headers must be strings")

    try:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)

        if headers:
            for i, header in enumerate(headers):
                ttk.Label(frame, text=header, 
                         font=(Config.FONT_FAMILY, 10, "bold")).grid(
                             row=0, column=i, padx=5, pady=5)
        for row_idx, row_data in enumerate(data, start=1):
            if not isinstance(row_data, dict):
                raise TypeError(f"Row {row_idx} is not a dictionary")
            for col_idx, (key, value) in enumerate(row_data.items()):
                ttk.Label(frame, text=str(value)).grid(
                    row=row_idx, column=col_idx, padx=5, pady=5)

        return frame
    except Exception as e:
        logger.error(f"Failed to create table: {str(e)}")
        raise
