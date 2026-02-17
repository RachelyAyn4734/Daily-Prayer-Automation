#!/bin/bash

# Render.com startup script for RunPrayers API
set -e

echo "🚀 Starting RunPrayers API deployment..."

# Set production environment
export DATA_MODE=database
export PYTHONPATH=/opt/render/project/src:$PYTHONPATH

echo "✅ Environment configured"
echo "   - DATA_MODE: $DATA_MODE"
echo "   - PORT: ${PORT:-10000}"
echo "   - PYTHON_PATH: $PYTHONPATH"

# Validate critical environment variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo "❌ CRITICAL: Missing Supabase credentials!"
    echo "   Please set SUPABASE_URL and SUPABASE_KEY in Render dashboard"
    exit 1
fi

if [ -z "$SENDER_EMAIL" ] || [ -z "$SENDER_PASSWORD" ]; then
    echo "❌ CRITICAL: Missing email credentials!"
    echo "   Please set SENDER_EMAIL and SENDER_PASSWORD in Render dashboard"
    exit 1
fi

echo "✅ Environment validation passed"

# Test database connectivity
echo "🔍 Testing Supabase connection..."
python -c "
import asyncio
import sys
import os
sys.path.append('/opt/render/project/src')
from app.core.supabase_client import get_supabase

async def test_connection():
    try:
        client = await get_supabase()
        if await client.is_connected():
            print('✅ Supabase connection successful')
            return True
        else:
            print('❌ Supabase connection failed')
            return False
    except Exception as e:
        print(f'❌ Supabase connection error: {e}')
        return False

result = asyncio.run(test_connection())
sys.exit(0 if result else 1)
"

if [ $? -ne 0 ]; then
    echo "❌ Database connection test failed!"
    echo "   Check your Supabase credentials and network connectivity"
    exit 1
fi

echo "✅ Database connection verified"

# Start the application
echo "🚀 Starting FastAPI application..."
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-10000} \
    --workers 2 \
    --worker-connections 1000 \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --log-level info \
    --access-logfile - \
    --error-logfile -