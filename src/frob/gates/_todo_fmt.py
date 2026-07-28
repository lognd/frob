"""frob.gates._todo_fmt -- TODO00x (bare/dangling/stale todo directives) and
FMT001 (over-length frob: directive lines) gate families, split out of
`frob.gates.__init__` (T-1077, following T-1072's WAIVE-family precedent).

Kept together because both are diff/comment-scanning gates over the same
`frob.lang`-parsed comment surface, distinct from the ticket-graph-shaped
gates (COV/TICK/SCOPE) and the invariant/decision gates that stayed behind.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_todo_fmt.py's \
# exclusivity-vocabulary hits are source-level design-rationale prose \
# (docstrings and comments describing already-implemented internal \
# behavior, verifiable by reading the code they annotate) rather than a \
# separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim -- module prose \
# split verbatim from the pre-T-1077 gates/__init__.py monolith"

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from frob.gates._fmt_directives import marker_for, read_line_length
from frob.gates._models import Severity, Violation
from frob.gitio import Diff, run_argv
from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.graph.dsl import fold_comment_runs
from frob.logging import get_logger
from frob.tickets import TicketQueue

_log = get_logger(__name__)

_TODO_RE = re.compile(r"\b(TODO|FIXME)\b")


# frob:enforces CHK-GATE-TODO002
def _todo002_edges(snapshot: GraphSnapshot, queue: TicketQueue) -> list[Violation]:
    """TODO002: `frob:todo` edges bound to a non-open (or missing) ticket.

    Distinct failure mode from TODO001 (a bare, wholly untracked comment):
    here the work IS accounted for -- a `frob:todo` directive exists -- but
    the ticket it references is closed or missing, so the reference is
    dangling. Split from a single conflated TODO001 in T-0425 so the two
    modes can be tiered, waived, and reported independently, matching
    frob's own one-id-per-failure-mode convention (WAIVE001/002, COV001-004,
    TEST001-010, DUP001/002, PERF001-004).
    """
    from frob.gates import _OPEN_STATES, _site_from_edge_origin

    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TODO:
            continue
        target = queue.tickets.get(edge.target)
        if target is not None and target.state in _OPEN_STATES:
            continue
        file, line = _site_from_edge_origin(edge.origin)
        _log.debug("TODO002: %s -> %s not open", edge.src, edge.target)
        violations.append(
            Violation(
                rule="TODO002",
                severity=Severity.WARN,
                file=file,
                line=line,
                message=(
                    f"TODO002: frob:todo {edge.target} at {edge.src} is not bound to "
                    f"an open ticket; run: frob ticket new, then rebind"
                ),
            )
        )
    return violations


# frob:ticket T-0783
# frob:waive EXHAUST001 reason="T-1056: leaked Unknown traces to run_argv (already \
# Result-returning, checked via .is_err above) and data.get('project', {}).get(\
# 'version') dict access on a dict tomllib.loads already produced inside the \
# caught try block; no unhandled raise path remains"
def _pyproject_version_at(root: Path, sha: str) -> str | None:
    """The `project.version` string from `pyproject.toml` AS IT READ at
    commit `sha` (`git show <sha>:pyproject.toml`), or `None` if the
    commit, the file at that commit, or its toml is unreadable/malformed --
    the same degrade-to-None posture `_current_version` already has for the
    working tree, reused here for a historical snapshot instead (T-0783's
    "version at the time the deferral comment landed")."""
    spawned = run_argv(("git", "-C", str(root), "show", f"{sha}:pyproject.toml"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.debug("TODO003: could not read pyproject.toml at %s", sha)
        return None
    try:
        data = tomllib.loads(spawned.danger_ok.stdout)
        version = data.get("project", {}).get("version")
    except tomllib.TOMLDecodeError:
        _log.debug("TODO003: unparseable pyproject.toml at %s", sha)
        return None
    return version if isinstance(version, str) else None


# frob:ticket T-0783
# frob:tests \
# tests/test_gates.py::TestCoverageGate.test_todo003_fires_after_version_bump_since_def\
# erral_landed  # noqa: E501
# frob:tests \
# tests/test_gates.py::TestCoverageGate.test_todo003_silent_when_no_version_bump_since_\
# deferral  # noqa: E501
# frob:tests \
# tests/test_gates.py::TestCoverageGate.test_todo003_silent_when_ticket_closes  # \
# noqa: E501
# frob:enforces CHK-GATE-TODO003
def _todo003_long_deferred(
    root: Path, snapshot: GraphSnapshot, queue: TicketQueue
) -> list[Violation]:
    """TODO003 (Audit M2 gate-direction, T-0783): a `frob:todo` edge bound
    to a STILL-OPEN ticket whose deferral comment landed under an OLDER
    project version than the one on disk now -- at least one `REL001`
    version bump has shipped since the deferral was written down, and
    nobody re-litigated it (the exact T-0476 shape the ticket cites: "open
    since the lease layer shipped"). Repo-wide, not diff-scoped, mirroring
    `_todo002_edges` -- a deferral does not stop being stale just because
    today's diff does not touch its line.

    "The comment landed" is read from `git blame` on the directive's own
    line (`_blame_shas`), not a new persisted state file -- this repo
    already has one durable per-line landing-commit oracle (git history
    itself), and deriving from it keeps this gate purely a function of
    `(snapshot, queue, git log)`, with no new mutable `.frob/` artifact to
    keep in sync or race against a concurrent `frob check` (T-0783 chose
    this over stamping a first-seen-version file precisely to avoid that
    class of bug). A line git cannot blame (uncommitted, blame failure) or
    a `pyproject.toml` that cannot be read at the landing commit degrades
    to "not evaluable, no finding" -- never a false fire.

    Scope note (T-0783 Done report, disclosed not silently dropped): only
    the structured `frob:todo T-####` directive is covered. The ticket
    body also mentions "that ticket's job shape" -- an informal prose
    deferral comment with no structured directive at all -- which this
    pass does not attempt to detect (no reliable structural signal exists
    for free-text deferral prose the way a dedicated edge kind already
    exists for the structured directive form); left as a follow-on gap.
    """
    from frob.gates import _OPEN_STATES, _current_version

    current_version = _current_version(root)
    if current_version is None:
        _log.debug("TODO003: no readable pyproject.toml version, skipping")
        return []
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TODO:
            continue
        target = queue.tickets.get(edge.target)
        if target is None or target.state not in _OPEN_STATES:
            continue
        violation = _todo003_violation_for_edge(root, edge, current_version)
        if violation is not None:
            violations.append(violation)
    return violations


# frob:ticket T-0976
def _todo003_violation_for_edge(
    root: Path, edge: Edge, current_version: str
) -> Violation | None:
    """One `frob:todo` `edge`'s TODO003 contribution, or `None` if it does
    not fire: fails closed (no finding) whenever the directive's line
    cannot be blamed to a real commit or that commit's `pyproject.toml`
    version cannot be read, and is otherwise silent when the landing
    version already matches `current_version` -- the per-edge half of
    `_todo003_long_deferred`, split from its queue-filtering loop."""
    from frob.gates import _UNCOMMITTED_SHA, _blame_shas, _site_from_edge_origin

    file, line = _site_from_edge_origin(edge.origin)
    shas = _blame_shas(root, file, line, line)
    if shas.is_nothing:
        return None
    real_shas = shas.danger_some - {_UNCOMMITTED_SHA}
    if not real_shas:
        return None
    landed_version: str | None = None
    for sha in real_shas:
        landed_version = _pyproject_version_at(root, sha)
        if landed_version is not None:
            break
    if landed_version is None or landed_version == current_version:
        return None
    _log.debug(
        "TODO003: %s -> %s deferred since v%s, now v%s",
        edge.src,
        edge.target,
        landed_version,
        current_version,
    )
    return Violation(
        rule="TODO003",
        severity=Severity.WARN,
        file=file,
        line=line,
        message=(
            f"TODO003: frob:todo {edge.target} at {edge.src} was deferred "
            f"under v{landed_version} and {edge.target} is still open at "
            f"v{current_version} -- at least one release has shipped since; "
            f"re-litigate the deferral (close {edge.target}, or confirm it "
            "is still the right call) rather than letting it fossilize"
        ),
    )


def _todo001_bare(snapshot: GraphSnapshot, diff: Diff) -> list[Violation]:
    """TODO001: bare todo/fixme comments in diff-touched, freshly parsed files.

    Distinct failure mode from TODO002 (a dangling `frob:todo` reference):
    here the work is not accounted for at all -- no ticket, no directive --
    so the fix is "file a ticket and convert to `frob:todo T-####`" rather
    than "fix the dangling reference". See `_todo002_edges`.
    """
    from frob.gates import _touched_files
    from frob.lang import parse_file  # local import: keep gates' top import list lean

    root = Path(snapshot.root)
    touched = sorted(_touched_files(diff))
    violations: list[Violation] = []
    for file in touched:
        parsed = parse_file(root / file)
        if parsed.is_err:
            continue
        for comment in parsed.danger_ok.comments:
            violations.extend(_todo001_bare_comment(file, comment))
    return violations


# frob:enforces CHK-GATE-TODO001
def _todo001_bare_comment(file: str, comment) -> list[Violation]:  # noqa: ANN001
    """Every bare (not `frob:`-prefixed) todo/fixme line inside one comment,
    as TODO001 `Violation`s."""
    violations: list[Violation] = []
    for offset, line_text in enumerate(comment.text.splitlines() or [comment.text]):
        if line_text.strip().startswith("frob:"):
            continue
        if _TODO_RE.search(line_text) is None:
            continue
        lineno = comment.span[0] + offset
        _log.debug("TODO001: bare TODO/FIXME at %s:%d", file, lineno)
        violations.append(
            Violation(
                rule="TODO001",
                severity=Severity.WARN,
                file=file,
                line=lineno,
                message=(
                    f"TODO001: bare TODO/FIXME at {file}:{lineno}; bind it: "
                    f"frob:todo <ticket-id>"
                ),
            )
        )
    return violations


def _todo001(
    snapshot: GraphSnapshot, queue: TicketQueue, diff: Diff
) -> tuple[Violation, ...]:
    """TODO001 + TODO002: a bare todo/fixme comment in a diff-touched file
    (parsed fresh via `frob.lang`, cheap since scoped to the diff, not the
    whole tree), and a `frob:todo` bound to a non-open ticket -- two distinct
    failure modes, each raised under its own rule id (see `_todo001_bare`
    and `_todo002_edges`)."""
    return (
        *_todo002_edges(snapshot, queue),
        *_todo001_bare(snapshot, diff),
    )


# frob:ticket T-0851
def _fmt001_touched_lines(diff: Diff, file: str) -> set[int]:
    """1-indexed line numbers `diff` touches in `file`, unioned across every
    hunk (T-0851, mirrors `_todo001_bare`'s diff-scoping posture -- FMT001
    only fires on lines an agent actually touched this diff, never on
    pre-existing non-canonical lines elsewhere in the file)."""
    lines: set[int] = set()
    for hunk in diff.hunks:
        if hunk.file != file:
            continue
        start, end = hunk.span
        lines.update(range(start, end + 1))
    return lines


# frob:doc docs/modules/gates.md#fmt001-t-0851
# frob:tests tests/test_gates.py::TestFmt001Gate.test_directive_run_over_limit_flagged
# frob:tests tests/test_gates.py::TestFmt001Gate.test_ordinary_long_comment_not_flagged
# frob:tests tests/test_gates.py::TestFmt001Gate.test_long_code_line_not_flagged
# frob:tests tests/test_gates.py::TestFmt001Gate.test_untouched_line_not_flagged
# frob:tests tests/test_gates.py::TestFmt001Gate.test_short_directive_not_flagged
def _fmt001_file(
    root: Path, file: str, limit: int, touched: set[int]
) -> list[Violation]:
    """FMT001 findings for one diff-touched `file`: every physical line of a
    `frob:` directive comment run that both (a) `diff` actually touches and
    (b) exceeds `limit` columns (T-0851, the deferred half of T-0441 --
    `frob check` previously had no gate for this at all, only `frob fmt
    --check` standalone).

    Reuses `frob.gates._fmt_directives.marker_for` (which language/suffix
    this scans) and `frob.graph.dsl.fold_comment_runs` (T-0286's own
    continuation-run folding, also what `canonicalize_text` folds through)
    rather than re-deriving either -- this function's only new logic is the
    length + diff-touch check on each run's physical lines. An ordinary
    (non-`frob:`) long comment or a long code line never enters a folded
    `frob:`-prefixed run, so neither is flagged -- only a directive run is
    in scope, matching the ticket's remediation ("run `frob fmt`", which
    only rewrites directive lines)."""
    if not touched:
        return []
    marker = marker_for(file)
    if marker is None:
        return []
    path = root / file
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        _log.debug("FMT001: skipping unreadable %s (%s)", path, exc)
        return []

    lines = text.split("\n")
    runs = fold_comment_runs(_fmt001_marker_entries(lines, marker))
    return _fmt001_violations_for_runs(file, lines, runs, limit, touched)


# frob:ticket T-0976
def _fmt001_marker_entries(
    lines: list[str], marker: str
) -> list[tuple[int, str, str, int]]:
    """Every line in `lines` that starts (after leading whitespace) with
    comment `marker`, as `fold_comment_runs`' expected `(index, content,
    "", 0)` entry tuple -- the marker-line-collection half of
    `_fmt001_file`."""
    entries: list[tuple[int, str, str, int]] = []
    for i, raw in enumerate(lines):
        stripped = raw.lstrip(" \t")
        if not stripped.startswith(marker):
            continue
        content = stripped[len(marker) :]
        if content.startswith(" "):
            content = content[1:]
        entries.append((i, content, "", 0))
    return entries


# frob:ticket T-0976
def _fmt001_violations_for_runs(
    file: str,
    lines: list[str],
    runs: list,
    limit: int,
    touched: set[int],
) -> list[Violation]:
    """FMT001 findings for every `frob:`-prefixed folded comment `run`
    whose diff-touched physical line exceeds `limit` columns -- the run-
    scan half of `_fmt001_file`, split from the marker-collection half."""
    violations: list[Violation] = []
    for logical_text, start_idx, _src, count in runs:
        if not logical_text.strip().startswith("frob:"):
            continue
        for offset in range(count):
            lineno = start_idx + offset + 1
            if lineno not in touched:
                continue
            raw_line = lines[start_idx + offset].rstrip("\r")
            if len(raw_line) <= limit:
                continue
            _log.debug("FMT001: %s:%d over %d cols", file, lineno, limit)
            violations.append(
                Violation(
                    rule="FMT001",
                    severity=Severity.WARN,
                    file=file,
                    line=lineno,
                    message=(
                        f"FMT001: {file}:{lineno} frob: directive line over "
                        f"{limit} cols; run `frob fmt {file}` to wrap it to "
                        f"canonical form"
                    ),
                )
            )
    return violations


# frob:doc docs/modules/gates.md#fmt001-t-0851
# frob:enforces CHK-GATE-FMT001
# frob:tests tests/test_gates.py::TestFmt001Gate.test_directive_run_over_limit_flagged
def fmt_gate(root: Path, diff: Diff) -> tuple[Violation, ...]:
    """FMT001 (warn): a diff-touched `frob:` directive comment line over the
    project's configured line length -- see `_fmt001_file`. Additive only:
    never suppresses or rewrites the underlying ruff/lint finding on the
    same line, just names `frob fmt` as the auto-fix."""
    from frob.gates import _touched_files

    limit = read_line_length(root)
    violations: list[Violation] = []
    for file in sorted(_touched_files(diff)):
        touched = _fmt001_touched_lines(diff, file)
        violations.extend(_fmt001_file(root, file, limit, touched))
    return tuple(violations)
