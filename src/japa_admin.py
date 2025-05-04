#!/usr/bin/env python3
"""
CLI tool for managing JAPA users and permissions.
"""
import argparse
import logging
import sys
import os
import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("japa-admin")

# Add parent directory to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from japa.user_database import UserDatabase


def list_users(db: UserDatabase, role: str = None) -> None:
    """
    List users from the database.
    
    Args:
        db: UserDatabase instance
        role: Optional role filter
    """
    if role:
        users = db.get_users_by_role(role)
        print(f"Users with role '{role}':")
    else:
        users = db.get_all_users()
        print("All users:")
        
    if not users:
        print("  No users found.")
        return
        
    # Format and print user data
    for user in users:
        reg_date = datetime.datetime.fromisoformat(user['registration_date']).strftime('%Y-%m-%d %H:%M')
        last_active = datetime.datetime.fromisoformat(user['last_active']).strftime('%Y-%m-%d %H:%M')
        print(f"  {user['user_id']} (@{user['username']}):")
        print(f"    Role: {user['role']}")
        print(f"    Registered: {reg_date}")
        print(f"    Last active: {last_active}")
        print()


def add_user(db: UserDatabase, user_id: int, username: str = None, role: str = "regular") -> None:
    """
    Add a new user to the database.
    
    Args:
        db: UserDatabase instance
        user_id: User ID
        username: Optional username
        role: User role
    """
    if not username:
        username = f"user_{user_id}"
        
    if not role in ["regular", "admin", "superadmin"]:
        print(f"Invalid role: {role}")
        print("Valid roles are: regular, admin, superadmin")
        return
        
    if db.add_user(user_id, username, role):
        print(f"User {user_id} (@{username}) added with role '{role}'.")
    else:
        print(f"Failed to add user {user_id}. User may already exist.")


def remove_user(db: UserDatabase, user_id: int) -> None:
    """
    Remove a user from the database.
    
    Args:
        db: UserDatabase instance
        user_id: User ID
    """
    if db.remove_user(user_id):
        print(f"User {user_id} removed successfully.")
    else:
        print(f"Failed to remove user {user_id}. User may not exist.")


def promote_user(db: UserDatabase, user_id: int, role: str = "admin") -> None:
    """
    Promote a user to a higher role.
    
    Args:
        db: UserDatabase instance
        user_id: User ID
        role: Target role
    """
    if not role in ["admin", "superadmin"]:
        print(f"Invalid role: {role}")
        print("Valid roles for promotion are: admin, superadmin")
        return
        
    user = db.get_user(user_id)
    if not user:
        print(f"User {user_id} not found.")
        return
        
    if user["role"] == role:
        print(f"User {user_id} is already a {role}.")
        return
        
    if db.update_user_role(user_id, role):
        print(f"User {user_id} (@{user['username']}) promoted to {role}.")
    else:
        print(f"Failed to promote user {user_id}.")


def demote_user(db: UserDatabase, user_id: int, role: str = "regular") -> None:
    """
    Demote a user to a lower role.
    
    Args:
        db: UserDatabase instance
        user_id: User ID
        role: Target role
    """
    if not role in ["regular", "admin"]:
        print(f"Invalid role: {role}")
        print("Valid roles for demotion are: regular, admin")
        return
        
    user = db.get_user(user_id)
    if not user:
        print(f"User {user_id} not found.")
        return
        
    if user["role"] == role:
        print(f"User {user_id} is already a {role} user.")
        return
        
    if db.update_user_role(user_id, role):
        print(f"User {user_id} (@{user['username']}) demoted to {role} user.")
    else:
        print(f"Failed to demote user {user_id}.")


def export_users(db: UserDatabase, output_file: str, format: str = "json") -> None:
    """
    Export users to a file.
    
    Args:
        db: UserDatabase instance
        output_file: Output file path
        format: Output format (json or csv)
    """
    import json
    import csv
    
    users = db.get_all_users()
    if not users:
        print("No users to export.")
        return
        
    try:
        if format.lower() == "json":
            with open(output_file, 'w') as f:
                json.dump({"users": users}, f, indent=2)
            print(f"Exported {len(users)} users to {output_file} in JSON format.")
            
        elif format.lower() == "csv":
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["user_id", "username", "role", "registration_date", "last_active"])
                for user in users:
                    writer.writerow([
                        user["user_id"],
                        user["username"],
                        user["role"],
                        user["registration_date"],
                        user["last_active"]
                    ])
            print(f"Exported {len(users)} users to {output_file} in CSV format.")
            
        else:
            print(f"Invalid format: {format}")
            print("Valid formats are: json, csv")
    except Exception as e:
        print(f"Error exporting users: {str(e)}")


