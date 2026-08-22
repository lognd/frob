"""Layer 1 of `_selfconform.py`'s SYS1xx split (T-2729): the shared
"observed capability kinds" computation over `KernelModel`/`CodeBinding`.

These functions carry no violation semantics of their own -- they answer
"what capability kinds does this node/file/binding actually exhibit" and
nothing about whether that is right or wrong. `_selfconform_core_rules.py`
(SYS100/SYS101/SYS103), `_selfconform_surface_rules.py` (SYS105/SYS108/
SYS110), `_selfconform_binding_rules.py` (SYS102/SYS106/SYS107), and
`_selfconform.py`'s own orchestration (`_collect_sys_violations`) all
build on this one shared layer rather than re-walking `root` or
re-deriving a node's owned files independently -- T-2729's own
investigation found `_observed_raw_kinds_by_node`/`_observed_kinds_for_
files` feeding both the SYS100-extended and SYS101 scans, which is
exactly the seam this module now names explicitly instead of leaving
implicit inside one 2290-line file."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs, walk_pruned
from frob.logging import get_logger
from frob.vet._capability import is_self_pattern_path, language_for, scan_file_capabilities

from ._code_binding import CodeBinding, FOREIGN, _node_code_globs
from ._effects import _KIND_MAP, _may_kind
from ._errors import StrataError
from ._models import KernelModel

_log = get_logger(__name__)

#: The vet capability kinds THREAT004's `_effects.py::_KIND_MAP` has no
#: tier-2 analog for (`_selfconform.py` module docstring's SYS100 gap
#: statement) -- the ONLY kinds this module's own file-level scan needs
#: to cover, since net/fs-write/exec are fully delegated to
#: `check_capability_conformance`.
# frob:ticket T-2729
_EXTENDED_KINDS = frozenset(
    {
        "eval",
        "process-control",
        "ffi",
        "install-hook",
        "sql",
        "deserialize",
        "html_render",
        "fetch_url",
        "client_storage",
        "net-mutate",
    }
)


# frob:ticket T-2729
def _sorted_owned_files(binding: CodeBinding) -> list[str]:
    """Every non-`FOREIGN` bound file path, in deterministic order
    (mirrors `_effects.py::_sorted_owned_files`)."""
    return sorted(rel for rel, owner in binding.owner.items() if owner != FOREIGN)


# frob:ticket T-2729
def _sorted_capability_files(root: Path) -> list[Path]:
    """Every file under `root` whose extension `vet._capability.language_for`
    recognizes (i.e. has a capability pattern table), skip-dir- AND
    `[graph].exclude`-filtered (T-0274), in deterministic path order
    (T-0169: the multi-language superset of `bind_code`'s `.py`-only walk
    -- `bind_code` itself stays Python-only since it also powers import-
    conformance, which is Python-syntax-specific; capability *observation*
    has no such constraint)."""
    exclude_globs = load_exclude_globs(root)
    found: list[Path] = []
    for path in sorted(walk_pruned(root, exclude_globs=exclude_globs)):
        if language_for(path) is None:
            continue
        found.append(path)
    return found


# frob:ticket T-2729
def _capability_binding(
    model: KernelModel,
    binding: CodeBinding,
    root: Path,
    capability_files: list[Path] | None = None,
) -> Result[CodeBinding, StrataError]:
    """`binding` (Python-only, from `bind_code`) extended with every OTHER
    capability-scannable-language file under `root`, bound by the SAME
    `code=` glob convention (T-0169 GAP STATEMENT: `bind_code` walks only
    `*.py` -- module docstring/T-0078 -- because it also backs import-
    conformance, which needs Python's import syntax specifically; that
    scope choice silently meant SYS100/SYS101 never saw a single TS/JS/
    Rust/C-C++ file either, even though `vet._capability` has scanned
    those languages since T-0079/T-0158. This function is the fix: it
    re-runs `bind_code`'s glob-match (via `_node_code_globs`, reused not
    reimplemented) over the non-`.py` capability-scannable file set, deny-
    by-default on ambiguity exactly like `bind_code`, and merges the
    result into `binding.owner` so every downstream SYS100/SYS101 join in
    this module sees every registry-covered language, not just Python).
    `capability_files` (T-1449): the caller's already-walked
    `_sorted_capability_files(root)` result, reused instead of re-walking
    the whole tree here -- `check_self_conformance` threads its ONE walk
    through both this function and `_coverage_totality_violations` so a
    single `check_self_conformance` call costs one full-tree walk, not
    two (T-1449's `TestRealGateGreen`/`TestCoverageTotality` full-repo-scan
    peak-memory ticket). Falls back to a fresh walk when `None` (every
    other caller/test that does not have one handy)."""
    globs = [(node.id, glob) for node in model.nodes for glob in _node_code_globs(node)]
    owner = dict(binding.owner)
    files = (
        capability_files
        if capability_files is not None
        else _sorted_capability_files(root)
    )
    for path in files:
        if path.suffix.lower() == ".py":
            continue  # already bound by `bind_code`
        rel = path.relative_to(root).as_posix()
        bound_id = _match_capability_owner(rel, globs)
        if bound_id.is_err:
            return Err(bound_id.danger_err)
        owner[rel] = bound_id.danger_ok
    bound = sum(1 for v in owner.values() if v != FOREIGN) - sum(
        1 for v in binding.owner.values() if v != FOREIGN
    )
    _log.info("capability binding: %d additional non-python file(s) bound", bound)
    return Ok(CodeBinding(owner=owner))


# frob:ticket T-2729
def _match_capability_owner(
    rel: str, globs: list[tuple[str, str]]
) -> Result[str, StrataError]:
    """The owning node id for `rel` against `globs` (`(node_id, glob)`
    pairs), `FOREIGN` if none match, deny-by-default on ambiguity -- split
    out of `_capability_binding` purely to keep its loop body short."""
    matched = {node_id for node_id, glob in globs if fnmatch.fnmatch(rel, glob)}
    if len(matched) > 1:
        _log.error(
            "capability binding: %s matched by multiple nodes %s",
            rel,
            tuple(sorted(matched)),
        )
        return Err(StrataError.AmbiguousCodeBinding)
    return Ok(next(iter(matched)) if matched else FOREIGN)


# frob:ticket T-2729
def _observed_raw_kinds_by_file(
    binding: CodeBinding, root: Path
) -> dict[str, frozenset[str]]:
    """Every owned file (`rel` path) -> the RAW `scan_file_capabilities`
    output for that ONE file (no `_EXTENDED_KINDS` filter, no `_KIND_MAP`
    normalization) -- the SINGLE per-file scan pass every other observed-
    kinds view in this module (per-node aggregate via
    `_observed_raw_kinds_by_node`, and T-1450's per-via `_stale_design_
    violations` join) derives from, so `scan_file_capabilities` still
    only ever runs once per owned file (H5/T-0830's single-scan property,
    now anchored at file granularity instead of node granularity so a
    per-`via`-surface join has something to narrow). `binding` here is
    ALWAYS the T-0169 `_capability_binding` superset, never the raw
    `.py`-only `bind_code` output -- see that function's docstring. Skips
    `is_self_pattern_path` files (T-0201): a pattern-catalog data file's
    needle literals are not code exercising the capability, the same
    self-match class `frob.vet._capability`'s own aggregation excludes."""
    per_file: dict[str, frozenset[str]] = {}
    for rel in _sorted_owned_files(binding):
        path = root / rel
        if is_self_pattern_path(path, root):
            continue
        found = scan_file_capabilities(path)
        if found:
            per_file[rel] = frozenset(found)
    return per_file


# frob:ticket T-2729
def _aggregate_raw_kinds_by_node(
    binding: CodeBinding, raw_by_file: dict[str, frozenset[str]]
) -> dict[str, frozenset[str]]:
    """Every node id -> the union of an already-scanned `raw_by_file`
    map's values across that node's owned files -- the per-node
    aggregation step split out of `_observed_raw_kinds_by_node` (T-1450)
    so a caller that also needs the per-file map (the per-via SYS101 join)
    can compute the file-level scan once and derive both views from it,
    instead of `_observed_raw_kinds_by_node` re-scanning independently."""
    per_node: dict[str, set[str]] = {}
    for rel, kinds in raw_by_file.items():
        owner = binding.owner[rel]
        per_node.setdefault(owner, set()).update(kinds)
    return {node_id: frozenset(kinds) for node_id, kinds in per_node.items()}


# frob:ticket T-2729
def _observed_raw_kinds_by_node(
    binding: CodeBinding, root: Path
) -> dict[str, frozenset[str]]:
    """Every node id -> the union of RAW `scan_file_capabilities` output
    (no `_EXTENDED_KINDS` filter, no `_KIND_MAP` normalization) across
    that node's `code=`-bound files -- the SINGLE per-file scan pass
    `_observed_extended_kinds_by_node` and `_observed_all_kinds_by_node`
    both derive their view from (H5/T-0830: each owned file used to be
    scanned TWICE, once per view, via two independent copies of this same
    loop; deriving both cheap set views from one raw scan halves the
    per-file resolution work `scan_file_capabilities` does). `binding`
    here is ALWAYS the T-0169 `_capability_binding` superset, never the
    raw `.py`-only `bind_code` output -- see that function's docstring.
    T-1450: now a thin wrapper over `_observed_raw_kinds_by_file` +
    `_aggregate_raw_kinds_by_node` for standalone callers -- the hot path
    (`_collect_sys_violations`) calls the file-level scan directly and
    aggregates itself so it can also hand the per-file map to the SYS101
    per-via join, without a second scan."""
    return _aggregate_raw_kinds_by_node(
        binding, _observed_raw_kinds_by_file(binding, root)
    )


# frob:ticket T-2729
def _extended_kinds_view(
    raw_by_node: dict[str, frozenset[str]],
) -> dict[str, frozenset[str]]:
    """`_EXTENDED_KINDS`-filtered view of an already-scanned raw per-node
    observed-kinds map (T-0830): derives SYS100-extended's vocabulary from
    `_observed_raw_kinds_by_node`'s single scan instead of re-scanning
    every owned file. Only includes a node when its filtered set is
    non-empty, matching the original per-file `if found:` guard. T-1075:
    no longer folds `env-read`/`env-write` through `_UNWIRED_ENV_MODE_
    ALIASES` (removed) -- `env` is no longer in `_EXTENDED_KINDS` at all
    (promoted to the tier-2 `_KIND_MAP` join, `_all_kinds_view` below), so
    this view naturally stops seeing it, same as `fs-read`'s own T-0717
    promotion."""
    return {
        node_id: extended
        for node_id, raw_kinds in raw_by_node.items()
        if (extended := raw_kinds & _EXTENDED_KINDS)
    }


# frob:ticket T-2729
def _all_kinds_view(
    raw_by_node: dict[str, frozenset[str]],
) -> dict[str, frozenset[str]]:
    """`_KIND_MAP`-normalized view of an already-scanned raw per-node
    observed-kinds map (T-0830): derives SYS101's full vocabulary
    (net/fs-write/fs-read/exec/env-read/env-write normalized to the
    precise, mode-qualified spelling `may` declarations resolve to,
    T-0717/T-1075) from `_observed_raw_kinds_by_node`'s single scan
    instead of re-scanning every owned file. Only includes a node with a
    non-empty raw set, matching the original per-file `if normalized:`
    guard (normalizing elementwise never turns a non-empty set empty).
    T-1075: no longer folds `env-read`/`env-write` through `_UNWIRED_ENV_
    MODE_ALIASES` (removed) -- both are now real `_KIND_MAP` keys, so
    `_KIND_MAP.get` alone normalizes them to `env.read`/`env.write`
    exactly like every other wired kind."""
    return {
        node_id: frozenset(_KIND_MAP.get(kind, kind) for kind in kinds)
        for node_id, kinds in raw_by_node.items()
        if kinds
    }


# frob:tests tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock.test_observed_extended_kinds_by_node_only_ever_yields_extended_kinds  # noqa: E501
# frob:ticket T-2729
def _observed_extended_kinds_by_node(
    binding: CodeBinding, root: Path
) -> dict[str, frozenset[str]]:
    """Every node id -> the union of `_EXTENDED_KINDS` capabilities
    `scan_file_capabilities` observes across that node's `code=`-bound
    files (module docstring's SYS100 extended case). `binding` here is
    ALWAYS the T-0169 `_capability_binding` superset, never the raw
    `.py`-only `bind_code` output -- see that function's docstring. Skips
    `is_self_pattern_path` files (T-0201): a pattern-catalog data file's
    needle literals are not code exercising the capability, the same
    self-match class `frob.vet._capability`'s own aggregation excludes.
    T-0830: a thin wrapper over `_observed_raw_kinds_by_node` +
    `_extended_kinds_view` for standalone callers -- the hot path
    (`_collect_sys_violations`) calls those two directly so this view and
    `_observed_all_kinds_by_node`'s share ONE scan of the owned-file set,
    not two."""
    return _extended_kinds_view(_observed_raw_kinds_by_node(binding, root))


# frob:tests tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock.test_observed_all_kinds_by_node_normalizes_through_kind_map  # noqa: E501
# frob:ticket T-2729
def _observed_all_kinds_by_node(
    binding: CodeBinding, root: Path
) -> dict[str, frozenset[str]]:
    """Every node id -> the union of ALL vet capability kinds observed
    across its bound files, net/fs-write/fs-read/exec normalized through
    `_effects.py::_KIND_MAP` to the SAME precise, mode-qualified spelling
    `may` declarations resolve to (`fs.write`/`fs.read`, T-0717) -- SYS101's
    observed side, which (unlike SYS100) needs the full vocabulary
    regardless of THREAT004's scope. `binding` here is the T-0169
    `_capability_binding` superset (see that function's docstring), so
    SYS101 stale-design also covers every registry-scanned language, not
    just Python. Skips `is_self_pattern_path` files (T-0201), same
    self-match exclusion as `_observed_extended_kinds_by_node` -- SYS101's
    declared-but-unobserved direction must not see a pattern catalog's own
    literals as "observed" either, or a real declaration gets masked by
    self-match noise on the OPPOSITE side of the join. T-0717: the old
    `_alias_legacy_fs_observations` bare-`fs`-aliasing hack is REMOVED --
    `_stale_design_violations` now judges staleness per DECLARED ATOM via
    `expand_declared_kind` (any of its modes observed discharges it), so no
    special-casing is needed on the observed side at all. T-0830: a thin
    wrapper over `_observed_raw_kinds_by_node` + `_all_kinds_view` for
    standalone callers -- see `_observed_extended_kinds_by_node`'s
    docstring for why the hot path bypasses both wrappers."""
    return _all_kinds_view(_observed_raw_kinds_by_node(binding, root))



# frob:ticket T-0361
# frob:waive DUP001 reason="T-1870: this 95%-similarity match against \
# src/frob/testing/_collect_ts.py::_find_ts_test_files only became visible after this \
# ticket deleted ~1900 unrelated lines earlier in this file, shifting the \
# duplicate-detector's resolution window -- the function body itself is byte-for-byte \
# unchanged by this ticket (confirmed: git show main:src/frob/strata/_selfconform.py \
# has the identical function, and this DUP001 does not fire against main at all). \
# Deduplicating a pre-existing, coincidental filesystem-walk similarity across two \
# unrelated modules (strata self-conformance vs. TS test-file discovery) is a real but \
# separate refactor, out of this ticket's declared scope"
# frob:ticket T-2729
def _repo_files_excluding_skip_dirs(root: Path) -> list[str]:
    """Every real file under `root`, as `root`-relative posix paths, with
    any path whose parts include a skip-dir (`is_skipped_dir`) omitted;
    split out of `_fully_excluded_node_ids`'s file-collection phase
    (T-0361)."""
    # Deliberately skip-dir-only pruning (no [graph].exclude): the SYS101
    # caller needs the pre-exclude file set to compare against is_excluded()
    # per-glob itself, so this cannot route through walk_pruned's
    # exclude_globs=() (which would fall back to loading frob.toml's
    # globs and collapse that distinction). Still prunes mid-descent via
    # os.walk's dirnames mutation, same as walk_pruned, just on a narrower
    # predicate.
    all_files: list[str] = []
    # frob:waive WALK001 reason="deliberately skip-dir-only, no [graph].exclude \
    # pruning -- the SYS101 caller needs the pre-exclude file set to compare against \
    # is_excluded() per-glob itself; walk_pruned's exclude_globs=() default would load \
    # frob.toml globs and collapse that distinction. Still prunes mid-descent via \
    # dirnames mutation, same shape as walk_pruned, just a narrower predicate"
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not is_skipped_dir(d)]
        current = Path(dirpath)
        for name in filenames:
            all_files.append((current / name).relative_to(root).as_posix())
    return sorted(all_files)


# frob:ticket T-0310
# frob:ticket T-2729
def _fully_excluded_node_ids(model: KernelModel, root: Path) -> frozenset[str]:
    """Node ids whose ENTIRE `code=` glob set resolves to `[graph].exclude`'d
    paths (T-0310, docs/strata/selfconform.md#sys101-fully-excluded-nodes):
    SYS101's 'declared but never observed' is a category error for such a
    node -- capability observation already skips excluded files (this
    module's `_sorted_capability_files`/`_capability_binding`, T-0274), so
    there is provably no file, excluded or not, observation could EVER see.
    A node qualifies only if its glob matches at least one REAL (skip-dir-
    filtered) file AND every such match is excluded -- a glob matching
    nothing at all is a different, pre-existing case (e.g. a typo'd glob)
    left to fire SYS101 unchanged, since that is genuine potential drift,
    not a structurally-unobservable node. Uses the SAME exclude source
    (`load_exclude_globs`/`is_excluded`) `_sorted_capability_files` already
    uses for observation, so observation and this skip cannot diverge."""
    exclude_globs = load_exclude_globs(root)
    if not exclude_globs:
        return frozenset()
    all_files = _repo_files_excluding_skip_dirs(root)
    fully_excluded: set[str] = set()
    for node in model.nodes:
        globs = _node_code_globs(node)
        if not globs:
            continue
        matched = [
            rel for rel in all_files if any(fnmatch.fnmatch(rel, g) for g in globs)
        ]
        if not matched:
            continue  # glob matches nothing at all -- unaffected, not this fix's target
        if all(is_excluded(rel, exclude_globs) for rel in matched):
            fully_excluded.add(node.id)
            _log.info(
                "selfconform: SYS101 skip: node %s code= glob resolves entirely "
                "to graph-excluded paths (%d file(s)); capability declarations "
                "unverifiable",
                node.id,
                len(matched),
            )
    return frozenset(fully_excluded)


# frob:ticket T-2729
def _raw_declared_kinds(node) -> frozenset[str]:  # noqa: ANN001
    """Every RAW (un-expanded, un-canonicalized) capability kind `node`'s
    `may` atoms name -- `_stale_design_violations`'s per-atom granularity
    needs the ORIGINAL spelling (`"fs"`, `"fs-read"`, `"fs.read"`, ...) so
    a waiver naming `SYS101:fs` still matches and a finding's `detail`
    still reads the declaration the author actually wrote, never a
    post-expansion synthetic id."""
    return frozenset(_may_kind(atom) for atom in node.may)


# frob:ticket T-2729
def _node_owned_files(binding: CodeBinding, node_id: str) -> list[str]:
    """Every owned file (`rel` path) `binding` binds to `node_id` -- T-1450's
    per-grant SYS101 join narrows this by a grant's own `via` globs, so it
    needs the node's owned-file set directly rather than the already-
    aggregated per-node kind union `observed_by_node` used to hand it."""
    return sorted(rel for rel, owner in binding.owner.items() if owner == node_id)


# frob:ticket T-2729
def _observed_kinds_for_files(
    files: list[str], all_kinds_by_file: dict[str, frozenset[str]]
) -> frozenset[str]:
    """The union of `all_kinds_by_file`'s (already `_KIND_MAP`-normalized,
    T-1450) values across `files` -- shared by a via-less grant's whole-
    node join and a `via`-scoped grant's narrowed join, the only
    difference between the two being which file list is passed in."""
    observed: set[str] = set()
    for rel in files:
        observed |= all_kinds_by_file.get(rel, frozenset())
    return frozenset(observed)



# frob:ticket T-2729
def _node_attr_values(node, prefix: str) -> list[str]:  # noqa: ANN001
    """Every `node.attrs` entry's tail past `prefix`, in declaration order
    -- the same opaque-attr-string convention `_code_binding.py::
    _node_code_globs` reads for `code=`, generalized to `interface=`/
    `purpose=` so SYS104/SYS105 do not duplicate the split logic."""
    return [attr[len(prefix) :] for attr in node.attrs if attr.startswith(prefix)]

