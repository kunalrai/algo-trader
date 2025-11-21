# Multi-Page Dashboard Architecture with Sidebar

## Overview

Transform the single-page dashboard into a multi-page application with sidebar navigation for better organization and scalability.

## Proposed Architecture

### Page Structure

```
Dashboard Application
├── Sidebar Navigation (Persistent)
│
├── Pages (Routed)
│   ├── Home / Overview          (/)
│   ├── Live Trading              (/trading)
│   ├── Strategy Management       (/strategies)
│   ├── Positions & Orders        (/positions)
│   ├── Performance & Analytics   (/analytics)
│   ├── Activity Feed            (/activity)
│   ├── Settings                 (/settings)
│   └── Help & Documentation     (/help)
```

## Implementation Options

### Option 1: Flask Multi-Route (Server-Side Rendering)
**Best for:** Traditional web apps, SEO, simpler state management

```
templates/
├── base.html                    # Base template with sidebar
├── pages/
│   ├── home.html               # Overview dashboard
│   ├── trading.html            # Live trading view
│   ├── strategies.html         # Strategy management
│   ├── positions.html          # Positions & orders
│   ├── analytics.html          # Charts & performance
│   ├── activity.html           # Activity feed
│   ├── settings.html           # Configuration
│   └── help.html               # Documentation
└── components/
    ├── sidebar.html            # Sidebar component
    ├── header.html             # Top header
    └── modals.html             # Shared modals
```

### Option 2: Single Page Application (SPA) with Client-Side Routing
**Best for:** Modern UI, smooth transitions, no page reloads

```
templates/
└── app.html                    # Single page app container

static/
├── js/
│   ├── app.js                  # Main app & router
│   ├── pages/
│   │   ├── home.js            # Home page component
│   │   ├── trading.js         # Trading page
│   │   ├── strategies.js      # Strategies page
│   │   ├── positions.js       # Positions page
│   │   ├── analytics.js       # Analytics page
│   │   ├── activity.js        # Activity page
│   │   ├── settings.js        # Settings page
│   │   └── help.js            # Help page
│   ├── components/
│   │   ├── sidebar.js         # Sidebar component
│   │   └── header.js          # Header component
│   └── utils/
│       ├── router.js          # Client-side router
│       └── api.js             # API client
└── css/
    ├── main.css               # Global styles
    └── pages/
        └── *.css              # Page-specific styles
```

### Option 3: Hybrid Approach (Recommended)
**Best for:** Balance of simplicity and modern UX

- Flask routes for page structure
- AJAX for data updates
- Client-side components for interactive elements
- No full page reloads for data updates

## Detailed Architecture (Option 3 - Recommended)

