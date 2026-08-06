"""frob.gates._fix_engine_text -- Tier-A diagnostic-line auto-fix handlers.

Split out of `frob.gates._fix_engine` (T-1646, LARGE001 residue burndown)
along the seam that module's own handler set already carried: the
handlers kept in `_fix_engine` (DOC007/DOC002/INV006-carry/TICK002) are
GRAPH-driven -- they resolve a rewrite target by walking `GraphSnapshot`/
`TicketQueue` state. Every handler in THIS module instead resolves its
rewrite by acting on the ONE specific source line a lint-style `Violation`
already names -- FMT001 (over-long `frob:` directive comment), SUPPRESS001
(missing paired dialect suppression), and E501 (a merge-introduced
over-length line) -- using `tokenize`/`fnmatch`/`tomllib` to find a line's
own trailing-comment boundary and this repo's ruff per-file-ignore config.
This is a narrower, LINE-scoped surface than the derived-artifact-sync
handler family in `frob.gates._fix_engine_sync` (REG010/REL002/SYS104/
SYS100/COV002/WAIVE004), which resyncs a whole generated artifact rather
than rewriting one diagnosed line. `TIER_A_HANDLERS` in `_fix_engine`
imports every public `fix_*` symbol from both text/sync modules and
dispatches through the same uniform `(root, snapshot, queue, ticket_id)
-> list[FixApplied]` call shape every handler uses -- this split changes
no behavior, only which file a given handler's body lives in.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool carried forward at the \
# T-1646 LARGE001 split: this module's exclusivity-vocabulary hits are the same \
# source-level design-rationale prose (docstrings/comments describing already- \
# implemented internal behavior, verifiable by reading the code they annotate) that \
# src/frob/gates/_fix_engine.py's own module-level INV006 waiver already covers -- \
# moved verbatim with the code, not a new claim"

from __future__ import annotations

import fnmatch
import io
import json
import logging
import re
import tokenize
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from frob.gates._fix_engine_shared import FixApplied, _write_text
from frob.graph import GraphSnapshot
from frob.process._guard import guarded_subprocess_run

if TYPE_CHECKING:
    from frob.gates._suppress import SuppressionDialect

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FMT001 (T-1261): a diff-touched `frob:` directive comment line over the
# project's configured line length -- `frob fmt` names itself as its own
# remedy.
#
# T-1391: `format_paths` being content-preserving everywhere it does NOT
# rewrite (a line already canonical anywhere else in the tree is left
# byte-for-byte alone by construction) does not make a whole-tree write
# SAFE from a land-scope-discipline standpoint -- a rewrite of a file
# outside a ticket's declared scope is still an out-of-scope WRITE, and
# land's own guards then reject the land that produced it (measured for
# real: `frob:waive` reason comments in an unrelated file mechanically
# rewritten by lands that never touched it, forcing one agent to widen
# its own ticket's scope record just to absorb the collateral edit).
# `fix_fmt001_directive_wrap`'s `only_paths` keyword restricts the
# rewrite to a caller-supplied set of `root`-relative paths instead of
# walking the whole tree; `only_paths=None` (the default) preserves the
# original whole-tree behaviour verbatim -- what a standalone `frob
# check --fix` still gets, and every existing caller until it opts in.
# This mirrors `fix_waive004_stale_waiver`'s `gates`/`ticket` keyword-
# only params below: a default-preserves-prior-behaviour scoping lever,
# testable directly with no change needed at any `TIER_A_HANDLERS`/
# `apply_tier_a_fixes` call site. Wiring a real caller (`frob ticket
# land`'s pre-land absorption step, `src/frob/app/ticket_runner/
# _land_cmd.py`, a different module) to actually pass its ticket's
# touched-file set through `only_paths` is tracked as a follow-up,
# outside this file's own scope.
# ---------------------------------------------------------------------------


def _fmt001_scoped_fixes(
    root: Path, limit: int, only_paths: frozenset[str]
) -> list[FixApplied]:
    """`fix_fmt001_directive_wrap`'s `only_paths` branch: format each
    named path individually (`format_paths` already accepts a single
    file as its `root` argument) instead of walking the whole tree. A
    named path that no longer exists (deleted since the caller's
    touched-set was computed) or is a directory is silently skipped,
    never an error -- the same no-guess Tier-A contract every other
    handler here follows. Reports `rel` (relative to the REAL repo
    `root`) rather than `format_paths`'s own per-call `change.path`,
    which would otherwise read as "." when called against a single
    file."""
    from frob.gates._fmt_directives import format_paths

    applied: list[FixApplied] = []
    for rel in sorted(only_paths):
        path = root / rel
        if not path.is_file():
            continue
        report = format_paths(path, check_only=False, limit=limit)
        applied.extend(
            FixApplied(
                rule="FMT001",
                file=rel,
                line=0,
                detail=f"{rel}: frob: directive comment(s) rewrapped to canonical form",  # noqa: E501
            )
            for _change in report.changes
        )
    return applied


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
def fix_fmt001_directive_wrap(
    root: Path,
    snapshot: GraphSnapshot,
    *,
    only_paths: frozenset[str] | None = None,
) -> list[FixApplied]:
    """Tier-A fix (T-1261): FMT001 already names its own remedy verbatim
    (`run frob fmt <file>`) -- `format_paths` (`frob.gates._fmt_
    directives`, T-0441) is already idempotent, so calling it in write
    mode IS the fix; no new rewrite logic lives here. `only_paths`, when
    given, restricts the rewrite to exactly that set of `root`-relative
    paths (see `_fmt001_scoped_fixes`, and this section's own T-1391
    module comment above for the land-scope-discipline rationale);
    `None` (the default) preserves the original whole-tree behaviour.
    `snapshot` is accepted for signature uniformity with its sibling
    Tier-A handlers; `format_paths` needs no graph state."""
    from frob.gates._fmt_directives import format_paths, read_line_length

    del snapshot  # signature uniformity only, format_paths needs no graph state
    limit = read_line_length(root)
    if only_paths is not None:
        return _fmt001_scoped_fixes(root, limit, only_paths)
    report = format_paths(root, check_only=False, limit=limit)
    return [
        FixApplied(
            rule="FMT001",
            file=change.path,
            line=0,
            detail=f"{change.path}: frob: directive comment(s) rewrapped to canonical form",  # noqa: E501
        )
        for change in report.changes
    ]


# ---------------------------------------------------------------------------
# SUPPRESS001 (T-1341, phase 2 of T-1339): write the reporting checker's
# own paired suppression, in this repo's observed canonical order, onto
# an evidence-driven dialect-mismatch line -- never a new judgment call,
# only the ONE rewrite `suppress001_gate` (`frob.gates._suppress`) already
# proves is correct: the reporting dialect's own rule code, verbatim.
# ---------------------------------------------------------------------------

#: This repo's own observed convention across every pre-existing dual-
#: dialect suppression line (confirmed by grep against the mypy-then-ty
#: paired-comment occurrences in src/tests at T-1341 authoring time):
#: mypy's ignore comment first, noqa second, ty's ignore comment last. A
#: line only ever carries the subset of these three it actually needs --
#: this order is the SLOT order, not a requirement that all three be
#: present.
_CANONICAL_DIALECT_ORDER = ("mypy", "ruff", "ty")

#: `suppress001_gate`'s own `Violation.message` shape (`_suppress001_
#: violation` in `frob.gates._suppress`): "... carries a {other_dialect}
#: suppression comment but {reporting_dialect} reports an unsuppressed
#: {code!r} diagnostic ...". Parsed back out rather than adding a
#: structured field to `Violation` just for this handler -- the same
#: precedent `_WAIVE004_TARGET_RULE_RE` above already sets for this
#: module.
_SUPPRESS001_MESSAGE_RE = re.compile(
    r"carries a \S+ suppression comment but (?P<reporting>\S+) reports an "
    r"unsuppressed (?P<code>'[^']*'|\"[^\"]*\") diagnostic"
)

#: A line carrying a `frob:` directive comment anywhere in its trailing
#: comment is `frob fmt`'s (FMT001's, `fix_fmt001_directive_wrap` above)
#: territory exclusively, never this handler's: FMT001 already prefers
#: backslash-continuation wrapping for an over-long directive, and its own
#: `canonicalize_text` already treats an existing trailing noqa pragma
#: (T-0985's own escape hatch) as deliberate and leaves it alone -- this
#: handler must never manufacture a competing suppression on a line
#: FMT001 also claims, or the two could double-fix or oscillate across
#: repeated `--fix` runs. Skipping any line matching this outright
#: (rather than trying to detect a genuine overlap) is the explicit
#: precedence this handler commits to: SUPPRESS001 never touches a
#: `frob:`-directive-bearing line, full stop.
_FROB_DIRECTIVE_MARKER_RE = re.compile(r"frob:")


def _parse_suppress001_message(message: str) -> tuple[str, str] | None:
    """The `(reporting_dialect, code)` pair a `suppress001_gate` finding's
    own message names, or `None` if the message does not match the
    expected shape (defensive; should not happen against this repo's own
    `_suppress001_violation`). The matched `code` group is always a
    Python `repr()` of a plain rule-code string (`_suppress001_violation`
    only ever formats `{code!r}` where `code` is a checker-reported rule
    id -- word characters and hyphens, never a quote character itself),
    so the surrounding quote characters are stripped directly rather than
    routed through `ast.literal_eval`/`eval` (an unnecessary opaque
    runtime-eval capability, per OPAQUE001, for input this simple and
    already regex-constrained to a quoted run with no embedded quote)."""
    match = _SUPPRESS001_MESSAGE_RE.search(message)
    if match is None:
        return None
    quoted = match.group("code")
    code = quoted[1:-1]
    return match.group("reporting"), code


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to \
# tokenize.generate_tokens/io.StringIO, stdlib calls the resolver cannot statically \
# bound past the except (TokenError, IndentationError, SyntaxError, ValueError) below; \
# every documented raise path tokenize.generate_tokens can produce is already caught"
# frob:waive EXHAUST002 reason="T-1371: same resolver artifact as EXHAUST003 above -- \
# tokenize's internal dict-keyed dispatch is conservatively assumed to leak KeyError; \
# no KeyError-raising call is reachable from this function's own source"
def _find_comment_start(line: str) -> int | None:
    """The column of the FIRST genuine trailing comment token on `line`
    (a single physical source line, no newline), or `None` if it carries
    no real comment -- tokenizes the DEDENTED line in isolation
    (`tokenize` correctly refuses to treat a `#` inside a string literal
    as a comment) and adds the stripped indentation back, so a line like
    `x = "a # b"` is never mistaken for carrying a trailing comment."""
    lstripped = line.lstrip()
    indent = len(line) - len(lstripped)
    try:
        for tok in tokenize.generate_tokens(io.StringIO(lstripped + "\n").readline):
            if tok.type == tokenize.COMMENT:
                return indent + tok.start[1]
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return None
    return None


def _split_suppression_line(line: str) -> tuple[str, str, str]:
    """`line` split into `(code_part, comment_text, newline)`:
    `code_part` is everything before the first genuine trailing comment
    (`_find_comment_start`), rstripped; `comment_text` is that comment
    verbatim (empty if none); `newline` is the original line ending (`""`
    or `"\\n"`), preserved so the rewrite never changes it."""
    newline = "\n" if line.endswith("\n") else ""
    body = line[: len(line) - len(newline)] if newline else line
    comment_start = _find_comment_start(body)
    if comment_start is None:
        return body.rstrip(), "", newline
    return body[:comment_start].rstrip(), body[comment_start:], newline


def _merged_dialect_codes(
    present: dict[str, set[str] | None], dialect: str, code: str
) -> dict[str, set[str] | None]:
    """`present` (a line's existing per-dialect suppression codes, from
    `frob.gates._suppress._line_suppressions`) with `code` added under
    `dialect` -- idempotent (a no-op if `code` is already covered) and
    NEVER widens an existing bare suppression (`None`) to a coded one, per
    this ticket's own acceptance: a bare comment already covers every
    code, so leaving it bare is strictly more permissive, never less
    correct."""
    merged = dict(present)
    if dialect in merged:
        current = merged[dialect]
        if current is None or code in current:
            return merged
        merged[dialect] = current | {code}
    else:
        merged[dialect] = {code}
    return merged


def _format_dialect_segment(dialect: str, codes: set[str] | None) -> str:
    """The rendered `# ...` comment fragment for one dialect's `codes`
    (`None` renders bare, matching each dialect's own bare-suppression
    comment syntax) -- the inverse of `frob.gates._suppress._line_
    suppressions`' own per-dialect regexes."""
    joined = "" if codes is None else ",".join(sorted(codes))
    if dialect == "mypy":
        return "# type: ignore" if codes is None else f"# type: ignore[{joined}]"
    if dialect == "ty":
        return "# ty: ignore" if codes is None else f"# ty: ignore[{joined}]"
    return "# noqa" if codes is None else f"# noqa: {joined}"


