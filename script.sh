#!/bin/bash
set -e

echo "--- Starting Multi-Component Deployment ---"

# 1. Start MCP Server
echo "[1/5] Starting MCP Server..."
python mcp_server/server.py &

# 2. Start Vector DB Workflow
echo "[2/5] Starting Vector DB Workflow..."
python vectordB_workflow/server.py &

# 3. Start Archive Worker
echo "[3/5] Starting Archive Worker..."
python data_sync_workflow/archive_worker.py &

# 4. Start Frontend (Port 3000)
echo "[4/5] Starting Frontend (Port 3000)..."
cd frontend && python -m http.server 3000 &
cd ..

# 5. Start Chatbot (Main App)
echo "[5/5] Starting Chatbot Main App..."
python chatbot/main.py
