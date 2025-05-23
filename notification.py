import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from config import Config
import re
import time
from functools import wraps

class NotificationError(Exception):
    """Custom exception for notification-related errors"""
    pass

def rate_limit(max_calls: int, time_frame: int):
    """Rate limiting decorator"""
    calls = []
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            calls[:] = [call for call in calls if call > now - time_frame]
            if len(calls) >= max_calls:
                raise NotificationError("Rate limit exceeded")
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

logger = logging.getLogger(__name__)

class NotificationSystem:
    MAX_RETRY_ATTEMPTS = 3
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    def __init__(self, db):
        if not db:
            raise ValueError("Database connection cannot be None")
        self.db = db
        self.logger = logging.getLogger(__name__)

    def send_message(self, message: str) -> None:
        logger.info(f"Notification sent: {message}")
        # In tests, this method may be patched to record calls.

    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        return bool(email and isinstance(email, str) and self.EMAIL_PATTERN.match(email))

    def _validate_loan_data(self, loan: Dict[str, Any]) -> bool:
        """Validate loan data"""
        required_fields = ['member_id', 'isbn', 'due_date']
        return all(field in loan and loan[field] for field in required_fields)

    @rate_limit(max_calls=100, time_frame=3600)  # 100 notifications per hour
    def notify_overdue_books(self, overdue_loans: List[Dict[str, Any]]) -> None:
        """Send notifications for overdue books"""
        if not overdue_loans:
            self.logger.info("No overdue books to process")
            return

        message = f"You have {len(overdue_loans)} overdue book(s)."
        self.send_message(message)

        for loan in overdue_loans:
            try:
                if not self._validate_loan_data(loan):
                    raise ValueError(f"Invalid loan data: {loan}")

                member = self.db.get_member(loan['member_id'])
                if not member or not member.get('email') or not member.get('name'):
                    raise ValueError(f"Invalid member data for ID: {loan['member_id']}")

                if not self._validate_email(member['email']):
                    raise ValueError(f"Invalid email address: {member['email']}")

                book = self.db.get_book(loan['isbn'])
                if not book or not book.get('title'):
                    raise ValueError(f"Invalid book data for ISBN: {loan['isbn']}")

                days_overdue = (datetime.now() - loan['due_date']).days
                
                message = self._create_overdue_message(
                    member['name'],
                    book['title'],
                    days_overdue,
                    loan['due_date']
                )
                
                self._send_email_with_retry(
                    member['email'],
                    "Library Book Overdue Notice",
                    message
                )
                
            except Exception as e:
                self.logger.error(f"Error processing overdue loan: {e}")
                continue

    def _create_overdue_message(self, 
                              member_name: str,
                              book_title: str,
                              days_overdue: int,
                              due_date: datetime) -> str:
        """Create the overdue notification message"""
        if not all([member_name, book_title, isinstance(days_overdue, int), 
                   isinstance(due_date, datetime)]):
            raise ValueError("Invalid parameters for creating message")

        return f"""
        Dear {member_name},

        This is a reminder that the following book is overdue:

        Title: {book_title}
        Due Date: {due_date.strftime('%B %d, %Y')}
        Days Overdue: {days_overdue}

        Please return the book as soon as possible to avoid additional fees.

        Best regards,
        Library Management System
        """

    def _send_email_with_retry(self, to_email: str, subject: str, message: str) -> None:
        """Send email with retry mechanism"""
        if not all([to_email, subject, message]):
            raise ValueError("Email parameters cannot be empty")

        for attempt in range(self.MAX_RETRY_ATTEMPTS):
            try:
                self._send_email(to_email, subject, message)
                return
            except Exception as e:
                if attempt == self.MAX_RETRY_ATTEMPTS - 1:
                    raise NotificationError(f"Failed to send email after {self.MAX_RETRY_ATTEMPTS} attempts")
                self.logger.warning(f"Retry attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def _send_email(self, to_email: str, subject: str, message: str) -> None:
        """Send email using configured SMTP server"""
        if not self._validate_email(to_email):
            raise ValueError(f"Invalid email address: {to_email}")

        try:
            if not all([Config.SMTP_SERVER, Config.SMTP_PORT, Config.SMTP_USER, 
                       Config.SMTP_PASSWORD, Config.SMTP_FROM]):
                raise ValueError("SMTP configuration is incomplete")

            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = Config.SMTP_FROM
            msg['To'] = to_email
            
            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                if Config.SMTP_USE_TLS:
                    server.starttls()
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.send_message(msg)
                
        except Exception as e:
            self.logger.error(f"Error sending email to {to_email}: {e}")
            raise NotificationError(f"Failed to send email: {str(e)}")
