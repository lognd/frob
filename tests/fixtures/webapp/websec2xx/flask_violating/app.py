"""Violating Flask app-factory fixture (T-5349): insecure cookies, no CSRF protection."""
from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = False
    return app
