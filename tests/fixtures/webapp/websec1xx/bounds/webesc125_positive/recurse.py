"""WEBSEC125 positive fixture: unbounded recursion, no depth guard."""


def process_tree(node):
    for child in node.children:
        process_tree(child)
