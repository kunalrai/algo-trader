"""
Create Superadmin User
Run this script to create the superadmin account

IMPORTANT: Run the Flask app first with 'python app.py'
Then in Python shell:
>>> from create_superadmin import create_superadmin
>>> create_superadmin()
"""

def create_superadmin():
    """Create superadmin user with email: admin@algotrader.com and password: superadmin123#"""
    try:
        from app import app
        from models import db, User, create_user_with_profile

        with app.app_context():
            # Check if superadmin already exists
            existing_admin = User.query.filter_by(email='admin@algotrader.com').first()

            if existing_admin:
                print("[INFO] Superadmin user already exists!")
                print(f"   Email: {existing_admin.email}")
                print(f"   Superadmin: {existing_admin.is_superadmin}")

                # Update to superadmin if not already
                if not existing_admin.is_superadmin:
                    existing_admin.is_superadmin = True
                    db.session.commit()
                    print("[OK] Updated existing user to superadmin")

                return existing_admin

            # Create new superadmin user
            print("Creating superadmin user...")

            admin_user = create_user_with_profile(
                email='admin@algotrader.com',
                password='superadmin123#',
                name='Super Admin'
            )

            # Set as superadmin
            admin_user.is_superadmin = True
            admin_user.is_verified = True
            db.session.commit()

            print("[OK] Superadmin user created successfully!")
            print(f"   Email: admin@algotrader.com")
            print(f"   Password: superadmin123#")
            print(f"   Login at: http://localhost:5000/auth/login")

            return admin_user
    except ImportError as e:
        print(f"[ERROR] {e}")
        print("\nPlease install dependencies first:")
        print("   pip install -r requirements.txt")
        print("\nOr run this in Flask shell after starting the app:")
        print("   python app.py")


if __name__ == '__main__':
    create_superadmin()
