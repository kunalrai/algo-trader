"""
Database Models for User Authentication and Profiles
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import os
import base64

db = SQLAlchemy()

# Encryption key for API keys - should be set in environment variable
def get_encryption_key():
    """Get or generate encryption key for API key storage"""
    key = os.getenv('ENCRYPTION_KEY')
    if not key or key == 'your_generated_fernet_key_here':
        # Generate a key if not set (for development only)
        # In production, always set ENCRYPTION_KEY environment variable
        key = Fernet.generate_key().decode()
        print(f"WARNING: ENCRYPTION_KEY not set. Using generated key. Set this in production!")
    return key.encode() if isinstance(key, str) else key


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for secure storage"""
    if not api_key:
        return ""
    f = Fernet(get_encryption_key())
    return f.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key for use"""
    if not encrypted_key:
        return ""
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted_key.encode()).decode()


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)  # Nullable for OAuth users
    name = db.Column(db.String(100), nullable=True)

    # OAuth fields
    google_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    avatar_url = db.Column(db.String(500), nullable=True)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_superadmin = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    trading_pairs = db.relationship('UserTradingPair', backref='user', cascade='all, delete-orphan')

    def set_password(self, password: str):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f'<User {self.email}>'


class UserTradingPair(db.Model):
    """User's selected trading pairs/instruments"""
    __tablename__ = 'user_trading_pairs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)  # e.g., "BTCUSDT"
    display_name = db.Column(db.String(50), nullable=False)  # e.g., "BTC"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint: one user can't have duplicate symbols
    __table_args__ = (
        db.UniqueConstraint('user_id', 'symbol', name='unique_user_symbol'),
    )

    def __repr__(self):
        return f'<UserTradingPair {self.display_name} ({self.symbol})>'


class UserProfile(db.Model):
    """User profile with trading settings and API keys"""
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    # Trading Mode
    trading_mode = db.Column(db.String(20), default='paper')  # 'paper' or 'live'

    # CoinDCX API Keys (encrypted)
    coindcx_api_key_encrypted = db.Column(db.Text, nullable=True)
    coindcx_api_secret_encrypted = db.Column(db.Text, nullable=True)

    # Paper Trading Settings
    simulated_balance = db.Column(db.Float, default=1000.0)

    # Risk Management (user-specific overrides)
    max_position_size_percent = db.Column(db.Float, default=10.0)
    leverage = db.Column(db.Integer, default=5)
    stop_loss_percent = db.Column(db.Float, default=2.0)
    take_profit_percent = db.Column(db.Float, default=4.0)
    max_open_positions = db.Column(db.Integer, default=3)

    # Preferences
    enable_notifications = db.Column(db.Boolean, default=True)
    default_strategy = db.Column(db.String(50), default='combined')

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def coindcx_api_key(self) -> str:
        """Decrypt and return the CoinDCX API key"""
        return decrypt_api_key(self.coindcx_api_key_encrypted) if self.coindcx_api_key_encrypted else ""

    @coindcx_api_key.setter
    def coindcx_api_key(self, value: str):
        """Encrypt and store the CoinDCX API key"""
        self.coindcx_api_key_encrypted = encrypt_api_key(value) if value else None

    @property
    def coindcx_api_secret(self) -> str:
        """Decrypt and return the CoinDCX API secret"""
        return decrypt_api_key(self.coindcx_api_secret_encrypted) if self.coindcx_api_secret_encrypted else ""

    @coindcx_api_secret.setter
    def coindcx_api_secret(self, value: str):
        """Encrypt and store the CoinDCX API secret"""
        self.coindcx_api_secret_encrypted = encrypt_api_key(value) if value else None

    @property
    def has_api_keys(self) -> bool:
        """Check if user has configured API keys"""
        return bool(self.coindcx_api_key_encrypted and self.coindcx_api_secret_encrypted)

    @property
    def can_live_trade(self) -> bool:
        """Check if user can do live trading"""
        return self.trading_mode == 'live' and self.has_api_keys

    def get_risk_settings(self) -> dict:
        """Get user's risk management settings"""
        return {
            'max_position_size_percent': self.max_position_size_percent,
            'leverage': self.leverage,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
            'max_open_positions': self.max_open_positions
        }

    def __repr__(self):
        return f'<UserProfile user_id={self.user_id} mode={self.trading_mode}>'


