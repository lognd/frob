"""Compliant Flask app-factory fixture (T-5349): secure cookies, CSRFProtect wired."""

from flask import Flask
from flask_wtf import CSRFProtect


def create_app():
    app = Flask(__name__)
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = 900
    CSRFProtect(app)
    return app
