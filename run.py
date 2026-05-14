"""
Startup script — always uses the correct venv Python/uvicorn.
Run with:  python run.py
"""
import os
import sys
import subprocess

# Make sure we're using the venv Python
venv_uvicorn = os.path.join(os.path.dirname(__file__), "venv", "Scripts", "uvicorn")
if not os.path.exists(venv_uvicorn):
    venv_uvicorn = os.path.join(os.path.dirname(__file__), "venv", "bin", "uvicorn")

if not os.path.exists(venv_uvicorn):
    print("[ERROR] venv not found. Run: python -m venv venv  then  venv\\Scripts\\pip install -r requirements.txt")
    sys.exit(1)

print("=" * 55)
print("  AI Travel Planner Agent")
print("  http://localhost:8000/docs")
print("=" * 55)

subprocess.run([
    venv_uvicorn,
    "app.main:app",
    "--reload",
    "--host", "0.0.0.0",
    "--port", "8000",
])