def _strip_known_pragma_comments(
    comment_text: str, dialects: dict[str, SuppressionDialect]
) -> str:
    """`comment_text` with every recognized dialect pragma
    (`ty`/`mypy`/`ruff`'s own patterns) removed, leaving any OTHER
    trailing prose comment intact -- preserves a genuinely human-written
    explanatory comment sharing the line with a suppression, rather than
    discarding it when this handler rebuilds the pragma block."""
    remainder = comment_text
    for dialect in dialects.values():
        remainder = re.sub(dialect.pattern, "", remainder)
    return remainder.strip()


def _render_suppression_line(
    code_part: str,
    codes: dict[str, set[str] | None],
    leftover: str,
    newline: str,
) -> str:
    """Reassemble one source line from `code_part`, every dialect pragma
    in `codes` (rendered in `_CANONICAL_DIALECT_ORDER`), and any
    preserved `leftover` prose comment -- the single place this handler
    ever produces final line text, so canonical order/spacing is
    guaranteed uniform regardless of which dialect triggered the
    rewrite."""
    segments = [
        _format_dialect_segment(dialect, codes[dialect])
        for dialect in _CANONICAL_DIALECT_ORDER
        if dialect in codes
    ]
    pieces = [code_part, *segments]
    rendered = "  ".join(pieces)
    if leftover:
        rendered = f"{rendered}  {leftover}"
    return rendered + newline


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to dict.get chained \
# three deep and dict.items() iteration in the list-comprehension below, plain dict \
# operations the resolver cannot statically bound; the one real raise path \
# (tomllib.loads on malformed TOML) is caught above"
def _ruff_per_file_ignores(root: Path) -> list[tuple[str, set[str]]]:
    """`[tool.ruff.lint.per-file-ignores]` from `root/pyproject.toml`, as
    `(glob, codes)` pairs -- an empty list if the file/section is
    missing/unreadable (fail toward "nothing is pre-ignored", never
    toward silently over-suppressing)."""
    pyproject = root / "pyproject.toml"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    section = (
        data.get("tool", {}).get("ruff", {}).get("lint", {}).get("per-file-ignores", {})
    )
    if not isinstance(section, dict):
        return []
    return [
        (str(pattern), {str(c) for c in codes})
        for pattern, codes in section.items()
        if isinstance(codes, list)
    ]


