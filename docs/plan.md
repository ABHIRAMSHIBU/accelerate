# JAPA Authentication Implementation Plan

## Overview

This document outlines the plan to implement authentication and admin privileges for the JAPA bot. We need to establish a proper permission system to:

1. Allow all users to view service statuses
2. Restrict restart/rebuild operations to admin users only
3. Create a super admin role with the ability to promote other users to admin status
4. Implement a secure workflow for promoting regular users to admin

## Current System Analysis

The current implementation has:
- A `registered_users` set that tracks who receives notifications
- No concept of roles or permission levels
- All commands are available to any registered user
- User data is saved in a simple `users.json` file

## Implementation Plan

### 1. User Role Management

#### 1.1 Data Structure Update
- Replace simple `registered_users` set with a comprehensive user management system
- Store user information in SQLite database instead of JSON:
  - `user_id`: Telegram user ID (primary key)
  - `username`: Telegram username 
  - `role`: User role (enum: "regular", "admin", "superadmin")
  - `registration_date`: When the user was registered
  - `last_active`: Last activity timestamp

#### 1.2 Database Schema
- Create a SQLite database with the following tables:
  ```sql
  CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    role TEXT CHECK(role IN ('regular', 'admin', 'superadmin')),
    registration_date TEXT,
    last_active TEXT
  );
  
  CREATE TABLE pending_requests (
    request_id TEXT PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    request_time TEXT,
    reason TEXT,
    expires TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
  );
  ```

#### 1.3 Migration Strategy
- Implement a migration script to transfer existing users from JSON to SQLite
- Ensure backward compatibility during transition

#### 1.4 Configuration Options
- Follow the separation of concerns principle:
  - JAPA config remains focused on service health checking and management
  - Add separate Telegram interface config for UI-specific settings
- Add super admin configuration options to:
  - Telegram config file (`superadmin_ids` array)
  - Command line arguments (`--superadmin-id`)
  - Environment variables (`JAPA_SUPERADMIN_ID`)

### 2. Authentication System

#### 2.1 Permission Checking
- Create a decorator/utility function `check_permission(update, required_role)` to verify user permissions
- Apply this to command handlers where appropriate
- Implement "denied access" response for unauthorized users

#### 2.2 Command Security
- Keep `/status`, `/list`, `/start`, `/stop`, `/help` available to all users
- Restrict `/restart` and `/rebuild` to users with "admin" or "superadmin" roles
- Create new admin-only commands:
  - `/admins` - List current admins
  - `/promote` - Promote a user to admin (superadmin only)
  - `/demote` - Demote an admin to regular user (superadmin only)
  - `/remove` - Completely remove a user from the database (superadmin only)

### 3. User Promotion Workflow

#### 3.1 Direct Promotion (Admin → Admin)
- Admins can promote other users with simple command:
  - `/promote @username` or `/promote <user_id>`
- Immediate effect with confirmation message

#### 3.2 Regular User Promotion Request
- Regular users can request admin status:
  - `/requestadmin [reason]`
- System will:
  1. Log the request
  2. Send request to all superadmins
  3. Allow superadmins to approve/deny with inline buttons

#### 3.3 Approval Mechanism
- Implement inline keyboard buttons for approval
  - "Approve" / "Deny" buttons
  - Include request reference ID
- Track pending requests with timeout/expiration

### 4. Command Implementation

#### 4.1 New Admin Commands
```
/admins - List all admins
/promote <user_id or @username> - Promote a user to admin 
/demote <user_id or @username> - Demote an admin to regular user
/remove <user_id or @username> - Remove a user completely from the database
/requestadmin [reason] - Request admin privileges (for regular users)
```

#### 4.2 Interface Separation
- Ensure proper separation of concerns:
  - JAPA should remain independent and not hardcode Telegram-specific logic
  - Telegram interface handles all UI/bot specific behaviors
  - Admin configuration should be specific to the interface (Telegram) not JAPA core

#### 4.3 Super Admin Identification
- Add command line option for setting super admin: `--superadmin <user_id>`
- Allow configuration via Telegram config file: `"superadmin_ids": [123456789]`
- Support environment variable: `JAPA_SUPERADMIN_ID=123456789`

### 5. CLI User Management Tool

#### 5.1 Features
- View all users and their roles
- Add new users with specified roles
- Remove users from the system
- Promote/demote users between roles
- Export user data for backup
- View and manage pending admin requests

#### 5.2 Command Structure
```
japa-admin users list [--role <role>]          # List all users or filter by role
japa-admin users add <user_id> [--role <role>] # Add a new user
japa-admin users remove <user_id>              # Remove a user
japa-admin users promote <user_id>             # Promote a user
japa-admin users demote <user_id>              # Demote a user
japa-admin users export [--format <format>]    # Export user data
japa-admin requests list                       # List pending requests
japa-admin requests approve <request_id>       # Approve a request
japa-admin requests deny <request_id>          # Deny a request
```

