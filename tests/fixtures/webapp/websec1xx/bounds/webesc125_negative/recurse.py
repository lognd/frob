"""WEBSEC125 negative fixture: the same recursion, with a depth guard."""


def process_tree(node, depth=0):
    if depth > 100:
        return
    for child in node.children:
        process_tree(child, depth + 1)
