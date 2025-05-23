import unittest
from database import DatabaseHandler, ValidationError
from config import Config
import os
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from notification import NotificationSystem
from session import Session
from ui import LoginWindow, MainWindow
import tkinter as tk
from unittest.mock import Mock, patch

# Setup logging
logger = logging.getLogger(__name__)

class TestLibrarySystem(unittest.TestCase):
    def setUp(self):
        """Setup test environment"""
        # Use a test database file
        Config.DB_PATH = 'test_library.db'
        
        # Try to remove existing test database with retries
        max_retries = 3
        retry_delay = 1  # seconds
        
        # First, make sure any existing DB handler is cleaned up
        if hasattr(self, 'db'):
            try:
                for conn in self.db.pool.pool.queue:
                    conn.close()
                self.db = None
            except Exception:
                pass
        
        # Then try to remove the file
        for attempt in range(max_retries):
            try:
                if os.path.exists(Config.DB_PATH):
                    os.remove(Config.DB_PATH)
                break
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise RuntimeError(f"Cannot access {Config.DB_PATH}. Please ensure no other processes are using it.")
        
        try:
            # Create database and tables first
            conn = sqlite3.connect(Config.DB_PATH)
            cursor = conn.cursor()
            
            # Create users table first
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    login_attempts INTEGER DEFAULT 0
                )
            """)
            conn.commit()
            conn.close()
            
            # Now initialize the database handler
            self.db = DatabaseHandler()
            
            # Set the highest isolation level for the test database
            with self.db.pool.get_connection() as conn:
                conn.isolation_level = None  # This enables autocommit mode
                conn.execute('PRAGMA journal_mode=WAL')  # Use WAL mode for better concurrency
                conn.execute('PRAGMA synchronous=NORMAL')  # Ensure synchronous writes
                
        except Exception as e:
            logger.error(f"Error in setUp: {e}")
            if os.path.exists(Config.DB_PATH):
                try:
                    os.remove(Config.DB_PATH)
                except Exception:
                    pass
            raise
        
    def tearDown(self):
        """Cleanup after tests"""
        try:
            # Close all connections first
            if hasattr(self, 'db'):
                for conn in self.db.pool.pool.queue:
                    conn.close()
            
            # Try to remove test database with retries
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    if os.path.exists(Config.DB_PATH):
                        os.remove(Config.DB_PATH)
                    break
                except PermissionError:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    logger.warning(f"Could not remove {Config.DB_PATH} after {max_retries} attempts")
        except Exception as e:
            logger.error(f"Error in tearDown: {e}")

    def test_user_authentication(self):
        """Test user authentication"""
        # Test default admin login
        user = self.db.authenticate_user("1", "1")
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "1")
        self.assertEqual(user['role'], "1")

    def test_book_management(self):
        """Test book operations"""
        # Test adding a book
        self.db.add_book(
            title="Test Book",
            author="Test Author",
            isbn="1234567890",
            quantity=5,
            category="Test"
        )
        
        # Test searching for the book
        books = self.db.search_books("Test Book")
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]['title'], "Test Book")
        self.assertEqual(books[0]['available'], 5)

    def test_member_management(self):
        """Test member operations"""
        # Test adding a member
        self.db.add_member(
            name="Test Member",
            email="test@example.com",
            phone="1234567890"
        )
        
        # Test getting all members
        members = self.db.get_all_members()
        self.assertGreaterEqual(len(members), 1)
        self.assertTrue(any(m['name'] == "Test Member" for m in members))

    def test_book_loan_operations(self):
        """Test book loan operations"""
        # Add test book
        self.db.add_book(
            title="Loan Test Book",
            author="Test Author",
            isbn="9876543210",  # Valid ISBN-10
            quantity=1,
            category="Test"
        )
        
        # Verify initial book state
        book = self.db.get_book_by_isbn("9876543210")
        self.assertIsNotNone(book, "Book should exist")
        self.assertEqual(book['available'], 1, "Initial available count should be 1")
        
        # Add test member
        self.db.add_member(
            name="Loan Test Member",
            email="loan@example.com",
            phone="9876543210"
        )
        
        # Get member ID
        members = self.db.get_all_members()
        member_id = next(m['id'] for m in members if m['name'] == "Loan Test Member")
        
        # Test issuing book
        self.db.issue_book(member_id, "9876543210")
        
        # Get fresh copy of book after issuing
        book = self.db.get_book_by_isbn("9876543210")
        self.assertEqual(book['available'], 0, "Available count should be 0 after issuing")
        
        # Test returning book
        self.db.return_book(member_id, "9876543210")
        
        # Get fresh copy of book after returning
        book = self.db.get_book_by_isbn("9876543210")
        self.assertEqual(book['available'], 1, "Available count should be 1 after return")

    def test_validation(self):
        """Test input validation"""
        # Test invalid ISBN
        with self.assertRaises(ValidationError):
            self.db.add_book(
                title="Invalid Book",
                author="Author",
                isbn="invalid",
                quantity=1,
                category="Test"
            )
            
        # Test invalid email
        with self.assertRaises(ValidationError):
            self.db.add_member(
                name="Invalid Member",
                email="invalid-email",
                phone="1234567890"
            )

    def test_database_pool(self):
        """Test database connection pool functionality"""
        # Test pool size
        self.assertEqual(len(self.db.pool.pool.queue), Config.CONNECTION_POOL_SIZE)
        
        # Test connection acquisition and release
        with self.db.pool.get_connection() as conn:
            self.assertIsInstance(conn, sqlite3.Connection)
            self.assertEqual(len(self.db.pool.pool.queue), Config.CONNECTION_POOL_SIZE - 1)
        self.assertEqual(len(self.db.pool.pool.queue), Config.CONNECTION_POOL_SIZE)

    def test_book_loan_edge_cases(self):
        """Test edge cases for book loans"""
        # Setup test data
        self.db.add_book(
            title="Edge Case Book",
            author="Test Author",
            isbn="1234567891",
            quantity=1,
            category="Test"
        )
        self.db.add_member(
            name="Edge Case Member",
            email="edge@test.com",
            phone="1234567890"
        )
        
        members = self.db.get_all_members()
        member_id = next(m['id'] for m in members if m['name'] == "Edge Case Member")
        
        # Test issuing more books than available
        self.db.issue_book(member_id, "1234567891")
        with self.assertRaises(ValidationError):
            self.db.issue_book(member_id, "1234567891")
            
        # Test returning already returned book
        self.db.return_book(member_id, "1234567891")
        with self.assertRaises(ValidationError):
            self.db.return_book(member_id, "1234567891")

    def test_overdue_book_handling(self):
        """Test overdue book detection and handling"""
        # Add test book and member
        self.db.add_book(
            title="Overdue Book",
            author="Test Author",
            isbn="1234567892",
            quantity=1,
            category="Test"
        )
        self.db.add_member(
            name="Overdue Member",
            email="overdue@test.com",
            phone="1234567890"
        )
        
        members = self.db.get_all_members()
        member_id = next(m['id'] for m in members if m['name'] == "Overdue Member")
        
        # Issue book
        self.db.issue_book(member_id, "1234567892")
        
        # Get overdue loans
        overdue_loans = self.db.get_overdue_loans()
        self.assertIsInstance(overdue_loans, list)

    def test_category_management(self):
        """Test category management functionality"""
        # Add books with different categories
        categories = ["Fiction", "Non-Fiction", "Science"]
        for i, category in enumerate(categories):
            self.db.add_book(
                title=f"Category Test Book {i}",
                author="Test Author",
                isbn=f"978000000000{i}",  # Valid ISBN-13 format
                quantity=1,
                category=category
            )
            
        # Test category retrieval
        db_categories = self.db.get_categories()
        for category in categories:
            self.assertIn(category, db_categories)
            
        # Test books by category
        category_counts = self.db.get_books_by_category()
        self.assertGreaterEqual(len(category_counts), len(categories))

    def test_search_functionality(self):
        """Test search functionality with filters"""
        # Add test books
        self.db.add_book(
            title="Python Programming",
            author="John Doe",
            isbn="1234567894",
            quantity=1,
            category="Programming"
        )
        self.db.add_book(
            title="Advanced Python",
            author="Jane Smith",
            isbn="1234567895",
            quantity=1,
            category="Programming"
        )
        
        # Test search by title
        results = self.db.search_books("Python")
        self.assertEqual(len(results), 2)
        
        # Test search by author
        results = self.db.search_books("John")
        self.assertEqual(len(results), 1)
        
        # Test search by category
        results = self.db.search_books("Programming")
        self.assertEqual(len(results), 2)

    def test_transaction_history(self):
        """Test transaction history tracking"""
        # Add test book and member
        self.db.add_book(
            title="History Test Book",
            author="Test Author",
            isbn="1234567896",
            quantity=1,
            category="Test"
        )
        self.db.add_member(
            name="History Test Member",
            email="history@test.com",
            phone="1234567890"
        )
        
        members = self.db.get_all_members()
        member_id = next(m['id'] for m in members if m['name'] == "History Test Member")
        
        # Create loan and return
        self.db.issue_book(member_id, "1234567896")
        self.db.return_book(member_id, "1234567896")
        
        # Check loan history
        history = self.db.get_book_loan_history("1234567896")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['status'], 'returned')

    def test_notification_system(self):
        """Test notification system functionality"""
        # Setup notification system
        notification = NotificationSystem(self.db)
        
        # Setup test data
        self.db.add_member(
            name="Test User",
            email="test@example.com",
            phone="1234567890"
        )
        self.db.add_book(
            title="Test Book",
            author="Test Author",
            isbn="1234567897",
            quantity=1,
            category="Test"
        )
        
        # Create an overdue loan
        loan = {
            'member_id': 1,
            'isbn': '1234567897',
            'due_date': datetime.now() - timedelta(days=5),
            'book_title': 'Test Book',
            'member_name': 'Test User',
            'member_email': 'test@example.com'
        }
        
        # Test overdue notification with proper mocking
        with patch('smtplib.SMTP') as mock_smtp:
            instance = mock_smtp.return_value
            notification.notify_overdue_books([loan])
            self.assertTrue(instance.send_message.called)

        # Test rate limiting
        with self.assertRaises(Exception):
            for _ in range(101):  # Exceed rate limit of 100 per hour
                notification.notify_overdue_books([loan])

    def test_session_management(self):
        """Test session management"""
        # Create test user session
        user = {'id': 1, 'username': 'test', 'role': 'admin'}
        session = Session(user)
        
        # Test initial session validity
        self.assertTrue(session.is_valid())
        
        # Test session timeout
        with patch('time.time') as mock_time:
            # Simulate time passing beyond timeout
            mock_time.return_value = time.time() + Config.SESSION_TIMEOUT + 1
            self.assertFalse(session.is_valid())
        
        # Test session refresh
        session.refresh()
        self.assertTrue(session.is_valid())

    def test_error_recovery(self):
        """Test error recovery scenarios"""
        # Test database connection loss
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.OperationalError("Connection failed")
            with self.assertRaises(RuntimeError):
                db = DatabaseHandler()
        
        # Test transaction rollback
        self.db.add_book(
            title="Rollback Test",
            author="Test Author",
            isbn="9876543211",
            quantity=1,
            category="Test"
        )
        
        # Attempt invalid operation that should trigger rollback
        with self.assertRaises(ValidationError):
            self.db.issue_book(999, "9876543211")  # Invalid member ID
        
        # Verify book quantity remained unchanged
        book = self.db.get_book_by_isbn("9876543211")
        self.assertEqual(book['available'], 1)

    @unittest.skipIf(not hasattr(tk, 'Tk'), "Tkinter not available")
    def test_ui_components(self):
        """Test UI components"""
        root = tk.Tk()
        
        # Create a basic mock style
        mock_style = Mock()
        mock_style.configure = Mock()
        mock_style.tk = root
        
        # Patch both Style and ThemedStyle
        with patch('tkinter.ttk.Style', return_value=mock_style), \
             patch('ttkthemes.themed_style.ThemedStyle', return_value=mock_style):
            window = MainWindow(root, self.db, Session({'id': 1, 'username': 'test', 'role': 'admin'}))
            window.toggle_theme()
            self.assertTrue(mock_style.configure.called)
        
        # Test form validation
        window.book_entries = {
            'Title:': Mock(get=lambda: ''),
            'Author:': Mock(get=lambda: 'Test Author'),
            'ISBN:': Mock(get=lambda: 'invalid-isbn'),
            'Quantity:': Mock(get=lambda: '1'),
            'Category:': Mock(get=lambda: 'Test')
        }
        
        with self.assertRaises(ValidationError):
            window.add_book()
        
        root.destroy()

    def test_concurrent_operations(self):
        """Test concurrent database operations"""
        import threading
        
        def concurrent_book_add(isbn):
            try:
                self.db.add_book(
                    title=f"Concurrent Test {isbn}",
                    author="Test Author",
                    isbn=isbn,
                    quantity=1,
                    category="Test"
                )
            except ValidationError:
                pass
        
        # Try to add same book concurrently
        threads = []
        for i in range(5):
            t = threading.Thread(target=concurrent_book_add, args=(f"97800000000{i}",))
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Verify no duplicate ISBNs were added
        books = self.db.get_all_books()
        isbns = [b['isbn'] for b in books]
        self.assertEqual(len(isbns), len(set(isbns)))  # No duplicates

if __name__ == '__main__':
    unittest.main()