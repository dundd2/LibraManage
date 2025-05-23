import os
from pathlib import Path
import logging
from dotenv import load_dotenv

# Ensure .env file is loaded correctly
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    # Database settings
    DB_PATH = os.getenv('DB_PATH', 'library.db')
    CONNECTION_POOL_SIZE = int(os.getenv('POOL_SIZE', '5'))

    # Loan settings
    LOAN_PERIOD_DAYS = int(os.getenv('LOAN_PERIOD_DAYS', '14'))  # Default loan period is 14 days

    # Security settings
    # Remove PASSWORD_SALT since Argon2 handles salting internally
    
    JWT_SECRET = os.getenv('JWT_SECRET')
    if not JWT_SECRET:
        JWT_SECRET = 'MY_SUPER_SECRET_JWT_456!@#$%^&*'  # Default value

    # UI settings
    THEME = os.getenv('THEME', 'default')
    ROWS_PER_PAGE = int(os.getenv('ROWS_PER_PAGE', '10'))

    # Logging
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.getenv('LOG_FILE', 'library.log')
    LOG_LEVEL = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())

    # Cache settings
    CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', '300'))
    
    # Enhanced UI Theme settings
    THEME_COLORS = {
        # Primary colors
        'primary': '#1976D2',
        'primary_light': '#42A5F5',
        'primary_dark': '#1565C0',
        
        # Secondary colors
        'secondary': '#757575',
        'secondary_light': '#9E9E9E',
        'secondary_dark': '#616161',
        
        # Background colors
        'background': '#FFFFFF',     # White background
        'surface': '#F5F5F5',        # Light gray surface
        'card': '#FFFFFF',
        'dialog': '#FFFFFF',
        
        # Status colors
        'success': '#4CAF50',
        'success_light': '#81C784',
        'warning': '#FFC107',
        'warning_light': '#FFD54F',
        'error': '#DC3545',
        'error_light': '#EF5350',
        'info': '#2196F3',
        'info_light': '#64B5F6',
        
        # Text colors
        'text': '#212121',           # Dark text
        'text_secondary': '#757575',
        'text_disabled': '#9E9E9E',
        'text_hint': '#9E9E9E',
        'text_inverse': '#FFFFFF',   # Light text for dark background
        
        # Border colors
        'border': '#E0E0E0',
        'border_light': '#F5F5F5',
        'border_dark': '#BDBDBD',
        
        # Table colors
        'table_header': '#1976D2',
        'table_row_even': '#FFFFFF',
        'table_row_odd': '#F5F5F5',
        'table_hover': '#E3F2FD',
        
        # Sidebar colors
        'sidebar_bg': '#FFFFFF',
        'sidebar_text': '#212121',
        'sidebar_hover': '#E3F2FD',
        'sidebar': '#f0f0f0',
        'sidebar_hover': '#e0e0e0'  # Add this item for setting hover background color
    }
    
    # Font settings
    FONT_FAMILY = "Segoe UI"
    PADDING = 5
    BUTTON_HEIGHT = 2
    
    # Modify FONT_SETTINGS
    FONT_SETTINGS = {
        'family': FONT_FAMILY,
        'sizes': {
            'small': 8,
            'default': 10,
            'medium': 12,
            'large': 14,
            'xlarge': 16,
            'title': 20,
            'header': 24
        },
        'weights': {
            'normal': 'normal',
            'bold': 'bold'
        }
    }
    
    # Component styling
    STYLE_DEFAULTS = {
        # Button styles
        'button': {
            'padding': 10,
            'height': 35,
            'width': 120,
            'radius': 4,
            'focus_color': '#42A5F5'
        },
        
        # Entry field styles
        'entry': {
            'width': 300,
            'padding': 8,
            'radius': 4,
            'border_width': 1
        },
        
        # Card styles
        'card': {
            'padding': 15,
            'radius': 8,
            'shadow': '2px 2px 5px rgba(0, 0, 0, 0.1)',
            'border_width': 1
        },
        
        # Table styles
        'table': {
            'header_height': 40,
            'row_height': 35,
            'cell_padding': 8,
            'border_width': 1
        },
        
        # Form styles
        'form': {
            'label_width': 120,
            'field_spacing': 15,
            'section_spacing': 25,
            'group_spacing': 20
        },
        
        # Dialog styles
        'dialog': {
            'width': 400,
            'min_height': 200,
            'padding': 20,
            'radius': 8
        },
        
        # Sidebar styles
        'sidebar': {
            'width': 240,
            'item_height': 40,
            'item_padding': 15,
            'icon_size': 20
        }
    }
    
    # Animation settings
    ANIMATIONS = {
        'duration': {
            'instant': 50,
            'fast': 150,
            'normal': 250,
            'slow': 350,
            'very_slow': 500
        },
        'effects': {
            'fade_in': {'alpha': 0, 'duration': 250},
            'slide_in': {'offset': 50, 'duration': 250},
            'scale_in': {'scale': 0.95, 'duration': 250}
        },
        'transitions': {
            'linear': 'linear',
            'ease': 'ease',
            'ease_in': 'ease-in',
            'ease_out': 'ease-out',
            'ease_in_out': 'ease-in-out'
        }
    }
    
    # Layout settings
    LAYOUT = {
        'padding': {
            'small': 5,
            'default': 10,
            'large': 20
        },
        'margins': {
            'small': 5,
            'default': 10,
            'large': 20
        },
        'spacing': {
            'small': 5,
            'default': 10,
            'large': 20
        }
    }
    
    # Component specific settings
    COMPONENTS = {
        'statusbar': {
            'height': 25,
            'padding': 5
        },
        'toolbar': {
            'height': 40,
            'padding': 5
        },
        'tooltip': {
            'delay': 500,
            'padding': 5
        },
        'scrollbar': {
            'width': 10,
            'min_thumb_length': 30
        }
    }
    
    # Theme variants
    THEME_VARIANTS = {
        'light': {
            'primary': '#1976D2',
            'background': '#F5F5F5',
            'surface': '#FFFFFF',
            'text': '#212121',
        },
        'dark': {
            'primary': '#90CAF9',
            'background': '#121212',
            'surface': '#1E1E1E',
            'text': '#FFFFFF',
        },
        'high_contrast': {
            'primary': '#FFFFFF',
            'background': '#000000',
            'surface': '#121212',
            'text': '#FFFFFF',
        }
    }
    
    # Advanced component styling
    ADVANCED_STYLES = {
        'custom_button': {
            'normal': {
                'background': 'primary',
                'foreground': 'text_inverse',
                'padding': (10, 20),
                'radius': 20,
                'font': ('default', 'bold')
            },
            'hover': {
                'background': 'primary_light',
                'scale': 1.02
            },
            'pressed': {
                'background': 'primary_dark',
                'scale': 0.98
            }
        },
        'search_field': {
            'width': 300,
            'height': 35,
            'radius': 20,
            'icon_size': 16,
            'placeholder_color': 'text_hint'
        },
        'notification': {
            'timeout': 3000,
            'animation': 'slide_in',
            'position': 'top_right',
            'margin': 20,
            'spacing': 10,
            'max_visible': 3
        }
    }
    
    # Update theme colors
    DARK_THEME = {
        'primary': '#90CAF9',
        'background': '#121212',
        'surface': '#1E1E1E',
        'card': '#242424',
        'text': '#FFFFFF',
        'text_secondary': '#B0B0B0',
        'button': '#1976D2',
        'button_hover': '#42A5F5',
        'sidebar': '#1A1A1A',
        'border': '#333333',
        'error': '#CF6679',
        'success': '#03DAC6',
        'warning': '#FFB74D'
    }
    
    LIGHT_THEME = {
        'primary': '#1976D2',
        'background': '#F5F5F5',
        'surface': '#FFFFFF',
        'card': '#FFFFFF',
        'text': '#212121',
        'text_secondary': '#757575',
        'button': '#1976D2',
        'button_hover': '#42A5F5',
        'sidebar': '#FFFFFF',
        'border': '#E0E0E0',
        'error': '#DC3545',
        'success': '#4CAF50',
        'warning': '#FFC107'
    }

    # Update button styles
    BUTTON_STYLE = {
        'height': 35,
        'padding': (20, 10),
        'radius': 5,
        'font': ('Helvetica', 10, 'bold')
    }
    
    # Update card styles
    CARD_STYLE = {
        'padding': 20,
        'radius': 12,
        'shadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
        'hover_shadow': '0 8px 12px rgba(0, 0, 0, 0.15)',
        'border': '1px solid rgba(0, 0, 0, 0.1)'
    }
    
    # Modern UI Colors
    COLORS = {
        'primary': '#2196F3',  # Blue
        'secondary': '#FF4081',  # Pink
        'success': '#4CAF50',  # Green
        'warning': '#FFC107',  # Amber
        'error': '#F44336',    # Red
        'info': '#2196F3',     # Blue
        'light': '#FAFAFA',    # Almost White
        'dark': '#212121',     # Almost Black
        'gray': '#9E9E9E',     # Gray
    }

    # Theme configurations
    LIGHT_THEME = {
        'background': '#FFFFFF',
        'surface': '#F5F5F5',
        'card': '#FFFFFF',
        'text': '#212121',
        'text_secondary': '#757575',
        'button': '#1976D2',
        'button_text': '#FFFFFF',
        'button_hover': '#1565C0',
        'primary': '#1976D2',
        'sidebar': '#F8F9FA',
        'sidebar_text': '#212121',
        'sidebar_hover': '#E3F2FD',
        'border': '#E0E0E0',
        'error': '#DC3545',
        'success': '#4CAF50',
        'warning': '#FFC107',
    }

    DARK_THEME = {
        'background': '#121212',
        'surface': '#1E1E1E',
        'card': '#242424',
        'text': '#FFFFFF',
        'text_secondary': '#B0B0B0',
        'button': '#BB86FC',
        'button_text': '#000000',
        'button_hover': '#3700B3',
        'primary': '#BB86FC',
        'sidebar': '#1A1A1A',
        'sidebar_text': '#FFFFFF',
        'sidebar_hover': '#333333',
        'border': '#333333',
        'error': '#CF6679',
        'success': '#03DAC6',
        'warning': '#FFB74D',
    }

    # UI Style configurations
    STYLES = {
        'button': {
            'padding': '8 15',
            'font': ('Segoe UI', 10),
            'radius': 4,
        },
        'entry': {
            'padding': '8 10',
            'font': ('Segoe UI', 10),
            'radius': 4,
        },
        'label': {
            'font': ('Segoe UI', 10),
        },
        'title': {
            'font': ('Segoe UI', 24, 'bold'),
        },
        'subtitle': {
            'font': ('Segoe UI', 16),
        },
    }
    
    # 添加動畫設定
    ANIMATIONS = {
        'duration': {
            'fast': 150,
            'normal': 250,
            'slow': 350
        },
        'transition': 'all 0.3s ease'
    }

    # 更新卡片樣式
    CARD_STYLE = {
        'padding': 20,
        'radius': 12,
        'shadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
        'hover_shadow': '0 8px 12px rgba(0, 0, 0, 0.15)',
        'border': '1px solid rgba(0, 0, 0, 0.1)'
    }

    # 圖標設定
    ICONS = {
        'dashboard': '📊',
        'books': '📚',
        'add': '➕',
        'members': '👥',
        'issue': '📋',
        'return': '↩️',
        'search': '🔍',
        'edit': '✏️',
        'delete': '🗑️',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    }
    
    # SMTP Configuration
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USE_TLS = True
    SMTP_FROM = "library@example.com"
    SMTP_USER = "your_email@gmail.com"
    SMTP_PASSWORD = "your_app_password"
    
    # Session settings
    SESSION_TIMEOUT = 3600  # 1 hour in seconds
    
    @classmethod
    def get_font(cls, size='default', weight='normal'):
        """Helper method to get font tuple"""
        return (
            cls.FONT_SETTINGS['family'],
            cls.FONT_SETTINGS['sizes'][size],
            cls.FONT_SETTINGS['weights'][weight]
        )

    @classmethod
    def setup_logging(cls):
        logging.basicConfig(
            format=cls.LOG_FORMAT,
            level=cls.LOG_LEVEL,
            handlers=[
                logging.FileHandler(cls.LOG_FILE),
                logging.StreamHandler()
            ]
        )
    
# Call Config.setup_logging() when the application starts

