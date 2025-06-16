#!/bin/bash
# Start Redis for BrowserBot caching

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "Redis is not installed. Installing..."
    
    # Detect OS and install Redis
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install redis
        else
            echo "Please install Homebrew first: https://brew.sh"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y redis-server
        elif command -v yum &> /dev/null; then
            sudo yum install -y redis
        else
            echo "Unsupported Linux distribution"
            exit 1
        fi
    else
        echo "Unsupported OS: $OSTYPE"
        exit 1
    fi
fi

# Check if Redis is already running
if pgrep -x "redis-server" > /dev/null; then
    echo "Redis is already running"
else
    echo "Starting Redis..."
    redis-server --daemonize yes --port 6379
    echo "Redis started on port 6379"
fi

# Verify Redis is responding
if redis-cli ping > /dev/null 2>&1; then
    echo "Redis is ready!"
else
    echo "Redis failed to start"
    exit 1
fi