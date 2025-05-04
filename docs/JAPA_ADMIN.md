# JAPA Admin CLI Tool

The JAPA Admin CLI tool provides command-line utilities for managing users and admin requests in the JAPA system.

## Overview

`japa_admin.py` allows administrators to:
- Manage users (list, add, remove, promote, demote)
- Export user data to JSON or CSV
- Manage admin requests (list, approve, deny)

## Installation

The tool is part of the JAPA package and doesn't require separate installation. Make sure it's executable:

```bash
chmod +x src/japa_admin.py
```

## Basic Usage

```bash
./src/japa_admin.py [--db-path DB_PATH] [--debug] COMMAND SUBCOMMAND [ARGUMENTS]
```

Global options:
- `--db-path DB_PATH`: Path to SQLite database file (default: users.db)
- `--debug`: Enable debug mode with extra logging

## User Management Commands

### Listing Users

List all users in the database or filter by role:

```bash
./src/japa_admin.py users list [--role ROLE]
```

Options:
- `--role ROLE`: Filter users by role (`regular`, `admin`, or `superadmin`)

Example:
```bash
# List all users
./src/japa_admin.py users list

# List only admin users
./src/japa_admin.py users list --role admin
```

Output format:
```
All users:
  123456789 (@username):
    Role: regular
    Registered: 2023-05-15 14:30
    Last active: 2023-05-15 18:45
```

### Adding Users

Add a new user to the database:

```bash
./src/japa_admin.py users add USER_ID [--username USERNAME] [--role ROLE]
```

Arguments:
- `USER_ID`: Telegram user ID (required)

Options:
- `--username USERNAME`: Telegram username (optional, defaults to `user_USER_ID`)
- `--role ROLE`: User role (optional, choices: `regular`, `admin`, `superadmin`, default: `regular`)

Example:
```bash
# Add a regular user
./src/japa_admin.py users add 123456789 --username john_doe

# Add an admin user
./src/japa_admin.py users add 987654321 --username admin_user --role admin
```

### Removing Users

Remove a user from the database:

```bash
./src/japa_admin.py users remove USER_ID
```

Arguments:
- `USER_ID`: Telegram user ID (required)

Example:
```bash
./src/japa_admin.py users remove 123456789
```

### Promoting Users

Promote a user to a higher role:

```bash
./src/japa_admin.py users promote USER_ID [--role ROLE]
```

Arguments:
- `USER_ID`: Telegram user ID (required)

Options:
- `--role ROLE`: Target role (optional, choices: `admin`, `superadmin`, default: `admin`)

Example:
```bash
# Promote a user to admin
./src/japa_admin.py users promote 123456789

# Promote a user to superadmin
./src/japa_admin.py users promote 123456789 --role superadmin
```

### Demoting Users

Demote a user to a lower role:

```bash
./src/japa_admin.py users demote USER_ID [--role ROLE]
```

Arguments:
- `USER_ID`: Telegram user ID (required)

Options:
- `--role ROLE`: Target role (optional, choices: `regular`, `admin`, default: `regular`)

Example:
```bash
# Demote an admin to regular user
./src/japa_admin.py users demote 123456789

# Demote a superadmin to admin
./src/japa_admin.py users demote 123456789 --role admin
```

### Exporting Users

Export user data to a file:

```bash
./src/japa_admin.py users export OUTPUT_FILE [--format FORMAT]
```

Arguments:
- `OUTPUT_FILE`: Path to output file (required)

Options:
- `--format FORMAT`: Output format (optional, choices: `json`, `csv`, default: `json`)

Example:
```bash
# Export users to JSON
./src/japa_admin.py users export users_backup.json

# Export users to CSV
./src/japa_admin.py users export users_backup.csv --format csv
```

## Admin Request Management Commands

### Listing Requests

List all pending admin requests:

```bash
./src/japa_admin.py requests list
```

Example:
```bash
./src/japa_admin.py requests list
```

Output format:
```
Pending admin requests:
  Request ID: req_a1b2c3d4
  User: 123456789 (@username)
  Reason: Need admin access to restart services
  Requested: 2023-05-15 14:30
  Expires: 2023-05-16 14:30
```

### Approving Requests

Approve an admin request:

```bash
./src/japa_admin.py requests approve REQUEST_ID
```

Arguments:
- `REQUEST_ID`: Request ID (required)

Example:
```bash
./src/japa_admin.py requests approve req_a1b2c3d4
```

### Denying Requests

Deny an admin request:

```bash
./src/japa_admin.py requests deny REQUEST_ID
```

Arguments:
- `REQUEST_ID`: Request ID (required)

Example:
```bash
./src/japa_admin.py requests deny req_a1b2c3d4
```

## Examples

### Workflow: Promoting a User

```bash
# First, check if the user exists
./src/japa_admin.py users list

# If not, add the user
./src/japa_admin.py users add 123456789 --username john_doe

# Promote the user to admin
./src/japa_admin.py users promote 123456789
```

### Workflow: Managing Admin Requests

```bash
# List pending requests
./src/japa_admin.py requests list

# Approve or deny a specific request
./src/japa_admin.py requests approve req_a1b2c3d4
./src/japa_admin.py requests deny req_e5f6g7h8
```

### Workflow: Backup and Migration

```bash
# Export user data to JSON
./src/japa_admin.py users export users_backup.json

# Later, use this to migrate users to a new instance
# (Using main.py's migrate-users option)
python src/main.py --migrate-users users_backup.json
```

## Troubleshooting

### Database Connection Issues

If you encounter database connection issues:

1. Verify the database path is correct:
   ```bash
   ./src/japa_admin.py --db-path /path/to/users.db users list
   ```

2. Check file permissions:
   ```bash
   ls -l /path/to/users.db
   ```

3. Run with debug mode for more information:
   ```bash
   ./src/japa_admin.py --debug users list
   ```

### Common Errors

- **User not found**: Make sure the user ID is correct and the user exists in the database
- **Invalid role**: Role must be one of: `regular`, `admin`, `superadmin`
- **Failed to add user**: The user might already exist in the database
- **Request not found**: Make sure the request ID is correct and the request has not expired 