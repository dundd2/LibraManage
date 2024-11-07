import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List
import time
import logging
from config import Config
from database import DatabaseHandler 
from session import Session  
from utils import (
    hash_password, validate_email, validate_phone, 
    validate_isbn, create_loading_indicator,
    show_status_message, create_tooltip
)
import subprocess
from matplotlib.figure import Figure

# Setup logging
Config.setup_logging()
logger = logging.getLogger(__name__)

# Handle optional dependencies
HAS_TTKTHEMES = False
try:
    from ttkthemes import ThemedTk, ThemedStyle
    HAS_TTKTHEMES = True
except ImportError:
    print("Installing ttkthemes...")
    try:
        subprocess.check_call(["pip", "install", "ttkthemes"])
        from ttkthemes import ThemedTk, ThemedStyle
        HAS_TTKTHEMES = True
    except Exception as e:
        print(f"Failed to install ttkthemes: {e}")
        HAS_TTKTHEMES = False

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    print("Installing matplotlib and pandas...")
    subprocess.check_call(["pip", "install", "matplotlib", "pandas"])
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class LoginWindow:
    def __init__(self, root: tk.Tk, db: DatabaseHandler):
        self.root = root
        self.db = db
        self.setup_login_window()

    def setup_login_window(self) -> None:
        self.root.title("Library Management System - Login")
        self.root.geometry("400x500")  # Taller window for better spacing
        
        # Apply theme
        self.root.configure(bg=Config.LIGHT_THEME['background'])
        
        # Create main frame with padding and rounded corners
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo/Icon (replace with your actual logo)
        logo_label = ttk.Label(main_frame, 
                             text="📚",
                             font=('Segoe UI', 48))
        logo_label.pack(pady=20)
        
        # Title with improved typography
        title_label = ttk.Label(main_frame, 
                               text="Welcome Back",
                               font=Config.STYLES['title']['font'])
        title_label.pack(pady=10)
        
        subtitle_label = ttk.Label(main_frame,
                                 text="Sign in to continue",
                                 font=Config.STYLES['subtitle']['font'])
        subtitle_label.pack(pady=(0, 20))
        
        # Login form with better spacing and style
        login_frame = ttk.Frame(main_frame)
        login_frame.pack(fill=tk.X, pady=10)
        
        # Username field with icon
        username_frame = ttk.Frame(login_frame)
        username_frame.pack(fill=tk.X, pady=5)
        ttk.Label(username_frame, text="👤").pack(side=tk.LEFT, padx=5)
        self.username = tk.StringVar()
        ttk.Entry(username_frame, 
                 textvariable=self.username,
                 font=Config.STYLES['entry']['font'],
                 width=30).pack(side=tk.LEFT, padx=5)
        
        # Password field with icon
        password_frame = ttk.Frame(login_frame)
        password_frame.pack(fill=tk.X, pady=5)
        ttk.Label(password_frame, text="🔒").pack(side=tk.LEFT, padx=5)
        self.password = tk.StringVar()
        ttk.Entry(password_frame,
                 textvariable=self.password,
                 show="•",
                 font=Config.STYLES['entry']['font'],
                 width=30).pack(side=tk.LEFT, padx=5)
        
        # Login button with hover effect
        login_button = ttk.Button(main_frame,
                                text="Sign In",
                                command=self.login,
                                style='Accent.TButton',
                                width=20)
        login_button.pack(pady=20)

    def login(self) -> None:
        username = self.username.get().strip()
        password = self.password.get()

        if not all([username, password]):
            show_status_message(self.root, "Please fill in all fields.", "error")
            return

        try:
            password_hash = hash_password(password)
            user = self.db.authenticate_user(username, password_hash)
            
            if user:
                logger.info(f"User {username} logged in successfully")
                main_window = MainWindow(self.root, self.db, Session(user))
                self.root.withdraw()
            else:
                logger.warning(f"Failed login attempt for user {username}")
                show_status_message(self.root, "Invalid username or password.", "error")

        except Exception as e:
            logger.error(f"Login error: {e}")
            show_status_message(self.root, "An error occurred during login.", "error")

