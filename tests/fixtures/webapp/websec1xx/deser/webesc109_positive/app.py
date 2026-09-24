from flask import render_template_string, request


def handler():
    name = request.args.get("name")
    return render_template_string(name)
