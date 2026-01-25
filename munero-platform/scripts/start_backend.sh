#!/bin/bash

# Munero AI Platform - Backend Startup Script

cd "$(dirname "$0")/.."

echo "🚀 Starting Munero AI Platform Backend..."
echo ""

# Check if venv exists
if [ ! -d "backend/venv" ]; then
    echo "❌ Virtual environment not found. Run ./scripts/setup.sh first"
    exit 1
fi

# Check if database exists
if [ ! -f "data/munero.sqlite" ]; then
    echo "❌ Database not found. Run ./scripts/setup.sh first"
    exit 1
fi

# Start the server
cd backend
exec ./venv/bin/python main.py
