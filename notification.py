import logging
from typing import List, Dict, Any
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from config import Config

class NotificationSystem:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
    def notify_overdue_books(self, overdue_loans: List[Dict[str, Any]]) -> None:
        """Send notifications for overdue books"""
        try:
            for loan in overdue_loans:
                member = self.db.get_member(loan['member_id'])
                book = self.db.get_book(loan['isbn'])
                
                days_overdue = (datetime.now() - loan['due_date']).days
                
                message = self._create_overdue_message(
                    member['name'],
                    book['title'],
                    days_overdue,
                    loan['due_date']
                )
                
                self._send_email(
                    member['email'],
                    "Library Book Overdue Notice",
                    message
                )
                
        except Exception as e:
            self.logger.error(f"Error sending overdue notifications: {e}")

    def _create_overdue_message(self, 
                              member_name: str,
                              book_title: str,
                              days_overdue: int,
                              due_date: datetime) -> str:
        """Create the overdue notification message"""
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

    def _send_email(self, to_email: str, subject: str, message: str) -> None:
        """Send email using configured SMTP server"""
        try:
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
