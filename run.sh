#!/bin/bash

# Daktari Development Runner
# Runs both backend and frontend servers

echo "🩺 Starting Daktari..."
echo ""

# Check if .env exists in backend
if [ ! -f backend/.env ]; then
    echo "⚠️  No backend/.env found. Copy backend/.env.example to backend/.env and add your API keys."
    echo ""
fi

# Start backend
echo "📡 Starting backend server on http://localhost:8000..."
cd backend
python -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 2

# Start frontend
echo "🖥️  Starting frontend on http://localhost:5173..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Daktari is running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Trap Ctrl+C to kill both processes
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Wait for either process to exit
wait
