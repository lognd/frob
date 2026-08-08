"""frob.gates._suppress -- SUPPRESS001, evidence-driven suppression-dialect
mismatch detection (T-1340, phase 1 of T-1339's suppression-dialect
compliance epic).

THE PROBLEM (T-1339): a source line can carry one type-checker's
suppression comment (mypy's `# type: ignore[name-defined]`) while a
DIFFERENT checker (`ty`) still errors on that exact line, because `ty`
does not honour mypy's suppression dialect at all -- and vice versa. That
is a dialect-portability gap, not a real type defect: the motivating
incident (two ty errors hand-fixed on main, tests/test_fuzz.py:159 and
tests/test_tickets_collision.py:826) turned out to be exactly this, not a
genuine type bug.

THE GOAL IS PORTABILITY, NOT CONFORMANCE (T-1339's DESIGN AMENDMENT,
2026-07-31, binding, supersedes this ticket's own acceptance criterion
[2] as originally written): this repo gates on `ty`, but a downstream
consumer type-checking frob's source with `mypy` must not eat spurious
errors either. So every suppressed line should ideally carry EVERY
supported dialect's suppression, including for a checker THIS repo never
runs. `SuppressionDialect.available` therefore means "an oracle exists in
THIS process to supply that dialect's diagnostics" (a capability limit),
never "is this tool configured for this project" -- gating a direction on
project configuration was the earlier (superseded) design.

DETECTION IS EVIDENCE-DRIVEN, NOT A STATIC CODE-MAPPING TABLE: mypy's and
ty's rule codes are not 1:1 (`name-defined` vs `unresolved-reference`,
`attr-defined` vs `unresolved-attribute`), so a static mapping table would
be lossy -- explicitly rejected by both T-1339 and this ticket. Instead,
SUPPRESS001 fires only where line L carries dialect A's suppression AND a
DIFFERENT, available-oracle dialect B reports an diagnostic at L that is
not ALSO covered by dialect B's own suppression on that same line. Each
dialect's own diagnostic supplies its own rule code -- no cross-dialect
code lookup is ever needed.

`mypy` is a DEV DEPENDENCY here used PURELY as a diagnostic oracle
(T-1339's user-sanctioned mechanism for making the ty->mypy direction
possible at all): `frob check` never gates on mypy's exit code or
diagnostics directly, only this gate's own correlation of them against
`ty`'s. `--warn-unused-ignores` is deliberately never passed to the mypy
oracle invocation below (T-1339's watch item) -- this gate's own
evidence-driven design does not need it, and turning it on would produce
unrelated unused-ignore noise from the 17 pre-existing legacy mypy-only
ignores that predate mypy running here at all.

Detection only. The Tier-A auto-fix that WRITES the paired suppression is
a separate, sibling ticket (T-1341) -- this module never edits a source
file.

WATCH ITEM (T-1635): `_mypy_diagnostics` pins `--cache-dir` INSIDE its
caller-supplied `root` rather than letting mypy fall back to its default
`.mypy_cache` (resolved against the process's CWD, not `root`). Under
`pytest-xdist`, every worker/test invoking this oracle shares the SAME
CWD (the repo root), so a default cache dir is a real cross-process
shared resource: concurrent invocations race on the same incremental-
cache files. Reproduced directly: a full-suite `-n auto` run
intermittently returned zero mypy diagnostics for a file this function's
own caller had just written and expected exactly one diagnostic from --
a torn/stale incremental-cache read racing another worker's concurrent
mypy invocation, not a real absence of the error. Pinning the cache
under `root` (always a fresh, test-owned `tmp_path` in tests; the same
default location as before in real `frob check` runs, where `cwd ==
root` already) removes the shared resource entirely.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from pydantic import BaseModel

from frob.gates._models import Severity, Violation
from frob.graph import GraphSnapshot
from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run

_log = get_logger(__name__)

# Comment syntax per dialect, as a regex naming an optional `code` group.
# A dialect with no `code` group match (a bare suppression -- e.g. a
# type-ignore comment with no bracketed code) is treated as covering
# every rule code on that line -- the exact semantics each of these
# three tools already gives a bare suppression comment.
_TY_PATTERN = r"#\s*ty:\s*ignore(?:\[(?P<code>[\w-]+)\])?"
_MYPY_PATTERN = r"#\s*type:\s*ignore(?:\[(?P<code>[\w, -]+)\])?"
_NOQA_PATTERN = r"#\s*noqa(?::\s*(?P<code>[\w, ]+))?"

# mypy's default text-output diagnostic line shape:
#   path/to/file.py:10: error: Name "x" is not defined  [name-defined]
# (optional `:col` between line and "error:", which this repo's oracle
# invocation does not request via --show-column-numbers, but the pattern
# tolerates it either way since mypy's exact column behaviour is not a
# guarantee this gate depends on).
_MYPY_DIAG_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?:\d+:)?\s*error:\s*.*?"
    r"\[(?P<code>[\w-]+)\]\s*$"
)


# frob:doc docs/modules/gates.md#public-api
# frob:tests \
# tests/test_gates_suppress.py::TestSuppressionDialects.test_registers_ty_mypy_ruff
class SuppressionDialect(BaseModel):
    """One suppression-comment dialect frob's Python source may carry:
    `name` (the dialect id used in SUPPRESS001 messages), `pattern` (a
    regex over a single source line, naming an optional `code` group),
    and `available` -- whether an oracle exists in THIS process to
    supply that dialect's real diagnostics right now (a capability
    limit: `shutil.which` finding the tool on `PATH`), never whether the
    tool happens to be configured for this specific project (T-1339's
    DESIGN AMENDMENT -- the goal is portability to every dialect a
    downstream consumer might run, not conformance to whichever checker
    this repo gates on)."""

    model_config = {}

    name: str
    pattern: str
    available: bool


# frob:doc docs/modules/gates.md#public-api
# frob:tests \
# tests/test_gates_suppress.py::TestSuppressionDialects.test_available_reflects_path_no\
# t_project_config
def suppression_dialects() -> dict[str, SuppressionDialect]:
    """The registry of every Python `SuppressionDialect` SUPPRESS001
    knows about (`ty`, `mypy`, `ruff`/noqa), each stamped with whether an
    oracle is available in THIS process (`shutil.which`) -- callers
    correlate a direction only when its dialect's `available` is `True`,
    per `suppress001_gate`'s own capability-limit posture."""
    return {
        "ty": SuppressionDialect(
            name="ty",
            pattern=_TY_PATTERN,
            available=shutil.which("ty") is not None,
        ),
        "mypy": SuppressionDialect(
            name="mypy",
            pattern=_MYPY_PATTERN,
            available=shutil.which("mypy") is not None,
        ),
        "ruff": SuppressionDialect(
            name="ruff",
            pattern=_NOQA_PATTERN,
            available=shutil.which("ruff") is not None,
        ),
    }


