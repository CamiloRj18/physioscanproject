"""Punto de entrada WSGI para producción (gunicorn / waitress).

gunicorn:  gunicorn "wsgi:application" --workers 4 --bind 0.0.0.0:8000
waitress:  waitress-serve --host=0.0.0.0 --port=8000 wsgi:application
"""
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

application = create_app("produccion")
