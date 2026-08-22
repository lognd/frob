# frob:waive LARGE001 reason="T-1651-grade: this module is one mechanism -- canonical \
# two-directional line-wrap/unwrap of frob: directive comments (T-0441) -- not a \
# rule-id family. Folding relies on frob.graph.dsl.fold_comment_runs; this module's \
# own new logic is choosing the physical-line layout (_canonical_lines) and driving it \
# over every directive kind (frob:waive/frob:debt/frob:ticket/etc) uniformly, which is \
# exactly why it is one file: a per-directive-kind split would duplicate the same \
# fold/unfold/rewrap pipeline once per directive kind for no distinct consumer -- \
# every caller goes through the same frob fmt entrypoint."
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

from __future__ import annotations

import json
import os
import re
import tempfile
import tomllib
from collections.abc import Sequence
from pathlib import Path

import yaml
from pydantic import BaseModel

from frob.graph import fold_comment_runs
from frob.logging import get_logger
from frob.yaml_io import fast_yaml_loader

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

_EFFECTIVELY_UNLIMITED = 10**9
"""T-1606: internal stand-in for "this language's formatter has no width
concept" (`resolve_line_length` returning `None`) -- large enough that
`_canonical_lines`' `len(prefix) + len(text) <= limit` check always takes
the single-line branch, so a no-width-limit directive is never wrapped,
without threading `int | None` through the wrap-math internals."""

_NOQA_SUFFIX_RE = re.compile(r"#\s*noqa(:\s*[A-Z0-9]+(\s*,\s*[A-Z0-9]+)*)?\s*$")
"""Matches a trailing `# noqa` / `# noqa: E501[,CODE...]` pragma at the end
of a logical directive line. T-0985: a single-physical-line `frob:` run
ending in this pragma is a deliberate escape hatch (used where the
directive's own content is one unbreakable token, e.g. a long dotted
pytest node id with no space to wrap at) -- treating it as ordinary
directive text and force-wrapping it defeats the whole point of the
pragma. `canonicalize_text` checks single-line runs against this pattern
and leaves a match byte-identical rather than re-wrapping it."""

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
    ".strata": "//",
}
"""Line-comment marker per supported file suffix. T-0441 scope is `#`/`//`
line comments only -- block comments (`/* ... */`) are out of scope, per
the ticket's own language-coverage note; a `frob:` directive written
inside a block comment is left untouched by this module. `.strata` (T-1581)
was originally missing here entirely -- `fix_cov002_ticket_directive_
insertion`'s own hardcoded, narrower table defaulted an unknown suffix to
`#`, and during T-1548's own land that silently wrote a Python-style
directive into a `.strata` file (comment leader `//`), breaking strata
parsing on main. Adding it here, the one shared marker table, means every
caller of `marker_for` gets the fix at once instead of each hand-rolled
table needing the same patch independently."""


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


