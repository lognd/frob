"""Pure touched-set test selection (docs/testing.md's Selection algorithm).

`select_tests` never touches the filesystem or spawns a process -- it is a
function of a `GraphSnapshot` and a `Diff`, so it is trivially unit-tested
and safe to call speculatively (e.g. `--dry-run`).
"""

from __future__ import annotations

from pathlib import PurePosixPath

from frob.gitio import Diff, Hunk
from frob.graph import EdgeKind, GraphSnapshot, SymbolRecord
from frob.logging import get_logger
from frob.testing._models import SelectConfig, SelectionReport

_log = get_logger(__name__)

# Mirrors frob.lang._EXTENSION_TABLE's extension -> language-label mapping
# (documented duplicate, same posture as frob.graph's _SOURCE_EXTENSIONS: adding a
# public extension-listing API to frob.lang for these two callers was judged out of
# scope). Test-file extensions map onto the SAME labels frob.lang.parse_file uses.
_EXTENSION_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".hh": "cpp",
}

# The all-suite sentinel `run_selected` recognizes in a language's selected tuple:
# render `all_command` instead of the placeholder-rendered `command`.
ALL_SENTINEL = "*"


# frob:doc docs/testing.md#public-api
def extension_language(path: str) -> str | None:
    """The `frob.lang` language label for `path`'s extension, or `None` if unknown."""
    suffix = PurePosixPath(path).suffix.lower()
    return _EXTENSION_LANGUAGE.get(suffix)


def _is_test_file(path: str) -> bool:
    """True if `path` is itself a test file by name or by a `tests/` dir component."""
    pure = PurePosixPath(path)
    if "tests" in pure.parts[:-1]:
        return True
    name = pure.stem
    return (
        name.startswith("test_")
        or name.endswith("_test")
        or ".test" in pure.name
        or "_test." in pure.name
    )


def _overlaps(hunk_span: tuple[int, int], sym_span: tuple[int, int]) -> bool:
    """True if two inclusive 1-indexed line ranges intersect."""
    return hunk_span[0] <= sym_span[1] and sym_span[0] <= hunk_span[1]


def _enclosing_class_symref(symbol: SymbolRecord) -> str | None:
    """`path::Parent` for a dotted qualname, else `None` (no enclosing symbol)."""
    qualname = symbol.id.qualname
    if "." not in qualname:
        return None
    parent, _, _ = qualname.rpartition(".")
    return f"{symbol.id.path}::{parent}"


# frob:doc docs/testing.md#public-api
def select_tests(
    snapshot: GraphSnapshot, diff: Diff, cfg: SelectConfig
) -> SelectionReport:
    """Resolve `diff`'s hunks against `snapshot` into a `SelectionReport` (pure)."""
    hunks_by_file: dict[str, list[Hunk]] = {}
    for hunk in diff.hunks:
        hunks_by_file.setdefault(hunk.file, []).append(hunk)

    touched_files = set(hunks_by_file)

    touched_symbols: set[str] = set()
    for symbol in snapshot.symbols.values():
        for hunk in hunks_by_file.get(symbol.id.path, ()):
            if _overlaps(hunk.span, symbol.span):
                touched_symbols.add(symbol.symref)
                break

    ripple: set[str] = set()
    for edge in snapshot.edges:
        if edge.kind == EdgeKind.USES_CONTRACT and edge.target in touched_symbols:
            ripple.add(edge.src)
    all_touched_symbols = touched_symbols | ripple

    enclosing_by_symref = {
        symref: _enclosing_class_symref(snapshot.symbols[symref])
        for symref in all_touched_symbols
        if symref in snapshot.symbols
    }
    files_of_touched_symbols = {
        snapshot.symbols[symref].id.path
        for symref in all_touched_symbols
        if symref in snapshot.symbols
    }

    selected: dict[str, set[str]] = {}
    bound_files: set[str] = set()

    def _add_selected(edge_src: str) -> None:
        """Group `edge_src` (a test's own symref/file) under its own language."""
        file_part = edge_src.split("::", 1)[0]
        language = extension_language(file_part)
        if language is None:
            _log.warning("select_tests: no language for test src %r", edge_src)
            return
        selected.setdefault(language, set()).add(edge_src)

    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        target = edge.target
        matched = target in all_touched_symbols
        if not matched:
            matched = any(
                enclosing_by_symref.get(symref) == target
                for symref in all_touched_symbols
            )
        if not matched and "::" not in target:
            if target in files_of_touched_symbols or target in touched_files:
                matched = True
            elif any(
                file.startswith(target.rstrip("/") + "/")
                for file in files_of_touched_symbols | touched_files
            ):
                matched = True
        if matched:
            _add_selected(edge.src)
            bound_files.update(files_of_touched_symbols)

    for file in touched_files:
        if _is_test_file(file):
            _add_selected(file)
            bound_files.add(file)

    unbound: list[str] = []
    for file in sorted(touched_files):
        if file in bound_files or _is_test_file(file):
            continue
        has_selected = any(
            edge.kind == EdgeKind.TESTS
            and (
                edge.target in all_touched_symbols
                or edge.target == file
                or file.startswith(edge.target.rstrip("/") + "/")
            )
            for edge in snapshot.edges
        )
        if has_selected:
            continue
        unbound.append(file)
        language = extension_language(file)
        if language is None:
            _log.warning("select_tests: unbound file %r has unknown language", file)
            continue
        if cfg.fallback == "package":
            package = str(PurePosixPath(file).parent)
            selected.setdefault(language, set()).add(package)
            _log.info("select_tests: fallback=package for %s -> %s", file, package)
        elif cfg.fallback == "suite":
            selected.setdefault(language, set()).add(ALL_SENTINEL)
            _log.info("select_tests: fallback=suite for %s -> all_command", file)
        elif cfg.fallback == "warn":
            _log.warning("select_tests: unbound file %s, fallback=warn (skipped)", file)
        else:
            _log.warning("select_tests: unknown fallback mode %r", cfg.fallback)

    touched = tuple(sorted(all_touched_symbols | touched_files))
    report = SelectionReport(
        touched=touched,
        selected={lang: tuple(sorted(ids)) for lang, ids in selected.items()},
        ripple=tuple(sorted(ripple)),
        unbound=tuple(unbound),
        fallback=cfg.fallback,
    )
    _log.info(
        "select_tests: touched=%d ripple=%d selected_langs=%d unbound=%d",
        len(touched),
        len(ripple),
        len(selected),
        len(unbound),
    )
    return report


__all__ = ["ALL_SENTINEL", "extension_language", "select_tests"]
