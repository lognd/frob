"""strata tier-2 code binding: `code` globs + import-level conformance
(docs/strata/surface.md#code-binding-tier-2-v0-implementation, T-0078).

Two steps, kept as two functions since they fail differently (charter law
1: no silent defaults):

1. `bind_code` glob-matches real source files against every node's
   `code=<glob>` attrs -- the tier-2 half of "the model is load-bearing"
   (law 6): unclassified code is foreign by default (law 2).
2. `check_import_conformance` walks each bound file's python imports and
   flags any crossing between two differently-owned files (including the
   `FOREIGN` bucket) whose exact direction (importer's owner -> imported
   file's owner) has no matching kernel `Flow` in that SAME direction --
   "design constrains code" (law 5), read direction. `Flow` is directed
   (`kernel.md`'s primitive table); a `Flow(src=A, dst=B)` authorizes an
   import from A's code into B's code and nothing else -- it does not
   also authorize a B -> A import, exactly as it would not authorize a
   B -> A data flow. Charter law 2 ("undeclared flows are forbidden")
   applies per-direction, not per-pair
   (docs/strata/surface.md#code-binding-tier-2-v0-implementation).

Neither function mutates a `KernelModel`; both are pure joins between the
model and the real file tree, exactly like `_facts.py`'s tier-1 closure is
a pure join between declared facts.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/strata/_code_binding.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs, walk_pruned
from frob.lang import resolve_local_import
from frob.logging import get_logger

from ._errors import StrataError
from ._models import KernelModel

_log = get_logger(__name__)

#: Node attr prefix for a tier-2 code-binding glob (one attr entry per
#: glob, mirroring the `skew=`/`fanout=`/`growth=` attr-string convention
#: in `_claims.py`/`_infra.py` -- see the doc anchor above for why this is
#: an attr rather than a new kernel field).
_CODE_PREFIX = "code="

#: The synthetic owner id for a file matched by no node's `code=` glob
#: (charter law 2: "unclassified code is foreign by default").
# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
FOREIGN = "__foreign__"

#: Node attr marker for a `managed` node (T-0172, mirrors `_elaborate.py::
#: _MANAGED_ATTR` -- kept as a local literal, not an import, for the same
#: no-cycle reason `_infra.py`'s copy is: this module sits below
#: `_elaborate.py` in the import graph). A managed node is external,
#: pure-config infrastructure declared to have no scannable code; tier-2
#: conformance is not required for it (docs/strata/surface.md
#: #key-construct-semantics).
_MANAGED_ATTR = "managed"


# frob:doc docs/strata/surface.md#key-construct-semantics
# frob:ticket T-0172
def is_managed(node) -> bool:
    """Whether `node` carries the `managed` attr (T-0172) -- external,
    pure-config infrastructure exempt from tier-2 code-binding conformance
    (docs/strata/surface.md#key-construct-semantics)."""
    return _MANAGED_ATTR in node.attrs


def _node_code_globs(node) -> tuple[str, ...]:
    """A node's declared `code=<glob>` attrs, in declaration order."""
    return tuple(
        attr[len(_CODE_PREFIX) :]
        for attr in node.attrs
        if attr.startswith(_CODE_PREFIX)
    )


# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
class CodeBinding(BaseModel):
    """Resolved `root`-relative file path -> owning node id (or `FOREIGN`)."""

    model_config = ConfigDict(frozen=True)

    owner: dict[str, str] = {}


def _sorted_owners(matched: set[str]) -> tuple[str, ...]:
    """Deterministic owner-id order for an ambiguous-binding log line."""
    return tuple(sorted(matched))


def _sorted_py_files(root: Path, exclude_globs: tuple[str, ...] = ()) -> list[Path]:
    """Every `.py` file under `root`, in deterministic path order (hoisted
    out of `bind_code`'s loop so the sort runs once, not per iteration).

    T-0414 (docs/audits/perf.md H2/M7): a plain `Path.rglob("*.py")` cannot
    prune a subtree mid-descent, so it fully walks and stats every excluded
    directory (in this repo, `.claude/worktrees/agent-*` alone holds 45k+
    stray `.py` files) before the caller's `is_skipped_dir`/`is_excluded`
    filter ever runs -- measured as the dominant cost of the `sys` gate's
    SYS003 check. `os.walk` with `_should_prune_dir` pruning `dirnames` in
    place (the same helper `frob.graph._walk_source_files` already uses)
    skips descending into those directories at all.

    T-0416: `_should_prune_dir` additionally prunes nested git checkouts
    (`_is_nested_worktree`, config-independent -- see `frob.excludes`),
    which the OLD `rglob` + `_bind_all_files` post-filter never checked
    (that filter only applied `is_skipped_dir`/`is_excluded`). For a repo
    whose `[graph] exclude` globs already cover every nested checkout
    (this repo: `.claude/worktrees/**`) the two walks converge on the same
    final file set. For a repo with a nested `.git` checkout NOT covered
    by any exclude glob, this walk now additionally omits it -- an
    intentional tightening (a nested git checkout is never this repo's
    own source, T-0239), not a bug, but NOT "the exact same final file
    set" unconditionally; do not assume file-set parity with the old
    behavior for such a repo."""
    found = [
        p for p in walk_pruned(root, exclude_globs=exclude_globs) if p.suffix == ".py"
    ]
    # frob:waive PERF004 reason="one sort after the walk loop above, not per iteration"
    return sorted(found)


def _bind_one(rel: str, globs: list[tuple[str, str]]) -> Result[str, StrataError]:
    """The single owner (or `FOREIGN`) for one `rel` path, or `Err` if ambiguous."""
    matched = {node_id for node_id, glob in globs if fnmatch.fnmatch(rel, glob)}
    if len(matched) > 1:
        _log.error(
            "code binding: %s matched by multiple nodes %s",
            rel,
            _sorted_owners(matched),
        )
        return Err(StrataError.AmbiguousCodeBinding)
    return Ok(next(iter(matched)) if matched else FOREIGN)


def _bind_all_files(
    root: Path, globs: list[tuple[str, str]], exclude_globs: tuple[str, ...]
) -> Result[dict[str, str], StrataError]:
    """Every non-skipped, non-excluded `.py` file under `root`, bound to its
    owner (or `FOREIGN`), in deterministic path order."""
    owner: dict[str, str] = {}
    for path in _sorted_py_files(root, exclude_globs):
        rel_path = path.relative_to(root)
        if any(is_skipped_dir(part) for part in rel_path.parts):
            continue
        rel = rel_path.as_posix()
        if exclude_globs and is_excluded(rel, exclude_globs):
            continue
        owned = _bind_one(rel, globs)
        if owned.is_err:
            return Err(owned.danger_err)
        owner[rel] = owned.danger_ok
    return Ok(owner)


# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
def bind_code(model: KernelModel, root: Path) -> Result[CodeBinding, StrataError]:
    """Partition every `.py` file under `root` by the node whose `code=`
    glob matches it; a file matched by no node is `FOREIGN`, a file matched
    by more than one node is `Err(StrataError.AmbiguousCodeBinding)` (deny
    by default -- see module docstring). Honors `[graph] exclude` (T-0274)
    in addition to the built-in skip-dir set, so a repo-declared excluded
    directory (e.g. a bundled frontend build under a `code=`-globbed
    directory) is never misattributed to a node."""
    globs: list[tuple[str, str]] = [
        (node.id, glob) for node in model.nodes for glob in _node_code_globs(node)
    ]
    if not globs:
        _log.info("code binding: no node declares a code= glob; binding is empty")
        return Ok(CodeBinding(owner={}))

    exclude_globs = load_exclude_globs(root)
    owned_result = _bind_all_files(root, globs, exclude_globs)
    if owned_result.is_err:
        return Err(owned_result.danger_err)
    owner = owned_result.danger_ok

    bound = sum(1 for v in owner.values() if v != FOREIGN)
    _log.info("code binding: %d file(s) bound, %d foreign", bound, len(owner) - bound)
    return Ok(CodeBinding(owner=owner))


# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
class ImportViolation(BaseModel):
    """One undeclared cross-component import: file:line with no matching `Flow`."""

    model_config = ConfigDict(frozen=True)

    file: str
    line: int
    spec: str
    src_component: str
    dst_component: str


# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
class ConformanceReport(BaseModel):
    """Every tier-2 import-conformance violation found, in file-then-line order."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ImportViolation, ...] = ()


def _parse_ast(path: Path) -> ast.Module | None:
    """`path` parsed to an `ast.Module`, or None (logged) on any read/parse failure."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, OSError, UnicodeDecodeError) as exc:
        _log.warning(
            "code binding: could not parse %s for import conformance: %s", path, exc
        )
        return None


def _absolute_imports(node: ast.AST) -> list[tuple[str, int]]:
    """(absolute dotted spec, line) for one `Import`/level-0 `ImportFrom` node."""
    if isinstance(node, ast.Import):
        return [(alias.name, node.lineno) for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
        return [(node.module, node.lineno)]
    return []


def _relative_base_dir(file_dir: Path, root: Path, level: int) -> Path | None:
    """The root-relative package directory `level` dots up from `file_dir`
    (python relative-import semantics: level 1 is the importing file's own
    package, i.e. `file_dir` itself; each further level goes up one more
    directory). None if that walks above `root`."""
    base = file_dir
    for _ in range(level - 1):
        if base == root:
            return None
        base = base.parent
    try:
        base.relative_to(root)
    except ValueError:
        return None
    return base


def _dotted(base_dir: Path, root: Path) -> str:
    """`base_dir`'s root-relative dotted package path ("" when `base_dir` is `root`)."""
    rel = base_dir.relative_to(root).as_posix()
    return "" if rel == "." else rel.replace("/", ".")


def _join_dotted(prefix: str, tail: str) -> str:
    """`prefix.tail`, or bare `tail` when `prefix` is empty (`base_dir == root`)."""
    return f"{prefix}.{tail}" if prefix else tail


def _relative_imports(
    node: ast.AST, file_dir: Path, root: Path
) -> list[tuple[str, int]]:
    """(absolute dotted spec, line) for one `ImportFrom` node with `level >= 1`
    (`from . import x`, `from ..pkg import y`) -- resolved against the
    importing file's own package position, not skipped (T-0078 review fix).
    `from . import x[, y]` has no `module`; each name is a candidate
    submodule of the target package, mirroring real python's own name
    resolution order (submodule first, plain attribute otherwise -- an
    attribute that doesn't resolve to a file is simply not in-repo, handled
    downstream by `resolve_local_import` returning None)."""
    if not (isinstance(node, ast.ImportFrom) and node.level >= 1):
        return []
    base_dir = _relative_base_dir(file_dir, root, node.level)
    if base_dir is None:
        return []
    prefix = _dotted(base_dir, root)
    if node.module is not None:
        return [(_join_dotted(prefix, node.module), node.lineno)]
    return [(_join_dotted(prefix, alias.name), node.lineno) for alias in node.names]


def _python_imports_with_lines(path: Path, root: Path) -> list[tuple[str, int]]:
    """(absolute dotted specifier, 1-based line) for every python import in
    `path`, including relative imports resolved to their absolute in-repo
    equivalent (T-0078 review fix -- `from .` / `from ..pkg` are the
    dominant intra-package style and must not be silently skipped).

    Uses stdlib `ast` directly rather than `frob.lang.extract_imports`
    because line numbers are needed here and `extract_imports` does not
    carry them (docs/strata/surface.md
    #code-binding-tier-2-v0-implementation); a general per-language "import
    statement -> line" walk belongs in `frob.lang`, out of this ticket's
    scope.
    """
    tree = _parse_ast(path)
    if tree is None:
        return []
    file_dir = path.parent
    results: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        results.extend(_absolute_imports(node))
        results.extend(_relative_imports(node, file_dir, root))
    return results


def _call_target_name(func: ast.expr) -> str | None:
    """The bare identifier one `ast.Call.func` resolves to: `Name.id` for a
    plain call (`sanitize(x)`) or `Attribute.attr` for a method/module call
    (`html.sanitize(x)` -> `"sanitize"`), or `None` for any other callable
    expression (a subscript, a call result) -- deliberately conservative,
    the same no-dynamic-dispatch-resolution posture `_effects.py`'s own
    substring observation already takes (docs/audits/strata.md G1)."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _call_names(tree: ast.Module) -> frozenset[str]:
    """Every distinct call-target name (`_call_target_name`) found anywhere
    in `tree`."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_target_name(node.func)
            if name is not None:
                names.add(name)
    return frozenset(names)


# frob:ticket T-0601
def _observed_call_names(
    binding: CodeBinding, root: Path, node_id: str
) -> frozenset[str]:
    """Every distinct call-target name observed anywhere in `node_id`'s
    `code=`-bound files (docs/audits/strata.md G1 stronger half) -- the
    code-side half of the ENDORSE-boundary predicate join
    `_threat.py::_predicate_is_code_bound` needs: a boundary's `predicate`
    (an opaque string like `"jwt_verified"`) is trusted as real evidence
    of a mitigation only when it ALSO names an observed call site in the
    guarded node's own bound code, not merely a plausible-sounding string
    declared in the model with nothing joined against it.

    A file that fails to parse contributes no call names rather than
    aborting the whole join (mirrors `_python_imports_with_lines`'s own
    `_parse_ast`-failure handling -- deny-by-default at the boundary
    level, not a hard crash at the file level)."""
    names: set[str] = set()
    for rel in sorted(binding.owner):
        if binding.owner[rel] != node_id:
            continue
        tree = _parse_ast(root / rel)
        if tree is None:
            continue
        names |= _call_names(tree)
    return frozenset(names)


def _bound_dst(
    binding: CodeBinding, spec: str, file_dir: Path, root: Path
) -> str | None:
    """The owner of `spec`'s resolved target, or None if it does not resolve in-repo."""
    dst_rel = resolve_local_import(spec, "python", file_dir=file_dir, root=root)
    if dst_rel is None:
        return None  # third-party/stdlib -- not in-repo, not a design concern
    return binding.owner.get(dst_rel, FOREIGN)


def _declared_pairs(model: KernelModel) -> set[tuple[str, str]]:
    """Every (src, dst) node-id pair with a declared kernel `Flow`, in the
    EXACT direction declared -- `Flow` is directed (`kernel.md`), so a
    `Flow(src=A, dst=B)` authorizes only an A -> B import, never B -> A
    (see module docstring; this was a REJECT-fix, T-0078 review round)."""
    return {(flow.src, flow.dst) for flow in model.flows}


def _sorted_owned_files(binding: CodeBinding) -> list[str]:
    """Every bound file path, in deterministic order (hoisted out of
    `check_import_conformance`'s loop so the sort runs once)."""
    return sorted(binding.owner)


def _file_violations(
    rel: str,
    owner: str,
    binding: CodeBinding,
    root: Path,
    declared_pairs: set[tuple[str, str]],
) -> list[ImportViolation]:
    """Every undeclared cross-component import inside one bound file `rel`."""
    found: list[ImportViolation] = []
    for spec, line in _python_imports_with_lines(root / rel, root):
        dst_owner = _bound_dst(binding, spec, (root / rel).parent, root)
        if (
            dst_owner is None
            or dst_owner == owner
            or (owner, dst_owner) in declared_pairs
        ):
            continue
        _log.warning(
            "code binding: undeclared cross-component import %s:%d %s -> %s (%s)",
            rel,
            line,
            owner,
            dst_owner,
            spec,
        )
        found.append(
            ImportViolation(
                file=rel,
                line=line,
                spec=spec,
                src_component=owner,
                dst_component=dst_owner,
            )
        )
    return found


# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
def check_import_conformance(
    model: KernelModel, binding: CodeBinding, root: Path
) -> ConformanceReport:
    """Every in-repo python import crossing two differently-owned files with
    no declared `Flow` in that EXACT direction (importer's owner -> target's
    owner) between those owner node ids -- "undeclared cross-component
    import" (T-0078). A `managed` (T-0172) node's owned files are skipped
    the SAME way `FOREIGN` files are: `managed` declares "no scannable code
    here", so any file a stray `code=` glob still happens to bind to it
    names a node with nothing to attest the crossing against either (docs/
    strata/surface.md#key-construct-semantics: "no tier-2 conformance")."""
    declared_pairs = _declared_pairs(model)
    nodes_by_id = {node.id: node for node in model.nodes}
    violations: list[ImportViolation] = []
    for rel in _sorted_owned_files(binding):
        owner = binding.owner[rel]
        if owner == FOREIGN:
            continue  # foreign code names no node to attest the crossing against
        owner_node = nodes_by_id.get(owner)
        if owner_node is not None and is_managed(owner_node):
            continue  # T-0172: managed node, no tier-2 conformance
        violations.extend(_file_violations(rel, owner, binding, root, declared_pairs))
    return ConformanceReport(violations=tuple(violations))


__all__ = [
    "FOREIGN",
    "CodeBinding",
    "ConformanceReport",
    "ImportViolation",
    "bind_code",
    "check_import_conformance",
    "is_managed",
]
