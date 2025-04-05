from app import app  # Esto importa tu aplicación Flask que está en app.py
from vercel_wsgi import handle_request

def handler(request, context):
    return handle_request(app, request)
