from __future__ import annotations

from pathlib import Path


def ensure_gitignore(root: Path) -> None:
    gi = root / ".gitignore"
    entry = ".frob/"
    if gi.exists():
        content = gi.read_text()
        if entry not in content:
            gi.write_text(content.rstrip() + f"\n{entry}\n")
    else:
        gi.write_text(f"{entry}\n")
