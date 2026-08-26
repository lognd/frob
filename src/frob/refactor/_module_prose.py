"""Non-Python reference surfaces for `frob refactor move-module`
(T-2990): the module PATH is what these are keyed on, not any single
symbol, so they are scanned once per module move rather than delegated
to the Python AST adapter.

Covers, in one pass over every non-`.py` text file plus every `.py`
file's own comment/docstring text (deliberately OUTSIDE the AST scan in
`_module_scan_python.py`, which never touches either):

- `frob.toml` dotted `module:symbol`/`module` config string values.
- `design/**/*.strata` `code="<path>"` bindings.
- `frob:doc`/`frob:tests`/`frob:ticket` comment-directive path citations
  (both inside `.py` files and in `tickets/**/ticket.md`).
- `tickets/**/ticket.md` (and the legacy `tickets.md`) `scope` glob
  citations.
- `docs/**/*.md` prose mentioning either spelling.

WORD-BOUNDARY MATCHING, NOT SUBSTRING: every occurrence check below
requires the matched token be flanked by non-identifier characters (see
`_token_spans`) -- `frob.yaml_io` never matches inside `frob.yaml_io_
extra` (the char right after the match, `_`, is a word character, so
the boundary check rejects it) or `frob.yaml_iomodel` (`m` rejects it
the same way). This is the module-move verb's must-NOT-fire guard
(T-2990 acceptance): a prefix-colliding sibling module's name is never
touched, and neither is a prose mention that merely CONTAINS the token
as a sub-word (there is no such thing as a partial word-boundary
match by construction). A prose occurrence that is not a reference at
all -- one that never spells the literal dotted path or file path --
is likewise never touched, because nothing here does semantic/fuzzy
matching: only an EXACT, boundary-delimited token match is rewritten.
"""

from __future__ import annotations

from pathlib import Path

from frob.excludes import walk_pruned
from frob.logging import get_logger
from frob.refactor._models import RewriteOp

_log = get_logger(__name__)

__all__ = ["scan_module_path_citations"]

#: File extensions this scan treats as text worth checking for a literal
#: module/path citation -- deliberately excludes `.py` (the AST scanner
#: owns Python import statements; this module only adds the comment/
#: docstring text AST never looks at, handled separately below) and any
#: binary-shaped extension.
_TEXT_EXTENSIONS = frozenset(
    {".md", ".toml", ".strata", ".yaml", ".yml", ".cfg", ".ini"}
)


def _is_word_char(ch: str) -> bool:
    """`True` for a character that continues an identifier-ish token --
    the boundary test every match below is anchored on."""
    return ch.isalnum() or ch == "_"


def _token_spans(line: str, token: str, *, path_like: bool) -> list[int]:
    """Every start index in `line` where `token` occurs as a whole token
    -- the character immediately before must not be an identifier
    character (and, for a path-like token, also not `/`), and the
    character immediately after must not be an identifier character.
    This is the exact-boundary guard the module docstring describes."""
    spans: list[int] = []
    start = 0
    while True:
        idx = line.find(token, start)
        if idx == -1:
            break
        before_ok = idx == 0 or not (
            _is_word_char(line[idx - 1]) or (path_like and line[idx - 1] == "/")
        )
        after_idx = idx + len(token)
        after_ok = after_idx >= len(line) or not _is_word_char(line[after_idx])
        if before_ok and after_ok:
            spans.append(idx)
        start = idx + 1
    return spans


def _rewrite_line(line: str, spans: list[int], old_len: int, replacement: str) -> str:
    """`line` with every span in `spans` (rightmost first, so earlier
    offsets never shift) replaced by `replacement`."""
    for idx in sorted(spans, reverse=True):
        line = line[:idx] + replacement + line[idx + old_len :]
    return line


def _scan_file_for_tokens(
    file_path: Path,
    old_module: str,
    new_module: str,
    old_rel_path: str,
    new_rel_path: str,
    *,
    comment_only: bool,
) -> list[RewriteOp]:
    """One file's line-by-line scan: the file-path token (checked first,
    since it is the more specific/longer spelling and may itself embed
    the dotted module as a substring) then the dotted-module token,
    each independently boundary-checked via `_token_spans`.
    `comment_only=True` restricts matching to lines that look like a
    `#`/`//`-prefixed comment or a `frob:*` directive -- used for `.py`
    files, where the AST scanner already owns every real import
    statement and this pass must never touch code, only the directive/
    comment text the AST scanner does not see."""
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    ops: list[RewriteOp] = []
    for i, line in enumerate(lines):
        if comment_only:
            stripped = line.lstrip()
            if not (stripped.startswith("#") or "frob:" in line):
                continue
        path_spans = _token_spans(line, old_rel_path, path_like=True)
        new_line = _rewrite_line(line, path_spans, len(old_rel_path), new_rel_path)
        mod_spans = _token_spans(new_line, old_module, path_like=False)
        final_line = _rewrite_line(new_line, mod_spans, len(old_module), new_module)
        if final_line != line:
            ops.append(
                RewriteOp(
                    file_path=str(file_path),
                    start_line=i + 1,
                    end_line=i + 1,
                    old_text=line,
                    new_text=final_line,
                    reason=(
                        f"path/module citation {old_module} -> {new_module} "
                        f"({old_rel_path} -> {new_rel_path})"
                    ),
                )
            )
    return ops


def _iter_candidate_files(repo_root: Path):
    """Every non-`.py` text file worth checking, plus every `.py` file
    (for its comment/directive text only) -- routed through
    `frob.excludes.walk_pruned` (T-1478, WALK001), the same pruned
    repo-wide walk `_scan.find_python_files`/`_repointer.py` already
    reuse, rather than a second hand-rolled directory walk."""
    for path in walk_pruned(repo_root):
        if path.suffix == ".py":
            yield path, True
        elif path.suffix in _TEXT_EXTENSIONS:
            yield path, False


# frob:doc docs/commands/refactor.md#scan_module_path_citations
# frob:tests tests/test_refactor.py::TestModuleProse.test_rewrites_frob_toml_dotted_ref
# frob:tests tests/test_refactor.py::TestModuleProse.test_leaves_prefix_colliding_sibling_untouched  # noqa: E501
# frob:tests \
# tests/test_refactor.py::TestModuleProse.test_leaves_unrelated_prose_untouched
def scan_module_path_citations(
    repo_root: Path,
    old_module: str,
    new_module: str,
    old_rel_path: str,
    new_rel_path: str,
) -> tuple[list[RewriteOp], list[str]]:
    """Repo-wide, boundary-safe literal citation scan for `old_module`
    (dotted) and `old_rel_path` (repo-relative file path) across
    `frob.toml`, `design/**/*.strata`, `docs/**/*.md`, `tickets/**` (both
    `ticket.md` per-ticket files and the legacy `tickets.md`/`tickets-
    archive.md` aggregators), and every `.py` file's own comment/
    directive lines. Returns `(ops, unresolved)`; `unresolved` is always
    empty today -- every match this scan makes it can also rewrite, so
    there is nothing partial to disclose (kept in the return shape for
    parity with every other scan function in this package)."""
    ops: list[RewriteOp] = []
    for file_path, comment_only in _iter_candidate_files(repo_root):
        ops.extend(
            _scan_file_for_tokens(
                file_path,
                old_module,
                new_module,
                old_rel_path,
                new_rel_path,
                comment_only=comment_only,
            )
        )
    _log.info(
        "refactor.module_prose: %s -> %s: %d citation op(s)",
        old_module,
        new_module,
        len(ops),
    )
    return ops, []
