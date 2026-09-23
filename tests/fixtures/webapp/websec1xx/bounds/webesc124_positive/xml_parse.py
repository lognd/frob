"""WEBSEC124 positive fixture: an XML parse call with no XXE guard."""

from xml.etree import ElementTree


def load_user_xml(path):
    return ElementTree.parse(path)
