"""`frob fmt`: canonical-form line-wrap/unwrap normalizer for `frob:`
directive comment lines (T-0441, docs/modules/gates.md#frob-fmt-directive-
canonicalization-t-0441).

A long `frob:waive`/`frob:debt`/etc. reason today either gets truncated
(losing the explanation) or hand-wrapped with T-0286's trailing-backslash
continuation syntax -- frob owns that continuation syntax, so frob should
own the wrapping. This module makes the wrap two-directional: canonical
form is the FEWEST physical lines that keep every line under the
configured limit -- one line when the logical text fits, wrapped only as
far as necessary otherwise. Running it on already-canonical text (wrapped
or not) is a no-op in both directions.

Folding an existing continuation run back into one logical string reuses
`frob.graph.dsl.fold_comment_runs` (T-0286's own fold, extended with a
physical-line-count) rather than re-deriving what counts as a continuation
line -- this module's only new logic is CHOOSING the physical-line layout
(`_canonical_lines`), not deciding what a continuation is.
"""
# frob:waive INV006 reason="T-0441: the module docstring's/comments' 'only' uses are \
# source-level design-rationale prose describing already-implemented scope limits \
# (block comments unsupported, per-language config unsupported, marker_for's only job) \
# verifiable by reading the code they annotate, not a separate cross-module contract \
# needing its own tracked invariant -- same T-0585 INV006 first-turn-on \
# calibration-batch disposition as the existing waivers in src/frob/graph/dsl.py and \
# src/frob/app/config.py"

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from pydantic import BaseModel

from frob.graph import fold_comment_runs
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441
class FmtChange(BaseModel):
    """One file whose `frob:` directive comments were (or would be, in
    check mode) rewritten to canonical form by `frob fmt`."""

    model_config = {}

    path: str
    """Repo-relative path of the changed file."""


# frob:doc docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441
class FmtReport(BaseModel):
    """The result of a `frob fmt` run: every file whose directive comments
    were not already in canonical form."""

    model_config = {}

    changes: tuple[FmtChange, ...] = ()
    """Files with a non-canonical `frob:` directive, in walk order."""


_DEFAULT_LIMIT = 88
"""Ruff's own default line length, used when `pyproject.toml` has none."""

_NOQA_SUFFIX_RE = re.compile(r"#\s*noqa(:\s*[A-Z0-9]+(\s*,\s*[A-Z0-9]+)*)?\s*$")
"""Matches a trailing `# noqa` / `# noqa: E501[,CODE...]` pragma at the end
of a logical directive line. T-0985: a single-physical-line `frob:` run
ending in this pragma is a deliberate escape hatch (used where the
directive's own content is one unbreakable token, e.g. a long dotted
pytest node id with no space to wrap at) -- treating it as ordinary
directive text and force-wrapping it defeats the whole point of the
pragma. `canonicalize_text` checks single-line runs against this pattern
and leaves a match byte-identical rather than re-wrapping it."""

# frob:doc docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441
_MARKERS: dict[str, str] = {
    ".py": "#",
    ".pyi": "#",
    ".ts": "//",
    ".tsx": "//",
    ".js": "//",
    ".jsx": "//",
    ".mjs": "//",
    ".rs": "//",
    ".c": "//",
    ".h": "//",
    ".cc": "//",
    ".cpp": "//",
    ".hpp": "//",
    ".hh": "//",
}
"""Line-comment marker per supported file suffix. T-0441 scope is `#`/`//`
line comments only -- block comments (`/* ... */`) are out of scope, per
the ticket's own language-coverage note; a `frob:` directive written
inside a block comment is left untouched by this module."""


# frob:doc docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441
# frob:tests tests/test_gates_fmt_directives.py::TestMarkerFor.test_python_uses_hash
# frob:tests \
# tests/test_gates_fmt_directives.py::TestMarkerFor.test_rust_uses_slash_slash
# frob:tests \
# tests/test_gates_fmt_directives.py::TestMarkerFor.test_unsupported_suffix_is_none
def marker_for(path: str) -> str | None:
    """The line-comment marker for `path`'s suffix (`#`, `//`), or `None`
    if `path`'s language is not one `frob fmt` covers."""
    return _MARKERS.get(Path(path).suffix)


