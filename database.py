import sqlite3
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager
from functools import lru_cache
from queue import Queue
from config import Config
import logging
from utils import hash_password, verify_password, validate_email, validate_phone
from datetime import datetime
import time

# Setup logging
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class DataValidator:
    @staticmethod
    def validate_string(value: str, field_name: str, min_length: int = 1, max_length: int = 255) -> str:
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        value = value.strip()
        if len(value) < min_length:
            raise ValidationError(f"{field_name} cannot be empty")
        if len(value) > max_length:
            raise ValidationError(f"{field_name} cannot exceed {max_length} characters")
        return value

    @staticmethod
    def validate_integer(value: Union[str, int], field_name: str, min_value: int = None, max_value: int = None) -> int:
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
        """Validate ISBN format with strict checking"""
        if not isinstance(isbn, str):
            raise ValidationError("ISBN must be a string")
        
        # Remove hyphens and spaces
        isbn = isbn.replace('-', '').replace(' ', '')
        
        # Basic format check
        if not isbn.replace('X', '').isdigit() or (len(isbn) != 10 and len(isbn) != 13):
            raise ValidationError("Invalid ISBN format - must be 10 or 13 digits")
            
        # ISBN-10 check
        if len(isbn) == 10:
            if not isbn[:9].isdigit() or (isbn[9] != 'X' and not isbn[9].isdigit()):
                raise ValidationError("Invalid ISBN-10 format")
                
        # ISBN-13 check
        elif len(isbn) == 13:
            if not isbn.isdigit():
                raise ValidationError("Invalid ISBN-13 format - must be all digits")
                
        return isbn

def validate_book_data(data: Dict[str, Any]) -> Dict[str, Any]:
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
    validated = {}
    try:
        validated['name'] = DataValidator.validate_string(data['name'], "Name")
        if not validate_email(data['email']):
            raise ValidationError("Invalid email format")
        validated['email'] = data['email']
        if not validate_phone(data['phone']):
            raise ValidationError("Invalid phone format")
        validated['phone'] = data['phone']
        return validated
    except Exception as e:
        raise ValidationError(f"Member validation failed: {str(e)}")

logger = logging.getLogger(__name__)

class DatabasePool:
    def __init__(self):
        # Initialize database connection pool
        self.pool = Queue(maxsize=Config.CONNECTION_POOL_SIZE)
        for _ in range(Config.CONNECTION_POOL_SIZE):
            conn = sqlite3.connect(Config.DB_PATH)
            # Ensure each connection has row_factory set
            conn.row_factory = sqlite3.Row
            # Configure connection for better transaction handling
            conn.isolation_level = None  # Enable autocommit mode
            conn.execute('PRAGMA journal_mode=WAL')  # Use WAL mode for better concurrency
            conn.execute('PRAGMA synchronous=NORMAL')  # Balance between safety and performance
            self.pool.put(conn)

    @contextmanager
    def get_connection(self):
        # Get database connection
        conn = self.pool.get()
        try:
            # Enable WAL mode and set timeout
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA busy_timeout=5000')  # Wait up to 5 seconds on locks
            yield conn
        finally:
            self.pool.put(conn)

