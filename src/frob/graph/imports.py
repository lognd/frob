"""File-level RESOLVED-import edge substrate (docs/modules/graph.md#import-graph).

Prerequisite for T-1665 (filed as T-1985): answers "does file Y import
module X, resolved to a real tracked file" -- a question no existing
`frob.graph`/`frob.lang` facility answers today. `frob.graph._models.
EdgeKind` only models `frob:`-directive edges; `frob.graph.callgraph`
deliberately excludes public/exported symbols and resolves calls, not
imports (see that module's docstring). This module is new, narrow
infrastructure: given a set of tracked repo-relative file paths, compute
`importer file -> resolved imported file(s)` edges, plus an explicit,
counted set of imports this substrate could not resolve.

DISCLOSED SCOPE (read before using this for anything): **Python only**,
v1. Every other language `frob.lang` parses (Rust, C, C++, TypeScript,
Kotlin, Strata) is out of scope for this module and contributes nothing
to `ImportGraph.edges` -- a non-`.py` file is neither silently skipped
nor silently counted as resolved; it is recorded once as an
`UnresolvedImport` with `reason="unsupported-language"` per file, so its
absence is visible in a resolved/unresolved measurement rather than
looking identical to "this file imports nothing" (T-1664's own point:
"I cannot analyse this" and "nothing found" must never collapse into the
same silent zero).

Python resolution uses the real `ast` module (stdlib), not `frob.lang`'s
tree-sitter walkers -- `frob.lang.RawSymbol` has no import-statement
extraction at all today (adding one is `frob.lang` scope, not this
ticket's), and Python's own grammar-correct parser is a strictly more
precise resolver than a regex/token scan for this one language: it finds
every `import`/`from ... import` statement regardless of nesting (inside
`if`/`try`/`TYPE_CHECKING` guards -- a real strength over a textual scan,
which cannot distinguish those from prose mentioning the same name), and
never mistakes a look-alike string or comment for an import.

Resolution rule (`_resolve_module`): a dotted module name resolves to a
tracked file if, after stripping this repo's own `src/` source-root
prefix, the dotted name (or a `__init__`-package form of it) matches a
tracked file's own derived module name. A `from X import Y` statement
resolves an edge to `X.Y` if THAT is itself a tracked file (the common
`from . import submodule` / `from pkg import submodule` shape, e.g. a
package `__init__.py` re-exporting its own submodules) -- an
unambiguous check, since it only fires when a real tracked file exists
at that exact dotted path -- and otherwise falls back to resolving `X`
itself (`Y` is an attribute/class/function/constant defined inside `X`,
which only `frob.lang`-level symbol resolution, out of scope here, could
further distinguish; the file-level edge to X is correct and fully
specified regardless). A star-import (`from X import *`) always takes
the `X`-fallback path (no explicit names to check as submodules) -- the
imported MODULE is still X, resolved the same way, whatever names X
re-exports.

An import that is syntactically real but names something outside this
repo's tracked file set (a stdlib or third-party import, e.g. `import
os`) is neither a resolved edge nor an `UnresolvedImport` -- it is
correctly and completely out of this substrate's domain (nothing here is
ambiguous or unanalysable about it), and is counted separately
(`ImportGraph.external_count`) purely for measurement transparency, never
folded into either the resolved or the unresolved tally.

`UnresolvedImport` is used, never a silent drop, for every case this
module KNOWS it cannot answer: a dynamic import (`importlib.
import_module(...)`, bare `__import__(...)`), a relative import whose
`level` walks above this repo's own root, a file that fails to parse at
all (`SyntaxError`), and any non-Python file (see above). This directly
reuses T-1664's `Severity.UNRESOLVED` DISTINCTION (a third outcome, not a
severity tier) -- not `frob.gates.Severity` itself, which this module
cannot import (`frob.gates` depends on `frob.graph`, never the reverse;
importing it here would be circular) -- so a future `frob.gates` consumer
maps `UnresolvedImport` onto `Severity.UNRESOLVED` at its own call site
instead of this substrate inventing a second, divergent "can't tell"
concept.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

__all__ = [
    "ImportGraph",
    "UnresolvedImport",
    "build_import_graph",
]

_PYTHON_SUFFIX = ".py"
# frob:ticket T-1985
# The source-root prefixes this repo's own dotted-module resolution
# strips before matching a tracked file's derived module name -- "src/"
# for this repo's own setuptools `where = ["src"]` src-layout (see
# pyproject.toml's `[tool.setuptools]`), plus the bare root ("") for a
# tracked file with no such prefix at all (e.g. a top-level script).
# DISCLOSED: hard-coded to this repo's own layout, not a generic
# multi-root resolver -- a consumer embedding this module in a different
# repo layout is future work, not silently assumed to work today.
_SOURCE_ROOTS = ("src/", "")


# frob:doc docs/modules/graph.md#import-graph
# frob:ticket T-1985
class UnresolvedImport(BaseModel):
    """One import this substrate KNOWS it could not resolve to a tracked
    file, T-1664's UNRESOLVED posture applied to import resolution:
    never a silent drop, always a counted, reasoned record. `reason` is
    one of `"dynamic-import"` (an `importlib.import_module`/`__import__`
    call, whose target is a runtime value, not a static name),
    `"relative-import-above-root"` (a `from . import x`-style import
    whose `level` walks above this repo's own tracked root),
    `"parse-error"` (the importer file is not valid Python at all), or
    `"unsupported-language"` (the importer file is not Python -- see
    `build_import_graph`'s module docstring for this module's disclosed
    v1 scope). `module` is the best-effort raw text identifying what
    could not be resolved (a dotted module name, or the literal call
    text for a dynamic import); empty string for `"unsupported-
    language"`/`"parse-error"`, where no single module name applies."""

    model_config = ConfigDict(frozen=True)

    importer: str
    module: str
    reason: str


# frob:doc docs/modules/graph.md#import-graph
# frob:ticket T-1985
class ImportGraph(BaseModel):
    """File-level resolved-import edges plus the honest unresolved/
    external counts alongside them (see `build_import_graph`'s module
    docstring for the full resolution contract and disclosed scope).

    `edges[importer]` is every tracked file `importer` resolves an
    import to, deduplicated and sorted -- never `importer` itself (a
    module never "imports" its own file under this resolution rule).
    `unresolved` is every `UnresolvedImport` this build recorded, in
    file-then-source-order. `external_count` is the number of
    syntactically real imports that named something outside this
    repo's tracked file set (stdlib/third-party) -- reported for
    measurement transparency only, never counted as resolved or
    unresolved (see module docstring: this is a fully-answered "not in
    this substrate's domain" case, not an unknown)."""

    model_config = ConfigDict(frozen=True)

    edges: Mapping[str, tuple[str, ...]] = {}
    unresolved: tuple[UnresolvedImport, ...] = ()
    external_count: int = 0


def _module_name_of(path: str) -> str | None:
    """The dotted module name a tracked file path resolves as an IMPORT
    TARGET, or `None` if `path` is not a Python file. Strips the first
    matching `_SOURCE_ROOTS` prefix, then converts the remaining POSIX
    path to a dotted name; a `__init__.py` resolves as its OWN PACKAGE's
    dotted name (dropping the trailing `.__init__`), matching Python's
    own import semantics (`import pkg` loads `pkg/__init__.py`)."""
    if not path.endswith(_PYTHON_SUFFIX):
        return None
    rest = path
    for root in _SOURCE_ROOTS:
        if root and path.startswith(root):
            rest = path[len(root) :]
            break
    dotted = rest[: -len(_PYTHON_SUFFIX)].replace("/", ".")
    if dotted.endswith(".__init__"):
        dotted = dotted[: -len(".__init__")]
    return dotted or None


def _build_module_index(paths: Sequence[str]) -> dict[str, str]:
    """`dotted module name -> tracked file path`, over every Python file
    in `paths` (`_module_name_of` applied to each; non-Python paths
    contribute nothing here -- callers handle those via the
    `"unsupported-language"` `UnresolvedImport` path instead)."""
    index: dict[str, str] = {}
    for path in paths:
        dotted = _module_name_of(path)
        if dotted is not None:
            index[dotted] = path
    return index


def _resolve_module(dotted: str, module_index: Mapping[str, str]) -> str | None:
    """`dotted` resolved against `module_index`: an exact match (a module
    or package `__init__`), else `None` if `dotted` names something
    outside the tracked set (external, or a submodule/attribute of a
    resolved package -- see `build_import_graph`'s docstring on `from X
    import Y` only ever resolving `X`, never `Y`)."""
    return module_index.get(dotted)


def _relative_module_name(
    importer: str, module: str | None, level: int
) -> tuple[str | None, bool]:
    """The absolute dotted module name a relative `from . import x` /
    `from .foo import bar` (ast `level >= 1`) resolves to, given the
    IMPORTER's own dotted package. Returns `(None, True)` when `level`
    walks above the importer's own tracked package depth (the
    `"relative-import-above-root"` UNRESOLVED case) -- second element is
    `True` exactly when that happened, so the caller can distinguish it
    from an ordinary external miss.

    T-1665 bug fix: an `__init__.py` importer's `_module_name_of` result
    IS ALREADY its own package's dotted name (that function's own
    docstring: "a `__init__.py` resolves as its OWN PACKAGE's dotted
    name, dropping the trailing `.__init__`") -- unconditionally dropping
    one more component below over-walked one package level for every
    `__init__.py` importer, silently mis-resolving `level=1` relative
    imports inside every package's own `__init__.py` to the PARENT
    package instead of the importer's real one (measured: `frob.
    _cli_parsers.__init__`'s own `from ._design import ...` resolved to
    `frob._design` instead of `frob._cli_parsers._design`, losing the
    edge entirely -- `frob._design` does not exist, so `_resolve_module`
    correctly failed to find it, but for the WRONG reason). The drop-one
    step belongs only to a REGULAR module importer (its trailing
    component is the module itself, not a package)."""
    importer_dotted = _module_name_of(importer) or ""
    parts = importer_dotted.split(".") if importer_dotted else []
    if not parts:
        return (None, True)
    if not importer.endswith("/__init__.py") and importer != "__init__.py":
        # A relative import's implicit base is the IMPORTER's own
        # enclosing package -- one dotted component per `level`, but a
        # REGULAR module's own trailing component (the module itself,
        # not a package) is already outside the package chain, so
        # `level=1` means "my own package", i.e. drop the importer's
        # last component once, then `level - 1` more times.
        parts = parts[:-1]  # importer's own package (level == 1 base)
    drop = level - 1
    if drop > len(parts):
        return (None, True)
    base_parts = parts[: len(parts) - drop] if drop else parts
    if module:
        return (".".join((*base_parts, module)) if base_parts else module, False)
    return (".".join(base_parts) if base_parts else None, False)


def _scan_dynamic_import_calls(tree: ast.AST) -> list[str]:
    """Every `importlib.import_module(...)` / bare `__import__(...)` call
    site's source-unparse text in `tree`, source order -- the
    `"dynamic-import"` UNRESOLVED case (T-1985): the real target is a
    runtime value, not a name this substrate can statically resolve, so
    it is reported UNRESOLVED rather than silently absent."""
    calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_import_module = (
            isinstance(func, ast.Attribute)
            and func.attr == "import_module"
            and isinstance(func.value, ast.Name)
            and func.value.id == "importlib"
        )
        is_dunder_import = isinstance(func, ast.Name) and func.id == "__import__"
        if is_import_module or is_dunder_import:
            try:
                calls.append(ast.unparse(node))
            except Exception:  # noqa: BLE001 -- unparse is best-effort display text only
                calls.append(f"{getattr(func, 'attr', getattr(func, 'id', '?'))}(...)")
    return calls


def _import_from_edges(
    path: str,
    node: ast.ImportFrom,
    module_index: Mapping[str, str],
) -> tuple[list[str], UnresolvedImport | None, int]:
    """One `ast.ImportFrom` node's resolved edges, `UnresolvedImport` (if
    its relative level walks above the tracked root), and external-import
    count -- split out of `_file_import_edges_and_gaps` (ARCH001, T-1985)
    to keep that function a thin per-node dispatch loop."""
    if node.level and node.level > 0:
        dotted, above_root = _relative_module_name(path, node.module, node.level)
        if above_root or dotted is None:
            return (
                [],
                UnresolvedImport(
                    importer=path,
                    module=f"{'.' * node.level}{node.module or ''}",
                    reason="relative-import-above-root",
                ),
                0,
            )
    else:
        dotted = node.module or ""
    base_target = _resolve_module(dotted, module_index)
    # `from X import name` -- `name` may be a SUBMODULE of package X
    # (`X.name` is itself a tracked file, e.g. `from . import b` inside a
    # package's own `__init__.py`) rather than an attribute defined
    # inside X. Checked per-name against `module_index` rather than
    # assumed either way: an unambiguous match (a real tracked file at
    # that dotted path) is resolved to THAT submodule; a name with no
    # such match falls back to resolving X itself (the attribute-import
    # case `build_import_graph`'s docstring already covers).
    submodule_targets = [
        t
        for alias in node.names
        if (t := _resolve_module(f"{dotted}.{alias.name}", module_index)) is not None
    ]
    if submodule_targets:
        return submodule_targets, None, 0
    if base_target is not None:
        return [base_target], None, 0
    return [], None, 1


def _file_import_edges_and_gaps(
    path: str,
    source: str,
    module_index: Mapping[str, str],
) -> tuple[list[str], list[UnresolvedImport], int]:
    """One Python file's resolved import edges, `UnresolvedImport`
    records, and external-import count -- `build_import_graph`'s per-file
    worker, split out to keep that function a thin driving loop."""
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return [], [UnresolvedImport(importer=path, module="", reason="parse-error")], 0

    resolved: list[str] = []
    unresolved: list[UnresolvedImport] = []
    external = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = _resolve_module(alias.name, module_index)
                if target is not None:
                    resolved.append(target)
                else:
                    external += 1
        elif isinstance(node, ast.ImportFrom):
            edges, gap, ext = _import_from_edges(path, node, module_index)
            resolved.extend(edges)
            if gap is not None:
                unresolved.append(gap)
            external += ext

    for call_text in _scan_dynamic_import_calls(tree):
        unresolved.append(
            UnresolvedImport(importer=path, module=call_text, reason="dynamic-import")
        )

    return resolved, unresolved, external


# frob:doc docs/modules/graph.md#import-graph
# frob:ticket T-1985
# frob:ticket T-1665
# T-1665 discharges the WIRE001 waiver this comment used to carry: this
# substrate is now wired into a real production caller,
# frob.gates._refs.ref_gate's resolved-import inbound-reference channel.
# frob:tests tests/test_graph_imports.py::TestBuildImportGraph.test_resolves_a_real_intra_repo_import_edge  # noqa: E501
# frob:tests tests/test_graph_imports.py::TestBuildImportGraph.test_dynamic_import_reports_unresolved_not_dropped  # noqa: E501
# frob:tests tests/test_graph_imports.py::TestBuildImportGraph.test_non_python_file_reports_unsupported_language_unresolved  # noqa: E501
# frob:tests tests/test_graph_imports.py::TestBuildImportGraph.test_stdlib_import_counts_as_external_not_unresolved  # noqa: E501
# frob:tests tests/test_graph_imports.py::TestBuildImportGraph.test_relative_import_resolves_within_package  # noqa: E501
# frob:tests tests/test_graph_imports.py::TestBuildImportGraph.test_star_import_resolves_the_module_not_its_names  # noqa: E501
# frob:tests tests/test_graph_imports.py::TestBuildImportGraph.test_unreadable_file_is_reported_unresolved_not_silently_skipped  # noqa: E501
def build_import_graph(root: Path, paths: Sequence[str]) -> ImportGraph:
    """Build the file-level resolved-import graph over `paths` (repo-root-
    relative POSIX file paths). See this module's own docstring for the
    full resolution contract, the Python-only v1 scope, and what counts
    as resolved vs. `UnresolvedImport` vs. external.

    Every `path` is visited exactly once, Python or not -- a non-Python
    path contributes one `"unsupported-language"` `UnresolvedImport` and
    nothing else; a Python path that fails to even read from disk (I/O
    error, e.g. a path listed but since deleted) contributes one
    `"parse-error"` `UnresolvedImport` rather than being silently
    dropped from the walk."""
    module_index = _build_module_index(paths)
    edges: dict[str, set[str]] = {}
    unresolved: list[UnresolvedImport] = []
    external_count = 0

    for path in paths:
        if not path.endswith(_PYTHON_SUFFIX):
            unresolved.append(
                UnresolvedImport(
                    importer=path, module="", reason="unsupported-language"
                )
            )
            continue
        try:
            source = (root / path).read_text(encoding="utf-8")
        except OSError:
            unresolved.append(
                UnresolvedImport(importer=path, module="", reason="parse-error")
            )
            continue
        resolved, file_unresolved, file_external = _file_import_edges_and_gaps(
            path, source, module_index
        )
        targets = {t for t in resolved if t != path}
        if targets:
            edges[path] = targets
        unresolved.extend(file_unresolved)
        external_count += file_external

    return ImportGraph(
        edges={p: tuple(sorted(v)) for p, v in edges.items()},
        unresolved=tuple(unresolved),
        external_count=external_count,
    )
