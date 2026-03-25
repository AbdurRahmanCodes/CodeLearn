"""Vercel serverless entrypoint for CodeLearn Flask app."""

from app import create_app

# Vercel expects a module-level `app` object for Python web frameworks.
app = create_app()
