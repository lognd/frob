"""T-4324/T-4407: LIVE deferred-sweep rapid-debt visibility, split out of
`verify_runner.py` to keep that module under LARGE001's 800-line
threshold. No behavior change -- see `docs/modules/verify-rapid-debt-
visibility.md` for the full liveness contract this module implements.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


# frob:doc docs/modules/verify-rapid-debt-visibility.md#liveness
# frob:tests \
# tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt.test_no_baseline_is_live
# frob:ticket T-4324
class RapidDebtEntryView(BaseModel):
    """One LIVE deferred-sweep rapid-debt entry (T-1681/T-4324)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    commit: str
    ticket_id: str


#: T-4324: `_rapid_sweep.py`'s deferred/UNMEASURABLE-sweep `skipped` value
#: (duplicated per T-3464's precedent, to avoid importing that module).
_DEFERRED_SWEEP_SKIPPED = "post-land-unscoped-sweep-deferred"
#: `.frob/rapid-debt.jsonl` and its rolling post-land-sweep baseline.
_RAPID_DEBT_REL = Path(".frob") / "rapid-debt.jsonl"
_RAPID_SWEEP_BASELINE_REL = Path(".frob") / "rapid-sweep-baseline.json"


# frob:ticket T-4324
def _read_rapid_sweep_baseline_commit(root: Path) -> str | None:
    """Last recorded rolling baseline commit, or `None` (unmeasured)."""
    path = root / _RAPID_SWEEP_BASELINE_REL
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        commit = raw.get("commit") if isinstance(raw, dict) else None
    except Exception:  # noqa: BLE001 -- corrupt/unreadable baseline
        return None
    return str(commit) if commit else None


# frob:ticket T-4324
def _commit_covered_by(root: Path, commit: str, cover: str) -> bool:
    """`commit` is `cover` or an ancestor of it; `False` on any spawn
    failure (never silently clears debt)."""
    from frob.gitio import run_argv

    cmd = ["git", "-C", str(root), "merge-base", "--is-ancestor", commit, cover]
    spawned = run_argv(cmd)
    return spawned.is_ok and spawned.danger_ok.returncode == 0


# frob:tests \
# tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt.test_no_baseline_is_live
# frob:tests \
# tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt.test_later_baseline_clears
# frob:tests \
# tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt.test_uncovered_stays_live
# frob:ticket T-4324
def _live_deferred_sweep_debt(root: Path) -> tuple[RapidDebtEntryView, ...]:
    """LIVE deferred-sweep `rapid-debt.jsonl` entries (T-1681/T-4324) --
    see `docs/modules/verify-rapid-debt-visibility.md` for liveness."""
    path = root / _RAPID_DEBT_REL
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        return ()
    baseline_commit = _read_rapid_sweep_baseline_commit(root)
    live: dict[tuple[str, str], RapidDebtEntryView] = {}
    for raw_line in raw_text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if (
            not isinstance(entry, dict)
            or entry.get("skipped") != _DEFERRED_SWEEP_SKIPPED
        ):
            continue
        commit = entry.get("commit")
        ticket_id = entry.get("ticket")
        if not isinstance(commit, str) or not commit or not isinstance(ticket_id, str):
            continue
        cleared = baseline_commit is not None and _commit_covered_by(
            root, commit, baseline_commit
        )
        if not cleared:
            live[(commit, ticket_id)] = RapidDebtEntryView(
                commit=commit, ticket_id=ticket_id
            )
    return tuple(live.values())
