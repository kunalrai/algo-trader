"""
Database migration to add is_superadmin column
Run this to update existing databases
"""

import sqlite3
import os

def migrate_database():
    """Add is_superadmin column to users table"""
    # Try common database locations
    db_paths = [
        'instance/algo_trader.db',
        'algo_trader.db',
        'instance\\algo_trader.db'
    ]

    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        print("Database not found in common locations:")
        for path in db_paths:
            print(f"  - {path}")
        print("\nThe column will be created automatically when you first run the app.")
        return

    print(f"Found database at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'is_superadmin' in columns:
            print("[OK] Column 'is_superadmin' already exists")
        else:
            # Add the column
            cursor.execute("ALTER TABLE users ADD COLUMN is_superadmin BOOLEAN DEFAULT 0")
            conn.commit()
            print("[OK] Successfully added 'is_superadmin' column to users table")

        conn.close()

        print("\nNow run: python create_superadmin.py")

    except Exception as e:
        print(f"[ERROR] {e}")
        conn.close()

if __name__ == '__main__':
    migrate_database()
