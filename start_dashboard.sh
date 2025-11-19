#!/bin/bash

echo "========================================"
echo "  Trading Bot Dashboard Launcher"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: Virtual environment not found"
    echo "Running with system Python..."
fi

echo ""
echo "Starting Flask dashboard..."
echo "Dashboard will be available at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python app.py
