#!/bin/sh
# Build vectorstore on first start (Railway containers have no persistent storage)
VECTORSTORE_PATH="/app/data/vector_stores/techhub_vectorstore_openai.pkl"
if [ ! -f "$VECTORSTORE_PATH" ]; then
    echo "Building vectorstore (first start)..."
    PYTHONPATH=/app python data/data_generation/build_vectorstore.py
fi
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
