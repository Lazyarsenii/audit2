#!/usr/bin/env python3
"""Startup script with error logging."""
import os
import sys
import traceback

def main():
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}...", flush=True)
    
    try:
        # Test imports first
        print("Testing imports...", flush=True)
        from app.main import app
        print("Imports OK!", flush=True)
        
        # Start uvicorn
        import uvicorn
        print(f"Starting uvicorn on 0.0.0.0:{port}", flush=True)
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        print(f"STARTUP ERROR: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