class DatabaseHandler:
    def __init__(self):
        try:
            self.pool = DatabasePool()
            self.create_tables()
            self.create_default_user()
        except Exception as e:
            logger.critical(f"Failed to initialize database: {e}")
            raise RuntimeError("Database initialization failed")

    def test_connection(self) -> bool:
        """Test if database connection is working"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def _execute_with_retry(self, operation, retries=3):
        """Execute database operation with retry mechanism"""
        last_error = None
        for attempt in range(retries):
            try:
                with self.pool.get_connection() as conn:
                    return operation(conn)
            except sqlite3.OperationalError as e:
                last_error = e
                if "database is locked" in str(e):
                    if attempt < retries - 1:
                        logger.warning(f"Database locked, attempt {attempt + 1} of {retries}")
                        time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                        continue
                logger.error(f"Database operation failed after {retries} attempts: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected database error: {e}")
                raise

    def create_tables(self):
        """Create necessary database tables if they don't exist"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Add login_attempts column if it doesn't exist
            try:
                cursor.execute("SELECT login_attempts FROM users LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE users ADD COLUMN login_attempts INTEGER DEFAULT 0")
                conn.commit()
            
            # Ensure correct users table structure
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL, -- Hashed password using Argon2
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    login_attempts INTEGER DEFAULT 0
                )
            """)
            
            # Create books table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    author TEXT,
                    isbn TEXT UNIQUE, -- International Standard Book Number
                    quantity INTEGER,
                    available INTEGER,
                    category TEXT DEFAULT 'General'
                )
            """)

            # Create members table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    email TEXT UNIQUE, -- Member's contact email
                    phone TEXT,
                    join_date TEXT
                )
            """)

            # Create transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    book_id INTEGER,
                    member_id INTEGER,
                    issue_date TEXT,
                    return_date TEXT,
                    status TEXT, -- Current status of the loan
                    FOREIGN KEY (book_id) REFERENCES books (id),
                    FOREIGN KEY (member_id) REFERENCES members (id)
                )
            """)

            # Create loans table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS loans (
                    id INTEGER PRIMARY KEY,
                    book_id INTEGER,
                    member_id INTEGER,
                    loan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    return_date TIMESTAMP,
                    FOREIGN KEY (book_id) REFERENCES books (id),
                    FOREIGN KEY (member_id) REFERENCES members (id)
                )
            """)
            
            conn.commit()

    def create_default_user(self):
        """Create default admin user if not exists"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                # Check if admin user already exists
                cursor.execute("SELECT * FROM users WHERE username = ?", ("1",))
                if not cursor.fetchone():
                    # Create if not exists
                    password_hash = hash_password("1")
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, role)
                        VALUES (?, ?, ?)
                    """, ("1", password_hash, "1"))
                    conn.commit()
                    logger.info("Default admin user created successfully")
        except Exception as e:
            logger.error(f"Error creating default user: {e}")
            raise

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with enhanced security"""
        try:
            # Sanitize inputs
            username = DataValidator.validate_string(username, "Username", min_length=1)
            if not password:
                raise ValidationError("Password cannot be empty")
            
            def operation(conn):
                cursor = conn.cursor()
                # Use parameterized query to prevent SQL injection
                cursor.execute("""
                    SELECT id, username, password_hash, role, 
                           COUNT(*) as login_attempts
                    FROM users 
                    WHERE username = ?
                    GROUP BY id
                """, (username,))
                user = cursor.fetchone()
                
                if not user:
                    logger.warning(f"Login attempt for non-existent user: {username}")
                    return None
                
                # Check for too many failed attempts
                if user['login_attempts'] >= 5:
                    logger.warning(f"Account locked due to too many failed attempts: {username}")
                    raise ValidationError("Account temporarily locked. Please try again later.")
                
                if verify_password(password, user['password_hash']):
                    # Reset login attempts on successful login
                    cursor.execute("UPDATE users SET login_attempts = 0 WHERE username = ?", (username,))
                    conn.commit()
                    
                    return {
                        'id': user['id'],
                        'username': user['username'],
                        'role': user['role']
                    }
                else:
                    # Increment failed login attempts
                    cursor.execute("UPDATE users SET login_attempts = login_attempts + 1 WHERE username = ?", (username,))
                    conn.commit()
                    return None
                    
            return self._execute_with_retry(operation)
            
        except ValidationError as e:
            logger.error(f"Validation error in authenticate_user: {e}")
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise

    def add_user(self, username: str, password: str, role: str = 'user') -> bool:
        """
        Add a new user with Argon2 hashed password
        """
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                password_hash = hash_password(password)  # Using new Argon2 hash function
                query = "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)"
                cursor.execute(query, (username, password_hash, role))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False

    def get_book_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        """Get book details by ISBN with proper error handling"""
        try:
            isbn = DataValidator.validate_isbn(isbn)
            
            def operation(conn):
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM books WHERE isbn = ?', (isbn,))
                result = cursor.fetchone()
                return dict(result) if result else None
                
            return self._execute_with_retry(operation)
                
        except Exception as e:
            logger.error(f"Error getting book by ISBN: {e}")
            raise

    def get_book(self, isbn: str) -> Optional[Dict[str, Any]]:
        """Get book details by ISBN"""
        try:
            isbn = DataValidator.validate_isbn(isbn)
            return self.get_book_by_isbn(isbn)  # Reuse existing method
                
        except Exception as e:
            logger.error(f"Error getting book by ISBN: {e}")
            raise

    def search_books(self, query: str, page: int = 1) -> List[Dict[str, Any]]:
        """Search books with pagination"""
        try:
            offset = (page - 1) * Config.ROWS_PER_PAGE
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                search_query = f'%{query}%'
                cursor.execute('''
                    SELECT * FROM books 
                    WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ? OR category LIKE ?
                    LIMIT ? OFFSET ?
                ''', (search_query, search_query, search_query, search_query,
                      Config.ROWS_PER_PAGE, offset))
                books = cursor.fetchall()
                return [dict(row) for row in books]
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            raise Exception("Failed to search books")

    def backup_database(self, backup_path: str) -> None:
        try:
            with self.pool.get_connection() as conn:
                backup = sqlite3.connect(backup_path)
                conn.backup(backup)
                backup.close()
                logger.info(f"Database backed up to {backup_path}")
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise

    def add_member(self, name: str, email: str, phone: str) -> None:
        """Add a new member with validation"""
        try:
            # Validate input data
            validated_data = validate_member_data({
                'name': name,
                'email': email,
                'phone': phone
            })
            
            def operation(conn):
                cursor = conn.cursor()
                # Check for duplicate email
                cursor.execute("SELECT id FROM members WHERE email = ?", (validated_data['email'],))
                if cursor.fetchone():
                    raise ValidationError("Member with this email already exists")
                
                cursor.execute('''
                    INSERT INTO members (name, email, phone, join_date)
                    VALUES (?, ?, ?, ?)
                ''', (
                    validated_data['name'],
                    validated_data['email'],
                    validated_data['phone'],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                conn.commit()
                logger.info(f"Member '{validated_data['name']}' added successfully")
                
            self._execute_with_retry(operation)
            
        except ValidationError as e:
            logger.error(f"Validation error while adding member: {e}")
            raise
        except Exception as e:
            logger.error(f"Error adding member: {e}")
            raise

    def get_total_books(self) -> int:
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM books')
            result = cursor.fetchone()
            return result['count'] if result else 0

    def get_available_books(self) -> int:
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT SUM(available) as count FROM books')
            result = cursor.fetchone()
            return result['count'] if result else 0

    def get_total_members(self) -> int:
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM members')
            result = cursor.fetchone()
            return result['count'] if result else 0

    def get_active_loans(self) -> int:
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM transactions WHERE return_date IS NULL')
            result = cursor.fetchone()
            return result['count'] if result else 0

    def get_book_categories(self) -> List[Dict[str, Any]]:
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT category as name, COUNT(*) as count 
                FROM books 
                GROUP BY category
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def add_book(self, title: str, author: str, isbn: str, quantity: int, category: str = 'General') -> None:
        """Add a new book with validation"""
        try:
            # Validate input data
            validated_data = validate_book_data({
                'title': title,
                'author': author,
                'isbn': isbn,
                'quantity': quantity,
                'category': category
            })
            
            def operation(conn):
                cursor = conn.cursor()
                conn.execute("BEGIN")
                try:
                    # Check for duplicate ISBN
                    cursor.execute("SELECT id FROM books WHERE isbn = ?", (validated_data['isbn'],))
                    if cursor.fetchone():
                        raise ValidationError("Book with this ISBN already exists")
                    
                    # Insert new book with quantity as initial available count
                    cursor.execute('''
                        INSERT INTO books (title, author, isbn, quantity, available, category)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        validated_data['title'],
                        validated_data['author'],
                        validated_data['isbn'],
                        validated_data['quantity'],
                        validated_data['quantity'],  # Set initial available to quantity
                        validated_data['category']
                    ))
                    conn.commit()
                    logger.info(f"Book '{validated_data['title']}' added successfully")
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                    
            self._execute_with_retry(operation)
            
        except ValidationError as e:
            logger.error(f"Validation error while adding book: {e}")
            raise
        except Exception as e:
            logger.error(f"Error adding book: {e}")
            raise

    def return_book(self, member_id: int, isbn: str) -> None:
        """Return a book with enhanced validation and error handling"""
        try:
            # Validate input
            member_id = DataValidator.validate_integer(member_id, "Member ID", min_value=1)
            isbn = DataValidator.validate_isbn(isbn)
            
            def operation(conn):
                cursor = conn.cursor()
                conn.execute("BEGIN")
                try:
                    # Get book details
                    cursor.execute("SELECT id FROM books WHERE isbn = ?", (isbn,))
                    book = cursor.fetchone()
                    if not book:
                        raise ValidationError("Book does not exist")
                    
                    # Check loan record
                    cursor.execute("""
                        SELECT id FROM transactions 
                        WHERE member_id = ? AND book_id = ? AND return_date IS NULL
                    """, (member_id, book['id']))
                    loan = cursor.fetchone()
                    if not loan:
                        raise ValidationError("No matching unreturned loan record found")
                    
                    # Update loan record
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("""
                        UPDATE transactions
                        SET return_date = ?, status = 'returned'
                        WHERE id = ?
                    """, (current_time, loan['id']))
                    
                    # Update book availability - simplified logic
                    cursor.execute("""
                        UPDATE books
                        SET available = available + 1
                        WHERE id = ?
                    """, (book['id'],))
                    
                    conn.commit()
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                    
            self._execute_with_retry(operation)
            
        except ValidationError as e:
            logger.error(f"Validation error in return_book: {e}")
            raise
        except Exception as e:
            logger.error(f"Error returning book: {e}")
            raise

    def issue_book(self, member_id: int, isbn: str) -> None:
        """Issue a book with enhanced validation and error handling"""
        try:
            # Validate input
            member_id = DataValidator.validate_integer(member_id, "Member ID", min_value=1)
            isbn = DataValidator.validate_isbn(isbn)
            
            def operation(conn):
                cursor = conn.cursor()
                cursor.execute("BEGIN IMMEDIATE")
                try:
                    # Get book details
                    cursor.execute("""
                        SELECT id, available FROM books WHERE isbn = ?
                    """, (isbn,))
                    book = cursor.fetchone()
                    
                    if not book:
                        raise ValidationError("Book does not exist")
                    if book['available'] <= 0:
                        raise ValidationError("Book is not available")
                    
                    # Check if member exists
                    cursor.execute("SELECT id FROM members WHERE id = ?", (member_id,))
                    if not cursor.fetchone():
                        raise ValidationError("Member does not exist")
                    
                    # Update book availability first
                    cursor.execute("""
                        UPDATE books 
                        SET available = available - 1 
                        WHERE id = ? AND available > 0
                        """, (book['id'],))
                    
                    if cursor.rowcount != 1:
                        raise ValidationError("Failed to update book availability")
                    
                    # Create loan record
                    cursor.execute("""
                        INSERT INTO transactions (book_id, member_id, issue_date, status)
                        VALUES (?, ?, ?, 'issued')
                        """, (book['id'], member_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    
                    conn.commit()
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                    
            self._execute_with_retry(operation)
            
        except ValidationError as e:
            logger.error(f"Validation error in issue_book: {e}")
            raise
        except Exception as e:
            logger.error(f"Error issuing book: {e}")
            raise

    def get_all_members(self) -> List[Dict[str, Any]]:
        """Get all member records"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        id,
                        name,
                        email,
                        phone,
                        datetime(join_date) as join_date
                    FROM members
                    ORDER BY id DESC
                ''')
                members = cursor.fetchall()
                return [dict(row) for row in members]
        except Exception as e:
            logger.error(f"Error getting members: {e}")
            raise Exception("Failed to retrieve members")

    def get_book_loan_history(self, isbn: str) -> List[Dict[str, Any]]:
        """Get loan history for specified book"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    t.id,
                    m.name AS member_name,
                    t.issue_date,
                    t.return_date,
                    t.status
                FROM transactions t
                JOIN books b ON t.book_id = b.id
                JOIN members m ON t.member_id = m.id
                WHERE b.isbn = ?
                ORDER BY t.issue_date DESC
            """, (isbn,))
            history = cursor.fetchall()
            return [dict(row) for row in history]

    def get_all_books(self) -> List[Dict[str, Any]]:
        """Retrieve all books from the database"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM books')
            books = cursor.fetchall()
            return [dict(book) for book in books]

    def get_books_by_category(self) -> List[tuple]:
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category, COUNT(*) 
                FROM books 
                GROUP BY category
            """)
            return cursor.fetchall()

    def get_monthly_loans(self) -> List[tuple]:
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT strftime('%Y-%m', issue_date) as month, COUNT(*) 
                FROM transactions 
                GROUP BY month 
                ORDER BY month DESC 
                LIMIT 12
            """)
            return cursor.fetchall()

    def get_categories(self) -> List[str]:
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM books")
            return [row[0] for row in cursor.fetchall()]

    def get_overdue_loans(self) -> List[Dict[str, Any]]:
        """Get all overdue book loans"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        t.id,
                        b.title as book_title,
                        m.name as member_name,
                        m.email as member_email,
                        t.issue_date,
                        JULIANDAY('now') - JULIANDAY(t.issue_date) as days_overdue
                    FROM transactions t
                    JOIN books b ON t.book_id = b.id
                    JOIN members m ON t.member_id = m.id
                    WHERE t.return_date IS NULL 
                    AND JULIANDAY('now') - JULIANDAY(t.issue_date) > ?
                    ORDER BY days_overdue DESC
                """, (Config.LOAN_PERIOD_DAYS,))
                overdue = cursor.fetchall()
                return [dict(loan) for loan in overdue]
        except Exception as e:
            logger.error(f"Error getting overdue loans: {e}")
            return []

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as a list of dictionaries
        
        Args:
            query: SQL query string with placeholders
            params: Tuple of parameters to substitute in query
            
        Returns:
            List of dictionaries containing query results
        """
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                # Get column names from cursor description
                columns = [desc[0] for desc in cursor.description]
                
                # Convert results to list of dictionaries
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                    
                return results
                
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise Exception(f"Query execution failed: {e}")

    def get_loans(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent loans with basic information"""
        query = """
            SELECT l.id, b.title as book_title, m.name as member_name, l.loan_date
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN members m ON l.member_id = m.id
            WHERE l.return_date IS NULL
            ORDER BY l.loan_date DESC
            LIMIT ?
        """
        return self.execute_query(query, (limit,))

    def get_returns(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent returns with basic information"""
        query = """
            SELECT l.id, b.title as book_title, m.name as member_name, l.return_date
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN members m ON l.member_id = m.id
            WHERE l.return_date IS NOT NULL
            ORDER BY l.return_date DESC
            LIMIT ?
        """
        return self.execute_query(query, (limit,))

    def get_member(self, member_id: int) -> Optional[Dict[str, Any]]:
        """Get member details by ID"""
        try:
            member_id = DataValidator.validate_integer(member_id, "Member ID", min_value=1)
            
            def operation(conn):
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM members WHERE id = ?', (member_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
                
            return self._execute_with_retry(operation)
                
        except Exception as e:
            logger.error(f"Error getting member by ID: {e}")
            raise
