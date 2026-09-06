"""T-3912: `frob.toml`'s `[gates.severity]` table can re-severity ANY rule
after `_depr003_violations` computes it -- so a gate returning the right
severity is not sufficient on its own; the config must agree. This module
is kept separate from `tests/gates_suite/test_debt.py` deliberately: that
file's existing scope-closure fan-out (many unrelated DEBT/DEPR tests
citing `src/frob/gates/__init__.py` and `src/frob/gates/_debt_deprecated.py`
as `frob:tests` targets) would otherwise drag this ticket's scope far
beyond the two files (`frob.toml`, this test) the fix actually touches.
"""

from pathlib import Path

from frob.gates import Severity, deprecated_gate
from frob.gates._waive import _apply_severity_overrides, _severity_overrides
from frob.tickets import TicketQueue, TicketState
from tests.conftest import _first_rule, _snapshot, _ticket
from tests.conftest import _write as _write_fixture


def test_depr003_survives_repo_severity_overrides(tmp_path: Path) -> None:
    """T-3912: a `DEPR003 = "error"` override forces an in-window
    deprecation to ERROR on every run, contradicting the sunset-window
    contract the rule exists to provide (T-3906 hit this live: a fresh,
    far-future `frob:deprecated` failed `frob check` the day it was
    added). Locks that the override mechanism itself works -- so the
    companion test below, proving THIS repo's `frob.toml` does not set
    it, is the actual regression guard against this recurring."""
    # frob:tests \
    # tests/gates_suite/test_depr003_severity_override.py::test_depr003_survives_repo_\
    # severity_overrides
    source = (
        "def helper(x):\n"
        '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
        "    return x\n"
    )
    _write_fixture(tmp_path, "src/a.py", source)
    _write_fixture(tmp_path, "frob.toml", '[gates.severity]\nDEPR003 = "error"\n')
    snap = _snapshot(tmp_path)
    queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
    violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
    overridden = _apply_severity_overrides(violations, tmp_path)
    v = _first_rule(overridden, "DEPR003")
    assert v is not None
    assert v.severity == Severity.ERROR


def test_depr003_not_forced_to_error_in_this_repo() -> None:
    """T-3912: this repo's own `frob.toml` must not re-force DEPR003 to
    error -- that config is exactly what turned a documented WARN (a
    deprecation still inside its sunset window) into a hard `frob check`
    failure the day the first live `frob:deprecated` directive (T-3906)
    was added, with no code change and no expiry involved. DEPR004
    (past-sunset escalation) is unaffected and stays error."""
    # frob:tests \
    # tests/gates_suite/test_depr003_severity_override.py::test_depr003_not_forced_to_\
    # error_in_this_repo
    repo_root = Path(__file__).resolve().parents[2]
    overrides = _severity_overrides(repo_root)
    assert overrides.get("DEPR003") != Severity.ERROR
    assert overrides.get("DEPR004") == Severity.ERROR
