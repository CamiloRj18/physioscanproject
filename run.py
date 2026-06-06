"""Punto de entrada para desarrollo local.

Uso:
    python run.py
    flask --app app run --debug
"""
import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app(os.environ.get("FLASK_ENV", "desarrollo"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
