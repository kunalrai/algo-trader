"""
Migration: Add active strategy fields to UserBotStatus table
"""

from app import app
from models import db

def migrate():
    """Add active_strategy and active_strategy_name columns to user_bot_status table"""
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user_bot_status')]

            if 'active_strategy' in columns and 'active_strategy_name' in columns:
                print("Migration already applied. Columns already exist.")
                return

            print("Adding active_strategy and active_strategy_name columns to user_bot_status table...")

            # Add columns using raw SQL
            with db.engine.connect() as conn:
                if 'active_strategy' not in columns:
                    conn.execute(db.text(
                        "ALTER TABLE user_bot_status ADD COLUMN active_strategy VARCHAR(100) DEFAULT 'combined'"
                    ))
                    conn.commit()
                    print("Added active_strategy column")

                if 'active_strategy_name' not in columns:
                    conn.execute(db.text(
                        "ALTER TABLE user_bot_status ADD COLUMN active_strategy_name VARCHAR(200) DEFAULT 'Combined Strategy'"
                    ))
                    conn.commit()
                    print("Added active_strategy_name column")

            print("Migration completed successfully!")

        except Exception as e:
            print(f"Migration failed: {e}")
            raise

if __name__ == '__main__':
    migrate()
