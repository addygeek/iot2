#!/bin/bash

# Meeting Recorder - Installation Script for Raspberry Pi 5
# This script installs all dependencies and sets up the system

set -e

echo "========================================================================"
echo "  MEETING RECORDER - RASPBERRY PI INSTALLATION"
echo "========================================================================"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/cpuinfo ] || ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo "⚠  Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg \
    git \
    curl

# Create project directory
PROJECT_DIR="/home/admin/iot2"
echo "📁 Creating project directory at $PROJECT_DIR..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create Python virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Download NLTK data for sumy
echo "📚 Downloading NLTK data..."
python3 -c "
import nltk
nltk.download('punkt')
nltk.download('stopwords')
print('✓ NLTK data downloaded')
"

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p models
mkdir -p sessions
mkdir -p app
mkdir -p client

# Check for Vosk model
echo ""
echo "========================================================================"
echo "  VOSK MODEL INSTALLATION"
echo "========================================================================"
echo ""

if [ ! -d "models/vosk-model-en-in-0.5" ]; then
    echo "⚠  Vosk model not found!"
    echo ""
    echo "Please download the model manually:"
    echo ""
    echo "  1. Visit: https://alphacephei.com/vosk/models"
    echo "  2. Download: vosk-model-en-in-0.5.zip"
    echo "  3. Extract to: $PROJECT_DIR/models/"
    echo ""
    echo "Or run these commands:"
    echo ""
    echo "  cd $PROJECT_DIR/models"
    echo "  wget https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip"
    echo "  unzip vosk-model-en-in-0.5.zip"
    echo "  rm vosk-model-en-in-0.5.zip"
    echo ""
    read -p "Download now? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        cd models
        wget https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip
        unzip vosk-model-en-in-0.5.zip
        rm vosk-model-en-in-0.5.zip
        cd ..
        echo "✓ Vosk model downloaded and extracted"
    fi
else
    echo "✓ Vosk model found"
fi

# Get Pi IP address
PI_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================================================"
echo "  INSTALLATION COMPLETE!"
echo "========================================================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Copy all Python files to: $PROJECT_DIR/app/"
echo "  2. Copy client files to: $PROJECT_DIR/client/"
echo ""
echo "  3. Start the server:"
echo "     cd $PROJECT_DIR"
echo "     source venv/bin/activate"
echo "     uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "  4. Open client in browser:"
echo "     http://$PI_IP:8000/client/recorder.html"
echo ""
echo "  5. Configure client with:"
echo "     Server URL: http://$PI_IP:8000"
echo ""
echo "========================================================================"
echo ""
