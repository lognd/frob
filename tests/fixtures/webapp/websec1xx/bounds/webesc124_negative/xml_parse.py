"""WEBSEC124 negative fixture: the same shape, via defusedxml."""

from defusedxml.ElementTree import parse


def load_user_xml(path):
    return parse(path)
