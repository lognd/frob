"""BARETOOL001 gate wiring (T-3887/T-4125): turns `frob.vet._bare_
toolchain.bare_toolchain_findings` into repo-wide `Violation`s over every
git-tracked `.py` file, the same tracked-file-scan shape `frob.gates.
_taint_gate`/`_secrets`/`_opaque` already use.

THE DEFECT THIS CLOSES: a bare toolchain-name argv literal (`["ty",
...]`, `["ruff", ...]`) resolves through the SPAWNING PROCESS's own PATH
rather than the checked project's own `uv`-managed environment -- T-4125
measured a land refusing a ticket on `ty` 0.0.58's verdict (a PATH-
resolved global install) when the project itself pins `ty` 0.0.46, and a
consumer independently reported the identical defect in the OPPOSITE
version direction. `frob.process._project_tool.project_tool_argv` is the
one correct spelling (`uv run --project <root> <tool> ...`); this gate
is the regrowth guard so a fourth bare-name call site cannot reappear
once the T-4125 population is fixed (three consumers have now reported
this defect class from three independent directions).

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`opaque_gate`/`taint_gate` already follow for a brand-new structural
rule: a first measured hit set needs a real fix-or-waive pass before
ERROR is safe repo-wide (this gate's OWN population was fixed as part of
landing it, so the expected first-turn-on hit count is zero, but the
posture is deliberately the same regardless)."""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.vet._bare_toolchain import bare_toolchain_findings

_log = get_logger(__name__)

__all__ = ["bare_toolchain_gate"]


def _tracked_python_files(root: Path) -> tuple[str, ...]:
    """`git ls-files -- '*.py'` under `root`, root-relative POSIX paths,
    `()` on any git failure -- mirrors `frob.gates._taint_gate`'s own
    copy of this exact shape."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", "--", "*.py"))
    if spawned.is_err:
        _log.warning("bare_toolchain_gate: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("bare_toolchain_gate: git ls-files exited %d", result.returncode)
        return ()
    files = tuple(line for line in result.stdout.splitlines() if line.strip())
    _log.debug("bare_toolchain_gate: %d tracked .py file(s)", len(files))
    return files


# frob:doc docs/modules/process.md#project-scoped-toolchain-spawns-t-3887t-4125
# frob:ticket T-3887
# frob:ticket T-4125
# frob:ticket T-4163
# frob:enforces CHK-GATE-BARETOOL001
# frob:tests tests/unit/vet/test_bare_toolchain.py::TestBareToolchainGate.test_flags_bare_argv_literal  # noqa: E501
# frob:tests tests/unit/vet/test_bare_toolchain.py::TestBareToolchainGate.test_clean_on_project_tool_argv_spelling  # noqa: E501
def bare_toolchain_gate(root: Path) -> tuple[Violation, ...]:
    """BARETOOL001: every git-tracked `.py` file scanned for a bare
    toolchain-name argv literal (`frob.vet._bare_toolchain.
    bare_toolchain_findings`) -- WARN-tier, see module docstring."""
    root = Path(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _tracked_python_files(root):
        abs_path = root / rel_path
        try:
            findings = bare_toolchain_findings(abs_path)
        except OSError as exc:
            _log.debug("bare_toolchain_gate: skipping unreadable %s: %s", rel_path, exc)
            continue
        scanned += 1
        for finding in findings:
            violations.append(
                Violation(
                    rule="BARETOOL001",
                    severity=Severity.WARN,
                    file=rel_path,
                    line=finding.line,
                    message=(
                        f"BARETOOL001: {rel_path}:{finding.line} argv literal "
                        f"starts with bare {finding.tool!r} -- this resolves "
                        f"through the SPAWNING process's own PATH, not the "
                        f"checked project's own environment (T-4125: a land "
                        f"refused a ticket on a PATH-resolved `ty` version the "
                        f"project neither uses nor pins). Route through "
                        f"`frob.process._project_tool.project_tool_argv(root, "
                        f"{finding.tool!r}, ...)` instead, or "
                        f'`frob:waive BARETOOL001 reason="..."` with a real '
                        f"justification (e.g. a probe that deliberately checks "
                        f"PATH resolution itself)"
                    ),
                )
            )

    _log.info(
        "bare_toolchain_gate: scanned %d tracked .py file(s), %d violation(s)",
        scanned,
        len(violations),
    )
    return tuple(violations)
