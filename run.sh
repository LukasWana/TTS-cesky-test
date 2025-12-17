#!/bin/bash

echo "🎤 XTTS-v2 Demo Setup"
echo "===================="

# Check Python - prefer 3.11, then 3.10, then 3.9
PYTHON_CMD=""
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    echo "Found Python 3.11"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    echo "Found Python 3.10"
elif command -v python3.9 &> /dev/null; then
    PYTHON_CMD="python3.9"
    echo "Found Python 3.9"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 9 ] && [ "$MINOR" -le 11 ]; then
        PYTHON_CMD="python3"
        echo "Found Python $PYTHON_VERSION"
    else
        echo "❌ Python 3.9-3.11 required. Found: $PYTHON_VERSION"
        echo "TTS does not support Python 3.12+"
        exit 1
    fi
else
    echo "❌ Python 3.9-3.11 not found. Please install Python 3.9, 3.10, or 3.11"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Create venv
echo "Creating virtual environment with $PYTHON_CMD..."
$PYTHON_CMD -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Create directories
mkdir -p models uploads outputs frontend/assets/demo-voices

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo ""
echo "1. Start backend:"
echo "   source venv/bin/activate"
echo "   cd backend"
echo "   python main.py"
echo ""
echo "2. Start frontend (in new terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "Then open: http://localhost:3000"

