"""Static fixture for T-3856: a `frob:todo` free-text note as a real
`#` comment (not inside a docstring) -- must parse in python exactly like
every other supported language."""


def f() -> None:
    """One-line WHY/WHAT: fixture no-op used only for DSL001 parsing."""
    # frob:todo T-0010 cache the lookup in a PyOnceLock
    return None
