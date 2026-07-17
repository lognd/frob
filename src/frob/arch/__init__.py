"""frob.arch -- lightweight architectural analysis (docs/modules/arch.md).

`analyze_project` walks a repo and flags long functions, god classes, deep
nesting, high coupling, large files, and shared-signature abstraction
opportunities. The per-language rule sets live in cohesive submodules
(`_python`, `_cpp`); this package module owns file collection, the
language-agnostic large-file check, and the orchestration that fans each
parsed file out to its language's checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from frob.arch import _cpp, _python
from frob.arch._models import (
    ArchCategory,
    ArchResult,
    ArchSeverity,
    ArchSuggestion,
)
from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "ArchCategory",
    "ArchResult",
    "ArchSeverity",
    "ArchSuggestion",
    "analyze_project",
]


def _is_skip_dir(name: str) -> bool:
    # frob:ticket T-0026
    return is_skipped_dir(name)


def _collect_files(root: Path) -> list[Path]:
    # frob:ticket T-0026
    exclude_globs = load_exclude_globs(root)
    result: list[Path] = []
    for p in root.rglob("*"):
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        if any(_is_skip_dir(part) for part in rel.parts):
            continue
        if exclude_globs and is_excluded(rel.as_posix(), exclude_globs):
            continue
        if p.is_file():
            result.append(p)
    return result


def _check_large_file(
    rel: str,
    lines: list[bytes],
    max_file_lines: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag a file whose line count exceeds `max_file_lines` (any language)."""
    n = len(lines)
    if n > max_file_lines:
        out.append(
            ArchSuggestion(
                file=rel,
                category="large-file",
                severity="info",
                message=f"file has {n} lines (threshold: {max_file_lines})",
            )
        )


@dataclass(frozen=True)
class _Limits:
    """The five architectural thresholds, bundled so per-file analysis takes
    one argument instead of five parallel ints."""

    max_function_lines: int
    max_class_methods: int
    max_local_imports: int
    max_nesting_depth: int
    max_file_lines: int


def _analyze_one_file(
    path: Path,
    root: Path,
    limits: _Limits,
    suggestions: list[ArchSuggestion],
    all_py_sigs: list[tuple[str, str, tuple[str, ...], str]],
) -> None:
    """Run every applicable check on one file, appending to `suggestions`
    and accumulating python signatures for the cross-file pass."""
    from frob.lang import raw_tree

    try:
        rel = str(path.relative_to(root))
    except ValueError:
        return
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _log.debug("arch: cannot read %s: %s", rel, exc)
        return

    _check_large_file(rel, raw.splitlines(), limits.max_file_lines, suggestions)

    parsed = raw_tree(path)
    if parsed.is_err:
        _log.debug("arch: %s not parsed (%s)", rel, parsed.err)
        return
    tree, _source, language = parsed.danger_ok

    if language == "python":
        _run_python_checks(tree, path, rel, root, limits, suggestions, all_py_sigs)
    elif language == "cpp":
        _cpp._check_long_functions(tree, rel, limits.max_function_lines, suggestions)
        _cpp._check_god_classes(tree, rel, limits.max_class_methods, suggestions)


def _run_python_checks(
    tree: object,
    path: Path,
    rel: str,
    root: Path,
    limits: _Limits,
    suggestions: list[ArchSuggestion],
    all_py_sigs: list[tuple[str, str, tuple[str, ...], str]],
) -> None:
    """Every python architectural check on one parsed file, plus signature
    accumulation for the cross-file abstraction pass."""
    _python._check_long_functions(tree, rel, limits.max_function_lines, suggestions)
    _python._check_god_classes(tree, rel, limits.max_class_methods, suggestions)
    _python._check_high_coupling(path, rel, root, limits.max_local_imports, suggestions)
    _python._check_deep_nesting(tree, rel, limits.max_nesting_depth, suggestions)
    all_py_sigs.extend(_python._extract_signatures(tree, rel))


# frob:doc docs/modules/arch.md#public-api
def analyze_project(
    root: Path,
    *,
    max_function_lines: int = 30,
    max_class_methods: int = 12,
    max_local_imports: int = 8,
    max_nesting_depth: int = 4,
    max_file_lines: int = 500,
) -> ArchResult:
    from frob.logging.quiet import quiet_stdout_logs

    limits = _Limits(
        max_function_lines=max_function_lines,
        max_class_methods=max_class_methods,
        max_local_imports=max_local_imports,
        max_nesting_depth=max_nesting_depth,
        max_file_lines=max_file_lines,
    )
    suggestions: list[ArchSuggestion] = []
    all_py_sigs: list[tuple[str, str, tuple[str, ...], str]] = []

    # frob.lang logs at INFO/DEBUG per parse; CLI callers piping `--json`
    # need that off stdout, same reasoning as frob.logging.quiet's docstring.
    with quiet_stdout_logs():
        for path in _collect_files(root):
            _analyze_one_file(path, root, limits, suggestions, all_py_sigs)

    _python._check_abstraction_opportunities(all_py_sigs, suggestions)
    return ArchResult(root=str(root), suggestions=suggestions)
