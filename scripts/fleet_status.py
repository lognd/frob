"""Report coordinator fleet state: root cleanliness, leases, worktree liveness.

WHY THIS EXISTS. Dispatching onto a dirty root DirtyMain-blocks every agent,
and removing a worktree whose agent is still live destroys its work. Both
have cost this fleet real time. This is the one-shot check that answers
"is it safe to dispatch, and which worktrees are actually idle?".

Liveness is inferred from each worktree's last commit age -- an agent that
has not committed in a long while is PROBABLY retired, but treat this as a
hint, not proof. `frob worktree remove` performs the authoritative
lease-and-liveness check and refuses when it is not safe; prefer it over
raw `git worktree remove`, which has deleted a live agent's checkout here.

Usage:
    python3 scripts/fleet_status.py [--idle-minutes N]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKTREES = REPO / ".claude" / "worktrees"
LEASES = REPO / ".git" / "frob-leases"


def _git(args: list[str], cwd: Path) -> str:
    """Run git in `cwd`, returning stripped stdout ('' on any failure)."""
    try:
        done = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def root_dirt() -> list[str]:
    """Porcelain lines for the root checkout; empty means safe to dispatch."""
    out = _git(["status", "--short", "--porcelain"], REPO)
    return [line for line in out.splitlines() if line.strip()]


def leases() -> list[dict]:
    """Every held scope lease, as parsed lease records."""
    if not LEASES.is_dir():
        return []
    records = []
    for path in sorted(LEASES.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            records.append({"ticket_id": path.stem, "worktree": "<unreadable>"})
    return records


def worktrees(idle_seconds: int) -> list[tuple[str, int, bool]]:
    """Return (name, seconds-since-last-commit, looks_idle) per worktree."""
    if not WORKTREES.is_dir():
        return []
    rows = []
    now = time.time()
    for path in sorted(p for p in WORKTREES.iterdir() if p.is_dir()):
        stamp = _git(["log", "-1", "--format=%ct"], path)
        age = int(now - int(stamp)) if stamp.isdigit() else -1
        rows.append((path.name, age, age >= idle_seconds))
    return rows


def main() -> int:
    """Print root/lease/worktree state; exit 1 when root is dirty."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idle-minutes", type=int, default=20)
    args = parser.parse_args()

    dirt = root_dirt()
    print(f"ROOT {'DIRTY -- do not dispatch' if dirt else 'CLEAN'}")
    for line in dirt:
        print(f"  {line}")

    held = leases()
    print(f"LEASES {len(held)}")
    for record in held:
        name = Path(record.get("worktree", "?")).name
        print(f"  {record.get('ticket_id')} -> {name}")

    print("WORKTREES")
    for name, age, idle in worktrees(args.idle_minutes * 60):
        mins = "unknown" if age < 0 else f"{age // 60}m"
        print(f"  {name:28} last-commit {mins:>9}{'  IDLE?' if idle else ''}")

    return 1 if dirt else 0


if __name__ == "__main__":
    raise SystemExit(main())
