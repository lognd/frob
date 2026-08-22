"""SYS102/SYS106/SYS107 rule family (T-2729 layer 2, split out of
`_selfconform.py`): unmodeled code, binding totality / laundering, and
via-less-may-on-a-large-node. See `_selfconform.py`'s own module
docstring for the full design narrative (including SYS107's
`SYS107_FAIL_CLOSED_ATOMS` fail-closed set); this module holds only the
code."""

# frob:waive REF002 reason="T-2729: this is one of six sibling rule-family modules the \
# LARGE001 split of _selfconform.py produced; only orchestration \
# (_selfconform.py::_collect_sys_violations) imports the whole family directly by \
# design, one anchor per module, the same shape every sibling split-out module in this \
# change has -- not an accidental single-consumer anchor"

from __future__ import annotations

from pathlib import Path

from frob.excludes import is_skipped_dir
from frob.lang import resolve_local_import
from frob.logging import get_logger
from frob.vet._capability import is_self_pattern_path, scan_file_capabilities

from ._code_binding import FOREIGN, CodeBinding, _python_imports_with_lines
from ._models import KernelModel, Node
from ._selfconform_ids import (
    _PACKAGE_ROOT,
    SYS_BINDING_TOTALITY,
    SYS_UNMODELED_CODE,
    SYS_VIA_LESS_LARGE_NODE,
)
from ._selfconform_models import SelfConformViolation

_log = get_logger(__name__)


# frob:ticket T-2729
def _reachable_local_files(start_files: list[str], root: Path) -> frozenset[str]:
    """BFS closure of every in-repo `.py` file reachable from `start_files`
    via resolved local python imports (`frob.lang.resolve_local_import`),
    visited-set guarded against import cycles -- SYS106's "reachable from
    a bound node" side (module docstring's SYS106 section).

    T-1208: calls `_code_binding._python_imports_with_lines` directly
    (memoized there via `_IMPORT_MEMO`) instead of parsing `path` itself
    and re-deriving imports with a local duplicate walk -- `check_import_
    conformance` (SYS003) parses this SAME ~800-file set in the SAME `frob
    sys` run, so sharing the one memo means the run parses each file once,
    not twice."""
    visited: set[str] = set(start_files)
    queue: list[str] = list(start_files)
    while queue:
        rel = queue.pop()
        path = root / rel
        for spec, _line in _python_imports_with_lines(path, root):
            dst = resolve_local_import(spec, "python", file_dir=path.parent, root=root)
            if dst is None or dst in visited:
                continue
            visited.add(dst)
            queue.append(dst)
    return frozenset(visited)


