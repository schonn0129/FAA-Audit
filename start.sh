#!/bin/bash

# FAA DCT Audit Application Startup Script

echo "Starting FAA DCT Audit Application..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed"
    exit 1
fi

# Install backend dependencies if needed
echo "Checking backend dependencies..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt
cd ..

# Find free ports (default 5000/3000)
find_free_port() {
    local port=$1
    local max_tries=20

    if ! command -v lsof &> /dev/null; then
        echo "$port"
        return
    fi

    while [ $max_tries -gt 0 ]; do
        if lsof -nP -iTCP:$port -sTCP:LISTEN &> /dev/null; then
            port=$((port + 1))
            max_tries=$((max_tries - 1))
        else
            echo "$port"
            return
        fi
    done

    echo "$port"
}

BACKEND_PORT=${BACKEND_PORT:-5000}
FRONTEND_PORT=${FRONTEND_PORT:-3000}

BACKEND_PORT=$(find_free_port "$BACKEND_PORT")
FRONTEND_PORT=$(find_free_port "$FRONTEND_PORT")

# Install frontend dependencies if needed
echo "Checking frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
cd ..

echo ""
echo "=========================================="
echo "Starting application..."
echo "=========================================="
echo ""
echo "Backend will run on: http://localhost:${BACKEND_PORT}"
echo "Frontend will run on: http://localhost:${FRONTEND_PORT}"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Start backend in background
cd backend
source venv/bin/activate
BACKEND_PORT=$BACKEND_PORT python app.py &
BACKEND_PID=$!
cd ..

# Start frontend
cd frontend
VITE_BACKEND_PORT=$BACKEND_PORT VITE_FRONTEND_PORT=$FRONTEND_PORT npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for user interrupt
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

wait
