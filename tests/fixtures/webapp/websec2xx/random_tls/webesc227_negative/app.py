import requests
from flask import Flask

app = Flask(__name__)


def call_upstream():
    return requests.get("https://upstream.example.com/data")