# frob:tests tests/unit/strata/test_selfconform.py::TestBindingTotality.test_laundered_capable_file_fires  # noqa: E501
# frob:ticket T-2729
def _binding_totality_violations(
    model: KernelModel, binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS106 (T-0670): a `FOREIGN` file reachable (via resolved local
    imports, `_reachable_local_files`) from ANY bound node's own files,
    that `scan_file_capabilities` observes a capability in -- "logic
    laundered into an unbound file" (module docstring's SYS106 section).
    One finding per such file (not per reaching node -- the file itself is
    the escaping unit, and could be reached from more than one node)."""
    bound_files = [
        rel
        for rel, owner in binding.owner.items()
        if owner != FOREIGN and rel.endswith(".py")
    ]
    if not bound_files:
        return []
    reachable = _reachable_local_files(bound_files, root)
    found: list[SelfConformViolation] = []
    for rel in sorted(reachable):
        if binding.owner.get(rel, FOREIGN) != FOREIGN:
            continue
        path = root / rel
        if is_self_pattern_path(path, root):
            continue
        kinds = scan_file_capabilities(path)
        if not kinds:
            continue
        # frob:waive PERF004 reason="kinds is THIS file's own distinct set (a \
        # different value every time the outer file loop advances), sorted only for \
        # deterministic WARNING log ordering -- not a repeated re-sort of identical \
        # data across iterations"
        capability = ", ".join(sorted(kinds))
        _log.warning(
            "selfconform: SYS106 laundered capable file %s (%s) reachable "
            "from bound code",
            rel,
            capability,
        )
        found.append(
            SelfConformViolation(
                rule=SYS_BINDING_TOTALITY,
                node=rel,
                detail=(
                    f"{rel} has an observed capability ({capability}), is "
                    "reachable from bound code via local imports, but no "
                    "node's code= glob binds it"
                ),
            )
        )
    return found


# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1451
# frob:waive COV007 reason="T-1636: docs/strata/surface.md's may-scope section \
# (T-1451) documents SYS107's blast-radius measure this private helper implements -- \
# same T-0524/T-0529 per-function architecture-doc precedent every other COV007 waiver \
# in this repo already carries, not accidental drift onto a private helper"
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
def _node_real_code_file_count(binding: CodeBinding, node_id: str) -> int:
    """The number of real (owned, non-`FOREIGN`) files `binding` binds to
    `node_id` -- SYS107's own "how large is this node's blast radius"
    measure, split out purely so `_via_less_large_node_violations`'s loop
    body stays short. Reuses `binding.owner` directly (already computed by
    the caller's `_capability_binding` pass) rather than re-walking
    `node.attrs`'s `code=` globs -- an owned-file count, not a glob count,
    is what actually determines how much a whole-node grant covers."""
    return sum(1 for owner in binding.owner.values() if owner == node_id)


# frob:ticket T-2224
# frob:waive COV007 reason="T-2224: docs/strata/surface.md#may-scope (T-1440/T-1451) \
# already documents the SYS107 via-less-large-node advisory this private helper \
# implements -- same T-0524/T-0529 per-function architecture-doc precedent every other \
# COV007 waiver in this module already carries, not accidental drift onto a private \
# helper"
# frob:ticket T-2729
def _via_less_atoms_for_node(node: Node) -> frozenset[str]:
    """The `may` atoms `node` grants WITHOUT any `via` scoping (T-2224,
    split out of `_via_less_large_node_violations` so the node-level
    "has any via-less grant at all" gate and the per-atom finding loop
    share one walk instead of two differently-shaped checks). `node.
    may_grants` empty entirely (a `Node` built directly, bypassing the
    parser) is treated as "every declared `may` atom is via-less" (the
    pre-T-1440 meaning `MayGrant.via=()` formalizes) -- mirrors this
    module's existing hand-built-`Node`-fixture compatibility note."""
    if not node.may_grants:
        return frozenset(node.may)
    return frozenset(grant.atom for grant in node.may_grants if not grant.via)


# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1451
# frob:ticket T-2224
# frob:tests tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory.test_via_less_grant_on_large_node_fires  # noqa: E501
# frob:tests tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory.test_via_less_grant_on_small_node_is_silent  # noqa: E501
# frob:tests tests/unit/strata/test_sys107_via_scope_advisory.py::TestViaLessLargeNodeAdvisory.test_via_scoped_grant_on_large_node_is_silent  # noqa: E501
# frob:waive COV007 reason="T-1636: docs/strata/surface.md's may-scope section \
# (T-1440/T-1451) documents the SYS107 via-less-large-node advisory this private \
# helper implements -- same T-0524/T-0529 per-function architecture-doc precedent \
# every other COV007 waiver in this repo already carries, not accidental drift onto a \
# private helper"
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
def _via_less_large_node_violations(
    model: KernelModel, binding: CodeBinding, threshold: int
) -> list[SelfConformViolation]:
    """SYS107 (T-1451, module docstring's SYS107 section): a node bound to
    more than `threshold` real files that declares at least one via-less
    `may` grant is an advisory finding.

    T-2224: now judged per (node, ATOM) -- one finding per offending
    via-less atom, not one per node -- rather than the pre-T-2224 "one
    finding per offending node" shape. This is what makes a PER-
    CAPABILITY severity decision possible at all: `capability=atom` is
    set on each finding (the same "multi-instance sub-target" shape
    SYS100/SYS101 already use), so `frob.gates._sys_selfaudit._
    selfaudit_severity` can escalate exactly the fail-closed kinds
    (`SYS107_FAIL_CLOSED_ATOMS` -- exec/eval/install-hook/ffi) to ERROR
    unconditionally while `net`/`fs.read`/`fs.write` keep the original
    WARN-unless-`require_may_scope` posture. A node with via-less grants
    on BOTH a fail-closed and a non-fail-closed atom now correctly
    produces one ERROR and one WARN finding, not one WARN finding
    covering both."""
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        if not node.may:
            continue
        file_count = _node_real_code_file_count(binding, node.id)
        if file_count <= threshold:
            continue
        via_less_atoms = _via_less_atoms_for_node(node)
        if not via_less_atoms:
            continue
        # frob:waive PERF004 reason="via_less_atoms is THIS node's own distinct set (a \
        # different value every time the outer node loop advances), sorted only for \
        # deterministic WARNING log ordering -- not a repeated re-sort of identical \
        # data across iterations"
        for atom in sorted(via_less_atoms):
            _log.warning(
                "selfconform: SYS107 via-less may %r grant on large node %s "
                "(%d files > threshold %d)",
                atom,
                node.id,
                file_count,
                threshold,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_VIA_LESS_LARGE_NODE,
                    node=node.id,
                    detail=(
                        f"node {node.id!r} binds {file_count} file(s) (> "
                        f"{threshold}) and declares a via-less {atom!r} may "
                        "grant -- consider narrowing it with via"
                    ),
                    capability=atom,
                )
            )
    return found


# frob:ticket T-2729
def _top_level_dirs(root: Path) -> list[str]:
    """Every immediate, non-skipped subdirectory name of `root / _PACKAGE_ROOT`
    (module docstring's SYS102 unit of "unmodeled code"), in sorted order.
    T-0211: `_PACKAGE_ROOT` ("src/frob") is frob's OWN package layout, not a
    general convention -- SYS102 only makes sense when auditing frob's own
    repo (module docstring: `design/frob.strata` models exactly this one
    tree). Every OTHER repo running `frob sys audit` structurally lacks
    `src/frob/` by design, not by drift, so that absence is an expected,
    silent no-op (empty SYS102 finding set) here -- previously this logged
    at WARNING unconditionally, which fired in every non-frob repo on every
    audit run and read as "the self-conformance proof is vacuous" even
    though the other checks (SYS100/SYS101/exhaustiveness) genuinely ran
    (filed from sibling-repo pilot P2, tickets.md T-0211). DEBUG here (not
    silence outright) still leaves a trace for anyone diagnosing frob's own
    SYS102 detection, without alarming operators of unrelated repos."""
    package_root = root / _PACKAGE_ROOT
    if not package_root.is_dir():
        _log.debug(
            "selfconform: %s does not exist -- not the frob repo (or repo "
            "root mismatch); skipping SYS102 unmodeled-code check",
            package_root,
        )
        return []
    return sorted(
        entry.name
        for entry in package_root.iterdir()
        if entry.is_dir() and not is_skipped_dir(entry.name)
    )


# frob:ticket T-2729
def _package_relative(binding: CodeBinding) -> list[tuple[str, str, str]]:
    """`(rel, tail, owner)` for every `binding.owner` entry under
    `_PACKAGE_ROOT`, where `tail` is `rel` with the `src/frob/` prefix
    stripped -- the common slice `_unmodeled_violations`'s three passes
    (loose top-level files, fully-foreign directories, foreign files
    inside a partially-owned directory) all need, hoisted so each pass is
    a plain filter over the same precomputed list rather than
    re-deriving `tail` three times (charter: no duplication)."""
    out: list[tuple[str, str, str]] = []
    for rel, owner in binding.owner.items():
        if not rel.startswith(f"{_PACKAGE_ROOT}/"):
            continue
        out.append((rel, rel[len(_PACKAGE_ROOT) + 1 :], owner))
    return out


# frob:ticket T-2729
def _loose_foreign_file_violations(
    relative: list[tuple[str, str, str]],
) -> list[SelfConformViolation]:
    """G4 (docs/audits/strata.md): a `.py`/`.ts`/etc. file placed DIRECTLY
    under `src/frob/` (no subdirectory) that no node's `code=` glob
    claims. `_top_level_dirs` (below) only ever iterates DIRECTORIES
    (`entry.is_dir()`), so a loose top-level file was invisible to SYS102
    no matter what it did -- and, being `FOREIGN`, invisible to SYS100/
    SYS101 too (module docstring: those only reconcile bound files)."""
    found: list[SelfConformViolation] = []
    for rel, tail, owner in sorted(relative):
        if "/" in tail or owner != FOREIGN:
            continue
        _log.warning("selfconform: SYS102 unmodeled loose file %s", rel)
        found.append(
            SelfConformViolation(
                rule=SYS_UNMODELED_CODE,
                node=rel,
                detail=f"{rel} has no node's code= glob binding it",
            )
        )
    return found


# frob:ticket T-2729
def _fully_foreign_dir_violations(
    root: Path, owned_dirs: frozenset[str]
) -> list[SelfConformViolation]:
    """SYS102 original case: a whole top-level `src/frob/` directory with
    no file owned by any node's `code=` glob (module docstring's SYS102
    gap statement)."""
    found: list[SelfConformViolation] = []
    for name in _top_level_dirs(root):
        if name in owned_dirs:
            continue
        _log.warning("selfconform: SYS102 unmodeled code src/frob/%s", name)
        found.append(
            SelfConformViolation(
                rule=SYS_UNMODELED_CODE,
                node=name,
                detail=f"src/frob/{name} has no node's code= glob binding it",
            )
        )
    return found


# frob:ticket T-2729
def _foreign_file_in_owned_dir_violations(
    relative: list[tuple[str, str, str]], owned_dirs: frozenset[str]
) -> list[SelfConformViolation]:
    """G4 (docs/audits/strata.md): a file inside an OTHERWISE-owned
    top-level directory that no node's `code=` glob actually matches.
    Before this, `_unmodeled_violations` marked a whole directory "owned"
    the moment ANY file in it was non-`FOREIGN` (`prefix_owned`/
    `owned_dirs` below) -- so a stray unglobbed file dropped into an
    already-modeled directory was invisible to SYS102 (its directory is
    not fully foreign) AND invisible to SYS100/SYS101 (it is `FOREIGN`,
    so no node's capability set is ever joined against it). This fires
    per such file, at file granularity, so "the directory has an owner"
    can no longer hide "this ONE file does not"."""
    found: list[SelfConformViolation] = []
    for rel, tail, owner in sorted(relative):
        if "/" not in tail or owner != FOREIGN:
            continue
        top = tail.split("/", 1)[0]
        if top not in owned_dirs:
            continue  # the fully-foreign-directory pass already covers this file
        _log.warning(
            "selfconform: SYS102 unmodeled file %s in otherwise-modeled directory "
            "src/frob/%s",
            rel,
            top,
        )
        found.append(
            SelfConformViolation(
                rule=SYS_UNMODELED_CODE,
                node=rel,
                detail=(
                    f"{rel} has no node's code= glob binding it (directory "
                    f"src/frob/{top} is otherwise modeled)"
                ),
            )
        )
    return found


# frob:ticket T-2729
def _unmodeled_violations(
    root: Path, binding: CodeBinding
) -> list[SelfConformViolation]:
    """SYS102: every `src/frob/` file (loose top-level, or inside a
    directory) that no node's `code=` glob binds -- module docstring's
    SYS102 gap statement, tightened by G4 (docs/audits/strata.md) to fire
    per-FOREIGN-file rather than only per fully-FOREIGN top-level
    directory (`_fully_foreign_dir_violations`'s original grain missed
    both a stray file in an otherwise-modeled directory and a file placed
    directly under `src/frob/` with no subdirectory at all -- see
    `_foreign_file_in_owned_dir_violations`/`_loose_foreign_file_
    violations`'s docstrings for each gap). `binding` is the T-0169
    `_capability_binding` superset here, not `bind_code`'s raw `.py`-only
    output: a directory containing ONLY a `.ts`/`.rs`/etc. file that a
    node's `code=` glob genuinely claims used to misreport SYS102
    ("unmodeled") because the Python-only binding never bound that file
    at all -- a spurious finding on top of the missed SYS100/SYS101, now
    fixed by using the same superset every other rule in this module
    uses."""
    relative = _package_relative(binding)
    owned_dirs = frozenset(
        tail.split("/", 1)[0]
        for _, tail, owner in relative
        if "/" in tail and owner != FOREIGN
    )
    return [
        *_fully_foreign_dir_violations(root, owned_dirs),
        *_foreign_file_in_owned_dir_violations(relative, owned_dirs),
        *_loose_foreign_file_violations(relative),
    ]
