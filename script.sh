#!/bin/bash
set -e

echo "--- Starting Multi-Component Deployment ---"

# Use /app as the base directory
export APP_HOME=/app

# 1. Start MCP Server
echo "[1/5] Starting MCP Server..."
python $APP_HOME/mcp_server/server.py &

# 2. Start Vector DB Workflow
echo "[2/5] Starting Vector DB Workflow..."
python $APP_HOME/vectordB_workflow/server.py &

# 3. Start Archive Worker
echo "[3/5] Starting Archive Worker..."
python $APP_HOME/data_sync_workflow/archive_worker.py &

# 4. Start Frontend (Port 3000)
echo "[4/5] Starting Frontend (Port 3000)..."
cd $APP_HOME/frontend && python -m http.server 3000 &
cd $APP_HOME

# 5. Start Chatbot (Main App)
echo "[5/5] Starting Chatbot Main App..."
# Use absolute path to avoid the // issue
python $APP_HOME/chatbot/main.py
