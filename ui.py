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

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class DataValidator:
    """Validation utilities for data input"""
    @staticmethod
    def validate_string(value: str, field_name: str, min_length: int = 1, max_length: int = 255) -> str:
        """Validate string input"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        value = value.strip()
        if len(value) < min_length:
            raise ValidationError(f"{field_name} cannot be empty")
        if len(value) > max_length:
            raise ValidationError(f"{field_name} cannot exceed {max_length} characters")
        return value

    @staticmethod
    def validate_integer(value: str, field_name: str, min_value: int = None, max_value: int = None) -> int:
        """Validate integer input"""
        try:
            num = int(value)
            if min_value is not None and num < min_value:
                raise ValidationError(f"{field_name} must be at least {min_value}")
            if max_value is not None and num > max_value:
                raise ValidationError(f"{field_name} must not exceed {max_value}")
            return num
        except ValueError:
            raise ValidationError(f"{field_name} must be a valid number")

    @staticmethod
    def validate_isbn(isbn: str) -> str:
        """Validate ISBN format"""
        isbn = isbn.replace('-', '').replace(' ', '')
        if not isbn.isdigit() or len(isbn) not in [10, 13]:
            raise ValidationError("Invalid ISBN format")
        return isbn

    @staticmethod
    def sanitize_input(value: str) -> str:
        """Sanitize input string"""
        if not isinstance(value, str):
            return str(value)
        return value.strip()

class SafeWidgetMixin:
    """Mixin class for safe widget operations"""
    def safe_get(self, widget, default="") -> str:
        """Safely get widget value"""
        try:
            if hasattr(widget, 'get'):
                return str(widget.get()).strip()
            return default
        except Exception:
            return default

    def safe_set(self, widget, value) -> None:
        """Safely set widget value"""
        try:
            if hasattr(widget, 'set'):
                widget.set(value)
            elif hasattr(widget, 'delete') and hasattr(widget, 'insert'):
                widget.delete(0, tk.END)
                widget.insert(0, str(value))
        except Exception as e:
            logger.error(f"Error setting widget value: {e}")

    def safe_destroy(self, widget) -> None:
        """Safely destroy widget"""
        try:
            if widget and widget.winfo_exists():
                widget.destroy()
        except Exception as e:
            logger.error(f"Error destroying widget: {e}")

class ErrorBoundary:
    """Error boundary for handling widget errors"""
    def __init__(self, widget, logger):
        self.widget = widget
        self.logger = logger

    def handle_error(self, exception: Exception, context: str = ""):
        """Handle errors in UI operations"""
        error_msg = str(exception)
        self.logger.error(f"Error in {context}: {error_msg}")
        
        # Clear the problematic widget
        for child in self.widget.winfo_children():
            child.destroy()
            
        # Show error message to user
        error_frame = ttk.Frame(self.widget)
        error_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(error_frame, 
                 text="⚠️ An error occurred",
                 font=(Config.FONT_FAMILY, 14, 'bold'),
                 foreground='red').pack(pady=5)
                 
        ttk.Label(error_frame, 
                 text=error_msg,
                 wraplength=300).pack(pady=5)
                 
        ttk.Button(error_frame,
                  text="Retry",
                  command=self.widget.retry_operation if hasattr(self.widget, 'retry_operation') else None).pack(pady=10)

class UIBase(SafeWidgetMixin):
    """Base class for UI components with error handling"""
    def __init__(self, root):
        self.root = root
        self.style = None
        self._is_dark_mode = False
        self.error_boundary = ErrorBoundary(self.root, logger)
        self.setup_theme()

    def setup_theme(self) -> None:
        """Setup theme based on current mode with error handling"""
        try:
            theme = Config.DARK_THEME if self._is_dark_mode else Config.LIGHT_THEME
            
            if HAS_TTKTHEMES:
                try:
                    self.style = ThemedStyle(self.root)
                except AttributeError as e:
                    logger.error(f"Error setting up theme: {e}")
                    self.style = ttk.Style(self.root)
            else:
                self.style = ttk.Style(self.root)

            # Configure base styles using string values for colors
            self.style.configure('.', 
                               background=str(theme['background']),
                               foreground=str(theme['text']),
                               fieldbackground=str(theme['background']))
            
            # Configure specific widget styles
            self.style.configure('TFrame', background=str(theme['background']))
            self.style.configure('TLabel', 
                               background=str(theme['background']),
                               foreground=str(theme['text']))
            self.style.configure('TButton', 
                               background=str(theme['button']),
                               foreground=str(theme['button_text']))
            self.style.map('TButton',
                          background=[('active', str(theme['button_hover']))],
                          foreground=[('active', str(theme['button_text']))])
            
            self.style.configure('Accent.TButton',
                               background=str(theme['primary']),
                               foreground=str(theme['button_text']))
            self.style.map('Accent.TButton',
                          background=[('active', str(theme['button_hover']))],
                          foreground=[('active', str(theme['button_text']))])
            
            self.style.configure('Card.TFrame',
                               background=str(theme['card']),
                               relief='solid',
                               borderwidth=1)
            self.style.configure('Card.TLabel',
                               background=str(theme['card']),
                               foreground=str(theme['text']))
            
            self.style.configure('Sidebar.TFrame',
                               background=str(theme['sidebar']))
            self.style.configure('Sidebar.TButton',
                               background=str(theme['sidebar']),
                               foreground=str(theme['text']),
                               font=('Segoe UI', 11),
                               padding=15)
            self.style.map('Sidebar.TButton',
                          background=[('active', str(theme['sidebar_hover']))],
                          foreground=[('active', str(theme['text']))])
            
            self.style.configure('Sidebar.TLabel',
                               background=str(theme['sidebar']),
                               foreground=str(theme['text']))
            
            # Configure Entry widget colors
            self.style.configure('TEntry',
                               fieldbackground=str(theme['background']),
                               foreground=str(theme['text']),
                               insertcolor=str(theme['text']))
            
            # Configure Combobox colors
            self.style.configure('TCombobox',
                               fieldbackground=str(theme['background']),
                               background=str(theme['background']),
                               foreground=str(theme['text']),
                               arrowcolor=str(theme['text']))
            
            # Configure Checkbutton colors
            self.style.configure('TCheckbutton',
                               background=str(theme['background']),
                               foreground=str(theme['text']))
            
            # Update root window background
            if self.root:
                self.root.configure(background=str(theme['background']))
                
            # Update all widgets recursively
            self._update_widget_theme(self.root, theme)
        except Exception as e:
            logger.error(f"Error setting up theme: {e}")
            # Fallback to default theme
            self.style = ttk.Style()
            self.style.configure('.', background='white', foreground='black')

    def _update_widget_theme(self, widget, theme):
        """Recursively update widget and its children with new theme colors"""
        if not widget:
            return
            
        try:
            widget_type = widget.winfo_class()
            
            if widget_type in ('TFrame', 'Frame'):
                widget.configure(background=theme['background'])
            elif widget_type in ('TLabel', 'Label'):
                widget.configure(background=theme['background'], foreground=theme['text'])
            elif widget_type == 'TButton':
                widget.configure(style='TButton')
            elif widget_type == 'TEntry':
                widget.configure(style='TEntry')
            elif widget_type == 'TCombobox':
                widget.configure(style='TCombobox')
            elif widget_type == 'Entry':
                widget.configure(
                    background=theme['background'],
                    foreground=theme['text'],
                    insertbackground=theme['text']
                )
            
            # Recursively update children
            for child in widget.winfo_children():
                self._update_widget_theme(child, theme)
                
        except Exception as e:
            # Log any errors but continue updating other widgets
            logger.error(f"Error updating widget theme: {e}")
            pass

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

    def safe_execute(self, operation, context: str = ""):
        """Execute UI operation with error handling"""
        try:
            return operation()
        except Exception as e:
            self.error_boundary.handle_error(e, context)
            return None

def validate_book_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate book input data"""
    validated = {}
    try:
        validated['title'] = DataValidator.validate_string(data['title'], "Title")
        validated['author'] = DataValidator.validate_string(data['author'], "Author")
        validated['isbn'] = DataValidator.validate_isbn(data['isbn'])
        validated['quantity'] = DataValidator.validate_integer(data['quantity'], "Quantity", min_value=0)
        validated['category'] = DataValidator.validate_string(data['category'], "Category")
        return validated
    except Exception as e:
        raise ValidationError(f"Book validation failed: {str(e)}")

