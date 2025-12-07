#!/bin/bash

# Launch script for Streamlit UI

echo "🚀 Starting PR-Agent Streamlit UI..."
echo ""

# Check if streamlit is installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "❌ Streamlit not found. Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
fi

# Export environment variables from .env if it exists
if [ -f ".env" ]; then
    echo "✅ Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "✅ Launching Streamlit UI..."
echo "   URL: http://localhost:8501"
echo ""

# Launch Streamlit
streamlit run streamlit_app.py --server.port 8501 --server.address localhost
