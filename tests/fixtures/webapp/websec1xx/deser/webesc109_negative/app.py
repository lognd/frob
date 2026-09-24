from flask import render_template_string


def handler():
    return render_template_string("<b>static label</b>")
