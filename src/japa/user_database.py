"""
SQLite database for user management.
"""
import datetime
import logging
import os
import sqlite3
import uuid
from typing import Dict, List, Optional, Set, Tuple, Any

# Configure logging
logger = logging.getLogger("UserDatabase")

class UserDatabase:
    """Database access layer for user management."""
    
    def __init__(self, db_path: str = "users.db", debug: bool = False):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file
            debug: Enable debug mode with extra logging
        """
        if debug:
            logger.setLevel(logging.DEBUG)
            
        logger.info(f"Initializing UserDatabase with database file: {db_path}")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables_if_not_exist()
    
    def _create_tables_if_not_exist(self) -> None:
        """Create database tables if they don't exist."""
        logger.debug("Creating tables if they don't exist")
        cursor = self.conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT CHECK(role IN ('regular', 'admin', 'superadmin')),
            registration_date TEXT,
            last_active TEXT
        )
        ''')
        
        # Create pending_requests table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_requests (
            request_id TEXT PRIMARY KEY,
            user_id INTEGER,
            username TEXT,
            request_time TEXT,
            reason TEXT,
            expires TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        
        self.conn.commit()
        logger.debug("Database tables created/verified")
    
    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.debug("Database connection closed")
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user data by user ID.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dict: User data dictionary or None if user not found
        """
        logger.debug(f"Getting user with ID: {user_id}")
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Get all users from the database.
        
        Returns:
            List: List of user data dictionaries
        """
        logger.debug("Getting all users")
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY role, username')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """
        Get users with a specific role.
        
        Args:
            role: User role ("regular", "admin", "superadmin")
            
        Returns:
            List: List of user data dictionaries
        """
        logger.debug(f"Getting users with role: {role}")
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE role = ? ORDER BY username', (role,))
        return [dict(row) for row in cursor.fetchall()]
    
    def add_user(self, user_id: int, username: str, role: str = 'regular') -> bool:
        """
        Add a new user.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            role: User role ("regular", "admin", "superadmin")
            
        Returns:
            bool: True if user was added successfully, False otherwise
        """
        logger.info(f"Adding user: {user_id} (@{username}) with role {role}")
        
        # Check if user already exists
        if self.get_user(user_id):
            logger.warning(f"User {user_id} already exists")
            return False
        
        try:
            cursor = self.conn.cursor()
            now = datetime.datetime.now().isoformat()
            cursor.execute(
                'INSERT INTO users (user_id, username, role, registration_date, last_active) VALUES (?, ?, ?, ?, ?)',
                (user_id, username, role, now, now)
            )
            self.conn.commit()
            logger.info(f"User {user_id} added successfully")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding user {user_id}: {str(e)}")
            self.conn.rollback()
            return False
    
    def update_user_role(self, user_id: int, new_role: str) -> bool:
        """
        Update a user's role.
        
        Args:
            user_id: Telegram user ID
            new_role: New role ("regular", "admin", "superadmin")
            
        Returns:
            bool: True if user's role was updated successfully, False otherwise
        """
        logger.info(f"Updating user {user_id} to role {new_role}")
        
        # Check if user exists
        if not self.get_user(user_id):
            logger.warning(f"User {user_id} not found")
            return False
        
        try:
            cursor = self.conn.cursor()
            now = datetime.datetime.now().isoformat()
            cursor.execute(
                'UPDATE users SET role = ?, last_active = ? WHERE user_id = ?',
                (new_role, now, user_id)
            )
            self.conn.commit()
            logger.info(f"User {user_id} updated to role {new_role}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            self.conn.rollback()
            return False
    
    def update_last_active(self, user_id: int) -> bool:
        """
        Update a user's last active timestamp.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if timestamp was updated successfully, False otherwise
        """
        logger.debug(f"Updating last active timestamp for user {user_id}")
        
        try:
            cursor = self.conn.cursor()
            now = datetime.datetime.now().isoformat()
            cursor.execute(
                'UPDATE users SET last_active = ? WHERE user_id = ?',
                (now, user_id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating timestamp for user {user_id}: {str(e)}")
            self.conn.rollback()
            return False
    
    def remove_user(self, user_id: int) -> bool:
        """
        Remove a user from the database.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if user was removed successfully, False otherwise
        """
        logger.info(f"Removing user {user_id}")
        
        # Check if user exists
        if not self.get_user(user_id):
            logger.warning(f"User {user_id} not found")
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # Remove pending requests
            cursor.execute('DELETE FROM pending_requests WHERE user_id = ?', (user_id,))
            
            # Remove user
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            
            self.conn.commit()
            logger.info(f"User {user_id} removed successfully")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error removing user {user_id}: {str(e)}")
            self.conn.rollback()
            return False
    
    def get_registered_users(self) -> Set[int]:
        """
        Get all registered user IDs.
        
        Returns:
            Set: Set of registered user IDs
        """
        logger.debug("Getting registered users")
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        return {row[0] for row in cursor.fetchall()}
    
    def create_admin_request(self, user_id: int, username: str, reason: str) -> Optional[str]:
        """
        Create a new admin request.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            reason: Reason for the request
            
        Returns:
            str: Request ID if created successfully, None otherwise
        """
        logger.info(f"Creating admin request for user {user_id} (@{username})")
        
        try:
            cursor = self.conn.cursor()
            request_id = f"req_{uuid.uuid4().hex[:8]}"
            now = datetime.datetime.now()
            request_time = now.isoformat()
            
            # Request expires in 24 hours
            expires = (now + datetime.timedelta(hours=24)).isoformat()
            
            cursor.execute(
                'INSERT INTO pending_requests VALUES (?, ?, ?, ?, ?, ?)',
                (request_id, user_id, username, request_time, reason, expires)
            )
            
            self.conn.commit()
            logger.info(f"Admin request {request_id} created for user {user_id}")
            return request_id
        except sqlite3.Error as e:
            logger.error(f"Error creating admin request for user {user_id}: {str(e)}")
            self.conn.rollback()
            return None
    
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """
        Get all pending admin requests.
        
        Returns:
            List: List of pending request dictionaries
        """
        logger.debug("Getting pending admin requests")
        cursor = self.conn.cursor()
        
        # Clean expired requests first
        self._clean_expired_requests()
        
        cursor.execute('SELECT * FROM pending_requests ORDER BY request_time')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific admin request.
        
        Args:
            request_id: Request ID
            
        Returns:
            Dict: Request data dictionary or None if not found
        """
        logger.debug(f"Getting admin request {request_id}")
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM pending_requests WHERE request_id = ?', (request_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def approve_request(self, request_id: str) -> Tuple[bool, str]:
        """
        Approve an admin request.
        
        Args:
            request_id: Request ID
            
        Returns:
            Tuple: (success, message)
        """
        logger.info(f"Approving admin request {request_id}")
        
        request = self.get_request(request_id)
        if not request:
            return False, "Request not found"
        
        user_id = request["user_id"]
        
        # Update user role to admin
        if self.update_user_role(user_id, "admin"):
            # Remove the request
            self.remove_request(request_id)
            return True, f"User {request['username']} promoted to admin"
        else:
            return False, f"Failed to promote user {request['username']}"
    
    def deny_request(self, request_id: str) -> bool:
        """
        Deny an admin request.
        
        Args:
            request_id: Request ID
            
        Returns:
            bool: True if request was denied successfully, False otherwise
        """
        logger.info(f"Denying admin request {request_id}")
        
        # Just remove the request
        return self.remove_request(request_id)
    
    def remove_request(self, request_id: str) -> bool:
        """
        Remove an admin request.
        
        Args:
            request_id: Request ID
            
        Returns:
            bool: True if request was removed successfully, False otherwise
        """
        logger.debug(f"Removing admin request {request_id}")
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM pending_requests WHERE request_id = ?', (request_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error removing admin request {request_id}: {str(e)}")
            self.conn.rollback()
            return False
    
    def _clean_expired_requests(self) -> None:
        """Remove expired admin requests."""
        logger.debug("Cleaning expired admin requests")
        
        try:
            cursor = self.conn.cursor()
            now = datetime.datetime.now().isoformat()
            cursor.execute('DELETE FROM pending_requests WHERE expires < ?', (now,))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error cleaning expired requests: {str(e)}")
            self.conn.rollback()
    
    def migrate_from_json(self, json_file: str) -> Tuple[int, int]:
        """
        Migrate users from a JSON file to the SQLite database.
        
        Args:
            json_file: Path to the JSON file
            
        Returns:
            Tuple: (num_migrated, num_failed)
        """
        logger.info(f"Migrating users from {json_file}")
        
        import json
        
        if not os.path.exists(json_file):
            logger.warning(f"JSON file {json_file} not found")
            return 0, 0
        
        num_migrated = 0
        num_failed = 0
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
                # Simple format with just user IDs
                if 'users' in data and isinstance(data['users'], list):
                    for user_id in data['users']:
                        if self.add_user(user_id, f"user_{user_id}", "regular"):
                            num_migrated += 1
                        else:
                            num_failed += 1
                            
                # Advanced format with user details
                elif 'users' in data and isinstance(data['users'], dict):
                    for user_id_str, user_data in data['users'].items():
                        user_id = int(user_id_str)
                        username = user_data.get('username', f"user_{user_id}")
                        role = user_data.get('role', 'regular')
                        
                        if self.add_user(user_id, username, role):
                            num_migrated += 1
                        else:
                            num_failed += 1
                            
            logger.info(f"Migration complete: {num_migrated} users migrated, {num_failed} failed")
            return num_migrated, num_failed
        except Exception as e:
            logger.error(f"Error migrating users from JSON: {str(e)}")
            return 0, 0 