class MainWindow:
    def __init__(self, root: tk.Tk, db: DatabaseHandler, session: Session):
        self.root = tk.Toplevel(root)  # Use Toplevel instead of the passed root
        self.db = db
        self.session = session
        self.is_dark_mode = tk.BooleanVar(value=False)
        self.content_frame = None
        
        # Set window size and title
        self.root.geometry("1200x800")
        self.root.title("Library Management System")
        
        # Ensure the entire application exits when the main window is closed
        self.root.protocol("WM_DELETE_WINDOW", root.destroy)
        
        # Initialize the interface
        self.setup_theme()
        self.setup_main_window()
        
        # Center the window
        self.center_window()

    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')

    def setup_theme(self) -> None:
        # Apply theme based on dark mode setting
        theme = Config.DARK_THEME if self.is_dark_mode.get() else Config.LIGHT_THEME
        
        if HAS_TTKTHEMES:
            self.style = ThemedStyle(self.root)
            self.style.set_theme("equilux" if self.is_dark_mode.get() else "breeze")
        else:
            self.style = ttk.Style(self.root)
        
        # Configure colors
        self.root.configure(bg=theme['background'])
        
        # Configure base styles
        self.style.configure('TFrame', background=theme['background'])
        self.style.configure('TLabel', 
                           background=theme['background'],
                           foreground=theme['text'])
        
        # Configure button style
        self.style.configure('TButton',
                           background=theme['button'],
                           foreground=theme['button_text'])
        
        # Configure custom styles
        self.style.configure('Sidebar.TFrame', 
                           background=theme['sidebar'])
        self.style.configure('Card.TFrame',
                           background=theme['card'],
                           relief='solid',
                           borderwidth=1)
        
        # Configure Accent button style
        self.style.configure('Accent.TButton',
                           background=theme['button'],
                           foreground=theme['button_text'],
                           padding=Config.STYLES['button']['padding'],
                           font=Config.STYLES['button']['font'])
        
        # Configure hover effects
        self.style.map('Accent.TButton',
                      background=[('active', theme['button'])])
        
        # Configure Entry style
        self.style.configure('TEntry',
                           fieldbackground=theme['surface'],
                           foreground=theme['text'],
                           padding=Config.STYLES['entry']['padding'])

    def setup_main_window(self) -> None:
        self.root.title("Library Management System")
        self.root.geometry("1200x800")
        
        # Add theme toggle button
        theme_btn = ttk.Button(
            self.root, 
            text="Toggle Theme",
            command=self.toggle_theme
        )
        theme_btn.pack(side=tk.TOP, anchor=tk.NE, padx=10, pady=5)
        
        # Create main container with improved styling
        self.main_container = ttk.Frame(self.root, style='TFrame')
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create sidebar with improved styling
        self.sidebar = ttk.Frame(self.main_container, style='Sidebar.TFrame')
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Create content area with improved styling
        self.content_area = ttk.Frame(self.main_container, style='TFrame')
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize content frame
        self.content_frame = ttk.Frame(self.content_area, style='TFrame')
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.setup_sidebar()
        self.show_dashboard()  # Show default view
        self.setup_custom_styles()

    def toggle_theme(self) -> None:
        self.is_dark_mode.set(not self.is_dark_mode.get())
        self.setup_theme()
        # Refresh current view
        self.show_dashboard()

    def setup_sidebar(self) -> None:
        # Add logo/title with improved styling
        title_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        title_frame.pack(fill=tk.X, pady=20, padx=10)
        
        ttk.Label(title_frame, 
                 text="Library System",
                 font=(Config.FONT_FAMILY, 16, "bold"),
                 foreground=Config.DARK_THEME['text'] if self.is_dark_mode.get() else Config.LIGHT_THEME['text'],
                 background=Config.DARK_THEME['sidebar'] if self.is_dark_mode.get() else Config.LIGHT_THEME['sidebar']
                ).pack()
        
        # Sidebar buttons with improved styling
        buttons = [
            ("📊 Dashboard", self.show_dashboard),
            ("📚 Books", self.show_books),
            ("➕ Add Book", self.show_add_book),
            ("👥 Members", self.show_members),
            ("➕ Add Member", self.show_add_member),
            ("📋 Issue Book", self.show_issue_book),
            ("↩️ Return Book", self.show_return_book),
        ]
        
        for text, command in buttons:
            btn = ttk.Button(self.sidebar, 
                           text=text, 
                           command=command,
                           style='Sidebar.TButton',
                           width=20)
            btn.pack(pady=5, padx=10)
            
            # Add hover effect
            self.add_button_hover_effect(btn)

    def add_button_hover_effect(self, button: ttk.Button) -> None:
        """Hover effect is handled by style.map, this method can be empty or removed"""
        pass

    def show_dashboard(self) -> None:
        self.clear_content()
        
        # Welcome message with card style
        welcome_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        welcome_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Label(welcome_frame,
                 text=f"Welcome back, {self.session.get_user().get('username')}!",
                 font=(Config.FONT_FAMILY, 20, 'bold'),
                 style='Card.TLabel').pack(padx=20, pady=20)

        # Statistics cards
        stats_frame = ttk.Frame(self.content_frame)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        try:
            stats = [
                ("Diverse editions books", self.db.get_total_books()),
                ("Total Available Books quantity", self.db.get_available_books()),
                ("Total Members", self.db.get_total_members()),
                ("Active Loans", self.db.get_active_loans())
            ]
            
            for title, value in stats:
                card = self.create_stat_card(stats_frame, title, value)
                card.pack(side=tk.LEFT, padx=10, pady=10, expand=True)
                
        except Exception as e:
            logger.error(f"Error loading dashboard stats: {e}")
            ttk.Label(stats_frame, 
                     text="Error loading statistics",
                     foreground=Config.THEME_COLORS['error']).pack()

    def show_books(self) -> None:
        self.clear_content()
        
        # Title
        title_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Label(title_frame, 
                 text="Book List",
                 font=(Config.FONT_FAMILY, 20, 'bold'),
                 style='Card.TLabel').pack(padx=20, pady=20)

        # Search frame
        search_frame = ttk.Frame(self.content_frame)
        search_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, 
                               textvariable=self.search_var,
                               width=40)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        # Search button
        ttk.Button(search_frame, 
                  text="Search",
                  command=self.search_books).pack(side=tk.LEFT, padx=5)
        
        # Results frame
        self.table_frame = ttk.Frame(self.content_frame)
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # Create table headers
        headers = ['Title', 'Author', 'ISBN', 'Available', 'Actions']
        for i, header in enumerate(headers):
            ttk.Label(self.table_frame, text=header,
                     font=(Config.FONT_FAMILY, 12, "bold")).grid(
                row=0, column=i, padx=10, pady=5, sticky='w')

        # Display all books initially
        self.display_books()

    def display_books(self) -> None:
        """Display all books in the table"""
        try:
            # Clear previous data (keep headers)
            for widget in self.table_frame.winfo_children():
                if type(widget) is not ttk.Label or widget.grid_info()['row'] != 0:
                    widget.destroy()

            # Get all books from the database
            books = self.db.get_all_books()
            
            # Display book data
            for i, book in enumerate(books, 1):
                # Title
                ttk.Label(self.table_frame, text=book['title']).grid(
                    row=i, column=0, padx=5, pady=2, sticky='w')
                    
                # Author
                ttk.Label(self.table_frame, text=book['author']).grid(
                    row=i, column=1, padx=5, pady=2, sticky='w')
                    
                # ISBN
                ttk.Label(self.table_frame, text=book['isbn']).grid(
                    row=i, column=2, padx=5, pady=2, sticky='w')
                    
                # Available quantity
                ttk.Label(self.table_frame, text=str(book['available'])).grid(
                    row=i, column=3, padx=5, pady=2, sticky='w')
                
                # Action buttons container
                action_frame = ttk.Frame(self.table_frame)
                action_frame.grid(row=i, column=4, padx=5, pady=2)
                
                # Details button
                ttk.Button(action_frame,
                          text="Details",
                          command=lambda b=book: self.show_book_details(b)).pack(
                              side=tk.LEFT, padx=2)
                              
                # Edit button
                ttk.Button(action_frame,
                          text="Edit",
                          command=lambda b=book: self.edit_book(b)).pack(
                              side=tk.LEFT, padx=2)

        except Exception as e:
            logger.error(f"Error displaying books: {e}")
            show_status_message(self.root, "Failed to display books.", "error")

    def search_books(self) -> None:
        # Clear previous results except headers
        for widget in self.table_frame.winfo_children():
            if type(widget) is not ttk.Label or widget.grid_info()['row'] != 0:
                widget.destroy()

        query = self.search_var.get()
        try:
            results = self.db.search_books(query, self.current_page)
            for i, book in enumerate(results, 1):
                ttk.Label(self.table_frame, text=book['title']).grid(
                    row=i, column=0, padx=5, pady=2)
                ttk.Label(self.table_frame, text=book['author']).grid(
                    row=i, column=1, padx=5, pady=2)
                ttk.Label(self.table_frame, text=book['isbn']).grid(
                    row=i, column=2, padx=5, pady=2)
                ttk.Label(self.table_frame, text=str(book['available'])).grid(
                    row=i, column=3, padx=5, pady=2)
                
                # Actions frame
                actions_frame = ttk.Frame(self.table_frame)
                actions_frame.grid(row=i, column=4, padx=5, pady=2)
                
                ttk.Button(actions_frame,
                          text="Details",
                          command=lambda b=book: self.show_book_details(b)).pack(
                              side=tk.LEFT, padx=2)
                ttk.Button(actions_frame,
                          text="Edit",
                          command=lambda b=book: self.edit_book(b)).pack(
                              side=tk.LEFT, padx=2)

        except Exception as e:
            logger.error(f"Search error: {e}")
            show_status_message(self.content_frame, 
                              "Search failed", 
                              "error")

    def show_book_details(self, book: Dict[str, Any]) -> None:
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Book Details - {book['title']}")
        details_window.geometry("600x400")
        
        # Apply theme
        details_window.configure(bg=Config.THEME_COLORS['background'])
        
        # Content
        content = ttk.Frame(details_window)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Book info
        info_frame = ttk.Frame(content, style='Card.TFrame')
        info_frame.pack(fill=tk.X, pady=10)
        
        fields = [
            ('Title:', book['title']),
            ('Author:', book['author']),
            ('ISBN:', book['isbn']),
            ('Available:', str(book['available'])),
            ('Total Copies:', str(book['quantity'])),
            ('Category:', book.get('category', 'N/A')),
            ('Added Date:', book.get('added_date', 'N/A'))
        ]
        
        for i, (label, value) in enumerate(fields):
            ttk.Label(info_frame, text=label,
                     font=(Config.FONT_FAMILY, 10, 'bold')).grid(
                         row=i, column=0, padx=10, pady=5, sticky='e')
            ttk.Label(info_frame, text=value).grid(
                row=i, column=1, padx=10, pady=5, sticky='w')

        # Loan history
        history_frame = ttk.Frame(content)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(history_frame, text="Loan History",
                 font=(Config.FONT_FAMILY, 12, 'bold')).pack(pady=5)
        
        history = self.db.get_book_loan_history(book['isbn'])
        self.create_table(history_frame, history)

    def check_session(self) -> None:
        if not self.session.is_valid():
            messagebox.showwarning("Session Expired", "Please login again")
            self.root.destroy()

    def add_book(self) -> None:
        try:
            # Validate inputs
            title = self.book_entries['Title:'].get().strip()
            author = self.book_entries['Author:'].get().strip()
            isbn = self.book_entries['ISBN:'].get().strip()
            quantity = self.book_entries['Quantity:'].get().strip()

            if not all([title, author, isbn, quantity]):
                raise ValueError("All fields are required!")

            if not validate_isbn(isbn):
                raise ValueError("Invalid ISBN format!")

            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive!")

            # Add to database (implementation in DatabaseHandler)
            self.db.add_book(title, author, isbn, quantity)
            messagebox.showinfo("Success", "Book added successfully!")
            self.clear_entries()

        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            logger.error(f"Error adding book: {e}")
            messagebox.showerror("Error", "An error occurred while adding the book")

    def clear_entries(self) -> None:
        """Clear all entry fields in the current form"""
        for entry in self.book_entries.values():
            entry.delete(0, tk.END)

    def show_add_member(self) -> None:
        """Display add member form"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.content_frame, text="Add New Member", 
                 font=('Helvetica', 16, 'bold')).pack(pady=10)

        form_frame = ttk.Frame(self.content_frame)
        form_frame.pack(pady=20)

        labels = ['Name:', 'Email:', 'Phone:']
        self.member_entries = {}

        for i, label in enumerate(labels):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, pady=5, padx=5)
            entry = ttk.Entry(form_frame, width=40)
            entry.grid(row=i, column=1, pady=5, padx=5)
            self.member_entries[label] = entry

        ttk.Button(form_frame, text="Add Member", 
                  command=self.add_member).grid(row=len(labels), 
                                              column=0, 
                                              columnspan=2, 
                                              pady=20)

    def add_member(self) -> None:
        """Handle adding a new member"""
        try:
            name = self.member_entries['Name:'].get().strip()
            email = self.member_entries['Email:'].get().strip()
            phone = self.member_entries['Phone:'].get().strip()

            if not all([name, email, phone]):
                raise ValueError("All fields are required!")

            if not validate_email(email):
                raise ValueError("Invalid email format!")

            if not validate_phone(phone):
                raise ValueError("Invalid phone format!")

            self.db.add_member(name, email, phone)
            messagebox.showinfo("Success", "Member added successfully!")
            self.clear_member_entries()

        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            logger.error(f"Error adding member: {e}")
            messagebox.showerror("Error", "Failed to add member")

    def show_issue_book(self) -> None:
        """Display book issue form"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.content_frame, text="Issue Book", 
                 font=('Helvetica', 16, 'bold')).pack(pady=10)

        form_frame = ttk.Frame(self.content_frame)
        form_frame.pack(pady=20)

        ttk.Label(form_frame, text="Member ID:").grid(row=0, column=0, pady=5, padx=5)
        self.member_id_entry = ttk.Entry(form_frame, width=40)
        self.member_id_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(form_frame, text="Book ISBN:").grid(row=1, column=0, pady=5, padx=5)
        self.book_isbn_entry = ttk.Entry(form_frame, width=40)
        self.book_isbn_entry.grid(row=1, column=1, pady=5, padx=5)

        ttk.Button(form_frame, text="Issue Book", 
                  command=self.issue_book).grid(row=2, column=0, columnspan=2, pady=20)

    def issue_book(self) -> None:
        """Handle issuing a book to a member"""
        try:
            member_id = self.member_id_entry.get().strip()
            isbn = self.book_isbn_entry.get().strip()

            if not all([member_id, isbn]):
                raise ValueError("All fields are required!")

            if not validate_isbn(isbn):
                raise ValueError("Invalid ISBN format!")

            self.db.issue_book(int(member_id), isbn)
            messagebox.showinfo("Success", "Book issued successfully!")
            self.member_id_entry.delete(0, tk.END)
            self.book_isbn_entry.delete(0, tk.END)

        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            logger.error(f"Error issuing book: {e}")
            messagebox.showerror("Error", "Failed to issue book")

    def previous_page(self) -> None:
        """Handle pagination - previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.search_books()

    def next_page(self) -> None:
        """Handle pagination - next page"""
        self.current_page += 1
        self.search_books()

    def clear_member_entries(self) -> None:
        """Clear all member form entries"""
        for entry in self.member_entries.values():
            entry.delete(0, tk.END)

    def set_status(self, message: str) -> None:
        """Update status bar message"""
        self.status_label.config(text=message)
        
    def show_loading(self) -> None:
        """Show loading overlay"""
        self.loading = ttk.Frame(self.root)
        self.loading.place(relx=0.5, rely=0.5, anchor='center')
        ttk.Label(self.loading, text="Loading...",
                 font=(Config.FONT_FAMILY, 14)).pack()
        self.root.update()

    def hide_loading(self) -> None:
        """Hide loading overlay"""
        if hasattr(self, 'loading'):
            self.loading.destroy()

    def show_add_book(self) -> None:
        self.clear_content()
        
        # Title with card style
        title_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Label(title_frame, 
                 text="Add New Book",
                 font=(Config.FONT_FAMILY, 20, 'bold'),
                 style='Card.TLabel').pack(padx=20, pady=20)

        # Form frame with card style
        form_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        form_frame.pack(padx=20, pady=10, fill=tk.X)
        
        # Book details input fields
        labels = ['Title:', 'Author:', 'ISBN:', 'Quantity:']
        self.book_entries = {}
        
        for i, label in enumerate(labels):
            # Label
            ttk.Label(form_frame, 
                     text=label,
                     font=(Config.FONT_FAMILY, 12)).grid(
                row=i, column=0, pady=10, padx=20, sticky='e')
            
            # Entry
            entry = ttk.Entry(form_frame, width=40)
            entry.grid(row=i, column=1, pady=10, padx=20, sticky='w')
            self.book_entries[label] = entry
        
        # Add button with improved styling
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=len(labels), column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, 
                  text="Add Book",
                  command=self.add_book,
                  style='Accent.TButton').pack(pady=10)

    def show_members(self) -> None:
        self.clear_content()
        
        # Title
        title_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Label(title_frame, 
                 text="Member List",
                 font=(Config.FONT_FAMILY, 20, 'bold'),
                 style='Card.TLabel').pack(padx=20, pady=20)

        # Search frame
        search_frame = ttk.Frame(self.content_frame)
        search_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side=tk.LEFT, padx=5)

        # Table frame
        table_frame = ttk.Frame(self.content_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Headers
        headers = ['ID', 'Name', 'Email', 'Phone', 'Join Date', 'Actions']
        for i, header in enumerate(headers):
            ttk.Label(table_frame, 
                     text=header,
                     font=(Config.FONT_FAMILY, 10, 'bold')).grid(
                row=0, column=i, padx=5, pady=5, sticky='w')

        try:
            # Get member data
            members = self.db.get_all_members()
            
            # Display members
            for i, member in enumerate(members, 1):
                ttk.Label(table_frame, text=str(member['id'])).grid(
                    row=i, column=0, padx=5, pady=2)
                ttk.Label(table_frame, text=member['name']).grid(
                    row=i, column=1, padx=5, pady=2)
                ttk.Label(table_frame, text=member['email']).grid(
                    row=i, column=2, padx=5, pady=2)
                ttk.Label(table_frame, text=member['phone']).grid(
                    row=i, column=3, padx=5, pady=2)
                ttk.Label(table_frame, text=member['join_date']).grid(
                    row=i, column=4, padx=5, pady=2)
                
                # Action buttons
                action_frame = ttk.Frame(table_frame)
                action_frame.grid(row=i, column=5, padx=5, pady=2)
                
                ttk.Button(action_frame, 
                          text="Edit",
                          command=lambda m=member: self.edit_member(m)).pack(
                              side=tk.LEFT, padx=2)
                ttk.Button(action_frame,
                          text="Delete",
                          command=lambda m=member: self.delete_member(m)).pack(
                              side=tk.LEFT, padx=2)

        except Exception as e:
            logger.error(f"Error displaying members: {e}")
            show_status_message(self.content_frame, 
                              "Error loading members", 
                              "error")

    def show_return_book(self) -> None:
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create return book form
        ttk.Label(self.content_frame, text="Return Book", 
                 font=('Helvetica', 16, 'bold')).pack(pady=10)
        
        form_frame = ttk.Frame(self.content_frame)
        form_frame.pack(pady=20)
        
        # Return book input fields
        labels = ['Member ID:', 'Book ISBN:']
        self.return_entries = {}
        
        for i, label in enumerate(labels):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, pady=5, padx=5)
            entry = ttk.Entry(form_frame, width=40)
            entry.grid(row=i, column=1, pady=5, padx=5)
            self.return_entries[label] = entry
        
        ttk.Button(form_frame, text="Return Book", 
                  command=self.return_book).grid(row=len(labels), 
                                               column=0, 
                                               columnspan=2, 
                                               pady=20)
    
    def return_book(self) -> None:
        """Handle book return"""
        try:
            member_id = self.return_entries['Member ID:'].get().strip()
            isbn = self.return_entries['Book ISBN:'].get().strip()
    
            if not all([member_id, isbn]):
                messagebox.showerror("Validation Error", "Please fill in all fields.")
                return
    
            if not member_id.isdigit():
                messagebox.showerror("Validation Error", "Member ID must be a number.")
                return
    
            if not validate_isbn(isbn):
                messagebox.showerror("Validation Error", "Invalid ISBN.")
                return
    
            self.db.return_book(int(member_id), isbn)
            messagebox.showinfo("Success", "Book returned successfully!")
            self.clear_return_entries()
    
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            logger.error(f"Error returning book: {e}")
            messagebox.showerror("Error", "Error occurred while returning book")

    def clear_return_entries(self) -> None:
        """Clear all inputs in the return form"""
        if hasattr(self, 'return_entries'):
            for entry in self.return_entries.values():
                if entry.winfo_exists():
                    entry.delete(0, tk.END)

    def clear_content(self) -> None:
        """Clear all widgets in the content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def create_stat_card(self, parent: ttk.Frame, title: str, value: int) -> ttk.Frame:
        """Create an improved statistics card"""
        theme = Config.DARK_THEME if self.is_dark_mode.get() else Config.LIGHT_THEME
        
        # Create a card with shadow effect
        card = ttk.Frame(parent, style='Card.TFrame')
        card.pack_propagate(False)
        card.configure(width=280, height=180)
        
        # Add content container for better layout control
        content = ttk.Frame(card, style='Card.TFrame')
        content.pack(expand=True)
        
        # Add icon
        icon = ("📚" if "Books" in title 
               else "👥" if "Members" in title 
               else "📋" if "Loans" in title 
               else "📊")
        
        icon_label = ttk.Label(content,
                             text=icon,
                             font=('Segoe UI', 32),
                             foreground=theme['button'],  # Use button color
                             style='Card.TLabel')
        icon_label.pack(pady=(20,5))
        
        # Title using secondary text color
        ttk.Label(content,
                 text=title,
                 font=('Segoe UI', 11),
                 foreground=theme['text'],  # Use text color
                 style='Card.TLabel').pack()
        
        # Value using primary color and larger font
        value_label = ttk.Label(content,
                              text=str(value),
                              font=('Segoe UI', 24, 'bold'),
                              foreground=theme['button'],  # Use button color
                              style='Card.TLabel')
        value_label.pack(pady=(5,20))
        
        return card

    def setup_custom_styles(self) -> None:
        """Setup improved custom styles"""
        theme = Config.DARK_THEME if self.is_dark_mode.get() else Config.LIGHT_THEME
        
        # Card style
        self.style.configure('Card.TFrame',
                           background=theme['card'],
                           relief='solid',
                           borderwidth=1)
        
        self.style.configure('Card.TLabel',
                           background=theme['card'])
        
        self.style.configure('CardHover.TFrame',
                           background=theme['surface'],
                           relief='solid',
                           borderwidth=1)
        
        # Sidebar button style
        self.style.configure('Sidebar.TButton',
                           background=theme['sidebar'],
                           foreground=theme['text'],
                           font=('Segoe UI', 11),
                           padding=15)
        
        # Modify button hover effect
        self.style.map('Sidebar.TButton',
                      background=[('active', theme['button_hover'])],
                      foreground=[('active', theme['button'])])  # Use button color
        
        # Primary button style
        self.style.configure('Primary.TButton',
                           background=theme['button'],  # Use button color
                           foreground=theme['button_text'],
                           font=('Segoe UI', 10, 'bold'),
                           padding=10)
        
        self.style.map('Primary.TButton',
                      background=[('active', theme['button_hover'])])

        # General button style
        self.style.configure('TButton',
                           background=theme['button'],
                           foreground=theme['button_text'],
                           padding=8)
        
        self.style.map('TButton',
                      background=[('active', theme['button_hover'])],
                      foreground=[('active', theme['button_text'])])

# Add main program entry
from tkinter import Tk
from config import Config  # Keep importing Config class
from session import Session

def main():
    try:
        Config.setup_logging()
        
        # Modify root window creation
        if (HAS_TTKTHEMES):
            root = ThemedTk()
            root.set_theme("breeze")  # Or other supported themes
        else:
            root = tk.Tk()
            style = ttk.Style()
            style.theme_use('default')
        
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
        
        root.mainloop()
    except Exception as e:
        logging.error(f"Program startup error: {e}")
        messagebox.showerror("Error", "Program startup failed, please check the log file")

if __name__ == "__main__":
    main()

class DatabaseHandler:
    # ...existing code...

    def get_all_books(self) -> List[Dict[str, Any]]:
        """Retrieve all books from the database"""
        try:
            # Assume there is a books table
            query = "SELECT title, author, isbn, available FROM books"
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            books = []
            for row in rows:
                books.append({
                    'title': row[0],
                    'author': row[1],
                    'isbn': row[2],
                    'available': row[3]
                })
            return books
        except Exception as e:
            logger.error(f"Error retrieving all books: {e}")
            return []



