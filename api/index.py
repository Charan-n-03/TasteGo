"""Vercel serverless entry point for TasteGo Flask app."""
import sys
import os

# Add parent directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app

# Vercel expects a variable named 'app' or a handler
app = app