def _code_ignored_for_path(root: Path, rel_path: str, code: str) -> bool:
    """True if ruff's own effective `per-file-ignores` configuration
    already silences `code` at `rel_path` -- adding a `# noqa: E501` there
    would be dead, no-op suppression noise (the T-1341 driver incident:
    2493 of 2623 `# noqa: E501` comments repo-wide sat under `tests/**`,
    where `E501` can never fire at all per this repo's own
    `pyproject.toml`). Prefix-matched (`code.startswith(ignored)`) so a
    broader category ignore (e.g. a bare `E5`) still covers `E501`,
    mirroring ruff's own rule-selector prefix semantics."""
    for pattern, codes in _ruff_per_file_ignores(root):
        if fnmatch.fnmatch(rel_path, pattern) and any(
            code.startswith(ignored) for ignored in codes
        ):
            return True
    return False


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to \
# guarded_subprocess_run, a cross-module wrapper the resolver cannot see through; the \
# one documented raise path (FileNotFoundError, ruff binary missing) is caught below"
def _run_ruff_format(path: Path) -> None:
    """Best-effort `ruff format <path>` delegation -- the coordinator-
    directed fix for an over-long CODE line (a def/class signature):
    `ruff format` already wraps these correctly and completely (verified:
    it splits a >88-char `def` into one-parameter-per-line with a
    trailing comma), so this handler defers to it entirely rather than
    hand-rolling a signature wrapper that would duplicate the formatter
    (this repo's NO DUPLICATION rule) and be fought by the next `ruff
    format` run, which is authoritative for code layout. Errors are
    logged and swallowed -- a failed format attempt must not abort the
    whole SUPPRESS001 fix pass; the surviving-violation path below still
    applies a suppression if the line is still too long afterward."""
    try:
        result = guarded_subprocess_run(
            ["ruff", "format", str(path)], capture_output=True, text=True
        )
    except FileNotFoundError:
        _log.warning("SUPPRESS001 auto-fix: ruff binary not found, skipping format")
        return
    if result.is_err:
        _log.warning(
            "SUPPRESS001 auto-fix: ruff format on %s failed: %s",
            path,
            result.danger_err,
        )


# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to \
# _split_suppression_line/_line_suppressions_for_fix/_merged_dialect_codes/ \
# _strip_known_pragma_comments/_render_suppression_line/_code_ignored_for_path, \
# module-local helpers the resolver cannot see through; the one real raise path \
# (path.read_text) is caught above"
# frob:waive EXHAUST002 reason="T-1371: same resolver artifact as EXHAUST003 above -- \
# _merged_dialect_codes indexes into `dialects` by `reporting`, a dict lookup the \
# resolver conservatively assumes can raise KeyError; `dialects` is always the full \
# SuppressionDialect registry passed in by the caller, and `reporting` is always a key \
# already validated against it upstream"
def _apply_one_suppress001_fix(
    root: Path,
    rel_file: str,
    line_no: int,
    reporting: str,
    code: str,
    dialects: dict[str, SuppressionDialect],
    limit: int,
) -> FixApplied | None:
    """The single-line rewrite for one SUPPRESS001 finding: append
    `reporting`'s own suppression for `code` in canonical order
    (`_render_suppression_line`), then -- only if the rewritten line now
    exceeds `limit` -- also add `# noqa: E501` UNLESS ruff's own
    `per-file-ignores` configuration already silences `E501` at this path
    (`_code_ignored_for_path`; adding one there would be dead-on-arrival
    noise, the T-1341 driver's own incident). Returns `None` (a no-op) if
    the file/line cannot be read, the line is `frob:`-directive-bearing
    (FMT001's territory, never this handler's), or the finding's own
    dialect/code is already covered (defensive; `suppress001_gate` should
    never emit that combination in the first place)."""
    path = root / rel_file
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    lines = text.splitlines(keepends=True)
    idx = line_no - 1
    if idx < 0 or idx >= len(lines):
        return None
    original_line = lines[idx]
    code_part, comment_text, newline = _split_suppression_line(original_line)
    if _FROB_DIRECTIVE_MARKER_RE.search(comment_text):
        return None
    present = _line_suppressions_for_fix(comment_text, dialects)
    new_codes = _merged_dialect_codes(present, reporting, code)
    if new_codes == present:
        return None
    leftover = _strip_known_pragma_comments(comment_text, dialects)
    rendered = _render_suppression_line(code_part, new_codes, leftover, newline)

    noqa_added = False
    if "ruff" not in new_codes and len(rendered.rstrip("\n")) > limit:
        if not _code_ignored_for_path(root, rel_file, "E501"):
            new_codes = _merged_dialect_codes(new_codes, "ruff", "E501")
            rendered = _render_suppression_line(code_part, new_codes, leftover, newline)
            noqa_added = True

    if rendered == original_line:
        return None
    lines[idx] = rendered
    if not _write_text(path, "".join(lines)):
        return None
    detail = f"{original_line.rstrip(chr(10))!r} -> {rendered.rstrip(chr(10))!r}"
    if noqa_added:
        detail += " (+ noqa E501, line still over the configured limit after the fix)"
    return FixApplied(rule="SUPPRESS001", file=rel_file, line=line_no, detail=detail)


