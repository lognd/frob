from pathlib import Path


def allowed(p: Path) -> bool:
    return str(p).startswith("src/")
