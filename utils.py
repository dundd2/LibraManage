import hashlib
import re
import logging
import tkinter as tk
from tkinter import ttk, messagebox  # Added messagebox import
from typing import Optional, List, Dict, Union
from datetime import datetime, timedelta
from config import Config
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Setup logging
logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """
    Hash a password using Argon2, which is currently the most secure password hashing algorithm.
    Argon2 won the Password Hashing Competition in 2015 and is recommended by cryptography experts.
    
    Args:
        password: The password to hash
        
    Returns:
        The hashed password as a string
    """
    ph = PasswordHasher()
    return ph.hash(password)

def verify_password(password: str, hash: str) -> bool:
    """
    Verify a password against its hash using Argon2
    
    Args:
        password: The password to verify
        hash: The hash to verify against
        
    Returns:
        True if the password matches the hash, False otherwise
    """
    ph = PasswordHasher()
    try:
        ph.verify(hash, password)
        return True
    except VerifyMismatchError:
        return False

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
    """Create a loading indicator label"""
    label = ttk.Label(parent, text="Loading...", font=('Segoe UI', 10))
    label.pack(pady=10)
    return label

def show_status_message(parent: Union[tk.Widget, tk.Tk, tk.Toplevel], message: str, type_: str = "info") -> None:
    """Show a status message with the given type (info, error, warning, success)"""
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

def create_tooltip(widget: tk.Widget, text: str) -> None:
    """Create a tooltip for a widget"""
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
