from pathlib import Path


def allowed(p: Path) -> bool:
    return p.parts[0] == "src"
