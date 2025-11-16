#!/bin/bash

# Meeting Recorder - Quick Start Script

set -e

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "✗ Virtual environment not found!"
    echo "  Run install.sh first"
    exit 1
fi

source venv/bin/activate

# Check for Vosk model
if [ ! -d "models/vosk-model-en-in-0.5" ]; then
    echo "✗ Vosk model not found!"
    echo "  Please download vosk-model-en-in-0.5 to models/"
    exit 1
fi

# Get IP address
PI_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================================================"
echo "  STARTING MEETING RECORDER"
echo "========================================================================"
echo ""
echo "  Server will be available at:"
echo "  📡 API: http://$PI_IP:8000"
echo "  🔌 WebSocket: ws://$PI_IP:8000/ws"
echo "  📝 Docs: http://$PI_IP:8000/docs"
echo "  🎙️ Client: http://$PI_IP:8000/client/recorder.html"
echo ""
echo "========================================================================"
echo ""

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000