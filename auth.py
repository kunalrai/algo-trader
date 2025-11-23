"""
Authentication Blueprint for Flask Application
Supports Google OAuth and Email/Password authentication
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from models import db, User, UserProfile, UserSimulatedWallet, UserTradingPair, create_user_with_profile
from datetime import datetime
from functools import wraps
import re

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Initialize OAuth
oauth = OAuth()


def init_auth(app):
    """Initialize authentication with the Flask app"""
    login_manager.init_app(app)
    oauth.init_app(app)

    # Configure Google OAuth
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))


def superadmin_required(f):
    """Decorator to require superadmin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_superadmin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# EMAIL/PASSWORD AUTHENTICATION
# ============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated.', 'error')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            user.update_last_login()

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page and handler"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()

        # Validation
        errors = []

        if not email:
            errors.append('Email is required.')
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors.append('Please enter a valid email address.')

        if not password:
            errors.append('Password is required.')
        elif len(password) < 8:
            errors.append('Password must be at least 8 characters long.')

        if password != confirm_password:
            errors.append('Passwords do not match.')

        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html', email=email, name=name)

        # Create user
        try:
            user = create_user_with_profile(
                email=email,
                password=password,
                name=name
            )
            login_user(user)
            flash('Registration successful! Welcome to Algo Trader.', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed. Please try again.', 'error')
            current_app.logger.error(f'Registration error: {e}')

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ============================================================================
# GOOGLE OAUTH AUTHENTICATION
# ============================================================================

@auth_bp.route('/google/login')
def google_login():
    """Initiate Google OAuth login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # Use http for localhost, https for production
    scheme = 'http' if request.host.startswith('localhost') or request.host.startswith('127.0.0.1') else 'https'
    redirect_uri = url_for('auth.google_callback', _external=True, _scheme=scheme)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            flash('Failed to get user info from Google.', 'error')
            return redirect(url_for('auth.login'))

        google_id = user_info.get('sub')
        email = user_info.get('email', '').lower()
        name = user_info.get('name', '')
        avatar_url = user_info.get('picture', '')

        # Check if user exists by Google ID or email
        user = User.query.filter(
            (User.google_id == google_id) | (User.email == email)
        ).first()

        if user:
            # Update Google info if not set
            if not user.google_id:
                user.google_id = google_id
            if not user.avatar_url:
                user.avatar_url = avatar_url
            if not user.name:
                user.name = name
            user.is_verified = True
            db.session.commit()
        else:
            # Create new user
            user = create_user_with_profile(
                email=email,
                name=name,
                google_id=google_id,
                avatar_url=avatar_url
            )

        login_user(user, remember=True)
        user.update_last_login()

        flash(f'Welcome, {user.name or user.email}!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        current_app.logger.error(f'Google OAuth error: {e}')
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))


# ============================================================================
# PROFILE MANAGEMENT
# ============================================================================

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    # Ensure user has a profile (create if missing)
    user_profile = current_user.profile
    if not user_profile:
        from models import UserProfile, UserSimulatedWallet
        user_profile = UserProfile(user_id=current_user.id)
        db.session.add(user_profile)
        wallet = UserSimulatedWallet(user_id=current_user.id)
        db.session.add(wallet)
        db.session.commit()
        # Refresh to get the new profile
        db.session.refresh(current_user)
        user_profile = current_user.profile

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            # Update basic profile info
            current_user.name = request.form.get('name', '').strip()
            db.session.commit()
            flash('Profile updated successfully.', 'success')

        elif action == 'update_trading':
            # Update trading settings
            profile = current_user.profile
            profile.trading_mode = request.form.get('trading_mode', 'paper')
            profile.simulated_balance = float(request.form.get('simulated_balance', 1000))
            profile.max_open_positions = int(request.form.get('max_open_positions', 3))
            profile.leverage = int(request.form.get('leverage', 5))
            profile.stop_loss_percent = float(request.form.get('stop_loss_percent', 2.0))
            profile.take_profit_percent = float(request.form.get('take_profit_percent', 4.0))
            profile.default_strategy = request.form.get('default_strategy', 'combined')
            db.session.commit()
            flash('Trading settings updated successfully.', 'success')

        elif action == 'update_api_keys':
            # Update CoinDCX API keys
            profile = current_user.profile
            api_key = request.form.get('coindcx_api_key', '').strip()
            api_secret = request.form.get('coindcx_api_secret', '').strip()

            if api_key:
                profile.coindcx_api_key = api_key
            if api_secret:
                profile.coindcx_api_secret = api_secret

            db.session.commit()
            flash('API keys updated successfully.', 'success')

        elif action == 'delete_api_keys':
            # Remove API keys
            profile = current_user.profile
            profile.coindcx_api_key_encrypted = None
            profile.coindcx_api_secret_encrypted = None
            profile.trading_mode = 'paper'  # Reset to paper trading
            db.session.commit()
            flash('API keys removed. Switched to paper trading.', 'info')

        elif action == 'reset_wallet':
            # Reset simulated wallet
            wallet = current_user.simulated_wallet
            if wallet:
                initial_balance = float(request.form.get('initial_balance', 1000))
                wallet.reset(initial_balance)
                db.session.commit()
                flash(f'Simulated wallet reset to ${initial_balance:.2f}', 'success')

        elif action == 'change_password':
            # Change password
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_new_password', '')

            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'error')
            elif len(new_password) < 8:
                flash('New password must be at least 8 characters.', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'error')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Password changed successfully.', 'success')

        return redirect(url_for('auth.profile'))

    # GET request - render profile page
    strategies = [
        {'id': 'combined', 'name': 'Combined Strategy'},
        {'id': 'ema_crossover', 'name': 'EMA Crossover'},
        {'id': 'macd', 'name': 'MACD Strategy'},
        {'id': 'rsi', 'name': 'RSI Strategy'}
    ]

    # Get user's trading pairs and convert to dict for template
    trading_pairs_db = UserTradingPair.query.filter_by(user_id=current_user.id).order_by(UserTradingPair.created_at).all()
    trading_pairs = [{
        'id': pair.id,
        'symbol': pair.symbol,
        'display_name': pair.display_name,
        'is_active': pair.is_active
    } for pair in trading_pairs_db]

    # Available trading pairs
    available_pairs = [
        {'symbol': 'BTCUSDT', 'name': 'BTC'},
        {'symbol': 'ETHUSDT', 'name': 'ETH'},
        {'symbol': 'XRPUSDT', 'name': 'XRP'},
        {'symbol': 'BNBUSDT', 'name': 'BNB'},
        {'symbol': 'SOLUSDT', 'name': 'SOL'},
        {'symbol': 'ADAUSDT', 'name': 'ADA'},
        {'symbol': 'DOGEUSDT', 'name': 'DOGE'},
        {'symbol': 'MATICUSDT', 'name': 'MATIC'},
        {'symbol': 'DOTUSDT', 'name': 'DOT'},
        {'symbol': 'LINKUSDT', 'name': 'LINK'},
        {'symbol': 'AVAXUSDT', 'name': 'AVAX'},
        {'symbol': 'UNIUSDT', 'name': 'UNI'},
        {'symbol': 'LTCUSDT', 'name': 'LTC'},
        {'symbol': 'ATOMUSDT', 'name': 'ATOM'},
        {'symbol': 'ETCUSDT', 'name': 'ETC'},
        {'symbol': 'TAOUSDT', 'name': 'TAO'},
        {'symbol': 'ZECUSDT', 'name': 'ZEC'},
    ]

    return render_template('auth/profile.html', strategies=strategies, profile=user_profile,
                         trading_pairs=trading_pairs, available_pairs=available_pairs)


@auth_bp.route('/trading-pairs/add', methods=['POST'])
@login_required
def add_trading_pair():
    """Add a trading pair to user's list"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').strip().upper()
        display_name = data.get('display_name', '').strip().upper()

        if not symbol or not display_name:
            return jsonify({'success': False, 'message': 'Symbol and display name are required'}), 400

        # Check if pair already exists
        existing = UserTradingPair.query.filter_by(
            user_id=current_user.id,
            symbol=symbol
        ).first()

        if existing:
            return jsonify({'success': False, 'message': 'Trading pair already added'}), 400

        # Add new trading pair
        new_pair = UserTradingPair(
            user_id=current_user.id,
            symbol=symbol,
            display_name=display_name
        )
        db.session.add(new_pair)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{display_name} added successfully',
            'pair': {
                'id': new_pair.id,
                'symbol': new_pair.symbol,
                'display_name': new_pair.display_name
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/trading-pairs/remove/<int:pair_id>', methods=['DELETE'])
@login_required
def remove_trading_pair(pair_id):
    """Remove a trading pair from user's list"""
    try:
        trading_pair = UserTradingPair.query.filter_by(
            id=pair_id,
            user_id=current_user.id
        ).first()

        if not trading_pair:
            return jsonify({'success': False, 'message': 'Trading pair not found'}), 404

        display_name = trading_pair.display_name
        db.session.delete(trading_pair)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{display_name} removed successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/trading-pairs/toggle/<int:pair_id>', methods=['POST'])
@login_required
def toggle_trading_pair(pair_id):
    """Toggle active status of a trading pair"""
    try:
        trading_pair = UserTradingPair.query.filter_by(
            id=pair_id,
            user_id=current_user.id
        ).first()

        if not trading_pair:
            return jsonify({'success': False, 'message': 'Trading pair not found'}), 404

        trading_pair.is_active = not trading_pair.is_active
        db.session.commit()

        status = 'enabled' if trading_pair.is_active else 'disabled'
        return jsonify({
            'success': True,
            'message': f'{trading_pair.display_name} {status}',
            'is_active': trading_pair.is_active
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# SUPERADMIN ROUTES
# ============================================================================

@auth_bp.route('/admin/users')
@superadmin_required
def admin_users():
    """Superadmin dashboard for managing all users"""
    users = User.query.order_by(User.created_at.desc()).all()

    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'email': user.email,
            'name': user.name or 'N/A',
            'is_active': user.is_active,
            'is_verified': user.is_verified,
            'is_superadmin': user.is_superadmin,
            'trading_mode': user.profile.trading_mode if user.profile else 'N/A',
            'has_api_keys': user.profile.has_api_keys if user.profile else False,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never',
        })

    return render_template('auth/admin_users.html', users=users_data)


@auth_bp.route('/admin/users/<int:user_id>/toggle-active', methods=['POST'])
@superadmin_required
def admin_toggle_user_active(user_id):
    """Toggle user active status"""
    try:
        user = User.query.get_or_404(user_id)

        if user.is_superadmin and user.id != current_user.id:
            return jsonify({'success': False, 'message': 'Cannot deactivate other superadmins'}), 403

        user.is_active = not user.is_active
        db.session.commit()

        status = 'activated' if user.is_active else 'deactivated'
        return jsonify({
            'success': True,
            'message': f'User {user.email} {status}',
            'is_active': user.is_active
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/admin/users/<int:user_id>/delete', methods=['DELETE'])
@superadmin_required
def admin_delete_user(user_id):
    """Delete a user"""
    try:
        user = User.query.get_or_404(user_id)

        if user.is_superadmin:
            return jsonify({'success': False, 'message': 'Cannot delete superadmin users'}), 403

        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot delete yourself'}), 403

        email = user.email
        db.session.delete(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'User {email} deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