### 1. Base Template Structure

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Trading Bot Dashboard{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white">
    <div class="flex h-screen">
        <!-- Sidebar -->
        <aside class="w-64 bg-gray-800">
            {% include 'components/sidebar.html' %}
        </aside>

        <!-- Main Content -->
        <main class="flex-1 overflow-y-auto">
            <!-- Top Header -->
            <header>
                {% include 'components/header.html' %}
            </header>

            <!-- Page Content -->
            <div class="p-6">
                {% block content %}{% endblock %}
            </div>
        </main>
    </div>

    <!-- Shared JavaScript -->
    <script src="/static/js/utils/api.js"></script>
    <script src="/static/js/components/notifications.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### 2. Sidebar Component

```html
<!-- templates/components/sidebar.html -->
<div class="flex flex-col h-full">
    <!-- Logo -->
    <div class="p-4 border-b border-gray-700">
        <h1 class="text-xl font-bold">🤖 Trading Bot</h1>
        <p class="text-xs text-gray-400">AI-Powered Trading</p>
    </div>

    <!-- Bot Status -->
    <div class="p-4 bg-gray-900 border-b border-gray-700">
        <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse" id="bot-status-dot"></div>
            <span class="text-sm" id="bot-status-text">Running</span>
        </div>
        <p class="text-xs text-gray-400 mt-1">Uptime: <span id="bot-uptime">0h 0m</span></p>
    </div>

    <!-- Navigation Menu -->
    <nav class="flex-1 p-4 overflow-y-auto">
        <ul class="space-y-1">
            <li>
                <a href="/" class="nav-item {% if active_page == 'home' %}active{% endif %}">
                    <svg><!-- Home icon --></svg>
                    <span>Overview</span>
                </a>
            </li>
            <li>
                <a href="/trading" class="nav-item {% if active_page == 'trading' %}active{% endif %}">
                    <svg><!-- Chart icon --></svg>
                    <span>Live Trading</span>
                </a>
            </li>
            <li>
                <a href="/strategies" class="nav-item {% if active_page == 'strategies' %}active{% endif %}">
                    <svg><!-- Strategy icon --></svg>
                    <span>Strategies</span>
                    <span class="badge">4</span>
                </a>
            </li>
            <li>
                <a href="/positions" class="nav-item {% if active_page == 'positions' %}active{% endif %}">
                    <svg><!-- Position icon --></svg>
                    <span>Positions</span>
                    <span class="badge" id="open-positions-count">0</span>
                </a>
            </li>
            <li>
                <a href="/analytics" class="nav-item {% if active_page == 'analytics' %}active{% endif %}">
                    <svg><!-- Analytics icon --></svg>
                    <span>Analytics</span>
                </a>
            </li>
            <li>
                <a href="/activity" class="nav-item {% if active_page == 'activity' %}active{% endif %}">
                    <svg><!-- Activity icon --></svg>
                    <span>Activity Feed</span>
                </a>
            </li>
        </ul>

        <!-- Bottom Section -->
        <div class="mt-8 pt-4 border-t border-gray-700">
            <ul class="space-y-1">
                <li>
                    <a href="/settings" class="nav-item {% if active_page == 'settings' %}active{% endif %}">
                        <svg><!-- Settings icon --></svg>
                        <span>Settings</span>
                    </a>
                </li>
                <li>
                    <a href="/help" class="nav-item {% if active_page == 'help' %}active{% endif %}">
                        <svg><!-- Help icon --></svg>
                        <span>Help</span>
                    </a>
                </li>
            </ul>
        </div>
    </nav>

    <!-- Mode Indicator -->
    <div class="p-4 bg-yellow-900 bg-opacity-30 border-t border-yellow-700">
        <div class="flex items-center gap-2">
            <svg class="w-4 h-4 text-yellow-500"><!-- Warning icon --></svg>
            <span class="text-xs font-semibold text-yellow-400" id="trading-mode">DRY RUN</span>
        </div>
    </div>
</div>
```

### 3. Page Definitions

#### Home / Overview Page
**Route:** `/`
**Purpose:** High-level dashboard with key metrics

**Content:**
- Bot status summary
- Quick stats (balance, P&L, positions)
- Recent signals
- Active strategy card
- Mini charts
- Quick actions

#### Live Trading Page
**Route:** `/trading`
**Purpose:** Real-time market monitoring and trading

**Content:**
- Live price tickers (all pairs)
- Market depth charts
- Order book visualization
- Quick trade buttons
- Open orders list
- Trade execution interface

#### Strategy Management Page
**Route:** `/strategies`
**Purpose:** Manage and configure strategies

**Content:**
- Strategy selector
- Active strategy details
- Strategy comparison table
- Performance metrics per strategy
- Parameter configuration forms
- Strategy backtesting tools
- Create custom strategy wizard

#### Positions & Orders Page
**Route:** `/positions`
**Purpose:** Manage open positions and orders

**Content:**
- Open positions table
- Position P&L tracking
- Close position buttons
- Order history
- Failed orders
- Position analytics
- Risk metrics per position

#### Performance & Analytics Page
**Route:** `/analytics`
**Purpose:** Detailed performance analysis

**Content:**
- Equity curve chart
- Win rate statistics
- Strategy performance comparison
- Monthly/weekly P&L breakdown
- Trade distribution charts
- Risk/reward analysis
- Correlation analysis
- Export reports

#### Activity Feed Page
**Route:** `/activity`
**Purpose:** Detailed activity log

**Content:**
- Full activity timeline
- Advanced filters
- Search functionality
- Export activity log
- Activity statistics
- Decision replay
- Error logs

#### Settings Page
**Route:** `/settings`
**Purpose:** Bot configuration

**Content:**
- Trading parameters
- Risk management settings
- API credentials (masked)
- Notification preferences
- Dashboard customization
- Backup/restore config
- Theme settings

#### Help & Documentation Page
**Route:** `/help`
**Purpose:** In-app documentation

**Content:**
- Getting started guide
- Strategy documentation
- API reference
- Troubleshooting
- FAQ
- Version info
- Support links

## Flask Route Structure

```python
# app.py

from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

# ============================================================================
# PAGE ROUTES
# ============================================================================

@app.route('/')
def home():
    """Home / Overview page"""
    return render_template('pages/home.html', active_page='home')

@app.route('/trading')
def trading():
    """Live Trading page"""
    return render_template('pages/trading.html', active_page='trading')

@app.route('/strategies')
def strategies():
    """Strategy Management page"""
    return render_template('pages/strategies.html', active_page='strategies')

@app.route('/positions')
def positions():
    """Positions & Orders page"""
    return render_template('pages/positions.html', active_page='positions')

@app.route('/analytics')
def analytics():
    """Performance & Analytics page"""
    return render_template('pages/analytics.html', active_page='analytics')

@app.route('/activity')
def activity():
    """Activity Feed page"""
    return render_template('pages/activity.html', active_page='activity')

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('pages/settings.html', active_page='settings')

@app.route('/help')
def help_page():
    """Help & Documentation page"""
    return render_template('pages/help.html', active_page='help')

# ============================================================================
# API ROUTES (Keep existing + add new)
# ============================================================================

# Existing API routes remain unchanged...

# New API routes for specific page data
@app.route('/api/analytics/equity-curve')
def get_equity_curve():
    """Get equity curve data for analytics page"""
    # Implementation
    pass

@app.route('/api/trading/orderbook/<pair>')
def get_orderbook(pair):
    """Get order book data for trading page"""
    # Implementation
    pass
```

## File Organization

```
algo-trader/
├── templates/
│   ├── base.html                      # Base template with sidebar
│   ├── components/
│   │   ├── sidebar.html               # Sidebar navigation
│   │   ├── header.html                # Top header bar
│   │   ├── bot_status_widget.html     # Bot status component
│   │   ├── price_card.html            # Price display card
│   │   ├── position_card.html         # Position card
│   │   └── modal_base.html            # Modal template
│   └── pages/
│       ├── home.html                  # Overview page
│       ├── trading.html               # Trading page
│       ├── strategies.html            # Strategies page
│       ├── positions.html             # Positions page
│       ├── analytics.html             # Analytics page
│       ├── activity.html              # Activity page
│       ├── settings.html              # Settings page
│       └── help.html                  # Help page
│
├── static/
│   ├── css/
│   │   ├── main.css                   # Global styles
│   │   ├── sidebar.css                # Sidebar styles
│   │   └── pages/                     # Page-specific styles
│   │       ├── home.css
│   │       ├── trading.css
│   │       └── ...
│   ├── js/
│   │   ├── main.js                    # Global JS
│   │   ├── utils/
│   │   │   ├── api.js                 # API client
│   │   │   ├── websocket.js           # WebSocket client
│   │   │   └── notifications.js       # Toast notifications
│   │   ├── components/
│   │   │   ├── sidebar.js             # Sidebar functionality
│   │   │   ├── chart.js               # Chart components
│   │   │   └── modal.js               # Modal handling
│   │   └── pages/
│   │       ├── home.js                # Home page JS
│   │       ├── trading.js             # Trading page JS
│   │       ├── strategies.js          # Strategies page JS
│   │       └── ...
│   └── images/
│       └── icons/                     # Custom icons
│
└── app.py                             # Updated with new routes
```

## Data Flow Pattern

```
1. User navigates to /strategies
        ↓
2. Flask renders templates/pages/strategies.html
        ↓
3. Page loads with skeleton/loading state
        ↓
4. JavaScript (strategies.js) executes:
        ↓
5. Fetches data from API endpoints:
   - GET /api/strategies/list
   - GET /api/strategies/active
   - GET /api/strategies/performance
        ↓
6. Updates DOM with real data
        ↓
7. Sets up refresh intervals for live data
        ↓
8. User interacts → AJAX calls → Update specific sections
   (No full page reload)
```

## Responsive Sidebar Behavior

```css
/* Desktop: Full sidebar */
@media (min-width: 1024px) {
    .sidebar { width: 256px; }
    .main-content { margin-left: 256px; }
}

/* Tablet: Collapsible sidebar */
@media (max-width: 1023px) and (min-width: 768px) {
    .sidebar { width: 64px; } /* Icon-only mode */
    .sidebar:hover { width: 256px; } /* Expand on hover */
}

/* Mobile: Hidden sidebar with toggle */
@media (max-width: 767px) {
    .sidebar {
        position: fixed;
        left: -256px; /* Hidden by default */
        transition: left 0.3s;
    }
    .sidebar.open { left: 0; } /* Show when toggled */
    .sidebar-overlay { display: block; }
}
```

## Progressive Enhancement Strategy

### Phase 1: Core Structure (Week 1)
- [ ] Create base.html with sidebar
- [ ] Create sidebar component
- [ ] Add Flask routes for all pages
- [ ] Create skeleton HTML for each page
- [ ] Basic navigation working

### Phase 2: Migrate Existing Features (Week 2)
- [ ] Move current dashboard to /trading page
- [ ] Create simple home/overview page
- [ ] Move strategy selector to /strategies page
- [ ] Move activity feed to /activity page
- [ ] Ensure all existing functionality works

### Phase 3: Enhance Pages (Week 3)
- [ ] Build out analytics page with charts
- [ ] Add position management features
- [ ] Create settings page
- [ ] Add help documentation
- [ ] Improve trading page with order book

### Phase 4: Polish & Optimize (Week 4)
- [ ] Add page transitions
- [ ] Optimize data loading
- [ ] Add loading states
- [ ] Mobile responsiveness
- [ ] User preferences (save sidebar state, etc.)

## Benefits of Multi-Page Architecture

### Organization
✅ Clear separation of concerns
✅ Easier to find specific features
✅ Better code organization

### Performance
✅ Load only what's needed per page
✅ Faster initial page load
✅ Better caching strategies

### User Experience
✅ Cleaner, less cluttered interface
✅ Bookmarkable pages
✅ Browser back/forward navigation
✅ Better mobile experience

### Development
✅ Easier to work on individual pages
✅ Multiple developers can work in parallel
✅ Simpler testing
✅ Better maintainability

### Scalability
✅ Easy to add new pages
✅ Can split into microservices later
✅ Better state management
✅ Modular architecture

## Migration Path

### Step 1: Keep Current Dashboard
- Don't break anything
- Create new pages alongside existing

### Step 2: Add Sidebar
- Add sidebar to current page first
- Test navigation
- Add Flask routes

### Step 3: Split Features
- Move features to dedicated pages gradually
- Keep links to old dashboard during transition
- Update one page at a time

### Step 4: Deprecate Old Dashboard
- Once all features migrated
- Redirect / to new home
- Archive old dashboard.html

## Next Steps

Would you like me to:

1. **Implement the basic structure** - Create base.html, sidebar, and page templates
2. **Build one complete page** - Fully implement one page (e.g., strategies) as a reference
3. **Create migration plan** - Detailed step-by-step migration guide
4. **Build SPA version** - Full client-side routing with React/Vue
5. **Something else** - Let me know your specific needs

## Recommendation

**Start with Hybrid Approach (Option 3):**
- Multi-page Flask routes for structure
- Keep existing AJAX patterns for data
- Add sidebar navigation
- Migrate features gradually
- Minimal disruption to current functionality

This gives you the best of both worlds: organized multi-page structure with modern SPA-like user experience.