def _line_suppressions(
    line: str, dialects: dict[str, SuppressionDialect]
) -> dict[str, set[str] | None]:
    """Every dialect's suppression present on `line`: `dialect_name ->
    codes` where `None` means a bare suppression (covers every rule code
    on the line, matching each tool's own bare-ignore semantics) and a
    `set[str]` means only those specific codes are covered."""
    found: dict[str, set[str] | None] = {}
    for name, dialect in dialects.items():
        match = re.search(dialect.pattern, line)
        if match is None:
            continue
        code_group = match.groupdict().get("code")
        if code_group is None:
            found[name] = None
        else:
            found[name] = {c.strip() for c in code_group.split(",") if c.strip()}
    return found


def _relativize(file: str | None, root: Path) -> str | None:
    """`file` (as reported by a checker, absolute or already root-relative)
    as a root-relative posix path, or `None` if it resolves outside
    `root` entirely (a diagnostic this gate cannot site against any
    tracked source line)."""
    if not file:
        return None
    path = Path(file)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    except Exception:
        # `.resolve()` can fail on a genuinely broken cwd/permission
        # (EXHAUST001, T-1371) -- an unresolvable root is exactly the
        # "cannot site this diagnostic" case this function already
        # documents for the ValueError branch.
        return None


def _ty_diagnostics(root: Path) -> list[tuple[str, int, str]]:
    """`(relfile, line, code)` for every `ty` diagnostic that carries both
    a line and a rule code -- reuses `frob.check._python._run_ty`'s
    existing hermetic invocation (T-0996) rather than re-deriving ty's
    own extra-search-path/venv resolution here."""
    from frob.check._python import _run_ty

    result = _run_ty(root)
    out: list[tuple[str, int, str]] = []
    for diag in result.diagnostics:
        rel = _relativize(diag.file, root)
        if rel is None or diag.line is None or not diag.code:
            continue
        out.append((rel, diag.line, diag.code))
    return out


