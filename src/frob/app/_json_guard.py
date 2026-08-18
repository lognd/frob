from __future__ import annotations

import contextlib
import sys


# frob:ticket T-2486
# frob:ticket T-2492
class _StderrRedirectStdout:
    """`sys.stdout` replacement installed by `_guard_json_stdout_writes`
    (T-2486, promoted to this shared module by T-2492 so every `--json`
    CLI runner can reuse it, not just `frob check`): every `write` reaches
    `sys.stderr` (captured once at guard entry, immune to a later
    stdout/stderr reassignment mid-guard) instead of the real stdout, so a
    stray `print()`/`sys.stdout.write()` anywhere in the guarded call
    stack surfaces to the operator (must-still-inform) rather than
    corrupting the `--json` payload building up elsewhere
    (must-now-protect). This is the STRUCTURAL counterpart to T-2484's
    single-instance fix -- T-2484 fixed the one known leak (a misleveled
    log call in `frob.__main__`); this class plus
    `_guard_json_stdout_writes` below make a NEW leak, of any shape (bare
    `print`, `sys.stdout.write`, a misleveled log call not already
    wrapped in `quiet_stdout_logs`), structurally unable to reach the
    payload for the duration the guard is active. Delegates every OTHER
    attribute access to the real stdout object it stands in for, so code
    that merely INSPECTS `sys.stdout` (encoding, `isatty()`) during the
    guarded window keeps seeing the real terminal's answers -- only
    writes are redirected."""

    def __init__(self, real_stdout, real_stderr) -> None:  # noqa: ANN001
        """Bind to the real stdout/stderr objects captured at guard
        entry -- both fixed for this instance's lifetime, never
        re-resolved on each write, so a later `sys.stdout`/`sys.stderr`
        reassignment elsewhere cannot retarget an already-active guard."""
        self._real_stdout = real_stdout
        self._real_stderr = real_stderr

    # frob:doc docs/modules/app.md#runners
    # frob:tests tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard.test_planted_print_still_reaches_stderr kind="unit"  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as this line's original home in \
    # check_runner.py before T-2492 promoted it here"
    # frob:waive SELFAUDIT001 reason="T-2492: this fs.write capability already lived \
    # at this line in src/frob/app/check_runner.py (declared in design/frob.strata \
    # gates node's fs.write via-list) before this move; design/frob.strata is out of \
    # this ticket's declared scope (src/frob/app/*.py only), so the via-list update to \
    # add src/frob/app/_json_guard.py alongside check_runner.py lands as part of \
    # T-2495's edit to this same gates node"
    def write(self, s: str) -> int:
        """Redirect the write to the captured real stderr instead of
        stdout -- the one behavior this whole class exists for."""
        return self._real_stderr.write(s)

    # frob:doc docs/modules/app.md#runners
    # frob:tests tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard.test_planted_print_still_reaches_stderr kind="unit"  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as this line's original home in \
    # check_runner.py before T-2492 promoted it here"
    def flush(self) -> None:
        """Flush the captured real stderr (the stream writes actually
        landed on), not the stdout this object is standing in for."""
        self._real_stderr.flush()

    # frob:waive OPAQUE001 reason="T-2486/T-2492: __getattr__ here is a deliberate \
    # pass-through delegator (encoding/isatty/etc. forwarded to the real stdout this \
    # proxy stands in for) -- the class's own docstring states this is its whole \
    # purpose; it never routes to an attacker- or config-controlled target, only the \
    # one real_stdout object captured at __init__ time"
    def __getattr__(self, name: str):
        """Every non-write attribute (encoding, `isatty`, etc.) passes
        through to the real stdout object unchanged -- this class only
        ever intercepts writes, never stdout's other characteristics."""
        # frob:waive OPAQUE001 reason="T-2486/T-2492: plain attribute forwarding to \
        # the captured real_stdout object (not a dynamic/attacker-controlled name) -- \
        # the delegation IS this method's documented job, see the class docstring"
        return getattr(self._real_stdout, name)


# frob:ticket T-2486
# frob:ticket T-2492
@contextlib.contextmanager
def _guard_json_stdout_writes():  # noqa: ANN201
    """Structural boundary guard (T-2486, promoted to this shared module
    by T-2492) for a `--json` run: for the duration of this context,
    `sys.stdout` is NOT the real stdout -- every write anywhere in the
    guarded call stack (the caller's own code or any function it calls
    into, present or future) is transparently redirected to `sys.stderr`
    instead (`_StderrRedirectStdout`). This supersedes `quiet_stdout_logs`
    in every place `--json` previously relied on it alone: that primitive
    only raises the shared root logger's stdout-handler LEVEL, so it
    protects against a misleveled INFO/DEBUG *log call* but does nothing
    for a bare `print()`/`sys.stdout.write()` anywhere in the guarded
    span -- exactly the gap a NEW leak (not caught by RENDER001's static
    scan, e.g. from a dependency or a call this repo does not lint) could
    exploit. `quiet_stdout_logs` is still fine to layer underneath at an
    existing call site (T-0125 reentrant, so nesting is a no-op, not a
    double-clamp) as defense in depth, not replaced.

    CALLER CONTRACT: exit this context (the `with` block ends) BEFORE
    emitting the real `--json` payload, exactly as `frob.app.
    check_runner`'s own guarded spans do -- see that module for the
    original precedent this was extracted from."""
    real_stdout = sys.stdout
    sys.stdout = _StderrRedirectStdout(real_stdout, sys.stderr)
    try:
        yield
    finally:
        sys.stdout = real_stdout