def _line_suppressions_for_fix(
    comment_text: str, dialects: dict[str, SuppressionDialect]
) -> dict[str, set[str] | None]:
    """`frob.gates._suppress._line_suppressions` applied to just
    `comment_text` (rather than a whole source line) -- a thin wrapper so
    an empty `comment_text` short-circuits to `{}` without a redundant
    regex pass."""
    from frob.gates._suppress import _line_suppressions

    if not comment_text:
        return {}
    return _line_suppressions(comment_text, dialects)


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:tests \
# tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_mypy_suppres\
# sed_ty_unsuppressed_gets_paired_suppression kind="unit"
# frob:tests \
# tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression.test_idempotent_s\
# econd_fix_pass_is_a_no_op kind="unit"
def fix_suppress001_paired_suppression(
    root: Path, snapshot: GraphSnapshot
) -> list[FixApplied]:
    """Tier-A fix (T-1341, phase 2 of T-1339): for every SUPPRESS001
    finding, append the reporting checker's own suppression for its own
    reported rule code, in this repo's observed canonical order
    (`_CANONICAL_DIALECT_ORDER`) -- never a guessed code, never a
    cross-dialect code-mapping table (the exact static approach T-1339
    rejected), only the rule code the finding's own reporting oracle
    already supplied.

    Ordering (coordinator-directed, T-1341): `ruff format` is delegated to
    FIRST, for every file with a violation, before anything is written --
    an over-long CODE line (a def/class signature) belongs to the
    formatter (`_run_ruff_format`), never a hand-rolled wrapper. Only
    after that does this handler re-run `suppress001_gate` (line numbers
    may have shifted) and apply a suppression to whatever violation
    SURVIVES formatting; if a suppressed line is STILL over the limit
    afterward, `# noqa: E501` is added too, unless ruff's own
    `per-file-ignores` config already silences `E501` at that path
    (`_code_ignored_for_path` -- never write a no-op suppression).

    Idempotent by construction, not by bookkeeping: once a line carries
    both dialects' matching suppressions, the underlying diagnostic that
    `suppress001_gate` correlates against is itself silenced for both
    checkers, so a second `--fix` pass finds nothing left to fix on that
    line at all. Never touches a line carrying a `frob:` directive
    comment (FMT001's exclusive territory -- see
    `_FROB_DIRECTIVE_MARKER_RE`'s own docstring for the precedence
    rationale)."""
    from frob.gates._fmt_directives import read_line_length
    from frob.gates._suppress import suppress001_gate, suppression_dialects

    violations = suppress001_gate(root, snapshot)
    if not violations:
        return []

    for rel in sorted({v.file for v in violations}):
        _run_ruff_format(root / rel)

    violations = suppress001_gate(root, snapshot)
    if not violations:
        return []

    dialects = suppression_dialects()
    limit = read_line_length(root)
    applied: list[FixApplied] = []
    for violation in violations:
        parsed = _parse_suppress001_message(violation.message)
        if parsed is None:
            continue
        reporting, code = parsed
        fix = _apply_one_suppress001_fix(
            root, violation.file, violation.line, reporting, code, dialects, limit
        )
        if fix is not None:
            applied.append(fix)
    return applied


