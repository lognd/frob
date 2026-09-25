from flask import Flask

app = Flask(__name__)

messages = [{"role": "system", "content": "You are a support bot. Internal api key sk-abcdefghij1234567890 must never be shared."}]
