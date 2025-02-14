import sqlite3
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from functools import lru_cache
from queue import Queue
from config import Config
import logging
from utils import hash_password, verify_password  # Updated import
from datetime import datetime  # New import

logger = logging.getLogger(__name__)

class DatabasePool:
    def __init__(self):
        # Initialize database connection pool
        self.pool = Queue(maxsize=Config.CONNECTION_POOL_SIZE)
        for _ in range(Config.CONNECTION_POOL_SIZE):
            conn = sqlite3.connect(Config.DB_PATH)
            self.pool.put(conn)

    @contextmanager
    def get_connection(self):
        # Get database connection
        conn = self.pool.get()
        conn.row_factory = sqlite3.Row  # Set row_factory to return dictionaries
        try:
            yield conn
        finally:
            self.pool.put(conn)

class DatabaseHandler:
    def __init__(self):
        self.pool = DatabasePool()
        self.create_tables()
        self.create_default_user()  # Ensure default user is created

    def create_tables(self):
        """Create necessary database tables if they don't exist"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Ensure correct users table structure
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL, -- Hashed password using Argon2
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        """
        Authenticate a user with username and password
        Now using Argon2 verification instead of direct hash comparison
        """
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT id, username, password_hash, role FROM users WHERE username = ?"
                cursor.execute(query, (username,))
                user = cursor.fetchone()
                
                if user and verify_password(password, user['password_hash']):  # Using verify_password instead of comparing hashes
                    return {
                        'id': user['id'],
                        'username': user['username'],
                        'role': user['role']
                    }
                return None
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

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

    @lru_cache(maxsize=100)
    def get_book_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM books WHERE isbn = ?', (isbn,))
            result = cursor.fetchone()
            return dict(result) if result else None

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

    def add_member(self, name: str, email: str, phone: str):
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO members (name, email, phone, join_date) VALUES (?, ?, ?, ?)',
                           (name, email, phone, datetime.now()))
            conn.commit()

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
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO books (title, author, isbn, quantity, available, category) VALUES (?, ?, ?, ?, ?, ?)',
                           (title, author, isbn, quantity, quantity, category))
            conn.commit()
            logger.info(f"Book '{title}' added to the database.")

    def return_book(self, member_id: int, isbn: str) -> None:
        """Process book return"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Get book ID
                cursor.execute("SELECT id FROM books WHERE isbn = ?", (isbn,))
                book = cursor.fetchone()
                if not book:
                    raise ValueError("Book does not exist.")
                book_id = book['id']

                # Check if loan record exists
                cursor.execute("""
                    SELECT id FROM transactions 
                    WHERE member_id = ? AND book_id = ? AND return_date IS NULL
                """, (member_id, book_id))
                loan = cursor.fetchone()
                if not loan:
                    raise ValueError("No unreturned loan record found.")

                # Update loan record as returned
                returned_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    UPDATE transactions
                    SET return_date = ?, status = 'returned'
                    WHERE id = ?
                """, (returned_at, loan['id']))

                # Increase available book quantity
                cursor.execute("""
                    UPDATE books
                    SET available = available + 1
                    WHERE id = ?
                """, (book_id,))

                conn.commit()
                logger.info(f"Book ISBN {isbn} has been returned by member ID {member_id}.")
            except Exception as e:
                conn.rollback()
                logger.error(f"Book return failed: {e}")
                raise e

    def issue_book(self, member_id: int, isbn: str) -> None:
        """Issue book to member"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Check if book exists and is available
                cursor.execute("SELECT id, available FROM books WHERE isbn = ?", (isbn,))
                book = cursor.fetchone()
                if not book:
                    raise ValueError("Book does not exist.")
                if book['available'] <= 0:
                    raise ValueError("No copies available.")

                # Check if member exists
                cursor.execute("SELECT id FROM members WHERE id = ?", (member_id,))
                member = cursor.fetchone()
                if not member:
                    raise ValueError("Member does not exist.")

                # Create loan record
                cursor.execute("""
                    INSERT INTO transactions (book_id, member_id, issue_date, status)
                    VALUES (?, ?, ?, 'issued')
                """, (book['id'], member_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

                # Decrease available book quantity
                cursor.execute("""
                    UPDATE books
                    SET available = available - 1
                    WHERE id = ?
                """, (book['id'],))

                conn.commit()
                logger.info(f"Book ISBN {isbn} successfully issued to member ID {member_id}.")
            except Exception as e:
                conn.rollback()
                logger.error(f"Book issue failed: {e}")
                raise e

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
