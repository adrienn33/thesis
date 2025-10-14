#!/bin/bash
# Start MCP Developer Portal

echo "🚀 Starting MCP Developer Portal..."
echo ""
echo "📋 Prerequisites:"
echo "  ✓ Docker container 'shopping' should be running"
echo "  ✓ MCP servers copied to container /tmp/"
echo ""

# Check if Docker container is running
if ! docker ps | grep -q shopping; then
    echo "❌ Error: Docker container 'shopping' is not running"
    echo "   Start it with: docker start shopping"
    exit 1
fi

echo "✅ Docker container is running"
echo ""

# Check if npm dependencies are installed
if [ ! -d "dev-portal/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd dev-portal && npm install && cd ..
fi

echo "🎯 Starting services..."
echo ""
echo "Backend API will run on: http://localhost:5000"
echo "Frontend will run on: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both services"
echo ""

# Start backend in background
source venv/bin/activate
python3 dev_portal_backend.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
cd dev-portal
npm run dev

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
