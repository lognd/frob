"""PLATFORM002: `os.kill(pid, 0)` outside the one sanctioned liveness probe
(T-3696, docs/modules/gates.md#platform002-oskillpid-0-outside-the-
sanctioned-liveness-probe-t-3696).

On POSIX, `os.kill(pid, 0)` is a genuine side-effect-free liveness probe:
signal `0` sends nothing, so a `ProcessLookupError` means the pid is gone.
On win32, it is NOT side-effect-free -- CPython's Windows `os.kill` maps
signal `0` to `signal.CTRL_C_EVENT` (numeric value `0`, the two are the
same int) and implements delivery via `GenerateConsoleCtrlEvent`, which
broadcasts a real Ctrl+C to every process attached to the caller's
console process group, including the calling process itself and any
subprocess sharing its console. T-3686 was a 20-round win32 debugging
saga caused by exactly this: `frob.check._pid_alive` (T-3256's admission-
registry pid-reaping helper) called `os.kill(pid, 0)` unconditionally on
every platform, self-interrupting `frob check` on win32 with an injected
SIGINT that had nothing to do with any real Ctrl+C.

The fix `frob.process._pid_liveness` already exists and is the one
sanctioned home for process-liveness probing (T-3018/T-3003/T-3191):
`pid_alive`/`pid_alive_tristate` never call `os.kill` on a win32 backend,
opening the pid with `PROCESS_QUERY_LIMITED_INFORMATION` (no kill/signal
rights at all) and reading `GetExitCodeProcess`/`STILL_ACTIVE` instead.
Per this repo's standing perf-findings-become-lint-rules doctrine, the
root cause -- a NEW `os.kill(<anything>, 0)` call site outside that one
module -- ships as a permanent static detector so this exact mistake
shape cannot recur silently, mirroring PLATFORM001's own "one incident,
one static check generalizing the detection" precedent
(`frob.gates._walk_lint`, T-2919).

Detection is AST-based (`ast.parse`/`ast.walk`), matching this package's
structural-gate precedent (`_walk_lint`/`_port_selfcheck`/
`_pii_structural`) rather than a regex/substring scan over source text --
this repo's standing token-grammar-fixes-never-lexical doctrine: a text
scan for `"os.kill"` would both miss an aliased/bare `from os import
kill` call and false-fire on prose mentioning the string (this module's
own docstring, for one). `_kill_zero_signal_hit` matches `os.kill(...)`
(dotted, or bare-imported via a proven `from os import kill [as x]`
binding, the same alias-safety `_walk_lint._collect_import_bindings`
established) whose SECOND positional argument is the literal integer
`0` -- a real (non-zero) signal, e.g. `signal.SIGTERM`, is genuine signal
delivery and must never flag; a non-literal/dynamic second argument
(cannot be proven `0`) is likewise not flagged, since this is a
detectable-mistake check, not an unknowable-intent one.

`src/frob/process/_pid_liveness.py` is the one sanctioned exception,
allowlisted by exact relpath with a reason -- the same
`_ALLOWLIST`/`_SELF_EXCLUDED_FILES` shape PORT001/WALK001 already use.
Scans `src/frob/**` repo-wide via `tracked_python_files_for_gate`
(shared with WALK001/RENDER001/PORT001, T-0861/T-2389), same posture:
a win32-unsafe liveness probe anywhere in `src/frob/` is a repo-wide
concern, not a subdir-scoped one.

WARN tier on arrival (T-3696), matching every other new-detector turn-on
precedent in this repo (PORT001 T-2388, PLATFORM001 T-2919, SCOPE002
T-0998, the T-0756 new-gate-rule acceptance policy's own convention):
promotion to ERROR is a separate, later step once a real-repo false-
positive measurement exists.
"""

from __future__ import annotations

import ast
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gates._parse_failures import local_parse001_violation
from frob.gates._walk_lint import tracked_python_files_for_gate
from frob.logging import get_logger

_log = get_logger(__name__)