# T-1606 DESIGN DECISION (recorded here, not left implicit): before this
# ticket, `format_paths`/`_fix_engine_text`/`_land_cmd`/`_todo_fmt` all
# called `read_line_length(root)` exactly ONCE per run and passed that
# single ruff-derived int to every file regardless of language -- correct
# for Python (ruff owns Python's width, and `# noqa: E501` is what a
# directive wrap is standing in for there) but wrong for every other
# language `frob fmt` wraps (Rust/TS/JS/C-family), which each have their
# OWN formatter and their own width knob. `resolve_line_length` below is
# the per-FILE replacement: each supported language gets its own width
# resolved from that language's own toolchain config (walking upward from
# the file, nearest-wins, matching how the real tools resolve a monorepo),
# falling back to that tool's own documented default when the config is
# absent -- never to ruff's number. `None` is a first-class answer here:
# a formatter with no configurable width (T-1606's own examples: gofmt,
# `zig fmt`, `shfmt`) must never be wrapped on width at all, or `frob fmt`
# would keep reformatting such a file every run for no reason. Go/Zig/
# Bash are not yet entries in `_MARKERS` (no adapter registers `.go`/
# `.zig`/`.sh` here today) -- when one is added, its `_LANGUAGE_WIDTH_
# SOURCES` entry should be `None` outright (no config lookup at all),
# exercising the exact same "no width limit" contract
# `TestResolveLineLength.test_no_limit_language_never_wraps` proves at the
# `canonicalize_text`/`_canonical_lines` level today. `.strata` (frob's
# own DSL, no external formatter) is deliberately left OUT of this table
# and keeps falling through to the `_DEFAULT_WIDTH_SOURCE` (ruff-derived)
# branch below -- unlike Go/Zig/Bash it has no formatter of its own to
# defer to, so preserving T-0441's original repo-wide behavior for it is
# the least-surprising default rather than an unstated policy call.
_RUST_CONFIG_FILES: tuple[str, ...] = ("rustfmt.toml", ".rustfmt.toml")
"""rustfmt's own config filenames, most-specific first (rustfmt itself
accepts either name; `_find_nearest_config` tries both at each directory
level before walking up, so a directory with only `.rustfmt.toml` still
resolves)."""

_RUST_DEFAULT_WIDTH = 100
"""rustfmt's documented default `max_width` when no config overrides it."""

_PRETTIER_CONFIG_FILES: tuple[str, ...] = (
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.yaml",
    ".prettierrc.yml",
    ".prettierrc.toml",
)
"""Prettier config filenames this resolver can parse without executing
JS -- `.prettierrc.js`/`.cjs`/`.mjs` and a `prettier.config.*` module are
deliberately not in this list (parsing them would mean running arbitrary
JavaScript); a project using one of those falls back to `_PRETTIER_
DEFAULT_WIDTH` here, same as having no prettier config at all."""

_PRETTIER_DEFAULT_WIDTH = 80
"""Prettier's documented default `printWidth` when no config overrides it."""

_CLANG_FORMAT_CONFIG_FILES: tuple[str, ...] = (".clang-format",)
"""clang-format's own config filename (YAML)."""

_CLANG_FORMAT_DEFAULT_WIDTH = 80
"""clang-format's documented default `ColumnLimit` when no `.clang-format`
overrides it (clang-format's built-in styles, e.g. LLVM/Google, all ship
80 as their own default)."""

_PY_SUFFIXES = frozenset({".py", ".pyi"})
_RUST_SUFFIXES = frozenset({".rs"})
_PRETTIER_SUFFIXES = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs"})
_CLANG_FORMAT_SUFFIXES = frozenset({".c", ".h", ".cc", ".cpp", ".hpp", ".hh"})


def _find_nearest_config(
    start_dir: Path, root: Path, filenames: Sequence[str]
) -> Path | None:
    """The nearest ancestor of `start_dir` (searched from `start_dir` up to
    and including `root`, then stopping) containing one of `filenames` --
    "nearest config wins", matching how rustfmt/prettier/clang-format
    themselves resolve a config file in a monorepo with a package-local
    override. Returns `None` if none of `filenames` exists anywhere in
    that range. `filenames` is short (at most 6 entries, `_PRETTIER_
    CONFIG_FILES` plus `package.json`) and checked once per directory
    level on a shallow ancestor chain, so the nested loop here is a fixed,
    small constant -- not the growing-with-input shape PERF003 flags.
    """
    try:
        current = start_dir.resolve()
        root_resolved = root.resolve()
    except OSError:
        return None
    # frob:waive PERF003 reason="a directory-ancestor walk (bounded by filesystem \
    # depth) over a fixed, short filenames tuple (<=6 entries) per level -- not a \
    # scale-sensitive cross join over two growing-with-input collections"
    while True:
        for name in filenames:
            candidate = current / name
            if candidate.is_file():
                return candidate
        if current == root_resolved or current.parent == current:
            return None
        current = current.parent


