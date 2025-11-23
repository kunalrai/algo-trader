"""
Database Migration: Add Per-User Isolation Tables

This migration adds the following tables for per-user bot and wallet isolation:
- user_bot_status: Per-user bot status tracking
- user_activities: Per-user activity logging

Run this script to update your database schema:
    python migrate_user_isolation.py
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, User, UserSimulatedWallet
from user_bot_status import UserBotStatus
from user_activity_log import UserActivity


def create_app():
    """Create Flask app for migration"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'migration-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///algo_trader.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app


def run_migration():
    """Run the database migration"""
    app = create_app()
    db.init_app(app)

    with app.app_context():
        print("=" * 60)
        print("Per-User Isolation Database Migration")
        print("=" * 60)

        # Check if tables already exist
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        new_tables = []

        # Create user_bot_status table
        if 'user_bot_status' not in existing_tables:
            print("\n[+] Creating 'user_bot_status' table...")
            UserBotStatus.__table__.create(db.engine)
            new_tables.append('user_bot_status')
            print("    -> Table created successfully")
        else:
            print("\n[=] 'user_bot_status' table already exists")

        # Create user_activities table
        if 'user_activities' not in existing_tables:
            print("\n[+] Creating 'user_activities' table...")
            UserActivity.__table__.create(db.engine)
            new_tables.append('user_activities')
            print("    -> Table created successfully")
        else:
            print("\n[=] 'user_activities' table already exists")

        # Check for user_simulated_wallets table (should exist from models.py)
        if 'user_simulated_wallets' not in existing_tables:
            print("\n[+] Creating 'user_simulated_wallets' table...")
            UserSimulatedWallet.__table__.create(db.engine)
            new_tables.append('user_simulated_wallets')
            print("    -> Table created successfully")
        else:
            print("\n[=] 'user_simulated_wallets' table already exists")

        # Initialize wallets for existing users
        print("\n[*] Checking existing users for wallets...")
        users = User.query.all()
        wallets_created = 0

        for user in users:
            wallet = UserSimulatedWallet.query.filter_by(user_id=user.id).first()
            if not wallet:
                # Get initial balance from profile if available
                initial_balance = 1000.0
                if user.profile:
                    initial_balance = user.profile.simulated_balance or 1000.0

                wallet = UserSimulatedWallet(
                    user_id=user.id,
                    balance=initial_balance,
                    initial_balance=initial_balance
                )
                db.session.add(wallet)
                wallets_created += 1
                print(f"    -> Created wallet for user {user.email} (${initial_balance:.2f})")

        if wallets_created > 0:
            db.session.commit()
            print(f"\n[+] Created {wallets_created} new user wallet(s)")
        else:
            print("\n[=] All users already have wallets")

        # Summary
        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)

        if new_tables:
            print(f"\nNew tables created: {', '.join(new_tables)}")
        else:
            print("\nNo new tables needed")

        if wallets_created > 0:
            print(f"User wallets created: {wallets_created}")

        print("\n[SUCCESS] Migration completed!")
        print("\nPer-user isolation is now enabled:")
        print("  - Each user has their own simulated wallet")
        print("  - Each user has their own bot status tracking")
        print("  - Each user has their own activity log")
        print("=" * 60)


if __name__ == '__main__':
    run_migration()
