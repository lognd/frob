import ssl
from flask import Flask

app = Flask(__name__)

context = ssl.SSLContext()
context.minimum_version = ssl.TLSVersion.TLSv1_2
