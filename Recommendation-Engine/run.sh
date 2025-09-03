#!/bin/bash

# Recommendation Engine Runner Script
# This script sets up the environment and runs the Streamlit app

echo "🛒 Starting Recommendation Engine..."

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "⚠️  No virtual environment found. Creating one..."
    python -m venv venv
    echo "✅ Virtual environment created."
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Activated virtual environment (venv)"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Activated virtual environment (.venv)"
fi

# Install dependencies if needed
echo "📦 Installing/updating dependencies..."
pip install -r requirements.txt

# Optional: Install interactive graph visualization
read -p "🎨 Install interactive graph visualization? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install st-link-analysis
    echo "✅ Interactive visualization installed"
fi

echo ""
echo "🚀 Starting Streamlit app..."
echo "📍 App will be available at: http://localhost:8501"
echo ""

# Run the Streamlit app
streamlit run app.py