#: The one sanctioned home for `os.kill(pid, 0)` (T-3018/T-3003/T-3191) --
#: it IS the safe implementation this rule exists to steer every other
#: call site toward, so it cannot flag itself.
_ALLOWLIST: dict[str, str] = {
    "src/frob/process/_pid_liveness.py": (
        "T-3018/T-3003/T-3191: the one sanctioned process-liveness probe "
        "-- its POSIX branch legitimately calls os.kill(pid, 0); its "
        "win32 branch never calls os.kill at all (OpenProcess/"
        "GetExitCodeProcess instead), which is the whole point of "
        "steering every OTHER call site here"
    ),
}

#: This module's own file: its docstring/detection logic names the
#: flagged shape as prose/string literals it must not self-flag, same
#: self-exclusion PORT001/LEXCHECK001 give themselves for the identical
#: reason.
_SELF_EXCLUDED_FILES = frozenset({"src/frob/gates/_win32_kill_signal.py"})


# frob:waive DUP001 reason="this module's own docstring states this local dotted-name \
# unparse is the same small shape as frob.gates._walk_lint's / \
# frob.gates._render_lint's / frob.gates._pii_structural._env_access's siblings, kept \
# local deliberately rather than sharing a private helper across modules"
def _dotted_prefix(node: ast.expr) -> str | None:
    """The dotted-name text of an `Attribute`/`Name` chain (`os.kill` ->
    `"os.kill"`), or `None` for anything else -- same local unparse shape
    `_walk_lint._dotted_prefix`/`_pii_structural._env_access._dotted_prefix`
    already use (small enough that importing across gate modules for one
    helper is not worth the coupling)."""
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    else:
        return None
    return ".".join(reversed(parts))


