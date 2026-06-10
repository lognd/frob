import sys

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

if sys.version_info >= (3, 11):
    import tomllib as toml
else:
    try:
        import tomllib as toml
    except ImportError:
        try:
            import tomli as toml  # type: ignore[no-redef]
        except ImportError:
            import toml  # type: ignore[no-redef]

__all__ = ['toml', 'Self']