class UserSimulatedWallet(db.Model):
    """Per-user simulated wallet for paper trading"""
    __tablename__ = 'user_simulated_wallets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    # Balance
    balance = db.Column(db.Float, default=1000.0)
    initial_balance = db.Column(db.Float, default=1000.0)
    locked_margin = db.Column(db.Float, default=0.0)
    total_pnl = db.Column(db.Float, default=0.0)

    # Statistics
    total_trades = db.Column(db.Integer, default=0)
    winning_trades = db.Column(db.Integer, default=0)
    losing_trades = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('simulated_wallet', uselist=False))
    positions = db.relationship('UserSimulatedPosition', backref='wallet', cascade='all, delete-orphan')
    trade_history = db.relationship('UserTradeHistory', backref='wallet', cascade='all, delete-orphan')

    @property
    def available_balance(self) -> float:
        """Calculate available balance"""
        return self.balance - self.locked_margin

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    def reset(self, initial_balance: float = 1000.0):
        """Reset wallet to initial state"""
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.locked_margin = 0.0
        self.total_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        # Clear positions and history
        UserSimulatedPosition.query.filter_by(wallet_id=self.id).delete()
        UserTradeHistory.query.filter_by(wallet_id=self.id).delete()


class UserSimulatedPosition(db.Model):
    """Simulated positions for paper trading"""
    __tablename__ = 'user_simulated_positions'

    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('user_simulated_wallets.id'), nullable=False)
    position_id = db.Column(db.String(50), unique=True, nullable=False)

    # Position details
    pair = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)  # 'long' or 'short'
    size = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=True)
    leverage = db.Column(db.Integer, default=5)
    margin = db.Column(db.Float, nullable=False)

    # TP/SL
    take_profit = db.Column(db.Float, nullable=True)
    stop_loss = db.Column(db.Float, nullable=True)

    # P&L
    pnl = db.Column(db.Float, default=0.0)
    pnl_percent = db.Column(db.Float, default=0.0)

    # Status
    is_open = db.Column(db.Boolean, default=True)

    # Timestamps
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)


class UserTradeHistory(db.Model):
    """Trade history for paper trading"""
    __tablename__ = 'user_trade_history'

    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('user_simulated_wallets.id'), nullable=False)

    # Trade details
    pair = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)
    size = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    leverage = db.Column(db.Integer, default=5)

    # P&L
    pnl = db.Column(db.Float, nullable=False)
    pnl_percent = db.Column(db.Float, nullable=False)

    # Metadata
    close_reason = db.Column(db.String(100), nullable=True)

    # Timestamps
    opened_at = db.Column(db.DateTime, nullable=False)
    closed_at = db.Column(db.DateTime, default=datetime.utcnow)


def init_db(app):
    """Initialize database with app context"""
    db.init_app(app)
    with app.app_context():
        db.create_all()


def create_user_with_profile(email: str, password: str = None, name: str = None,
                              google_id: str = None, avatar_url: str = None) -> User:
    """Helper function to create a user with associated profile and wallet"""
    user = User(
        email=email,
        name=name,
        google_id=google_id,
        avatar_url=avatar_url,
        is_verified=True if google_id else False
    )

    if password:
        user.set_password(password)

    db.session.add(user)
    db.session.flush()  # Get user.id

    # Create profile
    profile = UserProfile(user_id=user.id)
    db.session.add(profile)

    # Create simulated wallet
    wallet = UserSimulatedWallet(user_id=user.id)
    db.session.add(wallet)

    # Add default trading pairs
    default_pairs = [
        ('BTCUSDT', 'BTC'),
        ('ETHUSDT', 'ETH'),
        ('SOLUSDT', 'SOL'),
    ]
    for symbol, display_name in default_pairs:
        trading_pair = UserTradingPair(
            user_id=user.id,
            symbol=symbol,
            display_name=display_name
        )
        db.session.add(trading_pair)

    db.session.commit()
    return user
