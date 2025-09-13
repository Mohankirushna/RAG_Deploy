#!/bin/bash

# Start the backend server in the background
echo "Starting backend server..."
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start the frontend development server in the background
echo "Starting frontend development server..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

# Function to handle script termination
cleanup() {
  echo "Shutting down servers..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}

# Set up trap to handle script termination
trap cleanup SIGINT SIGTERM

# Keep the script running
wait
