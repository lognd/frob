"""SEC005 gate wiring (docs/modules/gates.md#rule-catalog, T-0781):
turns `frob.vet._taint.taint_findings` into repo-wide `Violation`s over
every git-tracked `.py` file, the same tracked-file-scan shape
`frob.gates._secrets`/`_opaque` already use.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.vet._taint import taint_findings

_log = get_logger(__name__)

__all__ = ["taint_gate"]


def _tracked_python_files(root: Path) -> tuple[str, ...]:
    """`git ls-files -- '*.py'` under `root`, root-relative POSIX paths,
    `()` on any git failure -- mirrors `frob.gates._opaque`/`_secrets`'s
    own per-module copy of this exact shape."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", "--", "*.py"))
    if spawned.is_err:
        _log.warning("taint_gate: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("taint_gate: git ls-files exited %d", result.returncode)
        return ()
    files = tuple(line for line in result.stdout.splitlines() if line.strip())
    _log.debug("taint_gate: %d tracked .py file(s)", len(files))
    return files


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0781
# frob:tests tests/unit/vet/test_taint.py::TestTaintGate.test_taint_gate_emits_warn_severity_violation  # noqa: E501
# frob:tests tests/unit/vet/test_taint.py::TestTaintGate.test_taint_gate_no_findings_on_empty_tracked_set  # noqa: E501
# frob:enforces CHK-GATE-SEC005
# frob:enforces CWE-88
def taint_gate(root: Path) -> tuple[Violation, ...]:
    """SEC005: every git-tracked `.py` file scanned for
    `frob.vet._taint.taint_findings` (T-0781 -- a value parsed from
    `.git/`/`.frob/` repo-writable state reaching a subprocess argv
    position with no validator hop or `--` terminator). WARN-tier at
    first turn-on -- same T-0688/T-0973 promotion posture `opaque_gate`
    already follows: a brand-new structural rule needs a real fix-or-
    waive pass over its first measured hit set before ERROR is safe."""
    root = Path(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _tracked_python_files(root):
        abs_path = root / rel_path
        try:
            findings = taint_findings(abs_path)
        except OSError as exc:
            _log.debug("taint_gate: skipping unreadable %s: %s", rel_path, exc)
            continue
        scanned += 1
        for finding in findings:
            violations.append(
                Violation(
                    rule="SEC005",
                    severity=Severity.WARN,
                    file=rel_path,
                    line=finding.sink_line,
                    message=(
                        f"SEC005: {rel_path}:{finding.sink_line} "
                        f"{finding.sink_call}(...) argv includes "
                        f"{finding.var_name!r}, sourced from a repo-"
                        f"writable-state read at line {finding.source_line} "
                        f"(.git/.frob JSON or text another worktree/agent "
                        f"can write) with no validator call or a preceding "
                        f'`"--"` literal between source and sink -- pass '
                        f"the value through a `validate_*`/`sanitize_*` "
                        f'helper first, add a literal `"--"` terminator '
                        f"before it in the argv list, or "
                        f'`frob:waive SEC005 reason="..."` with a real '
                        f"justification"
                    ),
                )
            )

    _log.info(
        "taint_gate: scanned %d tracked .py file(s), %d violation(s)",
        scanned,
        len(violations),
    )
    return tuple(violations)
