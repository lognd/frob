import yaml


def handler(raw_text):
    return yaml.load(raw_text)
