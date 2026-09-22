"""NUnit/Unity Test Framework C# test-method node id collection (T-4517,
story T-4516, epic T-4513) -- static source parsing via
`tree-sitter-language-pack`'s bundled `csharp` grammar, mirroring
`_collect_ts.py`'s per-language collector shape (module docstring there):
one self-contained module, re-imported by `_collect.py`/`frob.testing.
__init__` so `from frob.testing import collect_csharp_tests` resolves the
same way every other `collect_*_tests` does. Split out (T-1074-style) as
its own module rather than folded into `_collect.py` for the same
LARGE001/single-language-home reasons the other four collectors were.

WHY STATIC PARSING, NOT A REAL NUNIT RUNNER (unlike `collect_ts_tests`'s
`npx vitest list --json`): there is no npm-equivalent "list tests without
building" command this repo can assume is on PATH for a C#/.NET project --
`dotnet test --list-tests` requires a full build first, the same heavier
"already configured/built" cost `collect_kotlin_tests`'s module docstring
explicitly declines to pay. A source-level scan for the handful of
conventional NUnit/Unity Test Framework attributes is the same restraint
`collect_kotlin_tests` applies to gradle, moved one step earlier (parse
the source directly) since, unlike JVM/gradle, there is no equivalent
"report already exists on disk" fallback to read either.

NODE ID SHAPE: `<path>::<Namespace.Class>::<Method>` (three-part, doubly
`::`-separated -- distinct from `_kotlin_node_id`'s `source::dotted.qualname`
two-part shape) since a bare test method name is rarely unique across a
suite's fixture classes; namespace+class stays one dotted qualname segment
(mirrors `_walk_csharp.py`'s own qualname-joining convention) while the
method is split into its own segment so a `frob:tests` directive reads the
class and method boundary at a glance. A `[TestCase(...)]`-parameterized
method emits exactly ONE node id (parameter sets collapsed) -- NUnit expands
one method into N runtime cases, but frob's evidence-binding story binds to
the SOURCE method, matching how `collect_ts_tests`/`collect_kotlin_tests`
each already bind one node id per source-level test declaration, not one
per parameterized runtime invocation."""
# frob:ticket T-4517
# frob:ticket T-4517
# frob:ticket T-4517

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from tree_sitter import Node, Tree
from tree_sitter_language_pack import get_parser
from typani import Ok
from typani.result import Result

from frob.excludes import load_exclude_globs
from frob.lang._common import _child_text
from frob.logging import get_logger
from frob.testing._models import CollectedTests
from frob.testing._runners import TestingError

_log = get_logger(__name__)

# tree-sitter-language-pack's grammar name for C# (mirrors
# `_walk_csharp.py`'s dispatch-table entry, `frob.lang.__init__`'s
# `".cs": ("csharp", "csharp")`).
_GRAMMAR_NAME = "csharp"

# Cache file, mirroring `_collect_shared.py`'s `_KOTLIN_CACHE_REL`/
# `_TS_CACHE_REL` siblings -- kept local to this module rather than added
# to `_collect_shared.py` since this ticket's declared scope is this file
# alone (T-4517's `frob ticket show` scope list).
_CSHARP_CACHE_REL = Path(".frob") / "csharp-nunit-collect.json"

# The declaration node types that open a new dotted qualname segment,
# mirroring `_walk_csharp.py`'s `_CONTAINER_DECLS`.
_CONTAINER_DECLS = frozenset(
    {"class_declaration", "struct_declaration", "interface_declaration"}
)

# The NUnit/Unity Test Framework attribute names (bare, no leading `[`/
# trailing `Attribute` suffix -- tree-sitter-c-sharp's `attribute` node's
# `identifier` child is already just the bare name written in source,
# verified interactively) that make a method frob:tests-bindable.
# `SetUp`/`TearDown`/`OneTimeSetUp`/`OneTimeTearDown` are deliberately
# absent (the ticket's own exclusion) -- they carry none of these names,
# so no explicit skip is needed, only an allowlist of what counts.
_TEST_ATTRIBUTE_NAMES = frozenset({"Test", "TestCase", "TestCaseSource", "UnityTest"})


# frob:doc docs/modules/testing.md#public-api
# tests/test_testing.py::TestCollectCsharpTests.test_collect_csharp_tests_collects_test_and_unitytest  # noqa: E501
def parse_csharp(source: bytes) -> Tree:
    """Parse C# source bytes into a tree-sitter `Tree` via the language
    pack's bundled `csharp` grammar (mirrors `_walk_kotlin.parse_kotlin`)."""
    parser = get_parser(_GRAMMAR_NAME)
    return parser.parse(source)


