#!/bin/bash

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if venv exists
if [ ! -d "$DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$DIR/venv"
    echo "Installing dependencies..."
    "$DIR/venv/bin/pip" install -r "$DIR/requirements.txt"
fi

# Run the agent
echo "Starting PR Agent System..."
"$DIR/venv/bin/python" "$DIR/main.py"
