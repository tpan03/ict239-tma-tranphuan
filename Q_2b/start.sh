#!/bin/bash
# -----------------------------
# Flask Library App Launcher
# -----------------------------

echo "🚀 Starting Flask Library Application..."

# Activate your virtual environment (if you have one)
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️ No virtual environment found. Using system Python."
fi

# Check MongoDB connection
echo "Checking MongoDB status..."
if pgrep mongod > /dev/null; then
    echo "✅ MongoDB is already running."
else
    echo "⚙️ Starting MongoDB service..."
    sudo service mongod start
fi

# Export Flask environment variables
export FLASK_APP=app.py
export FLASK_ENV=development
export PYTHONPATH=$(pwd)

# Run Flask app
echo "Running Flask server at http://127.0.0.1:5000 ..."
flask run --host=127.0.0.1 --port=5000

# Deactivate virtual environment on exit
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

echo "🛑 Flask app stopped."
