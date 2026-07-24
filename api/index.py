"""
Vercel Serverless Function entry point for AI Calorie Assistant.
Mounts the FastAPI application for Vercel's Python runtime.
"""
import sys
import os

# Ensure the backend directory is in the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app
