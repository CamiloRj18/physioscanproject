"""Punto de entrada WSGI para producción (gunicorn / waitress).

gunicorn:  gunicorn "wsgi:application" --workers 4 --bind 0.0.0.0:8000
waitress:  waitress-serve --host=0.0.0.0 --port=8000 wsgi:application
"""
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402
from werkzeug.middleware.proxy_fix import ProxyFix  # noqa: E402

application = create_app("produccion")
# Trust X-Forwarded-Proto and X-Forwarded-Host from Vercel/Railway reverse proxy
# so url_for(..., _external=True) generates https:// links with the correct hostname.
application.wsgi_app = ProxyFix(application.wsgi_app, x_proto=1, x_host=1)