def _parse_mypy(stdout: str) -> list[tuple[str, int, str]]:
    """`(file, line, code)` for every `error:` line in mypy's default text
    output that carries a bracketed rule code -- a code-less error (a
    handful of mypy's internal/config errors) is not actionable evidence
    for a specific dialect code and is skipped, mirroring `ty`'s own
    diagnostics being filtered the same way in `_ty_diagnostics`."""
    out: list[tuple[str, int, str]] = []
    for raw in stdout.splitlines():
        match = _MYPY_DIAG_RE.match(raw.strip())
        if match is None:
            continue
        out.append((match.group("file"), int(match.group("line")), match.group("code")))
    return out


def _mypy_diagnostics(root: Path) -> list[tuple[str, int, str]]:
    """`(relfile, line, code)` for every mypy diagnostic against `root`,
    via a direct oracle invocation (T-1339: mypy is a dev dependency used
    PURELY to supply ground-truth diagnostics here, never a gate --
    `--warn-unused-ignores` is deliberately never passed, per this
    module's docstring watch item). An unavailable/disabled `mypy`
    yields an empty list rather than raising -- `suppress001_gate` only
    calls this when `suppression_dialects()["mypy"].available` is
    `True`, but this stays defensive against a race between that check
    and the actual invocation. T-1635: `--cache-dir` pinned INSIDE
    `root` -- see the module docstring's T-1635 watch item."""
    try:
        run_result = guarded_subprocess_run(
            [
                "mypy",
                "--hide-error-context",
                "--no-color-output",
                "--no-error-summary",
                "--cache-dir",
                str(root / ".mypy_cache"),  # T-1635: never the ambient CWD
                # mypy skips type-checking an untyped `def`'s BODY by
                # default (only its signature) -- this repo's own source
                # is annotated throughout, but the oracle must not go
                # silently blind on any function that is not, or the
                # ty->mypy direction would under-report by construction.
                "--check-untyped-defs",
                str(root),
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []
    except Exception:
        # "An unavailable/disabled mypy yields an empty list rather than
        # raising" (this function's own docstring) covers any invocation
        # surprise, not just `FileNotFoundError` (EXHAUST001, T-1371).
        return []
    if run_result.is_err:
        return []
    proc = run_result.danger_ok
    out: list[tuple[str, int, str]] = []
    try:
        for file, line, code in _parse_mypy(proc.stdout):
            rel = _relativize(file, root)
            if rel is None:
                continue
            out.append((rel, line, code))
    except TypeError:
        # A surprising mypy output shape (this oracle invocation's own
        # docstring already treats "unavailable" as an empty list, not a
        # raise) is the same "cannot use this oracle run" outcome, not a
        # crash of the whole suppress001 comparison (EXHAUST001/EXHAUST002,
        # T-1371).
        return []
    except ValueError:
        return []
    return out


def _suppress001_violation(
    *, file: str, line: int, other_dialect: str, reporting_dialect: str, code: str
) -> Violation:
    """The single SUPPRESS001 finding for one evidence-driven mismatch:
    `file:line` already carries `other_dialect`'s suppression, but
    `reporting_dialect` reports an unsuppressed `code` there -- naming
    both dialects and the reporting checker's own rule code, exactly as
    T-1340's acceptance [0] requires."""
    _log.error(
        "SUPPRESS001: %s:%d carries %s suppression but %s reports unsuppressed %s here",
        file,
        line,
        other_dialect,
        reporting_dialect,
        code,
    )
    return Violation(
        rule="SUPPRESS001",
        severity=Severity.ERROR,
        file=file,
        line=line,
        message=(
            f"SUPPRESS001: {file}:{line} carries a {other_dialect} "
            f"suppression comment but {reporting_dialect} reports an "
            f"unsuppressed {code!r} diagnostic on this line -- a "
            f"downstream consumer running {reporting_dialect} would eat "
            f"a spurious error here; add a matching {reporting_dialect} "
            f"suppression for {code!r} (detection only -- T-1341 is the "
            f"paired-suppression auto-fix)"
        ),
    )


def _suppress001_correlate(
    root: Path,
    dialects: dict[str, SuppressionDialect],
    oracle_diagnostics: dict[str, list[tuple[str, int, str]]],
) -> tuple[Violation, ...]:
    """The evidence-driven correlation itself: for every diagnostic a
    `oracle_diagnostics`-listed (i.e. available-oracle) `reporting`
    dialect reports at `file:line`, fire SUPPRESS001 iff that line is NOT
    already suppressed for `reporting`'s own dialect/code AND carries at
    least one OTHER dialect's suppression comment. This is symmetric by
    construction: whichever dialects have an available oracle each get a
    turn as `reporting`, so mypy->ty and ty->mypy both fire from the same
    loop with no direction hard-coded."""
    violations: list[Violation] = []
    line_cache: dict[str, list[str]] = {}
    for reporting, diagnostics in sorted(oracle_diagnostics.items()):
        for file, line, code in diagnostics:
            lines = line_cache.get(file)
            if lines is None:
                try:
                    lines = (root / file).read_text(encoding="utf-8").splitlines()
                except OSError as exc:
                    _log.warning(
                        "SUPPRESS001: could not read %s for %s diagnostic "
                        "correlation: %s",
                        file,
                        reporting,
                        exc,
                    )
                    lines = []
                line_cache[file] = lines
            if not (1 <= line <= len(lines)):
                continue
            present = _line_suppressions(lines[line - 1], dialects)
            if reporting in present:
                own_codes = present[reporting]
                if own_codes is None or code in own_codes:
                    # Already suppressed for its OWN dialect on this line
                    # (bare, or a matching code) -- acceptance [1]: nothing
                    # to report, this line is exactly as portable as it
                    # claims to be for `reporting`.
                    continue
            others = [name for name in present if name != reporting]
            if not others:
                continue
            violations.append(
                _suppress001_violation(
                    file=file,
                    line=line,
                    other_dialect=others[0],
                    reporting_dialect=reporting,
                    code=code,
                )
            )
    return tuple(violations)


# frob:doc docs/modules/gates.md#public-api
# frob:tests \
# tests/test_gates_suppress.py::TestSuppress001Gate.test_mypy_suppressed_ty_unsuppresse\
# d_fires
# frob:tests \
# tests/test_gates_suppress.py::TestSuppress001Gate.test_ty_suppressed_mypy_unsuppresse\
# d_fires
# frob:tests \
# tests/test_gates_suppress.py::TestSuppress001Gate.test_both_dialects_present_reports_\
# nothing
# frob:tests \
# tests/test_gates_suppress.py::TestSuppress001Gate.test_no_available_oracle_reports_no\
# thing
# frob:tests \
# tests/test_gates_suppress.py::TestSuppress001RepoWideLock.test_repo_is_currently_clean
# frob:ticket T-1342
# frob:enforces CHK-GATE-SUPPRESS001
def suppress001_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """SUPPRESS001: every evidence-driven suppression-dialect mismatch
    against `root` -- correlates whichever of `ty`/`mypy`'s diagnostics
    have an available oracle in THIS process against the suppression
    comments already present on the reporting line (`suppression_
    dialects`/`_suppress001_correlate`). `snapshot` is accepted (matching
    every other root-scoped gate's `(root, snapshot)` call shape in
    `frob.gates.__init__`) but not read directly -- this gate's own
    source of truth is the live oracle invocations, not the parsed
    symbol graph."""
    del snapshot
    dialects = suppression_dialects()
    oracle_diagnostics: dict[str, list[tuple[str, int, str]]] = {}
    if dialects["ty"].available:
        oracle_diagnostics["ty"] = _ty_diagnostics(root)
    if dialects["mypy"].available:
        oracle_diagnostics["mypy"] = _mypy_diagnostics(root)
    if not oracle_diagnostics:
        _log.info("SUPPRESS001: no available oracle for any dialect -- skipping")
        return ()
    return _suppress001_correlate(root, dialects, oracle_diagnostics)