def _match_dir_excluded(rel_child: str, glob: str) -> bool:
    """True if `rel_child` (or anything under it) could match `glob` --
    a conservative prefix check so a directory is pruned when its own
    path, or a `**`-style descendant of it, is excluded (mirrors the
    intent of `frob.excludes.is_excluded` without importing its private
    fnmatch internals into this module)."""
    import fnmatch

    return fnmatch.fnmatch(rel_child, glob) or fnmatch.fnmatch(f"{rel_child}/x", glob)


def _find_cs_files(root: Path) -> list[Path]:
    """Every `.cs` file under `root`, exclusions pruned (mirrors
    `_find_ts_test_files`'s bounded walk, but repo-wide like
    `_find_vitest_projects`'s outer walk since C# carries no per-directory
    project marker file this collector needs to discover first)."""
    exclude_globs = load_exclude_globs(root)
    found: list[Path] = []
    # frob:waive WALK001 reason="needs per-directory exclude pruning the file-only iter_files/walk_pruned API cannot express; mirrors _find_vitest_projects/_find_kotlin_gradle_projects's own os.walk shape"  # noqa: E501
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        kept: list[str] = []
        for name in dirnames:
            rel_child = (rel_dir / name).as_posix()
            if exclude_globs and any(
                _match_dir_excluded(rel_child, glob) for glob in exclude_globs
            ):
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in filenames:
            if name.endswith(".cs"):
                found.append(Path(dirpath) / name)
    return sorted(found)


def _cs_attribute_names(node: Node) -> set[str]:
    """Bare attribute names (`Test`, `TestCase(1,2)` -> `TestCase`, ...)
    directly attached to `node` (a `method_declaration`) via one or more
    leading `attribute_list` children."""
    names: set[str] = set()
    for child in node.children:
        if child.type != "attribute_list":
            continue
        for attr in child.children:
            if attr.type != "attribute":
                continue
            name_node = attr.child_by_field_name("name")
            if name_node is None:
                # positional fallback: the grammar's `attribute` node did
                # not expose a "name" field in the pinned grammar version
                # -- take its first `identifier`/`qualified_name` child.
                name_node = next(
                    (
                        c
                        for c in attr.children
                        if c.type in ("identifier", "qualified_name")
                    ),
                    None,
                )
            text = _child_text(name_node)
            if text:
                # a qualified attribute (`NUnit.Framework.Test`) -- only
                # the last dotted segment is the conventional bare name.
                names.add(text.rsplit(".", 1)[-1])
    return names


def _cs_test_methods(container: Node, stack: tuple[str, ...]) -> list[tuple[str, ...]]:
    """Every `(*stack, method_name)` qualname tuple for a test-attributed
    method found under `container`, descending through namespaces and
    class/struct/interface bodies exactly like `_walk_csharp._cs_visit`
    (this module's own copy: importing `_walk_csharp`'s private recursion
    would couple a RawSymbol-shaped walker to a collector that needs no
    RawSymbol at all, and this ticket's declared scope is this file
    alone)."""
    found: list[tuple[str, ...]] = []
    active_stack = stack
    for node in container.children:
        if node.type == "file_scoped_namespace_declaration":
            name_node = node.child_by_field_name("name")
            name = _child_text(name_node)
            active_stack = (*stack, name) if name else stack
            continue
        found.extend(_cs_dispatch_test_methods(node, active_stack))
    return found


def _cs_dispatch_test_methods(
    node: Node, stack: tuple[str, ...]
) -> list[tuple[str, ...]]:
    """One node's contribution to `_cs_test_methods`: a test-attributed
    method under `stack`, or a recursive descent into a namespace/
    container body."""
    if node.type in _CONTAINER_DECLS:
        name_node = node.child_by_field_name("name")
        body = node.child_by_field_name("body")
        name = _child_text(name_node)
        if name and body is not None:
            # frob:invariant terminates reason="body is node's own body field child, a proper descendant of node, which is itself a child of the container passed in by the caller" measure="container's subtree depth strictly decreases"  # noqa: E501
            return _cs_test_methods(body, (*stack, name))
        return []
    if node.type == "namespace_declaration":
        name_node = node.child_by_field_name("name")
        body = node.child_by_field_name("body")
        name = _child_text(name_node)
        if body is not None:
            return _cs_test_methods(body, (*stack, name) if name else stack)
        return []
    if node.type == "method_declaration" and stack:
        if _cs_attribute_names(node) & _TEST_ATTRIBUTE_NAMES:
            name_node = node.child_by_field_name("name")
            method_name = _child_text(name_node)
            if method_name:
                return [(*stack, method_name)]
        return []
    return []


