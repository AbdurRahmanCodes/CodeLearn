"""Compatibility runner for the modular Flask application.

This file intentionally remains as a tiny shim so existing commands such as
`python app.py` continue to work while all app logic lives in the modular
package under app/.
"""

from app import create_app


app = create_app()


if __name__ == "__main__":
    print("=" * 60)
    print("CodeLearn Platform - Modular Runtime")
    print("=" * 60)
    print("Starting Flask development server...")
    print("Visit: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host="127.0.0.1", port=5000)
