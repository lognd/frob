from flask import Flask

app = Flask(__name__)

messages = [
    {"role": "system", "content": "You are a helpful support bot for Acme Corp."}
]
