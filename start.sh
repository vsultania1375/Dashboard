#!/bin/bash

echo ""
echo "================================================"
echo " Service Analysis Dashboard v2.0"
echo " PAN India Alarm System Intelligence Platform"
echo "================================================"
echo ""

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker Desktop is not running!"
    echo ""
    echo "Please open Docker Desktop and wait for it to start."
    echo "Then run this script again."
    exit 1
fi

echo "[OK] Docker is running"
echo ""
echo "Starting all services..."
echo ""

cd "$(dirname "$0")"
docker-compose up -d --build

if [ $? -ne 0 ]; then
    echo "[ERROR] Something went wrong. See error above."
    exit 1
fi

echo ""
echo "Waiting for database to initialize..."
sleep 10

echo ""
echo "================================================"
echo " Dashboard is ready!"
echo ""
echo " Open your browser and go to:"
echo " http://localhost"
echo ""
echo " Login: admin / Admin@1234"
echo " (You will be asked to change password)"
echo "================================================"
echo ""

# Try to open browser automatically
if command -v xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost
elif command -v open > /dev/null 2>&1; then
    open http://localhost
fi

echo "Dashboard is running. Press Ctrl+C to view logs."
echo ""
docker-compose logs -f backend