# ---------------------------------------------------------------------------
# E501 (T-1547): a line-too-long finding introduced specifically by a
# land-time merge -- a targeted `ruff format` over just the merge-touched
# files, distinct from fix_fmt001_directive_wrap (scoped to `frob:`-
# directive comment lines only, never ordinary code).
# ---------------------------------------------------------------------------


def _merge_touched_python_files(root: Path) -> list[str]:
    """Repo-relative `.py` paths touched by the most recent MERGE commit at
    `root`'s `HEAD` (a real two-parent commit, `git diff --name-only
    HEAD^1 HEAD^2`), or -- when `HEAD` is not itself a merge -- the `.py`
    files with uncommitted working-tree changes against `HEAD` (`git diff
    --name-only HEAD`), covering the in-progress-merge shape `frob ticket
    land`'s own pre-land Tier-A phase runs in (T-1175: `_tier_a_pre_land_
    step` fires on an already `git merge`-d, not-yet-committed worktree).
    Empty on any git failure or when neither shape applies -- this handler
    only ever acts on a genuinely merge-shaped touched set, never guesses
    at "everything E501 currently flags", per this ticket's own targeted
    scope."""
    parents = guarded_subprocess_run(
        ["git", "-C", str(root), "rev-list", "--parents", "-n", "1", "HEAD"],
        capture_output=True,
        text=True,
    )
    if parents.is_err or parents.danger_ok.returncode != 0:
        return []
    fields = parents.danger_ok.stdout.split()
    diff_argv: list[str]
    if len(fields) >= 3:
        # HEAD itself is a merge commit: diff between its two parents.
        diff_argv = [
            "git",
            "-C",
            str(root),
            "diff",
            "--name-only",
            fields[1],
            fields[2],
        ]
    else:
        # Not a committed merge yet -- the T-1175 in-progress-merge shape:
        # uncommitted working-tree changes against HEAD.
        diff_argv = ["git", "-C", str(root), "diff", "--name-only", "HEAD"]
    diffed = guarded_subprocess_run(diff_argv, capture_output=True, text=True)
    if diffed.is_err or diffed.danger_ok.returncode != 0:
        return []
    return [
        line.strip()
        for line in diffed.danger_ok.stdout.splitlines()
        if line.strip().endswith(".py")
    ]


# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# guarded_subprocess_run, a cross-module Result-returning wrapper the resolver cannot \
# see through, and result.danger_ok.stdout attribute access on its own return type; \
# the one real raise path (json.loads on malformed ruff output) is caught below"
def _e501_lines_for_file(root: Path, rel_file: str) -> set[int] | None:
    """1-indexed line numbers `ruff check --select E501` reports for
    `rel_file`, or `None` on any spawn/parse failure -- distinguishing
    "genuinely clean" (empty set) from "could not measure" (`None`) so the
    caller never counts an unmeasurable file as fixed."""
    result = guarded_subprocess_run(
        [
            "ruff",
            "check",
            "--select",
            "E501",
            "--output-format",
            "json",
            rel_file,
        ],
        capture_output=True,
        text=True,
        cwd=root,
    )
    if result.is_err:
        return None
    try:
        items = json.loads(result.danger_ok.stdout)
    except json.JSONDecodeError:
        return None
    lines: set[int] = set()
    for item in items:
        loc = item.get("location", {})
        row = loc.get("row")
        if isinstance(row, int):
            lines.add(row)
    return lines


# frob:doc docs/modules/gates.md#fix_e501_merge_introduced-auto-fix-t-1547
# frob:tests tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced.test_e501_merge_introduced_targeted_format_applies  # noqa: E501
# frob:tests tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced.test_e501_no_merge_shape_is_a_no_op  # noqa: E501
# frob:ticket T-1547
# frob:enforces CHK-GATE-E501
def fix_e501_merge_introduced(root: Path, snapshot: GraphSnapshot) -> list[FixApplied]:
    """Tier-A fix (T-1547): run a targeted `ruff format` over exactly the
    `.py` files a land-time merge touched (`_merge_touched_python_files`)
    that still carry an E501 (line-too-long) finding afterward, then
    re-verify E501 is actually gone from that file before counting it as
    fixed -- never claims a fix `ruff format` did not actually make (a
    `ruff format` pass cannot always shorten every over-long line, e.g. an
    unbreakable string literal). Distinct from `fix_fmt001_directive_wrap`,
    which only ever rewraps `frob:`-directive comment lines, never
    ordinary code -- this handler's own targeted scope is the merge-
    touched set specifically, never a whole-tree `ruff format` sweep
    (that would re-litigate every pre-existing E501 finding in the repo,
    not just ones this land's own merge introduced)."""
    del snapshot  # signature uniformity only; this handler reads git + ruff directly
    touched = _merge_touched_python_files(root)
    if not touched:
        return []
    applied: list[FixApplied] = []
    for rel_file in touched:
        path = root / rel_file
        if not path.is_file():
            continue
        before = _e501_lines_for_file(root, rel_file)
        if not before:
            continue
        _run_ruff_format(path)
        after = _e501_lines_for_file(root, rel_file)
        if after is None:
            continue
        fixed_lines = before - after
        if not fixed_lines:
            continue
        applied.append(
            FixApplied(
                rule="E501",
                file=rel_file,
                line=min(fixed_lines),
                detail=(
                    f"targeted ruff format resolved {len(fixed_lines)} E501 "
                    f"line(s) introduced by this land's merge"
                ),
            )
        )
    return applied


# ---------------------------------------------------------------------------
