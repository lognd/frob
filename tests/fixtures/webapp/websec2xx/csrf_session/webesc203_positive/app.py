from flask import Flask
from flask_wtf import CSRFProtect

app = Flask(__name__)
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 1800
csrf = CSRFProtect(app)
