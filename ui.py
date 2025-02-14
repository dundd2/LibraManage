import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Union, Optional, cast
import logging
from config import Config
from database import DatabaseHandler
from session import Session
from utils import (
    hash_password, validate_email, validate_phone, 
    validate_isbn, create_loading_indicator,
    show_status_message, create_tooltip
)
from matplotlib.figure import Figure
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from notification import NotificationSystem

# Setup logging
logger = logging.getLogger(__name__)

# Handle optional dependencies
HAS_TTKTHEMES = False
try:
    from ttkthemes import ThemedTk, ThemedStyle
    HAS_TTKTHEMES = True
except ImportError:
    print("ttkthemes not found - using default theme")

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    print("matplotlib not found - charts will be disabled")

class UIBase:
    """Base class for UI components with common functionality"""
    def __init__(self, root):  # added root parameter
        self.root = root  # now the attribute "root" is available
        self.style: Optional[ttk.Style] = None
        self.is_dark_mode: bool = False
        self.setup_theme()

    def setup_theme(self) -> None:
        theme = Config.DARK_THEME if self.is_dark_mode else Config.LIGHT_THEME
        
        if HAS_TTKTHEMES and hasattr(self, 'root') and self.root is not None:
            self.style = ThemedStyle(self.root)
            self.style.set_theme("equilux" if self.is_dark_mode else "breeze")
        else:
            self.style = ttk.Style()
        
        self.style.configure('TFrame', background=theme['background'])
        self.style.configure('TLabel', background=theme['background'], foreground=theme['text'])
        self.style.configure('TButton', background=theme['button'], foreground=theme['button_text'])
        self.style.configure('Card.TFrame', background=theme['card'], relief='solid', borderwidth=1)
        self.style.configure('Card.TLabel', background=theme['card'])
        self.style.configure('Sidebar.TButton',
                           background=theme['sidebar'],
                           foreground=theme['text'],
                           font=('Segoe UI', 11),
                           padding=15)

    def create_card(self, parent: ttk.Frame, title: str, value: Any) -> ttk.Frame:
        """Create a styled card widget"""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.pack_propagate(False)
        card.configure(width=280, height=180)
        
        content = ttk.Frame(card, style='Card.TFrame')
        content.pack(expand=True)
        
        icon = self._get_card_icon(title)
        ttk.Label(content, text=icon, font=('Segoe UI', 32), style='Card.TLabel').pack(pady=(20,5))
        ttk.Label(content, text=title, font=('Segoe UI', 11), style='Card.TLabel').pack()
        ttk.Label(content, text=str(value), font=('Segoe UI', 24, 'bold'), style='Card.TLabel').pack(pady=(5,20))
        
        return card

    def _get_card_icon(self, title: str) -> str:
        """Helper method to get appropriate icon for cards"""
        if "Books" in title: return "📚"
        if "Members" in title: return "👥"
        if "Loans" in title: return "📋"
        return "📊"

    def create_table(self, parent: ttk.Frame, data: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> None:
        """Create a styled table widget"""
        if not data:
            ttk.Label(parent, text="No data to display").pack()
            return
            
        # If headers not provided, use dictionary keys from first row
        table_headers: List[str] = headers if headers is not None else list(data[0].keys())
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create headers
        for i, header in enumerate(table_headers):
            ttk.Label(table_frame, 
                    text=header.title(),
                    font=(Config.FONT_FAMILY, 10, 'bold')).grid(
                        row=0, column=i, padx=5, pady=5, sticky='w')
        
        # Create rows
        for i, row in enumerate(data, 1):
            for j, (key, value) in enumerate(row.items()):
                if key in table_headers:
                    ttk.Label(table_frame, text=str(value)).grid(
                        row=i, column=j, padx=5, pady=2, sticky='w')

class LoginWindow(UIBase):
    def __init__(self, root: tk.Tk, db: DatabaseHandler):
        self.db: DatabaseHandler = db
        # Don't create a new root window, use the passed one
        self.root = root
        super().__init__(root)
        self.setup_login_window()

    def setup_login_window(self) -> None:
        """Setup the login window"""
        self.root.title("Library Management System - Login")
        self.root.geometry("400x500")
        
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo
        ttk.Label(main_frame, text="📚", font=('Segoe UI', 48)).pack(pady=20)
        
        # Title
        ttk.Label(main_frame, text="Welcome Back", font=Config.STYLES['title']['font']).pack(pady=10)
        ttk.Label(main_frame, text="Sign in to continue", font=Config.STYLES['subtitle']['font']).pack(pady=(0, 20))
        
        # Login form
        self._create_login_form(main_frame)

    def _create_login_form(self, parent: ttk.Frame) -> None:
        """Create the login form elements"""
        login_frame = ttk.Frame(parent)
        login_frame.pack(fill=tk.X, pady=10)
        
        # Initialize StringVars before creating entry fields
        self.username = tk.StringVar(self.root)
        self.password = tk.StringVar(self.root)
        
        # Username field
        username_frame = ttk.Frame(login_frame)
        username_frame.pack(fill=tk.X, pady=5)
        ttk.Label(username_frame, text="👤").pack(side=tk.LEFT, padx=5)
        username_entry = ttk.Entry(username_frame, textvariable=self.username, font=Config.STYLES['entry']['font'], width=30)
        username_entry.pack(side=tk.LEFT, padx=5)
        
        # Password field
        password_frame = ttk.Frame(login_frame)
        password_frame.pack(fill=tk.X, pady=5)
        ttk.Label(password_frame, text="🔒").pack(side=tk.LEFT, padx=5)
        password_entry = ttk.Entry(password_frame, textvariable=self.password, show="•", font=Config.STYLES['entry']['font'], width=30)
        password_entry.pack(side=tk.LEFT, padx=5)
        
        # Login button
        ttk.Button(parent, text="Sign In", command=self.login, style='Accent.TButton', width=20).pack(pady=20)

    def login(self) -> None:
        """Handle login attempt"""
        # Check if the StringVars exist and are properly initialized
        if not hasattr(self, 'username') or not hasattr(self, 'password'):
            logger.error("Login fields not properly initialized")
            show_status_message(self.root, "Internal error: Login fields not initialized", "error")
            return

        username = self.username.get().strip()
        password = self.password.get()

        if not username or not password:
            show_status_message(self.root, "Please fill in both username and password", "error")
            return

        try:
            user = self.db.authenticate_user(username, password)
            
            if user:
                logger.info(f"User {username} logged in successfully")
                MainWindow(self.root, self.db, Session(user))
                self.root.withdraw()
            else:
                logger.warning(f"Failed login attempt for user {username}")
                show_status_message(self.root, "Invalid username or password", "error")

        except Exception as e:
            logger.error(f"Login error: {e}")
            show_status_message(self.root, "An error occurred during login", "error")

class MainWindow(UIBase):
    def __init__(self, root: tk.Tk, db: DatabaseHandler, session: Session):
        self.root: tk.Toplevel = tk.Toplevel(root)
        self.db: DatabaseHandler = db
        self.session: Session = session
        self._is_dark_mode: tk.BooleanVar = tk.BooleanVar(value=False)
        self.notification_system: NotificationSystem = NotificationSystem(db)
        self.current_page: int = 1
        self.table_frame: Optional[ttk.Frame] = None
        self.members_table: Optional[ttk.Treeview] = None
        self.sort_var: tk.BooleanVar = tk.BooleanVar(value=False)
        super().__init__(root)
        self.setup_main_window()
        self.center_window()
        self.check_overdue_books()

    @property
    def is_dark_mode(self) -> bool:
        return bool(self._is_dark_mode.get())

    @is_dark_mode.setter
    def is_dark_mode(self, value: bool) -> None:
        self._is_dark_mode.set(value)

    def setup_main_window(self) -> None:
        self.root.title("Library Management System")
        self.root.geometry("1200x800")
        
        # Main container
        self.main_container = ttk.Frame(self.root, style='TFrame')
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Sidebar and content areas
        self.setup_sidebar()
        self.setup_content_area()
        self.show_dashboard()

    def setup_sidebar(self) -> None:
        self.sidebar = ttk.Frame(self.main_container, style='Sidebar.TFrame')
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # System title
        title_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        title_frame.pack(fill=tk.X, pady=20, padx=10)
        ttk.Label(title_frame, text="Library System", 
                 font=(Config.FONT_FAMILY, 16, "bold"),
                 style='Sidebar.TLabel').pack()

        # Navigation buttons
        self.create_nav_buttons()

    def create_nav_buttons(self) -> None:
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
            btn = ttk.Button(self.sidebar, text=text, command=command,
                           style='Sidebar.TButton', width=20)
            btn.pack(pady=5, padx=10)

    def setup_content_area(self) -> None:
        self.content_area = ttk.Frame(self.main_container, style='TFrame')
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Theme toggle
        theme_btn = ttk.Button(self.content_area, text="🌓 Toggle Theme",
                             command=self.toggle_theme)
        theme_btn.pack(side=tk.TOP, anchor=tk.NE, padx=10, pady=5)
        
        self.content_frame = ttk.Frame(self.content_area, style='TFrame')
        self.content_frame.pack(fill=tk.BOTH, expand=True)

    def show_dashboard(self) -> None:
        self.clear_content()
        
        # Welcome card
        welcome_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        welcome_frame.pack(fill=tk.X, padx=20, pady=20)
        ttk.Label(welcome_frame, text=f"Welcome back, {self.session.get_user().get('username')}!",
                 font=(Config.FONT_FAMILY, 20, 'bold'), style='Card.TLabel').pack(padx=20, pady=20)

        # Statistics
        stats_frame = ttk.Frame(self.content_frame)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        try:
            stats = [
                ("Total Books", self.db.get_total_books()),
                ("Available Books", self.db.get_available_books()),
                ("Total Members", self.db.get_total_members()),
                ("Active Loans", self.db.get_active_loans())
            ]
            
            for title, value in stats:
                card = self.create_card(stats_frame, title, value)
                card.pack(side=tk.LEFT, padx=10, pady=10, expand=True)
                
            # Charts
            if 'FigureCanvasTkAgg' in globals():
                self.create_dashboard_charts()
            
            # Recent activities
            self.show_recent_activities()
            
        except Exception as e:
            logger.error(f"Error loading dashboard: {e}")
            show_status_message(self.content_frame, "Error loading dashboard", "error")

    def create_dashboard_charts(self) -> None:
        charts_frame = ttk.Frame(self.content_frame)
        charts_frame.pack(fill=tk.X, padx=20, pady=10)
        
        fig = Figure(figsize=(12, 4))
        
        # Books by category
        categories = self.db.get_books_by_category()
        ax1 = fig.add_subplot(121)
        ax1.pie([count for _, count in categories], 
                labels=[cat for cat, _ in categories],
                autopct='%1.1f%%')
        ax1.set_title('Books by Category')
        
        # Monthly loans trend
        loans_data = self.db.get_monthly_loans()
        ax2 = fig.add_subplot(122)
        ax2.plot([date for date, _ in loans_data],
                 [count for _, count in loans_data])
        ax2.set_title('Monthly Loans Trend')
        ax2.tick_params(axis='x', rotation=45)
        
        canvas = FigureCanvasTkAgg(fig, charts_frame)
        canvas.draw()
        canvas.get_tk_widget().pack()

    def show_books(self) -> None:
        self.clear_content()
        
        # Title
        title_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        ttk.Label(title_frame, text="Book Collection", 
                 font=(Config.FONT_FAMILY, 20, 'bold'),
                 style='Card.TLabel').pack(padx=20, pady=20)
        
        # Search and filters
        self.create_book_search_panel()
        
        # Books table
        self.display_books()

    def create_book_search_panel(self) -> None:
        search_frame = ttk.Frame(self.content_frame)
        search_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Search
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var, width=40).pack(side=tk.LEFT, padx=5)
        
        # Category filter
        ttk.Label(search_frame, text="Category:").pack(side=tk.LEFT, padx=5)
        self.category_var = tk.StringVar(value="All")
        ttk.Combobox(search_frame, textvariable=self.category_var,
                    values=["All"] + self.db.get_categories(),
                    state="readonly").pack(side=tk.LEFT, padx=5)
        
        # Availability filter
        self.available_only = tk.BooleanVar()
        ttk.Checkbutton(search_frame, text="Available Only",
                       variable=self.available_only).pack(side=tk.LEFT, padx=5)
        
        # Search button
        ttk.Button(search_frame, text="Search",
                  command=self.search_books).pack(side=tk.LEFT, padx=5)

    def display_books(self) -> None:
        table_frame = ttk.Frame(self.content_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # Table headers
        headers = ['Title', 'Author', 'ISBN', 'Category', 'Available', 'Actions']
        self.create_table(table_frame, self.db.get_all_books(), headers)

    def show_add_book(self) -> None:
        self.clear_content()
        
        title_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        ttk.Label(title_frame, text="Add New Book",
                 font=(Config.FONT_FAMILY, 20, 'bold'),
                 style='Card.TLabel').pack(padx=20, pady=20)

        form_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        form_frame.pack(padx=20, pady=10, fill=tk.X)
        
        # Book form fields
        self.book_entries = {}
        fields = ['Title:', 'Author:', 'ISBN:', 'Quantity:', 'Category:']
        
        for i, label in enumerate(fields):
            ttk.Label(form_frame, text=label,
                     font=(Config.FONT_FAMILY, 12)).grid(
                row=i, column=0, pady=10, padx=20, sticky='e')
            
            entry = ttk.Entry(form_frame, width=40)
            entry.grid(row=i, column=1, pady=10, padx=20, sticky='w')
            self.book_entries[label] = entry
        
        ttk.Button(form_frame, text="Add Book",
                  command=self.add_book,
                  style='Accent.TButton').grid(
                      row=len(fields), column=0, columnspan=2, pady=20)

    def add_book(self) -> None:
        try:
            data = {k: v.get().strip() for k, v in self.book_entries.items()}
            
            if not all(data.values()):
                raise ValueError("All fields are required!")
                
            if not validate_isbn(data['ISBN:']):
                raise ValueError("Invalid ISBN format!")
                
            quantity = int(data['Quantity:'])
            if quantity <= 0:
                raise ValueError("Quantity must be positive!")

            self.db.add_book(
                title=data['Title:'],
                author=data['Author:'],
                isbn=data['ISBN:'],
                quantity=quantity,
                category=data['Category:']
            )
            
            show_status_message(self.root, "Book added successfully!", "success")
            self.clear_entries(self.book_entries)
            
        except ValueError as e:
            show_status_message(self.root, str(e), "error")
        except Exception as e:
            logger.error(f"Error adding book: {e}")
            show_status_message(self.root, "Failed to add book", "error")

    def show_members(self) -> None:
        self.clear_content()
        
        title_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        ttk.Label(title_frame, text="Library Members",
                 font=(Config.FONT_FAMILY, 20, 'bold'),
                 style='Card.TLabel').pack(padx=20, pady=20)

        # Member search
        search_frame = ttk.Frame(self.content_frame)
        search_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.member_search = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.member_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Search",
                  command=self.search_members).pack(side=tk.LEFT, padx=5)

        # Members table
        try:
            members = self.db.get_all_members()
            headers = ['ID', 'Name', 'Email', 'Phone', 'Join Date', 'Actions']
            self.create_table(self.content_frame, members, headers)
        except Exception as e:
            logger.error(f"Error loading members: {e}")
            show_status_message(self.content_frame, "Error loading members", "error")

    def show_add_member(self) -> None:
        self.clear_content()
        
        title_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        ttk.Label(title_frame, text="Add New Member",
                 font=(Config.FONT_FAMILY, 20, 'bold'),
                 style='Card.TLabel').pack(padx=20, pady=20)

        form_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        form_frame.pack(pady=20)

        self.member_entries = {}
        fields = ['Name:', 'Email:', 'Phone:']
        
        for i, label in enumerate(fields):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, pady=5, padx=5)
            entry = ttk.Entry(form_frame, width=40)
            entry.grid(row=i, column=1, pady=5, padx=5)
            self.member_entries[label] = entry

        ttk.Button(form_frame, text="Add Member",
                  command=self.add_member,
                  style='Accent.TButton').grid(
                      row=len(fields), column=0, columnspan=2, pady=20)

    def show_issue_book(self) -> None:
        self.clear_content()
        
        title_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        ttk.Label(title_frame, text="Issue Book",
                 font=(Config.FONT_FAMILY, 20, 'bold'),
                 style='Card.TLabel').pack(padx=20, pady=20)

        form_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        form_frame.pack(pady=20)

        # Issue book form
        ttk.Label(form_frame, text="Member ID:").grid(row=0, column=0, pady=5, padx=5)
        self.member_id_entry = ttk.Entry(form_frame, width=40)
        self.member_id_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(form_frame, text="Book ISBN:").grid(row=1, column=0, pady=5, padx=5)
        self.book_isbn_entry = ttk.Entry(form_frame, width=40)
        self.book_isbn_entry.grid(row=1, column=1, pady=5, padx=5)

        ttk.Button(form_frame, text="Issue Book",
                  command=self.issue_book,
                  style='Accent.TButton').grid(
                      row=2, column=0, columnspan=2, pady=20)

    def show_return_book(self) -> None:
        self.clear_content()
        
        title_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        ttk.Label(title_frame, text="Return Book",
                 font=(Config.FONT_FAMILY, 20, 'bold'),
                 style='Card.TLabel').pack(padx=20, pady=20)

        form_frame = ttk.Frame(self.content_frame, style='Card.TFrame')
        form_frame.pack(pady=20)

        self.return_entries = {}
        fields = ['Member ID:', 'Book ISBN:']
        
        for i, label in enumerate(fields):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, pady=5, padx=5)
            entry = ttk.Entry(form_frame, width=40)
            entry.grid(row=i, column=1, pady=5, padx=5)
            self.return_entries[label] = entry

        ttk.Button(form_frame, text="Return Book",
                  command=self.return_book,
                  style='Accent.TButton').grid(
                      row=len(fields), column=0, columnspan=2, pady=20)

    # Utility methods
    def clear_content(self) -> None:
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def clear_entries(self, entries: Dict) -> None:
        for entry in entries.values():
            if hasattr(entry, 'delete'):
                entry.delete(0, tk.END)

    def center_window(self) -> None:
        if self.root is None:
            return
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')

    def check_overdue_books(self) -> None:
        overdue_loans = self.db.get_overdue_loans()
        if overdue_loans:
            self.notification_system.notify_overdue_books(overdue_loans)
        self.root.after(24*60*60*1000, self.check_overdue_books)

    def toggle_theme(self) -> None:
        if isinstance(self._is_dark_mode, tk.BooleanVar):
            self._is_dark_mode.set(not self._is_dark_mode.get())
        self.setup_theme()
        self.show_dashboard()  # Refresh current view

    def search_books(self) -> None:
        """Search books based on current filters"""
        if self.table_frame is None:
            return
            
        # Clear previous results except headers
        for widget in self.table_frame.winfo_children():
            if type(widget) is not ttk.Label or widget.grid_info()['row'] != 0:
                widget.destroy()

        try:
            query = self.search_var.get()
            category = self.category_var.get()
            available_only = self.available_only.get()
            sort_by = self.sort_var.get()
            
            results = self.db.search_books(query, self.current_page)
            self.display_books()  # Remove results parameter
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            show_status_message(self.root, "Search failed", "error")

    def search_members(self) -> None:
        """Search members based on current query"""
        try:
            query = self.member_search.get()
            members = [m for m in self.db.get_all_members() 
                      if query.lower() in m['name'].lower() or 
                         query.lower() in m['email'].lower()]
            self.display_members(members)
        except Exception as e:
            logger.error(f"Member search error: {e}")
            show_status_message(self.root, "Search failed", "error")

    def show_recent_activities(self) -> None:
        """Show recent library activities"""
        activities_frame = ttk.Frame(self.content_frame)
        activities_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(activities_frame,
                text="Recent Activities",
                font=(Config.FONT_FAMILY, 16, 'bold')).pack(pady=10)
        
        try:
            # Use more basic database queries instead
            loan_activities = self.db.get_loans(limit=5)  # Assuming this method exists
            return_activities = self.db.get_returns(limit=5)  # Assuming this method exists
            
            for activity in loan_activities:
                activity_label = ttk.Label(
                    activities_frame,
                    text=f"Loan - {activity['book_title']} by {activity['member_name']}"
                )
                activity_label.pack(pady=2)
                
            for activity in return_activities:
                activity_label = ttk.Label(
                    activities_frame,
                    text=f"Return - {activity['book_title']} by {activity['member_name']}"
                )
                activity_label.pack(pady=2)
                
        except Exception as e:
            logger.error(f"Error loading activities: {e}")
            ttk.Label(activities_frame,
                    text="Unable to load recent activities",
                    foreground="red").pack(pady=10)

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
            show_status_message(self.root, "Member added successfully!", "success")
            self.clear_member_entries()

        except ValueError as e:
            show_status_message(self.root, str(e), "error")
        except Exception as e:
            logger.error(f"Error adding member: {e}")
            show_status_message(self.root, "Failed to add member", "error")

    def display_members(self, members: List[Dict[str, Any]]) -> None:
        """Display member data in the table"""
        if self.members_table is None:
            return
            
        for widget in self.members_table.winfo_children():
            if type(widget) is not ttk.Label or widget.grid_info()['row'] != 0:
                widget.destroy()

        for i, member in enumerate(members, 1):
            ttk.Label(self.members_table, text=str(member['id'])).grid(
                row=i, column=0, padx=5, pady=2)
            ttk.Label(self.members_table, text=member['name']).grid(
                row=i, column=1, padx=5, pady=2)
            ttk.Label(self.members_table, text=member['email']).grid(
                row=i, column=2, padx=5, pady=2)
            ttk.Label(self.members_table, text=member['phone']).grid(
                row=i, column=3, padx=5, pady=2)
            
            actions_frame = ttk.Frame(self.members_table)
            actions_frame.grid(row=i, column=4, padx=5, pady=2)
            
            ttk.Button(actions_frame, text="Edit",
                      command=lambda m=member: self.edit_member(m)).pack(
                          side=tk.LEFT, padx=2)
            ttk.Button(actions_frame, text="Delete",
                      command=lambda m=member: self.delete_member(m)).pack(
                          side=tk.LEFT, padx=2)

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
            show_status_message(self.root, "Book issued successfully!", "success")
            self.member_id_entry.delete(0, tk.END)
            self.book_isbn_entry.delete(0, tk.END)

        except ValueError as e:
            show_status_message(self.root, str(e), "error")
        except Exception as e:
            logger.error(f"Error issuing book: {e}")
            show_status_message(self.root, "Failed to issue book", "error")

    def return_book(self) -> None:
        """Handle book return"""
        try:
            member_id = self.return_entries['Member ID:'].get().strip()
            isbn = self.return_entries['Book ISBN:'].get().strip()
    
            if not all([member_id, isbn]):
                raise ValueError("Please fill in all fields.")

            if not member_id.isdigit():
                raise ValueError("Member ID must be a number.")
    
            if not validate_isbn(isbn):
                raise ValueError("Invalid ISBN.")
    
            self.db.return_book(int(member_id), isbn)
            show_status_message(self.root, "Book returned successfully!", "success")
            self.clear_return_entries()
    
        except ValueError as e:
            show_status_message(self.root, str(e), "error")
        except Exception as e:
            logger.error(f"Error returning book: {e}")
            show_status_message(self.root, "Error occurred while returning book", "error")

    def show_status_message(self, widget: Union[tk.Widget, tk.Tk, tk.Toplevel], message: str, status: str) -> None:
        # Display a temporary status message at the bottom of the widget
        color = "red" if status.lower() == "error" else "green"
        status_label = ttk.Label(widget, text=message, foreground=color)
        status_label.pack(side=tk.BOTTOM, pady=10)
        widget.after(3000, status_label.destroy)

    def clear_member_entries(self) -> None:
        for entry in self.member_entries.values():
            if hasattr(entry, 'delete'):
                entry.delete(0, tk.END)

    def clear_return_entries(self) -> None:
        for entry in self.return_entries.values():
            if hasattr(entry, 'delete'):
                entry.delete(0, tk.END)

    def edit_member(self, member: Dict[str, Any]) -> None:
        # Implementation for editing member
        pass

    def delete_member(self, member: Dict[str, Any]) -> None:
        # Implementation for deleting member
        pass