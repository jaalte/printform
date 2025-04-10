#!/bin/bash

# Try to find python3
if ! command -v python3 &> /dev/null; then
    echo "python3 not found. Please install Python 3."
    exit 1
fi

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    ERROR_OUTPUT=$(python3 -m venv venv 2>&1)
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Error:"
        echo "$ERROR_OUTPUT"
        echo "Please ensure python3-venv is installed for your distribution."
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate || {
    echo "Failed to activate virtual environment"
    exit 1
}

echo "Installing/Updating Python packages..."
pip install -r requirements.txt || {
    echo "Failed to install requirements"
    exit 1
}
 
echo "Starting server..."
python app.py 