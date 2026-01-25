#!/bin/bash

# Munero AI Platform - Quick Setup Script
# This script sets up the complete backend environment

set -e  # Exit on error

echo "============================================================"
echo "🚀 Munero AI Platform - Setup Script"
echo "============================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "README.md" ]; then
    echo "❌ Error: Please run this script from the munero-platform root directory"
    exit 1
fi

# Step 1: Create virtual environment if it doesn't exist
if [ ! -d "backend/venv" ]; then
    echo "📦 Creating Python virtual environment..."
    cd backend
    python3 -m venv venv
    cd ..
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Step 2: Install dependencies
echo ""
echo "📥 Installing Python dependencies..."
backend/venv/bin/pip install --quiet --upgrade pip
backend/venv/bin/pip install --quiet -r backend/requirements.txt
echo "✅ Dependencies installed"

# Step 3: Create database if it doesn't exist
if [ ! -f "data/munero.sqlite" ]; then
    echo ""
    echo "💾 Creating database from CSV files..."
    python3 scripts/ingest_data.py
else
    echo ""
    echo "✅ Database already exists at data/munero.sqlite"
    echo "   To recreate it, delete the file and run: python3 scripts/ingest_data.py"
fi

# Step 4: Check Ollama
echo ""
echo "🤖 Checking Ollama status..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running"
    
    # Check if the model is available
    if curl -s http://localhost:11434/api/tags | grep -q "qwen2.5-coder:7b"; then
        echo "✅ Model qwen2.5-coder:7b is available"
    else
        echo "⚠️  Model qwen2.5-coder:7b not found"
        echo "   Run: ollama pull qwen2.5-coder:7b"
    fi
else
    echo "⚠️  Ollama is not running"
    echo "   Start it with: ollama serve"
    echo "   Then pull the model: ollama pull qwen2.5-coder:7b"
fi

echo ""
echo "============================================================"
echo "✅ SETUP COMPLETE!"
echo "============================================================"
echo ""
echo "📚 Next steps:"
echo ""
echo "1. Start the backend server:"
echo "   cd backend"
echo "   ./venv/bin/python main.py"
echo ""
echo "2. Or use the start script:"
echo "   ./scripts/start_backend.sh"
echo ""
echo "3. Open the API docs:"
echo "   http://localhost:8000/docs"
echo ""
echo "4. Test the health endpoint:"
echo "   curl http://localhost:8000/health"
echo ""
