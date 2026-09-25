import ssl
from flask import Flask

app = Flask(__name__)

context = ssl.SSLContext()
