#!/usr/bin/env python3
"""
Setup script for Financial Consolidator Django project.
This script helps automate the initial setup process.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_postgresql():
    """Check if PostgreSQL is running and accessible."""
    print("\nChecking PostgreSQL connection...")
    try:
        result = subprocess.run(
            "psql -U postgres -d consolidator_db -c 'SELECT 1;'",
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✓ PostgreSQL connection successful")
            return True
        else:
            print("✗ PostgreSQL connection failed")
            print("Please ensure PostgreSQL is running and the database 'consolidator_db' exists")
            return False
    except FileNotFoundError:
        print("✗ PostgreSQL client not found")
        print("Please install PostgreSQL client tools")
        return False

def main():
    """Main setup function."""
    print("=" * 60)
    print("Financial Consolidator - Setup Script")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("manage.py").exists():
        print("✗ Error: manage.py not found. Please run this script from the project root directory.")
        sys.exit(1)
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠ Warning: Virtual environment not detected")
        print("Please activate your virtual environment before running this script")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Check PostgreSQL connection
    if not check_postgresql():
        print("\nTo fix PostgreSQL issues:")
        print("1. Install PostgreSQL: brew install postgresql (macOS)")
        print("2. Start PostgreSQL: brew services start postgresql")
        print("3. Create database: createdb -U postgres consolidator_db")
        print("4. Update settings.py with correct credentials")
        response = input("Continue with setup anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Run Django setup commands
    commands = [
        ("python manage.py makemigrations", "Creating database migrations"),
        ("python manage.py migrate", "Applying database migrations"),
    ]
    
    success = True
    for command, description in commands:
        if not run_command(command, description):
            success = False
            break
    
    if success:
        print("\n" + "=" * 60)
        print("✓ Setup completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Create a superuser: python manage.py createsuperuser")
        print("2. Start the development server: python manage.py runserver")
        print("3. Access the admin interface: http://127.0.0.1:8000/admin/")
        print("\nFor more information, see README.md")
    else:
        print("\n" + "=" * 60)
        print("✗ Setup failed. Please check the error messages above.")
        print("=" * 60)

if __name__ == "__main__":
    main()
