import sys

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

# tomllib is stdlib on 3.11+; fall back to tomli or toml on older Python.
# Unconditional try/except so ty only evaluates the first branch.
try:
    import tomllib as toml  # type: ignore[import-not-found,no-redef]  # ty: ignore[unresolved-import]
except ImportError:
    try:
        import tomli as toml  # type: ignore[import-not-found,no-redef]
    except ImportError:
        import toml  # type: ignore[import-not-found,no-redef]  # ty: ignore[unresolved-import]

__all__ = ["toml", "Self"]