def _collect_kill_bindings(tree: ast.Module) -> frozenset[str]:
    """Every local name, in ONE module, DEMONSTRABLY bound to `os.kill`
    via a top-level or nested `from os import kill [as x]` statement --
    a bare `kill(...)` call only counts when it provably reaches `os.kill`
    and not, say, a locally-defined function that happens to share the
    name (the same false-positive class `_walk_lint._collect_import_
    bindings`'s own docstring documents and guards against for
    `os.walk`)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module != "os":
            continue
        for alias in node.names:
            if alias.name == "kill":
                names.add(alias.asname or alias.name)
    return frozenset(names)


def _is_zero_signal(arg: ast.expr) -> bool:
    """Whether `arg` is provably the literal integer `0` -- a bare bool
    constant (`True`/`False`) is deliberately excluded even though
    `False == 0` in Python, since a caller writing `os.kill(pid, False)`
    is not writing the signal-0 liveness idiom this rule targets. A
    non-`Constant` (a name, an expression) is never provably zero and is
    deliberately not flagged -- deny-by-default would make this a
    "os.kill anywhere" nag rather than the detectable signal-0 mistake
    shape it exists to catch."""
    return (
        isinstance(arg, ast.Constant)
        and not isinstance(arg.value, bool)
        and arg.value == 0
    )


def _kill_zero_signal_hit(
    call: ast.Call, kill_names: frozenset[str]
) -> ast.expr | None:
    """The flagged second-argument node for a `os.kill(<anything>, 0)`-
    shaped call (dotted `os.kill(...)`, or a bare name proven bound to it
    by `kill_names`), or `None` if `call` doesn't match. Only a
    POSITIONAL second argument counts -- `os.kill` takes no keyword
    arguments in the stdlib signature, so a `sig=0` keyword is not a real
    call shape to worry about."""
    dotted = _dotted_prefix(call.func)
    is_kill = dotted == "os.kill" or (
        isinstance(call.func, ast.Name) and call.func.id in kill_names
    )
    if not is_kill or len(call.args) < 2:
        return None
    sig_arg = call.args[1]
    return sig_arg if _is_zero_signal(sig_arg) else None


def _scan_kill_zero_signal(tree: ast.Module) -> tuple[ast.expr, ...]:
    """Every `os.kill(<anything>, 0)` call site's flagged signal-argument
    node in `tree`, dotted or bare-imported alike."""
    kill_names = _collect_kill_bindings(tree)
    hits: list[ast.expr] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            hit = _kill_zero_signal_hit(node, kill_names)
            if hit is not None:
                hits.append(hit)
    return tuple(hits)


# frob:enforces CHK-GATE-PLATFORM002
def _platform002_violation(rel_path: str, lineno: int) -> Violation:
    """The PLATFORM002 `Violation` for one `os.kill(<pid>, 0)` call site
    outside `frob.process._pid_liveness` -- WARN tier on arrival (T-3696,
    this module's own docstring)."""
    _log.warning(
        "PLATFORM002: %s:%d os.kill(<pid>, 0) outside the sanctioned liveness probe",
        rel_path,
        lineno,
    )
    return Violation(
        rule="PLATFORM002",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
        message=(
            f"PLATFORM002: {rel_path}:{lineno} calls os.kill(<pid>, 0) "
            f"as a liveness probe -- on win32, CPython's os.kill maps "
            f"signal 0 to signal.CTRL_C_EVENT and delivers it via "
            f"GenerateConsoleCtrlEvent, broadcasting a real Ctrl+C to "
            f"every process on the caller's console (T-3686: a 20-round "
            f"win32 debugging saga was exactly this call self-"
            f"interrupting frob check). Use "
            f"frob.process._pid_liveness.pid_alive / pid_alive_tristate "
            f"instead -- the one sanctioned, console-safe liveness probe "
            f'-- or `frob:waive PLATFORM002 reason="..."` if this is '
            f"genuinely real signal delivery misidentified by this "
            f"scan"
        ),
    )


def _parse001_violation(rel_path: str, reason: str) -> Violation:
    """PARSE001 for a file this gate's own `ast.parse` could not get
    through -- shares the drive-wide convention, never a silent drop."""
    return local_parse001_violation(
        rel_path,
        reason,
        "PLATFORM002 cannot inspect it for a win32-unsafe os.kill call",
    )


# frob:ticket T-3696
# frob:doc \
# docs/modules/gates.md#platform002-oskillpid-0-outside-the-sanctioned-liveness-probe-t\
# -3696
# frob:tests tests/unit/gates/test_win32_kill_signal.py::TestPlatform002.test_zero_signal_kill_is_flagged  # noqa: E501
# frob:tests tests/unit/gates/test_win32_kill_signal.py::TestPlatform002.test_real_signal_kill_is_not_flagged  # noqa: E501
# frob:tests tests/unit/gates/test_win32_kill_signal.py::TestPlatform002.test_sanctioned_module_is_allowlisted  # noqa: E501
# frob:tests tests/unit/gates/test_win32_kill_signal.py::TestPlatform002.test_bare_imported_kill_is_flagged  # noqa: E501
# frob:tests tests/unit/gates/test_win32_kill_signal.py::TestPlatform002.test_unparseable_file_is_parse001_not_silent  # noqa: E501
# frob:tests tests/unit/gates/test_win32_kill_signal.py::TestPlatform002.test_frob_itself_is_clean  # noqa: E501
def win32_kill_signal_gate(root: Path) -> tuple[Violation, ...]:
    """PLATFORM002: every git-tracked `.py` file under `src/frob/**` that
    calls `os.kill(<pid>, 0)` (dotted or bare-imported), unless the file
    is `src/frob/process/_pid_liveness.py` (the one sanctioned
    implementation, `_ALLOWLIST`) -- the win32 Ctrl+C-broadcast footgun
    T-3686 fixed one call site of (module docstring). A file this gate
    cannot read/parse fires PARSE001 instead of silently dropping out of
    the scan, matching WALK001/PORT001's own convention."""
    root = Path(root)
    violations: list[Violation] = []
    scanned_files = tracked_python_files_for_gate(
        root, log_prefix="win32_kill_signal_gate"
    )
    for rel_path in scanned_files:
        if rel_path in _SELF_EXCLUDED_FILES or rel_path in _ALLOWLIST:
            continue
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
            tree = ast.parse(text, filename=rel_path)
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            violations.append(_parse001_violation(rel_path, str(exc)))
            continue
        for hit in _scan_kill_zero_signal(tree):
            violations.append(_platform002_violation(rel_path, hit.lineno))
    _log.warning(
        "win32_kill_signal_gate: scanned %d tracked src/frob/**/*.py file(s), "
        "%d violation(s)",
        len(scanned_files),
        len(violations),
    )
    return tuple(violations)


__all__ = ["win32_kill_signal_gate"]