def _cs_node_id(root: Path, cs_path: Path, qualname: tuple[str, ...]) -> str:
    """`<relpath>::<Namespace.Class>::<Method>` (module docstring's node id
    shape) from a `(*namespace/class segments, method)` qualname tuple."""
    rel = cs_path.resolve().relative_to(root.resolve()).as_posix()
    *class_parts, method = qualname
    return f"{rel}::{'.'.join(class_parts)}::{method}"


def _collect_cs_file(root: Path, cs_path: Path) -> list[str]:
    """Every test node id found in one `.cs` file, `[]` (with a warning,
    never a hard failure) on an unreadable file or a parse tree that
    carries an `ERROR` node -- mirrors `_parse_junit_xml`'s "one bad file
    never fails the whole collection" posture, applied to a source parse
    instead of an XML parse."""
    try:
        source = cs_path.read_bytes()
    except OSError as exc:
        _log.warning("collect_csharp_tests: could not read %s: %s", cs_path, exc)
        return []
    tree = parse_csharp(source)
    if tree.root_node.has_error:
        _log.warning(
            "collect_csharp_tests: %s did not parse cleanly, best-effort scan anyway",
            cs_path,
        )
    node_ids: list[str] = []
    for qualname in _cs_test_methods(tree.root_node, ()):
        node_ids.append(_cs_node_id(root, cs_path, qualname))
    return node_ids


def _csharp_content_key(root: Path, cs_files: list[Path]) -> str:
    """Sha256 over every discovered `.cs` file's `(relpath, sha256)` pair --
    the cache key (mirrors `_ts_content_key`/`_kotlin_content_key`)."""
    hasher = hashlib.sha256()
    for path in sorted(set(cs_files)):
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            _log.warning("collect_csharp_tests: could not read %s: %s", path, exc)
            continue
        rel = path.resolve().relative_to(root.resolve()).as_posix()
        hasher.update(f"{rel}:{digest}\n".encode())
    return hasher.hexdigest()


def _load_cache(cache_path: Path, key: str) -> frozenset[str] | None:
    """The cached node id set if `cache_path` exists and matches `key`,
    else `None` (local copy of `_collect_shared._load_cache`'s exact
    behavior -- see `_CSHARP_CACHE_REL`'s docstring for why this module
    does not import from `_collect_shared.py`)."""
    if not cache_path.exists():
        return None
    try:
        doc = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("collect_csharp_tests: unreadable cache %s: %s", cache_path, exc)
        return None
    if doc.get("key") != key:
        return None
    return frozenset(doc.get("node_ids", []))


def _store_cache(cache_path: Path, key: str, node_ids: frozenset[str]) -> None:
    """Persist `node_ids` keyed by `key` to `cache_path` (local copy of
    `_collect_shared._store_cache`'s exact behavior, no `extra` payload --
    see `_CSHARP_CACHE_REL`'s docstring)."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    doc: dict = {"key": key, "node_ids": sorted(node_ids)}
    cache_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


# frob:doc docs/modules/testing.md#public-api
def collect_csharp_tests(root: Path) -> Result[CollectedTests, TestingError]:
    """Every NUnit `[Test]`/`[TestCase(...)]`/`[TestCaseSource(...)]` and
    Unity Test Framework `[UnityTest]` method under `root`, as stable
    `<path>::<Namespace.Class>::<Method>` node ids (module docstring),
    found by parsing `.cs` source directly with `tree-sitter-language-
    pack`'s bundled `csharp` grammar -- no `dotnet`/NUnit console runner
    invocation, mirroring `collect_kotlin_tests`'s "no build/run just to
    collect" restraint. Cached on the discovered files' own content hash
    (mirrors every other `collect_*_tests`). Always `Ok` -- a repo with no
    `.cs` files, or none carrying a recognized test attribute, degrades to
    an empty result, never a hard failure."""
    cs_files = _find_cs_files(root)
    key = _csharp_content_key(root, cs_files)
    cache_path = root / _CSHARP_CACHE_REL
    cached = _load_cache(cache_path, key)
    if cached is not None:
        _log.debug("collect_csharp_tests: cache hit, %d node id(s)", len(cached))
        return Ok(CollectedTests(node_ids=cached))

    node_ids: set[str] = set()
    for cs_path in cs_files:
        node_ids.update(_collect_cs_file(root, cs_path))

    if not cs_files:
        _log.debug("collect_csharp_tests: no .cs files found under %s", root)

    frozen = frozenset(node_ids)
    _store_cache(cache_path, key, frozen)
    _log.info("collect_csharp_tests: collected %d node id(s)", len(frozen))
    return Ok(CollectedTests(node_ids=frozen))


__all__ = [
    "collect_csharp_tests",
    "parse_csharp",
]