#### 5.3 Implementation
- Implement as a standalone Python script
- Use argparse for command-line arguments
- Share database connection code with main application
- Include comprehensive help text and examples

### 6. Implementation Phases

#### Phase 1: SQLite Database Setup
1. Create SQLite database schema
2. Implement data access layer for user management
3. Migrate existing user data from JSON to SQLite
4. Update `TelegramInterface` to use SQLite instead of JSON

#### Phase 2: Configuration Separation
1. Split configuration into JAPA and Telegram-specific parts
2. Ensure JAPA remains independent of Telegram
3. Update main script to handle both configuration files properly
4. Modify TelegramInterface to accept JAPA instance rather than create one

#### Phase 3: Basic Role System
1. Implement role-based permission checking
2. Add configuration options for superadmin
3. Restrict sensitive commands to admin roles

#### Phase 4: User Management Commands
1. Implement `/admins` command
2. Implement `/promote` and `/demote` for superadmins
3. Update help text to reflect available commands

#### Phase 5: Promotion Workflow
1. Implement `/requestadmin` command
2. Create approval system with inline buttons
3. Implement notification mechanism for requests

#### Phase 6: CLI Tool Development
1. Implement basic CLI structure and commands
2. Add user management functionality
3. Add request management functionality
4. Add data export/backup features

#### Phase 7: Testing & Documentation
1. Test each permission scenario
2. Document new commands and workflows
3. Ensure backward compatibility
4. Document CLI tool usage

### 7. Future Security Enhancements

After completing the initial implementation, we'll consider these additional security measures:

#### 7.1 User ID Hashing
- Research appropriate hashing algorithms for Telegram user IDs
- Implement a secure way to hash and verify user IDs without compromising security
- Update database schema to store hashed IDs instead of raw IDs
- Ensure all queries and operations work with hashed IDs

## Technical Details

### Database Access Layer
```python
class UserDatabase:
    """Database access layer for user management."""
    
    def __init__(self, db_path: str):
        """Initialize the database connection."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables_if_not_exist()
    
    def _create_tables_if_not_exist(self) -> None:
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT CHECK(role IN ('regular', 'admin', 'superadmin')),
            registration_date TEXT,
            last_active TEXT
        )
        ''')
        
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
    
    def get_user(self, user_id: int) -> dict:
        """Get user data by user ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def add_user(self, user_id: int, username: str, role: str = 'regular') -> bool:
        """Add a new user."""
        try:
            cursor = self.conn.cursor()
            now = datetime.datetime.now().isoformat()
            cursor.execute(
                'INSERT INTO users VALUES (?, ?, ?, ?, ?)',
                (user_id, username, role, now, now)
            )
            self.conn.commit()
            return True
        except sqlite3.Error:
            self.conn.rollback()
            return False
    
    # Additional methods for user management...
```

### Permission Checking Function
```python
def check_permission(update: Update, required_role: str) -> bool:
    """
    Check if the user has the required role or higher.
    Roles hierarchy: regular < admin < superadmin
    
    Args:
        update: Telegram Update object
        required_role: Required role ("regular", "admin", "superadmin")
        
    Returns:
        bool: True if user has sufficient permissions, False otherwise
    """
    user_id = update.effective_user.id
    user_data = self.db.get_user(user_id) or {"role": "regular"}
    user_role = user_data["role"]
    
    if required_role == "regular":
        return True
    elif required_role == "admin":
        return user_role in ["admin", "superadmin"]
    elif required_role == "superadmin":
        return user_role == "superadmin"
        
    return False
```

## Additional Considerations

1. **Data Integrity**: Using SQLite provides better data integrity than JSON files
2. **Concurrency**: SQLite handles concurrent access better than file-based storage
3. **Security**: No sensitive information (like tokens) should be shown in messages
4. **Privacy**: Limit user information visibility to admins only
5. **Usability**: CLI tool provides easy management without Telegram interface
6. **Logging**: Enhanced logging for security-related events
7. **Resilience**: Graceful handling of edge cases (unknown users, etc.)
8. **Backup**: Regular backups of the SQLite database file
9. **Separation of Concerns**: Keep JAPA core separate from Telegram-specific functionality

## Future Enhancements

1. **Rate Limiting**: Prevent abuse of commands
2. **Session Management**: Timeout for admin permissions
3. **Audit Trail**: Track admin actions
4. **Enhanced Security**: Add 2FA for sensitive operations
5. **Fine-grained Permissions**: Service-specific permissions
6. **User ID Encryption/Hashing**: Implement full encryption of user identifiers 