def validate_member_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate member input data"""
    validated = {}
    try:
        validated['name'] = DataValidator.validate_string(data['name'], "Name")
        validated['email'] = DataValidator.validate_string(data['email'], "Email")
        if not validate_email(data['email']):
            raise ValidationError("Invalid email format")
        validated['phone'] = DataValidator.validate_string(data['phone'], "Phone")
        if not validate_phone(data['phone']):
            raise ValidationError("Invalid phone format")
        return validated
    except Exception as e:
        raise ValidationError(f"Member validation failed: {str(e)}")

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
        """Handle login with enhanced security"""
        def operation():
            try:
                # Rate limiting check
                if hasattr(self, '_last_login_attempt'):
                    time_diff = datetime.now() - self._last_login_attempt
                    if time_diff.seconds < 3:  # 3 seconds cooldown
                        raise ValidationError("Please wait before trying again")
                
                self._last_login_attempt = datetime.now()
                username = DataValidator.validate_string(
                    self.safe_get(self.username), 
                    "Username",
                    min_length=1
                )
                password = self.password.get()
                if not password:
                    raise ValidationError("Password cannot be empty")

                # Attempt authentication with timeout
                user = self.db.authenticate_user(username, password)
                
                if user:
                    logger.info(f"User {username} logged in successfully")
                    MainWindow(self.root, self.db, Session(user))
                    self.root.withdraw()
                else:
                    logger.warning(f"Failed login attempt for user {username}")
                    show_status_message(self.root, "Invalid username or password", "error")

            except ValidationError as e:
                show_status_message(self.root, str(e), "error")
            except Exception as e:
                logger.error(f"Login error: {e}")
                show_status_message(self.root, "An error occurred during login", "error")
                raise
                
        self.safe_execute(operation, "login")

class MainWindow(UIBase):
    def __init__(self, root: tk.Tk, db: DatabaseHandler, session: Session):
        self.root: tk.Toplevel = tk.Toplevel()
        self.db: DatabaseHandler = db
        self.session: Session = session
        self._is_dark_mode = False
        self.notification_system: NotificationSystem = NotificationSystem(db)
        self.current_page: int = 1
        self.table_frame: Optional[ttk.Frame] = None
        self.members_table: Optional[ttk.Treeview] = None
        self.sort_var: tk.BooleanVar = tk.BooleanVar(value=False)
        super().__init__(self.root)
        self.setup_main_window()
        self.center_window()
        self.check_overdue_books()

    def setup_main_window(self) -> None:
        """Setup the main window with proper dimensions"""
        self.root.title("Library Management System")
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate window size (80% of screen size)
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        # Set minimum size
        self.root.minsize(1024, 768)
        
        # Set window size and position
        self.root.geometry(f"{window_width}x{window_height}")
        
        # Configure grid weights for proper resizing
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Main container with proper expansion
        self.main_container = ttk.Frame(self.root, style='TFrame')
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Setup sidebar and content areas
        self.setup_sidebar()
        self.setup_content_area()
        self.show_dashboard()

    def center_window(self) -> None:
        """Center the window on the screen"""
        if self.root is None:
            return
            
        self.root.update_idletasks()
        
        # Get window size
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate position
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set window position
        self.root.geometry(f"+{x}+{y}")

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
        
        # Theme toggle with icon
        theme_text = "🌙 Dark Mode" if not self._is_dark_mode else "☀️ Light Mode"
        self.theme_btn = ttk.Button(self.content_area, 
                                  text=theme_text,
                                  command=self.toggle_theme,
                                  style='Accent.TButton')
        self.theme_btn.pack(side=tk.TOP, anchor=tk.NE, padx=10, pady=5)
        
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
        """Add book with input validation and error handling"""
        def operation():
            try:
                # Collect and validate all inputs first
                data = {k: DataValidator.sanitize_input(self.safe_get(v)) 
                       for k, v in self.book_entries.items()}
                
                # Use validator to check data
                validated_data = validate_book_data({
                    'title': data['Title:'],
                    'author': data['Author:'],
                    'isbn': data['ISBN:'],
                    'quantity': data['Quantity:'],
                    'category': data['Category:']
                })
                
                # Check for duplicate ISBN
                if self.db.book_exists(validated_data['isbn']):
                    raise ValidationError("A book with this ISBN already exists")

                # Attempt database operation with transaction
                self.db.add_book(**validated_data)
                show_status_message(self.root, "Book added successfully!", "success")
                self.clear_entries(self.book_entries)
                
            except ValidationError as e:
                show_status_message(self.root, str(e), "error")
            except Exception as e:
                logger.error(f"Error adding book: {e}")
                show_status_message(self.root, "Failed to add book", "error")
                raise
                
        self.safe_execute(operation, "adding book")

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

    def add_member(self) -> None:
        """Add member with input validation and error handling"""
        def operation():
            try:
                # Collect and validate all inputs first
                data = {k: v.get().strip() for k, v in self.member_entries.items()}
                
                # Use validator to check data
                validated_data = validate_member_data({
                    'name': data['Name:'],
                    'email': data['Email:'],
                    'phone': data['Phone:']
                })
                
                # Attempt database operation
                self.db.add_member(**validated_data)
                show_status_message(self.root, "Member added successfully!", "success")
                self.clear_member_entries()
                
            except ValidationError as e:
                show_status_message(self.root, str(e), "error")
            except Exception as e:
                logger.error(f"Error adding member: {e}")
                show_status_message(self.root, "Failed to add member", "error")
                raise
                
        self.safe_execute(operation, "adding member")

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

    def issue_book(self) -> None:
        """Issue book with input validation and error handling"""
        def operation():
            try:
                member_id = self.member_id_entry.get().strip()
                isbn = self.book_isbn_entry.get().strip()

                # Validate inputs
                member_id = DataValidator.validate_integer(member_id, "Member ID", min_value=1)
                isbn = DataValidator.validate_isbn(isbn)

                # Attempt database operation
                self.db.issue_book(member_id, isbn)
                show_status_message(self.root, "Book issued successfully!", "success")
                self.member_id_entry.delete(0, tk.END)
                self.book_isbn_entry.delete(0, tk.END)

            except ValidationError as e:
                show_status_message(self.root, str(e), "error")
            except Exception as e:
                logger.error(f"Error issuing book: {e}")
                show_status_message(self.root, "Failed to issue book", "error")
                raise
                
        self.safe_execute(operation, "issuing book")

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

    def return_book(self) -> None:
        """Return book with input validation and error handling"""
        def operation():
            try:
                member_id = self.return_entries['Member ID:'].get().strip()
                isbn = self.return_entries['Book ISBN:'].get().strip()

                # Validate inputs
                member_id = DataValidator.validate_integer(member_id, "Member ID", min_value=1)
                isbn = DataValidator.validate_isbn(isbn)

                # Attempt database operation
                self.db.return_book(member_id, isbn)
                show_status_message(self.root, "Book returned successfully!", "success")
                self.clear_return_entries()

            except ValidationError as e:
                show_status_message(self.root, str(e), "error")
            except Exception as e:
                logger.error(f"Error returning book: {e}")
                show_status_message(self.root, "Failed to return book", "error")
                raise
                
        self.safe_execute(operation, "returning book")

    # Utility methods
    def clear_content(self) -> None:
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def clear_entries(self, entries: Dict) -> None:
        for entry in entries.values():
            if hasattr(entry, 'delete'):
                entry.delete(0, tk.END)

    def check_overdue_books(self) -> None:
        overdue_loans = self.db.get_overdue_loans()
        if overdue_loans:
            self.notification_system.notify_overdue_books(overdue_loans)
        self.root.after(24*60*60*1000, self.check_overdue_books)

    def toggle_theme(self) -> None:
        """Toggle between light and dark mode"""
        self._is_dark_mode = not self._is_dark_mode
        
        # Update theme button text
        theme_text = "☀️ Light Mode" if self._is_dark_mode else "🌙 Dark Mode"
        self.theme_btn.configure(text=theme_text)
        
        # Apply new theme
        self.setup_theme()
        
        # Ensure all frames are updated
        if self.main_container:
            theme = Config.DARK_THEME if self._is_dark_mode else Config.LIGHT_THEME
            self._update_widget_theme(self.main_container, theme)
            self._update_widget_theme(self.sidebar, theme)
            self._update_widget_theme(self.content_area, theme)
            self._update_widget_theme(self.content_frame, theme)
        
        # Refresh current view to ensure all widgets are properly themed
        self.show_dashboard()

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