"""
WSGI Entry Point
Run with: python wsgi.py
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("CodeLearn Platform - Phase 1 Architecture")
    print("=" * 60)
    print("Starting Flask development server...")
    print("Visit: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host='127.0.0.1', port=5000)
