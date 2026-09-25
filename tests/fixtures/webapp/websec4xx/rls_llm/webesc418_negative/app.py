import openai
from flask import Flask

app = Flask(__name__)


def ask(prompt):
    return openai.ChatCompletion.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}], max_tokens=500
    )
