import openai
from flask import Flask

app = Flask(__name__)


def run_agent(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}]
    )
    code = response.choices[0].message.content
    exec(code)
