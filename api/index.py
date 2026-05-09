"""Vercel serverless entry point for TasteGo Flask app."""
import sys
import os

# Add parent directory to path so imports work
parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, parent_dir)

# Set template and static folders explicitly for Vercel
os.chdir(parent_dir)

from app import app

# Vercel needs this named 'app'
app = app