# frob:doc docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441
# frob:tests \
# tests/test_gates_fmt_directives.py::TestReadLineLength.test_reads_configured_limit
# frob:tests \
# tests/test_gates_fmt_directives.py::TestReadLineLength.test_missing_file_defaults_to_\
# 88
# frob:tests \
# tests/test_gates_fmt_directives.py::TestReadLineLength.test_missing_ruff_section_defa\
# ults_to_88
def read_line_length(root: Path) -> int:
    """The project's configured line-length limit, read from `[tool.ruff]
    line-length` in `root/pyproject.toml`, falling back to 88 (ruff's own
    default) when unset or unreadable.

    T-0441 known limitation: this reads ONE project-wide limit sourced from
    ruff's own config; a genuinely per-language limit (`rustfmt.toml`'s
    `max_width`, a `.prettierrc`'s `printWidth`, clang-format's
    `ColumnLimit`) is not wired up here -- every supported language is
    wrapped against this single ruff-derived limit today. Filed as a
    follow-up rather than silently assumed solved; see T-0441's Done
    report.
    """
    pyproject = root / "pyproject.toml"
    try:
        data = tomllib.loads(pyproject.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.debug(
            "read_line_length: %s unreadable (%s), using default %d",
            pyproject,
            exc,
            _DEFAULT_LIMIT,
        )
        return _DEFAULT_LIMIT
    value = data.get("tool", {}).get("ruff", {}).get("line-length")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return _DEFAULT_LIMIT


def _canonical_lines(text: str, *, marker: str, indent: str, limit: int) -> list[str]:
    """Split `text` (one logical directive's delimiter-stripped content,
    e.g. `frob:waive RULE reason="..."`) into the fewest physical comment
    lines -- each `indent + marker + ' ' + content`, every non-final line
    ending in a trailing `\\` continuation -- such that every physical line
    is at most `limit` columns wide.

    A single line is returned whenever `text` already fits: this is what
    makes the operation a canonicalizer rather than a one-way wrapper --
    the same function handles both "wrap because it's too long" and
    "un-wrap because it now fits", the caller just re-runs it on whatever
    physical-line count currently exists. The split always lands on a
    space boundary (never mid-word) when one exists within budget, and the
    space is kept on the EARLIER line so re-joining with the empty string
    (T-0286's own fold rule) reproduces `text` exactly -- this is the
    property the round-trip test asserts.
    """
    prefix = f"{indent}{marker} "
    if len(prefix) + len(text) <= limit:
        return [prefix + text]

    lines: list[str] = []
    remaining = text
    while True:
        room = limit - len(prefix)
        if len(remaining) <= room:
            lines.append(prefix + remaining)
            return lines
        # One char of `room` is reserved for the trailing "\" continuation
        # marker on every non-final physical line.
        budget = room - 1
        if budget <= 0:
            # Degenerate: indent/marker alone leave no room to wrap into.
            # Emit the remainder verbatim rather than infinite-loop or
            # corrupt the text -- round-trip correctness beats staying
            # under `limit` in this unwrappable corner case.
            lines.append(f"{prefix}{remaining}\\")
            return lines
        # frob:ticket T-0984
        # Off-by-one (T-0972 incident): searching for a space up to and
        # INCLUDING index `budget` (`rfind`'s end bound is exclusive, so
        # `budget + 1` lets index `budget` itself match), then keeping that
        # space attached to `head` (`remaining[: cut + 1]` below), yields a
        # `head` of length `budget + 1` -- one column over `budget`, which
        # becomes one column over `limit` once `prefix` and the trailing
        # "\" continuation marker are added. The search span must exclude
        # index `budget` itself (`[0, budget)`, not `[0, budget]`) so the
        # latest possible cut still leaves `head` at length `budget`, never
        # `budget + 1`.
        cut = remaining.rfind(" ", 0, budget)
        if cut <= 0:
            # No breakable space within budget -- break at the budget
            # boundary verbatim (still round-trips, just not word-aligned).
            cut = budget
            head, tail = remaining[:cut], remaining[cut:]
        else:
            # Keep the space attached to the earlier line so folding with
            # the empty string reproduces the original spacing exactly.
            head, tail = remaining[: cut + 1], remaining[cut + 1 :]
        lines.append(f"{prefix}{head}\\")
        remaining = tail


# frob:ticket T-0976
def _fmt_marker_entries_with_indents(
    lines: list[str], marker: str
) -> tuple[dict[int, str], list[tuple[int, str, str, int]]]:
    """Every `marker`-prefixed line in `lines` as both its own leading
    indent (`index -> indent string`) and `fold_comment_runs`' expected
    entry tuple -- the marker-scan half of `canonicalize_text`, split from
    the run-rewrite half since `_canonical_lines` needs each run's
    original indent to reproduce it."""
    indents: dict[int, str] = {}
    entries: list[tuple[int, str, str, int]] = []
    for i, raw in enumerate(lines):
        stripped = raw.lstrip(" \t")
        if not stripped.startswith(marker):
            continue
        content = stripped[len(marker) :]
        if content.startswith(" "):
            content = content[1:]
        indents[i] = raw[: len(raw) - len(stripped)]
        entries.append((i, content, "", 0))
    return indents, entries


# frob:ticket T-0976
# frob:ticket T-0985
def _rewrite_lines_via_runs(
    lines: list[str],
    runs: list,
    indents: dict[int, str],
    *,
    marker: str,
    limit: int,
) -> list[str]:
    """Rebuild `lines` with each `frob:`-prefixed folded `run` replaced by
    its T-0441 canonical form (`_canonical_lines`, preserving the run's
    own CR convention), and every other run/line passed through verbatim
    -- the run-rewrite half of `canonicalize_text`, split from the
    marker-scan half that built `runs`/`indents`.

    T-0985: a run ending in a `# noqa`/`# noqa: CODE` pragma
    (`_NOQA_SUFFIX_RE`) is a deliberate escape hatch for an unwrappable
    single token and is passed through verbatim like a non-`frob:` run,
    rather than being canonicalized."""
    out: list[str] = []
    run_idx = 0
    i = 0
    n = len(lines)
    # frob:waive PERF003 reason="two-pointer merge scan over lines/runs advancing \
    # together, O(n) total, not a cross join"  # noqa: E501
    while i < n:
        if run_idx < len(runs) and runs[run_idx][1] == i:
            logical_text, _lineno, _src, count = runs[run_idx]
            run_idx += 1
            if logical_text.strip().startswith("frob:") and not _NOQA_SUFFIX_RE.search(
                logical_text
            ):
                # `fold_comment_runs` already rstrips "\r" off every
                # constituent line while folding (T-0286's own fold rule),
                # so `logical_text` is always "\r"-free regardless of the
                # run's original convention -- reapply it here, once per
                # run, from the run's FIRST physical line.
                run_had_cr = lines[i].endswith("\r")
                canonical = _canonical_lines(
                    logical_text, marker=marker, indent=indents[i], limit=limit
                )
                if run_had_cr:
                    canonical = [line + "\r" for line in canonical]
                out.extend(canonical)
            else:
                out.extend(lines[i : i + count])
            i += count
        else:
            out.append(lines[i])
            i += 1
    return out


# frob:doc docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441
# frob:tests \
# tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_wraps_over_long_single_\
# line_directive
# frob:tests \
# tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_joins_over_split_direct\
# ive_that_now_fits
# frob:tests \
# tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_idempotent_on_already_c\
# anonical_text
# frob:tests \
# tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985.test_over_long_single_l\
# ine_with_noqa_e501_is_byte_identical
# frob:tests \
# tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985.test_over_long_single_l\
# ine_with_bare_noqa_is_byte_identical
# frob:tests \
# tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985.test_over_long_line_wit\
# hout_noqa_still_wraps
# frob:tests \
# tests/test_gates_fmt_directives.py::TestRepoWideIdempotenceT0985.test_canonicalizing_\
# twice_over_real_repo_files_is_a_no_op
# frob:ticket T-0972
# frob:ticket T-0985
# frob:waive AFFECT001 reason="T-0976 pure internal refactor: extraction of cohesive helpers from this already-documented function, no external contract/behavior change, doc anchor(s) remain accurate as-is"  # noqa: E501
def canonicalize_text(text: str, *, path: str, limit: int) -> str:
    """Rewrite every `frob:` directive comment run in `text` (source for
    `path`, consulted only to pick the line-comment marker via
    `marker_for`) into T-0441 canonical form: the fewest physical lines
    that keep each line within `limit`, joined/split via T-0286
    continuation backslashes.

    Non-directive comments and all code are left byte-for-byte untouched.
    Returns `text` unchanged if `path`'s language is unsupported
    (`marker_for` returns `None`). Idempotent: canonicalizing already-
    canonical text returns it unchanged, in both the wrap and un-wrap
    direction.

    T-0985: a directive run whose logical text ends in a `# noqa`/`# noqa:
    CODE` pragma (`_NOQA_SUFFIX_RE`) is a deliberate escape hatch for
    content that cannot be wrapped without breaking a single unbreakable
    token (e.g. a long dotted pytest node id) -- such a run is left
    byte-identical rather than force-wrapped.
    """
    marker = marker_for(path)
    if marker is None:
        return text

    # T-0441 CRLF fix (reviewer CRITICAL): `text` must be split on "\n" only,
    # never on "\r\n"/"\r" -- doing so on a CRLF file would strip the "\r"
    # from EVERY line, including ones this function never touches. Instead
    # each `lines[i]` below still carries its own trailing "\r" verbatim
    # (split("\n") alone leaves it attached) so an untouched code/comment
    # line is reproduced byte-for-byte. Only freshly generated canonical
    # directive lines (which `_canonical_lines` builds LF-only) need a "\r"
    # re-added, matched to the run's OWN original convention (`run_had_cr`
    # below) rather than a single global guess -- see the CRLF regression
    # tests in tests/test_gates_fmt_directives.py.
    had_trailing_newline = text.endswith("\n")
    lines = text.split("\n")
    if had_trailing_newline:
        lines = lines[:-1]

    indents, entries = _fmt_marker_entries_with_indents(lines, marker)
    runs = fold_comment_runs(entries)
    out = _rewrite_lines_via_runs(lines, runs, indents, marker=marker, limit=limit)

    result = "\n".join(out)
    if had_trailing_newline:
        result += "\n"
    return result


# frob:ticket T-0979
def _read_source_for_format(path: Path) -> str | None:
    """`_format_one_path`'s read half: returns `path`'s raw text with
    CRLF-preserving `newline=""` semantics, or `None` for an unsupported
    language (no directive marker) or an unreadable file -- either case
    is a silent skip, logged at DEBUG, matching `format_paths`'s
    documented best-effort posture."""
    if marker_for(str(path)) is None:
        return None
    try:
        # `pathlib.Path.read_text`/`write_text` gained a `newline=`
        # parameter only in Python 3.13; this repo targets 3.11, so the
        # `newline=""` universal-newline opt-out has to go through the
        # plain `open()` builtin instead (same effect: "\r\n"/"\r"
        # survive verbatim rather than being translated to "\n").
        with open(path, encoding="utf-8", newline="") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        _log.debug("format_paths: skipping unreadable %s (%s)", path, exc)
        return None


# frob:ticket T-0979
def _write_formatted(path: Path, rewritten: str) -> None:
    """`_format_one_path`'s write half: rewrite `path` in place with
    `rewritten`'s content, `newline=""` preserving whatever CRLF/LF
    convention the caller already decided on (see `format_paths`'s
    docstring for the full rationale)."""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(rewritten)


# frob:ticket T-0979
def _relpath_for_change(path: Path, root: Path) -> str:
    """`_format_one_path`'s reported-path half: `path` relative to `root`
    when possible, else `path` unchanged -- the display string an
    `FmtChange` carries."""
    if path.is_relative_to(root):
        return str(path.relative_to(root))
    return str(path)


# frob:ticket T-0979
def _format_one_path(
    path: Path, root: Path, *, limit: int, check_only: bool
) -> "FmtChange | None":
    """`format_paths`'s per-file half: canonicalize `path` (skipping an
    unsupported language or an unreadable file), returning its
    `FmtChange` if it is not already canonical, and -- unless `check_only`
    -- rewriting it in place. See `format_paths`'s own docstring for the
    CRLF-preserving `newline=""` rationale this shares."""
    original = _read_source_for_format(path)
    if original is None:
        return None
    rewritten = canonicalize_text(original, path=str(path), limit=limit)
    if rewritten == original:
        return None
    if not check_only:
        _write_formatted(path, rewritten)
    return FmtChange(path=_relpath_for_change(path, root))


# frob:doc docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441
# frob:tests \
# tests/test_gates_fmt_directives.py::TestFormatPaths.test_check_mode_reports_without_w\
# riting
# frob:tests \
# tests/test_gates_fmt_directives.py::TestFormatPaths.test_write_mode_rewrites_file
# frob:waive AFFECT001 reason="T-0976 pure internal refactor: extraction of cohesive helpers from this already-documented function, no external contract/behavior change, doc anchor(s) remain accurate as-is"  # noqa: E501
def format_paths(
    root: Path, *, check_only: bool, limit: int | None = None
) -> FmtReport:
    """Canonicalize every `frob:` directive comment under `root` (a repo
    root or a single file), skipping the usual excluded/pruned dirs via
    `frob.excludes.iter_files`.

    In `check_only` mode, nothing is written -- `FmtReport.changes` lists
    every file that is NOT already canonical (this is what `frob check`'s
    remediation hint is built from). Otherwise, each non-canonical file is
    rewritten in place. `limit` overrides `read_line_length`'s
    pyproject-derived default, mainly for tests.

    T-0441 CRLF fix (reviewer CRITICAL): both the read and the write use
    `newline=""`, which disables Python's universal-newline translation in
    BOTH directions -- `read_text()`'s default translates any "\r\n"/"\r"
    to "\n" on read, and `write_text()`'s default re-translates "\n" to
    `os.linesep` on write (a no-op on Linux, which is exactly how a
    CRLF-authored TS/Rust/C/C++ file's line endings were silently getting
    flattened to LF on every line -- including lines this function never
    touches -- when this ran on a Linux worktree). With `newline=""`, `"\r"`
    characters survive verbatim in the string on both sides, and
    `canonicalize_text` only ever changes the physical lines of a
    non-canonical `frob:` directive run -- everything else is byte-for-byte
    identical. `original` and `rewritten` are read/compared through this
    SAME `newline=""` transform, so the `rewritten == original` check-only
    change-detection below can never report a false-positive change from a
    newline-translation mismatch between the two sides -- both sides see
    the file's raw bytes the same way.
    """
    from frob.excludes import iter_files

    resolved_limit = limit if limit is not None else read_line_length(root)
    paths = (root,) if root.is_file() else iter_files(root)
    changes: list[FmtChange] = []
    for path in paths:
        change = _format_one_path(
            path, root, limit=resolved_limit, check_only=check_only
        )
        if change is not None:
            changes.append(change)
    _log.info(
        "format_paths: %d file(s) %s under %s",
        len(changes),
        "would change" if check_only else "changed",
        root,
    )
    return FmtReport(changes=tuple(changes))


__all__ = [
    "FmtChange",
    "FmtReport",
    "canonicalize_text",
    "format_paths",
    "marker_for",
    "read_line_length",
]