def _read_toml_key(config: Path, key: str) -> object | None:
    """`config`'s top-level `key`, or `None` if the file is unreadable,
    unparseable, or the key is absent -- callers treat `None` as "use the
    tool's own default", never as an error."""
    try:
        data = tomllib.loads(config.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.debug("_read_toml_key: %s unreadable (%s)", config, exc)
        return None
    return data.get(key)


def _read_yaml_or_json_key(config: Path, key: str) -> object | None:
    """`config`'s top-level `key` from a YAML (or JSON, a YAML subset)
    file, or `None` if unreadable/unparseable/absent -- same "use the
    tool's own default" contract as `_read_toml_key`."""
    try:
        data = yaml.load(config.read_text(), Loader=fast_yaml_loader())
    except (OSError, yaml.YAMLError) as exc:
        _log.debug("_read_yaml_or_json_key: %s unreadable (%s)", config, exc)
        return None
    if not isinstance(data, dict):
        return None
    return data.get(key)


def _as_int(value: object) -> int | None:
    """`value` as a plain `int`, or `None` if it is missing, a `bool`
    (pydantic/JSON's own `bool`-is-an-`int` trap), or any other non-int
    type -- shared validation for every config-derived width below."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _resolve_rust_width(path: Path, root: Path) -> int:
    """rustfmt's `max_width` for `path`: the nearest `rustfmt.toml`/
    `.rustfmt.toml` walking upward from `path`'s directory to `root`, or
    `_RUST_DEFAULT_WIDTH` if none is found or the key is absent/invalid."""
    config = _find_nearest_config(path.parent, root, _RUST_CONFIG_FILES)
    if config is None:
        return _RUST_DEFAULT_WIDTH
    value = _as_int(_read_toml_key(config, "max_width"))
    return value if value is not None else _RUST_DEFAULT_WIDTH


def _resolve_prettier_width(path: Path, root: Path) -> int:
    """Prettier's `printWidth` for `path`: the nearest prettier config
    (`_PRETTIER_CONFIG_FILES`, or a `package.json` carrying a `prettier`
    object -- both walked for together so the nearer of the two wins) from
    `path`'s directory up to `root`, or `_PRETTIER_DEFAULT_WIDTH` if
    neither is found or the key is absent/invalid.
    """
    config = _find_nearest_config(
        path.parent, root, (*_PRETTIER_CONFIG_FILES, "package.json")
    )
    if config is None:
        return _PRETTIER_DEFAULT_WIDTH
    if config.name == "package.json":
        try:
            data = json.loads(config.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            _log.debug("_resolve_prettier_width: %s unreadable (%s)", config, exc)
            data = {}
        prettier_key = data.get("prettier") if isinstance(data, dict) else None
        value = (
            _as_int(prettier_key.get("printWidth"))
            if isinstance(prettier_key, dict)
            else None
        )
    elif config.suffix == ".toml":
        value = _as_int(_read_toml_key(config, "printWidth"))
    else:
        value = _as_int(_read_yaml_or_json_key(config, "printWidth"))
    return value if value is not None else _PRETTIER_DEFAULT_WIDTH


def _resolve_clang_format_width(path: Path, root: Path) -> int:
    """clang-format's `ColumnLimit` for `path`: the nearest `.clang-format`
    walking upward from `path`'s directory to `root`, or `_CLANG_FORMAT_
    DEFAULT_WIDTH` if none is found or the key is absent/invalid."""
    config = _find_nearest_config(path.parent, root, _CLANG_FORMAT_CONFIG_FILES)
    if config is None:
        return _CLANG_FORMAT_DEFAULT_WIDTH
    value = _as_int(_read_yaml_or_json_key(config, "ColumnLimit"))
    return value if value is not None else _CLANG_FORMAT_DEFAULT_WIDTH


# frob:doc docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441
# frob:tests \
# tests/test_gates_fmt_directives.py::TestResolveLineLength.test_python_uses_ruff_config
# frob:tests \
# tests/test_gates_fmt_directives.py::TestResolveLineLength.test_rust_uses_rustfmt_toml
# frob:tests \
# tests/test_gates_fmt_directives.py::TestResolveLineLength.test_rust_falls_back_to_too\
# l_default
# frob:tests \
# tests/test_gates_fmt_directives.py::TestResolveLineLength.test_prettier_uses_prettier\
# rc
# frob:tests \
# tests/test_gates_fmt_directives.py::TestResolveLineLength.test_prettier_uses_package_\
# json_key
# frob:tests \
# tests/test_gates_fmt_directives.py::TestResolveLineLength.test_prettier_falls_back_to\
# _tool_default
# frob:tests \
# tests/test_gates_fmt_directives.py::TestResolveLineLength.test_clang_format_uses_conf\
# ig
# frob:tests \
# tests/test_gates_fmt_directives.py::TestResolveLineLength.test_clang_format_falls_bac\
# k_to_tool_default
# frob:tests \
# tests/test_gates_fmt_directives.py::TestResolveLineLength.test_nearest_config_wins_ov\
# er_root_config
# frob:tests \
# tests/test_gates_fmt_directives.py::TestResolveLineLength.test_unregistered_suffix_fa\
# lls_back_to_ruff_derived_default
def resolve_line_length(path: Path, root: Path) -> int | None:
    """The width `path`'s OWN formatter would enforce -- Rust's rustfmt,
    TS/JS's prettier, or C-family's clang-format, each read from that
    tool's own config (nearest ancestor wins, `_find_nearest_config`),
    falling back to that tool's documented default when no config exists.
    Python (`.py`/`.pyi`) is unchanged from `read_line_length`: ruff stays
    the sole owner of Python's width. Every other registered suffix
    (currently only `.strata`) falls back to the same ruff-derived value
    for want of a language-specific formatter of its own -- see this
    function's own T-1606 design-decision comment, directly above.

    Returns `None` for a language whose formatter has no configurable
    width at all (not yet reachable through `_MARKERS` today -- see the
    T-1606 design-decision comment) -- callers must treat `None` as "never
    wrap this file's directives on width", not as "use some default".
    """
    suffix = path.suffix
    if suffix in _RUST_SUFFIXES:
        return _resolve_rust_width(path, root)
    if suffix in _PRETTIER_SUFFIXES:
        return _resolve_prettier_width(path, root)
    if suffix in _CLANG_FORMAT_SUFFIXES:
        return _resolve_clang_format_width(path, root)
    # Python and every other still-ruff-derived suffix (.strata today).
    return read_line_length(root)


# frob:ticket T-0991
def _shift_cut_off_boundary_space(remaining: str, budget: int) -> int:
    """The fallback (no-breakable-space-within-budget) cut point for
    `_canonical_lines`, walked back off `budget` while `remaining[cut]` is
    a space.

    `rfind(" ", 0, budget)` only sees indices `< budget`, so a word
    boundary sitting exactly AT `budget` is invisible to it and the naive
    fallback (`cut = budget`) would land right on top of that space --
    stranding it as the first character of the continuation line
    (`remaining[cut:]`). The real directive parser's comment extraction
    (`_strip_comment_delims`) fully `.strip()`s each physical line, so a
    leading space there is silently dropped, concatenating the token
    before and after the boundary with no separator (T-0991). Backing
    `cut` off any such space(s) leaves both `head` (`remaining[:cut]`) and
    `tail` (`remaining[cut:]`) free of an edge space -- it lands safely
    mid-line on the next physical line instead.
    """
    cut = budget
    while cut > 0 and remaining[cut] == " ":
        cut -= 1
    return cut


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
            # frob:ticket T-0991
            # No breakable space within [0, budget) -- break at the budget
            # boundary verbatim, UNLESS `remaining[budget]` is itself a
            # space (one column past `rfind`'s exclusive bound): stranding
            # that as `tail`'s leading char gets silently eaten by the real
            # parser's full-`.strip()` comment extraction, concatenating
            # the two tokens with no separator (T-0991). Walk `cut` back
            # over it so neither `head` nor `tail` carries a boundary
            # space -- see `_shift_cut_off_boundary_space`'s docstring.
            cut = _shift_cut_off_boundary_space(remaining, budget)
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


# frob:ticket T-1987
def _rewrite_directive_run(
    logical_text: str,
    lines: list[str],
    *,
    i: int,
    count: int,
    marker: str,
    indent: str,
    limit: int,
) -> list[str]:
    """One `frob:` directive run's replacement, canonicalized -- the
    per-run body of `_rewrite_lines_via_runs`, split out to keep that
    function's dispatch loop under the ARCH001 line threshold.

    T-0985: a run ending in a `# noqa`/`# noqa: CODE` pragma
    (`_NOQA_SUFFIX_RE`) is left byte-identical, full stop -- never
    force-wrapped, never rewritten. T-1605 previously made this
    "self-retiring": if the reason text (minus the pragma) had a clean
    word-boundary wrap available, that wrap was taken and the `noqa` was
    dropped, on the theory that the pragma was then "never load-bearing".
    T-1987 reverted that: a `frob fmt` rewrap of an already-noqa-suppressed
    single physical line into several physical lines is never harmless
    just because the words happen to break cleanly -- it changes the
    PHYSICAL LINE COUNT of the enclosing function, which line-count-
    sensitive gates like ARCH001 see directly. Two separate real lands
    (T-1970, T-1968) hit exactly this: a WALK001 waiver deliberately kept
    on one noqa-suppressed physical line got auto-expanded to four lines
    mid-land and tripped ARCH001 on the enclosing function. Whether a
    clean wrap exists says nothing about whether physical-line-count
    growth is safe, so `noqa` is now treated as what it always was meant
    to be: an unconditional "leave this run alone" marker, not a ratchet
    to be second-guessed."""
    # `fold_comment_runs` already rstrips "\r" off every constituent line
    # while folding (T-0286's own fold rule), so `logical_text` is always
    # "\r"-free regardless of the run's original convention -- reapply it
    # here, once per run, from the run's FIRST physical line.
    run_had_cr = lines[i].endswith("\r")
    if _NOQA_SUFFIX_RE.search(logical_text) is not None:
        # Deliberate escape hatch (T-0985): pass the run through verbatim,
        # byte-identical, regardless of whether a clean wrap exists.
        return lines[i : i + count]
    canonical = _canonical_lines(
        logical_text, marker=marker, indent=indent, limit=limit
    )
    return [line + "\r" for line in canonical] if run_had_cr else canonical


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
    its T-0441 canonical form (`_rewrite_directive_run`, preserving the
    run's own CR convention), and every other run/line passed through
    verbatim -- the run-rewrite half of `canonicalize_text`, split from
    the marker-scan half that built `runs`/`indents`."""
    out: list[str] = []
    run_idx = 0
    i = 0
    n = len(lines)
    while i < n:
        if run_idx < len(runs) and runs[run_idx][1] == i:
            logical_text, _lineno, _src, count = runs[run_idx]
            run_idx += 1
            if logical_text.strip().startswith("frob:"):
                out.extend(
                    _rewrite_directive_run(
                        logical_text,
                        lines,
                        i=i,
                        count=count,
                        marker=marker,
                        indent=indents[i],
                        limit=limit,
                    )
                )
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
# frob:tests \
# tests/test_gates_fmt_directives.py::TestNoqaAlwaysPreservedT1987.test_wrappable_reaso\
# n_keeps_its_noqa
# frob:tests \
# tests/test_gates_fmt_directives.py::TestNoqaAlwaysPreservedT1987.test_idempotent_with\
# _noqa_kept
# frob:ticket T-0972
# frob:ticket T-0985
# frob:ticket T-1987
def canonicalize_text(text: str, *, path: str, limit: int | None) -> str:
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

    T-1606: `limit=None` means `path`'s language has no configurable width
    at all (`resolve_line_length` returning `None`) -- every directive run
    is folded to its single logical line unconditionally and never wrapped
    on width, via `_EFFECTIVELY_UNLIMITED` so the existing int-only wrap
    math in `_canonical_lines` needs no Optional handling of its own.

    T-0985: a directive run whose logical text ends in a `# noqa`/`# noqa:
    CODE` pragma (`_NOQA_SUFFIX_RE`) is a deliberate escape hatch for
    content that cannot be wrapped without breaking a single unbreakable
    token (e.g. a long dotted pytest node id) -- such a run is left
    byte-identical rather than force-wrapped.
    """
    marker = marker_for(path)
    if marker is None:
        return text
    effective_limit = _EFFECTIVELY_UNLIMITED if limit is None else limit

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
    out = _rewrite_lines_via_runs(
        lines, runs, indents, marker=marker, limit=effective_limit
    )

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
# frob:ticket T-1359
# frob:raises OSError
# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# path.parent.mkdir/tempfile.mkstemp/os.fdopen/os.fsync/os.replace, stdlib calls the \
# resolver's curated table does not cover; every one of them is a genuine OSError \
# source and the function's own except OSError block (and its bare re-raise, now \
# declared via # frob:raises OSError above) is the intended, documented boundary for \
# all of them"
def _write_formatted(path: Path, rewritten: str) -> None:
    """`_format_one_path`'s write half: rewrite `path` in place with
    `rewritten`'s content, `newline=""` preserving whatever CRLF/LF
    convention the caller already decided on (see `format_paths`'s
    docstring for the full rationale).

    T-1359: crash-safe (temp file in the same directory + `fsync` +
    `os.replace`), the same house pattern
    `frob.tickets._store.atomic_write` uses -- but that primitive cannot
    be reused directly here since it has no `newline=""` opt-out, and
    losing it would silently re-translate a CRLF-authored file's line
    endings on every `frob fmt` run (the exact T-0441 regression
    `format_paths`'s docstring already documents). A process killed
    mid-write now leaves the ORIGINAL file intact rather than truncated
    or garbled, matching T-1348's FMT001-adjacent Tier-A handlers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(rewritten)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except OSError:
        _log.error("format_paths: atomic write to %s failed", path, exc_info=True)
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


# frob:ticket T-0979
def _relpath_for_change(path: Path, root: Path) -> str:
    """`_format_one_path`'s reported-path half: `path` relative to `root`
    when possible, else `path` unchanged -- the display string an
    `FmtChange` carries."""
    if path.is_relative_to(root):
        return str(path.relative_to(root))
    return str(path)


#: T-2298: a `.strata` file under a `tests/` root is a test INPUT --
#: `tests/unit/strata/litmus/*.strata` and
#: `tests/fixtures/**/*.strata` are both real, measured incidents of a
#: broad `frob fmt` rewriting a corpus a test asserts byte-for-byte
#: against. `.strata` files OUTSIDE `tests/` (`design/frob.strata`,
#: `design/litmus/*.strata`) are genuine project source and stay in scope.
_TEST_CORPUS_SUFFIXES = frozenset({".strata"})


def _is_test_corpus_path(rel_path: str) -> bool:
    """True if `rel_path` (root-relative, POSIX-separated) is a test-input
    corpus file `format_paths` must not rewrite unless
    `include_test_corpora=True` (T-2298): a `tests/` root component
    combined with one of `_TEST_CORPUS_SUFFIXES`. Scoped to `tests/`
    specifically -- a broad "any fixture-shaped path" rule would also
    catch legitimate source under an unrelated `fixtures`-named directory
    outside the test tree, which is not this bug."""
    if Path(rel_path).suffix not in _TEST_CORPUS_SUFFIXES:
        return False
    parts = Path(rel_path).parts
    return "tests" in parts


# frob:ticket T-0979
# frob:ticket T-2298
def _format_one_path(
    path: Path,
    root: Path,
    *,
    limit: int | None,
    check_only: bool,
    include_test_corpora: bool,
) -> "FmtChange | None":
    """`format_paths`'s per-file half: canonicalize `path` (skipping an
    unsupported language, an unreadable file, or -- unless
    `include_test_corpora` -- a test-input corpus file per
    `_is_test_corpus_path`, T-2298), returning its `FmtChange` if it is not
    already canonical, and -- unless `check_only` -- rewriting it in place.
    See `format_paths`'s own docstring for the CRLF-preserving `newline=""`
    rationale this shares.

    T-1606: `limit=None` means "resolve `path`'s own language-specific
    width via `resolve_line_length`" -- `format_paths` passes `None`
    through per file precisely so each file gets ITS OWN language's width,
    never a single value pinned for the whole walk; a caller wanting the
    pre-T-1606 uniform behavior still can by resolving its own limit and
    passing an int here."""
    if not include_test_corpora and _is_test_corpus_path(
        _relpath_for_change(path, root)
    ):
        _log.debug("format_paths: skipping test-corpus file %s", path)
        return None
    original = _read_source_for_format(path)
    if original is None:
        return None
    resolved_limit = limit if limit is not None else resolve_line_length(path, root)
    rewritten = canonicalize_text(original, path=str(path), limit=resolved_limit)
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
def format_paths(
    root: Path,
    *,
    check_only: bool,
    limit: int | None = None,
    include_test_corpora: bool = False,
) -> FmtReport:
    """Canonicalize every `frob:` directive comment under `root` (a repo
    root or a single file), skipping the usual excluded/pruned dirs via
    `frob.excludes.iter_files`.

    In `check_only` mode, nothing is written -- `FmtReport.changes` lists
    every file that is NOT already canonical (this is what `frob check`'s
    remediation hint is built from). Otherwise, each non-canonical file is
    rewritten in place.

    T-1606: `limit` defaults to `None`, which means EACH FILE resolves its
    OWN width via `resolve_line_length` (Rust's rustfmt config, TS/JS's
    prettier config, C-family's clang-format config, or `None` outright
    for a formatter with no width concept) -- a single walk over `root`
    can span several languages, each wrapped against its own tool's limit
    rather than one pinned-for-the-whole-walk number. Passing an explicit
    `limit` overrides this per-file resolution uniformly for every file in
    the walk (the pre-T-1606 behavior, still used by tests and by
    anything that genuinely wants one number everywhere).

    T-2298: `include_test_corpora=False` (the default) skips any file
    `_is_test_corpus_path` flags -- a `.strata` file under `tests/`. A real
    incident landed here: `frob fmt .` with a broad path rewrote 49
    unrelated `.strata` fixture files in one run. A fixture is a test
    INPUT; a formatter rewriting one can silently change what a test
    asserts against while every gate still reads green, and the diff looks
    like routine formatting so a reviewer skims past it. Pass
    `include_test_corpora=True` (CLI: `--include-test-corpora`) to opt
    back into the old unscoped behavior when a corpus file's own
    formatting genuinely needs fixing.

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

    # T-2298: a single FILE named explicitly as `root` is a deliberate,
    # scoped target -- the corpus exclusion only applies to a BROAD path's
    # expanded walk (`iter_files`), never to "the caller asked for exactly
    # this file". `format_paths(a_fixture_path, ...)` still formats it.
    explicit_single_file = root.is_file()
    paths = (root,) if explicit_single_file else iter_files(root)
    changes: list[FmtChange] = []
    for path in paths:
        change = _format_one_path(
            path,
            root,
            limit=limit,
            check_only=check_only,
            include_test_corpora=include_test_corpora or explicit_single_file,
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
    "resolve_line_length",
]