def list_requests(db: UserDatabase) -> None:
    """
    List pending admin requests.
    
    Args:
        db: UserDatabase instance
    """
    requests = db.get_pending_requests()
    if not requests:
        print("No pending admin requests.")
        return
        
    print("Pending admin requests:")
    for req in requests:
        request_time = datetime.datetime.fromisoformat(req['request_time']).strftime('%Y-%m-%d %H:%M')
        expires = datetime.datetime.fromisoformat(req['expires']).strftime('%Y-%m-%d %H:%M')
        
        print(f"  Request ID: {req['request_id']}")
        print(f"  User: {req['user_id']} (@{req['username']})")
        print(f"  Requested: {request_time}")
        print(f"  Expires: {expires}")
        print(f"  Reason: {req['reason']}")
        print()


def approve_request(db: UserDatabase, request_id: str) -> None:
    """
    Approve an admin request.
    
    Args:
        db: UserDatabase instance
        request_id: Request ID
    """
    success, message = db.approve_request(request_id)
    if success:
        print(f"Request {request_id} approved successfully.")
        print(message)
    else:
        print(f"Failed to approve request {request_id}.")
        print(message)


def deny_request(db: UserDatabase, request_id: str) -> None:
    """
    Deny an admin request.
    
    Args:
        db: UserDatabase instance
        request_id: Request ID
    """
    if db.deny_request(request_id):
        print(f"Request {request_id} denied successfully.")
    else:
        print(f"Failed to deny request {request_id}.")


def main() -> None:
    """
    Main entry point.
    """
    parser = argparse.ArgumentParser(description="JAPA User Management CLI")
    parser.add_argument(
        "--db-path", type=str, default="users.db",
        help="Path to SQLite database file (default: users.db)"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug mode with extra logging"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Users commands
    users_parser = subparsers.add_parser("users", help="User management commands")
    users_subparsers = users_parser.add_subparsers(dest="subcommand", help="User subcommand")
    
    # List users
    list_parser = users_subparsers.add_parser("list", help="List users")
    list_parser.add_argument(
        "--role", type=str, choices=["regular", "admin", "superadmin"],
        help="Filter users by role"
    )
    
    # Add user
    add_parser = users_subparsers.add_parser("add", help="Add a user")
    add_parser.add_argument("user_id", type=int, help="User ID")
    add_parser.add_argument("--username", type=str, help="Username")
    add_parser.add_argument(
        "--role", type=str, default="regular",
        choices=["regular", "admin", "superadmin"],
        help="User role"
    )
    
    # Remove user
    remove_parser = users_subparsers.add_parser("remove", help="Remove a user")
    remove_parser.add_argument("user_id", type=int, help="User ID")
    
    # Promote user
    promote_parser = users_subparsers.add_parser("promote", help="Promote a user")
    promote_parser.add_argument("user_id", type=int, help="User ID")
    promote_parser.add_argument(
        "--role", type=str, default="admin",
        choices=["admin", "superadmin"],
        help="Target role"
    )
    
    # Demote user
    demote_parser = users_subparsers.add_parser("demote", help="Demote a user")
    demote_parser.add_argument("user_id", type=int, help="User ID")
    demote_parser.add_argument(
        "--role", type=str, default="regular",
        choices=["regular", "admin"],
        help="Target role"
    )
    
    # Export users
    export_parser = users_subparsers.add_parser("export", help="Export users")
    export_parser.add_argument("output_file", type=str, help="Output file path")
    export_parser.add_argument(
        "--format", type=str, default="json",
        choices=["json", "csv"],
        help="Output format"
    )
    
    # Requests commands
    requests_parser = subparsers.add_parser("requests", help="Admin request management commands")
    requests_subparsers = requests_parser.add_subparsers(dest="subcommand", help="Request subcommand")
    
    # List requests
    requests_subparsers.add_parser("list", help="List pending admin requests")
    
    # Approve request
    approve_parser = requests_subparsers.add_parser("approve", help="Approve an admin request")
    approve_parser.add_argument("request_id", type=str, help="Request ID")
    
    # Deny request
    deny_parser = requests_subparsers.add_parser("deny", help="Deny an admin request")
    deny_parser.add_argument("request_id", type=str, help="Request ID")
    
    # Parse args
    args = parser.parse_args()
    
    # Set debug mode if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        
    # If no command is provided, show help
    if not args.command:
        parser.print_help()
        return
        
    # Open database connection
    db = UserDatabase(args.db_path, debug=args.debug)
    
    try:
        # Users commands
        if args.command == "users":
            if args.subcommand == "list":
                list_users(db, args.role)
            elif args.subcommand == "add":
                add_user(db, args.user_id, args.username, args.role)
            elif args.subcommand == "remove":
                remove_user(db, args.user_id)
            elif args.subcommand == "promote":
                promote_user(db, args.user_id, args.role)
            elif args.subcommand == "demote":
                demote_user(db, args.user_id, args.role)
            elif args.subcommand == "export":
                export_users(db, args.output_file, args.format)
            else:
                users_parser.print_help()
        
        # Requests commands
        elif args.command == "requests":
            if args.subcommand == "list":
                list_requests(db)
            elif args.subcommand == "approve":
                approve_request(db, args.request_id)
            elif args.subcommand == "deny":
                deny_request(db, args.request_id)
            else:
                requests_parser.print_help()
    finally:
        # Close database connection
        db.close()


if __name__ == "__main__":
    main() 