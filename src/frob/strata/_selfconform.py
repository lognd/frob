"""frob self-conformance: reconcile OUR OWN `src/frob/` capability surface
against the interfaces `design/frob.strata` declares (T-0150,
docs/strata/selfconform.md).

POST-REVIEW REWORK (T-0150 REJECT round): the first version of this
module invented a parallel `frob.toml` node<->path/node<->capability
mapping, on the mistaken belief that `code=`/`may` were not reachable
from `.strata` surface text. They ARE (T-0132, `strata-core/src/parse.rs`
`code STRING+` / `may STRING`, `_elaborate.py::_elaborate_node` maps them
straight onto `Node.attrs`'s `code=<glob>` convention and `Node.may`) --
`design/frob.strata`'s own header comment was simply stale and has been
corrected as part of this rework. This module is now a THIN layer: it
declares `code "..."`/`may "..."` directly on `design/frob.strata`'s
nodes (measured honestly from a real `scan_file_capabilities` sweep, same
numbers as the original version) and reuses the ALREADY-SHIPPED
`bind_code` (T-0078) + `check_capability_conformance`/THREAT004 (T-0079/
T-0113) machinery wherever it already expresses one of this ticket's three
rules. Only what that machinery genuinely cannot express gets new code
here, each with a written gap statement:

SYS100 undeclared interface -- a capability OBSERVED in a node's
`code=`-bound files but not DECLARED in that node's `may` atoms.
  - net/fs-write/exec: DELEGATED to `check_capability_conformance`
    (THREAT004) verbatim, just relabeled SYS100 -- that function already
    computes exactly this join at file:line granularity via `_effects.py`'s
    `_KIND_MAP`/`_line_effects`, zero new detection.
  - eval/env/ffi/install-hook: NEW code (`_extended_kind_violations`).
    GAP STATEMENT: `_effects.py::_KIND_MAP` is scoped (by its own
    docstring, T-0079) to net/fs-write/exec only -- "eval/env/ffi/
    install-hook are vet-specific dependency-vetting signals with no
    `may`-capability analog yet" -- so THREAT004 structurally cannot see
    these four kinds no matter what `may` declares. `scan_file_
    capabilities` (vet's own per-file scanner, already imported
    READ-ONLY by `_effects.py` for the other three kinds) is reused
    directly for these four, at file granularity, joined against
    `Node.may` via `_effects.py::_declared_kinds` (reused, not
    reimplemented).

SYS101 stale design -- a capability DECLARED in a node's `may` atoms with
zero observed sites anywhere in that node's `code=`-bound files. NEW code
for ALL kinds. GAP STATEMENT: neither `check_capability_conformance` nor
any other shipped join checks this direction -- THREAT004's `_effects.py`
module docstring is explicit that "an observed effect with no matching
`may` declaration is a violation... not a silent pass" is the ONLY
direction it discharges; a declared-but-unexercised capability is not a
concept the tier-2 machinery has ever computed. `check_effect_
completeness`'s own docstring (`_threat.py`) confirms this: THREAT004 is
"the code-level `undeclared capability in code is an error` kicker",
singular direction.

SYS102 unmodeled code -- a `src/frob/` top-level directory whose `.py`
files are ALL bound to `FOREIGN` (or entirely absent from `bind_code`'s
partition) -- i.e. no node's `code=` glob claims it at all. NEW code.
GAP STATEMENT: `bind_code` computes the FOREIGN bucket but nothing
downstream currently treats "this directory is entirely FOREIGN" as a
reportable finding; `check_import_conformance` explicitly SKIPS FOREIGN
files ("an unclassified file names no kernel node to attest the
crossing against") rather than flagging them, which is correct for ITS
rule (imports) but leaves "a whole directory has no owner" unraised
anywhere -- exactly the gap this ticket asked SYS102 to close.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs
from frob.logging import get_logger
from frob.vet._capability import (
    is_self_pattern_path,
    language_for,
    scan_file_capabilities,
)

from ._code_binding import FOREIGN, CodeBinding, _node_code_globs, bind_code
from ._effects import _KIND_MAP, _declared_kinds, check_capability_conformance
from ._errors import StrataError
from ._models import KernelModel
from ._waive import STALE_WAIVER_RULE, apply_waivers, stale_detail

_log = get_logger(__name__)

# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS100 undeclared interface: a capability
#: observed in a node's `code=`-bound files but not declared in `may`.
SYS_UNDECLARED_INTERFACE = "SYS100"
# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS101 stale design: a `may` capability
#: declared for a node but never observed in its `code=`-bound files.
SYS_STALE_DESIGN = "SYS101"
# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS102 unmodeled code: a `src/frob/`
#: directory whose files are all `FOREIGN` to `bind_code`'s partition.
SYS_UNMODELED_CODE = "SYS102"

#: `src/` subtree self-conformance actually scans -- our own package root
#: (module docstring: `design/frob.strata` models exactly this one tree).
_PACKAGE_ROOT = "src/frob"

#: The vet capability kinds THREAT004's `_effects.py::_KIND_MAP` has no
#: tier-2 analog for (module docstring's SYS100 gap statement) -- the ONLY
#: kinds this module's own file-level scan needs to cover, since net/fs-
#: write/exec are fully delegated to `check_capability_conformance`. T-0158
#: adds `sql`/`deserialize`/`html_render`/`fetch_url`/`client_storage`: new
#: `CAPABILITY_KINDS` the structured dangerous-operations registry patterns
#: that likewise have no `_KIND_MAP` tier-2 analog.
_EXTENDED_KINDS = frozenset(
    {
        "eval",
        "env",
        "ffi",
        "install-hook",
        "sql",
        "deserialize",
        "html_render",
        "fetch_url",
        "client_storage",
        #: T-0018 (graphite adoption): read-only filesystem access, split
        #: from `fs`/`fs-write` so a node that only ever reads is not
        #: forced into a `waive "SYS101:fs"` (module docstring below,
        #: `_alias_legacy_fs_observations`).
        "fs-read",
    }
)


# frob:doc docs/strata/selfconform.md#the-three-rules
class SelfConformViolation(BaseModel):
    """One SYS100/SYS101/SYS102 finding: rule id, the node (or directory,
    for SYS102) it concerns, a human-readable detail string, and (SYS100/
    SYS101 only) the capability kind this specific instance fired for.
    `capability` is T-0174's multi-instance sub-target: SYS100/SYS101 can
    each fire more than once per node (once per capability kind), so a
    `waive` clause targeting one of them must name a sub-target
    (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`) and matching needs a
    structured field to compare against -- never parsed back out of
    `detail`'s free text."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    capability: str | None = None


# frob:doc docs/strata/selfconform.md#the-three-rules
class SelfConformReport(BaseModel):
    """Every UNWAIVED self-conformance violation, in rule-then-node order
    (module docstring), plus `waived` (T-0174: findings suppressed by a
    matching `waive` clause, kept here for report visibility -- never
    silently dropped, `_waive.py` module docstring). A stale waiver (its
    `(node, rule)` matched zero findings) is folded back INTO `violations`
    as a `SYSWAIVE002` entry rather than a separate field, so the existing
    `not selfconform.danger_ok.violations` gate condition (`sys_runner.py::
    _run_audit`) fails closed on drift without a second check to forget."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[SelfConformViolation, ...] = ()
    waived: tuple[SelfConformViolation, ...] = ()


def _core_undeclared_violations(
    model: KernelModel, binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS100 for net/fs-write/exec, delegated verbatim to THREAT004's
    `check_capability_conformance` -- zero new detection (module
    docstring's SYS100 core case). REVIEWER-CAUGHT T-0169 CORRECTION: this
    function does no language filtering itself -- it only ever sees what
    `binding` puts in front of it. Earlier in this same ticket, the caller
    passed `bind_code`'s raw Python-only binding here on the mistaken
    belief that `check_capability_conformance` was Python-import-syntax-
    specific like `bind_code`'s OWN binding step is. It is not:
    `_effects.py::_line_effects`/`check_capability_conformance` call
    `language_for`/`_PATTERNS` directly, the SAME multi-language
    (python/typescript/rust/c-cpp) machinery `vet._capability` and this
    module's SYS100-extended/SYS101 already use -- there is no Python-
    specific parsing anywhere in this delegated path. So `check_self_
    conformance` now passes THIS function the same `_capability_binding`
    superset as the other two rules, and a `.ts`/`.rs`/`.c`/`.cpp` file's
    raw net/fs-write/exec effects reach SYS100 exactly like a `.py`
    file's do."""
    conformance = check_capability_conformance(model, binding, root)
    return [_core_undeclared_violation(v) for v in conformance.violations]


def _core_undeclared_violation(violation) -> SelfConformViolation:  # noqa: ANN001
    """Build the SYS100 finding for one THREAT004 conformance violation,
    split out of `_core_undeclared_violations` purely to keep its loop
    body short."""
    _log.warning(
        "selfconform: SYS100 (via THREAT004) %s:%d %s effect on %s",
        violation.file,
        violation.line,
        violation.kind,
        violation.component,
    )
    return SelfConformViolation(
        rule=SYS_UNDECLARED_INTERFACE,
        node=violation.component,
        detail=(
            f"capability {violation.kind!r} observed at "
            f"{violation.file}:{violation.line} but not declared"
        ),
        capability=violation.kind,
    )


def _sorted_owned_files(binding: CodeBinding) -> list[str]:
    """Every non-`FOREIGN` bound file path, in deterministic order
    (mirrors `_effects.py::_sorted_owned_files`)."""
    return sorted(rel for rel, owner in binding.owner.items() if owner != FOREIGN)


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
    for path in sorted(root.rglob("*")):
        if not path.is_file() or language_for(path) is None:
            continue
        rel_path = path.relative_to(root)
        if any(is_skipped_dir(part) for part in rel_path.parts):
            continue
        if exclude_globs and is_excluded(rel_path.as_posix(), exclude_globs):
            continue
        found.append(path)
    return found


def _capability_binding(
    model: KernelModel, binding: CodeBinding, root: Path
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
    this module sees every registry-covered language, not just Python)."""
    globs = [(node.id, glob) for node in model.nodes for glob in _node_code_globs(node)]
    owner = dict(binding.owner)
    for path in _sorted_capability_files(root):
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
    self-match class `frob.vet._capability`'s own aggregation excludes."""
    per_node: dict[str, set[str]] = {}
    for rel in _sorted_owned_files(binding):
        path = root / rel
        if is_self_pattern_path(path, root):
            continue
        owner = binding.owner[rel]
        found = scan_file_capabilities(path) & _EXTENDED_KINDS
        if found:
            per_node.setdefault(owner, set()).update(found)
    return {node_id: frozenset(kinds) for node_id, kinds in per_node.items()}


def _observed_all_kinds_by_node(
    binding: CodeBinding, root: Path
) -> dict[str, frozenset[str]]:
    """Every node id -> the union of ALL vet capability kinds observed
    across its bound files, net/fs-write/exec normalized through
    `_effects.py::_KIND_MAP` to the SAME kind spelling `may` declarations
    use ("fs" not "fs-write") -- SYS101's observed side, which (unlike
    SYS100) needs the full vocabulary regardless of THREAT004's scope.
    `binding` here is the T-0169 `_capability_binding` superset (see that
    function's docstring), so SYS101 stale-design also covers every
    registry-scanned language, not just Python. Skips `is_self_pattern_
    path` files (T-0201), same self-match exclusion as `_observed_
    extended_kinds_by_node` -- SYS101's declared-but-unobserved direction
    must not see a pattern catalog's own literals as "observed" either, or
    a real declaration gets masked by self-match noise on the OPPOSITE
    side of the join."""
    per_node: dict[str, set[str]] = {}
    for rel in _sorted_owned_files(binding):
        path = root / rel
        if is_self_pattern_path(path, root):
            continue
        owner = binding.owner[rel]
        raw = scan_file_capabilities(path)
        normalized = {_KIND_MAP.get(kind, kind) for kind in raw}
        if normalized:
            per_node.setdefault(owner, set()).update(normalized)
    return {
        node_id: _alias_legacy_fs_observations(frozenset(kinds))
        for node_id, kinds in per_node.items()
    }


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
def _alias_legacy_fs_observations(observed: frozenset[str]) -> frozenset[str]:
    """T-0018 (graphite adoption) backward compatibility: a pre-existing
    `may "fs"` declaration predates the `fs-read`/`fs-write` split and meant
    "any real filesystem access". If `observed` contains `fs-read` (a
    read-only node), also report bare `fs` as observed so SYS101's
    `declared - observed` join does not call an existing `may "fs"`
    declaration stale just because the only real access turns out to be
    reads rather than writes. Deliberately one-directional and confined to
    SYS101's declared-vs-observed side only (`_stale_design_violations`) --
    NOT applied to SYS100's observed-vs-declared side
    (`_extended_kind_violations`/`_core_undeclared_violations`), which would
    otherwise report both `fs-read` and its `fs` alias as separately
    undeclared for the same single read observation, a redundant duplicate
    finding for one real capability. A node that declares `may "fs-read"`
    specifically is unaffected either way: it already matches the raw
    `fs-read` observation with no aliasing needed."""
    if "fs-read" in observed and "fs" not in observed:
        return observed | {"fs"}
    return observed


def _extended_kind_violations(
    model: KernelModel, binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS100 for eval/env/ffi/install-hook (+ `fs-read`) -- the slice
    `check_capability_conformance` structurally cannot see (module
    docstring's SYS100 gap statement). T-0304 follow-up (SYS100 direction
    of the `fs`/`fs-read` split, `_alias_legacy_fs_observations`'s sibling
    on THIS side of the join): a bare `may "fs"` declaration predates the
    split and means "any real filesystem access", so it is a SUPERSET of
    `fs-read` and must cover an observed `fs-read` with no finding -- a
    node that only ever reads should not have to narrow its own broader
    `may "fs"` down to `may "fs-read"` just to silence SYS100. This is
    deliberately one-directional and confined to `fs-read` specifically:
    a node declaring `may "fs-read"` only does NOT cover an observed
    fs-write-class effect (that join lives in `_core_undeclared_
    violations`/THREAT004, which already requires `may "fs"` for a
    fs-write observation and correctly still fires when only `fs-read`
    is declared) -- narrower declarations never cover broader
    observations, only the reverse."""
    observed_by_node = _observed_extended_kinds_by_node(binding, root)
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        full_declared = _declared_kinds(node)
        declared = full_declared & _EXTENDED_KINDS
        if "fs" in full_declared:
            declared = declared | {"fs-read"}
        observed = observed_by_node.get(node.id, frozenset())
        # frob:waive PERF004 reason="distinct small per-node diff set, not repeated"
        for kind in sorted(observed - declared):
            _log.warning(
                "selfconform: SYS100 (extended) %s observed but undeclared on %s",
                kind,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_UNDECLARED_INTERFACE,
                    node=node.id,
                    detail=f"capability {kind!r} observed but not declared",
                    capability=kind,
                )
            )
    return found


# frob:doc docs/strata/selfconform.md#sys101-fully-excluded-nodes
# frob:ticket T-0310
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
    all_files: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(root)
        if any(is_skipped_dir(part) for part in rel_path.parts):
            continue
        all_files.append(rel_path.as_posix())
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


def _stale_design_violations(
    model: KernelModel, binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS101 over every kind (net/fs/exec included) -- new code, since no
    shipped join checks this direction (module docstring's SYS101 gap
    statement). T-0310: skips any node in `_fully_excluded_node_ids` --
    a node whose entire code-glob set is graph-excluded has nothing
    observable, so 'declared but never observed' is a category error, not
    real design drift (docs/strata/selfconform.md#sys101-fully-excluded-nodes)."""
    observed_by_node = _observed_all_kinds_by_node(binding, root)
    skip_nodes = _fully_excluded_node_ids(model, root)
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        if node.id in skip_nodes:
            continue
        declared = _declared_kinds(node)
        observed = observed_by_node.get(node.id, frozenset())
        # frob:waive PERF004 reason="distinct small per-node diff set, not repeated"
        for kind in sorted(declared - observed):
            _log.warning(
                "selfconform: SYS101 %s declared but never observed on %s",
                kind,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_STALE_DESIGN,
                    node=node.id,
                    detail=f"capability {kind!r} declared but never observed",
                    capability=kind,
                )
            )
    return found


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


def _unmodeled_violations(
    root: Path, binding: CodeBinding
) -> list[SelfConformViolation]:
    """SYS102: every top-level `src/frob/` directory whose files (if any)
    are ALL `FOREIGN` to `code=`'s partition -- no node's `code=` glob
    claims it at all (module docstring's SYS102 gap statement). `binding`
    is the T-0169 `_capability_binding` superset here, not `bind_code`'s
    raw `.py`-only output: a directory containing ONLY a `.ts`/`.rs`/etc.
    file that a node's `code=` glob genuinely claims used to misreport
    SYS102 ("unmodeled") because the Python-only binding never bound that
    file at all -- a spurious finding on top of the missed SYS100/SYS101,
    now fixed by using the same superset every other rule in this module
    uses."""
    prefix_owned: set[str] = set()
    for rel, owner in binding.owner.items():
        if owner == FOREIGN or not rel.startswith(f"{_PACKAGE_ROOT}/"):
            continue
        top = rel[len(_PACKAGE_ROOT) + 1 :].split("/", 1)[0]
        prefix_owned.add(top)

    found: list[SelfConformViolation] = []
    for name in _top_level_dirs(root):
        if name in prefix_owned:
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


# frob:doc docs/strata/selfconform.md#the-three-rules
def check_self_conformance(
    model: KernelModel, root: Path
) -> Result[SelfConformReport, StrataError]:
    """The `frob sys audit` self-conformance entrypoint (T-0150): `bind_code`
    (T-0078, reused verbatim) partitions `src/frob/` by each node's `code=`
    glob, then SYS100/SYS101/SYS102 reconcile that partition against
    `Node.may` (module docstring: SYS100's net/fs-write/exec slice
    delegates to THREAT004 outright; the rest is new code with a written
    gap statement each). ALL THREE rules run over `_capability_binding`'s
    superset (T-0169), not `bind_code`'s raw `.py`-only partition:
    `check_capability_conformance` (SYS100 core's delegate) is language-
    generic (`_effects.py::_line_effects` uses `language_for`/`_PATTERNS`,
    no Python-specific parsing), so restricting it to the Python-only
    binding was itself part of the same wiring bug this ticket fixes (see
    `_core_undeclared_violations`'s docstring). SYS102 also uses the
    superset for its ownership check, so a directory claimed only through
    a non-Python file no longer misreports as unmodeled (see
    `_unmodeled_violations`'s docstring). `bind_code`'s raw Python-only
    binding remains the ONLY input to `bind_code` itself (Python-import-
    syntax-specific by design) -- it is simply no longer handed to any
    SYS100/SYS101/SYS102 join. `Err` propagates `bind_code`'s (or
    `_capability_binding`'s) `AmbiguousCodeBinding` unchanged -- deny by
    default, never a silent partial scan."""
    bound_binding = _bind_conformance_inputs(model, root)
    if bound_binding.is_err:
        return Err(bound_binding.danger_err)
    capability_binding = bound_binding.danger_ok

    violations = _collect_sys_violations(model, capability_binding, root)
    applied = _apply_sys_waivers(model, violations)
    return Ok(_finalize_self_conform_report(applied, root))


def _finalize_self_conform_report(applied, root: Path) -> SelfConformReport:  # noqa: ANN001
    """Fold stale-waiver findings + waived-violation details and log the
    summary, split out of `check_self_conformance` purely to keep that
    function's body short."""
    kept = list(applied.kept)
    kept.extend(_stale_waiver_violations(applied))
    waived_violations = _fold_waived_violations(applied)
    _log.info(
        "selfconform: %d violation(s), %d waived, %d stale waiver(s) found under %s",
        len(kept),
        len(waived_violations),
        len(applied.stale),
        root,
    )
    return SelfConformReport(violations=tuple(kept), waived=waived_violations)


def _bind_conformance_inputs(
    model: KernelModel, root: Path
) -> Result[CodeBinding, StrataError]:
    """`bind_code` then `_capability_binding`, in order -- the two fallible
    binding steps `check_self_conformance` needs before any SYS rule can
    run, split out purely to keep that function's body short."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    capability_bound = _capability_binding(model, bound.danger_ok, root)
    if capability_bound.is_err:
        return Err(capability_bound.danger_err)
    return Ok(capability_bound.danger_ok)


def _collect_sys_violations(
    model: KernelModel, capability_binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """Every SYS100/SYS100-extended/SYS101/SYS102 finding, in that order,
    for `check_self_conformance`."""
    violations = _core_undeclared_violations(model, capability_binding, root)
    violations.extend(_extended_kind_violations(model, capability_binding, root))
    violations.extend(_stale_design_violations(model, capability_binding, root))
    violations.extend(_unmodeled_violations(root, capability_binding))
    return violations


def _apply_sys_waivers(model: KernelModel, violations: list[SelfConformViolation]):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174): a
    matched waiver moves its finding into `waived` (still visible, never
    dropped); a waiver that matched nothing is STALE and becomes a new
    SYSWAIVE002 violation so drift fails the audit rather than silently
    going stale forever (`_waive.py` module docstring). Split out of
    `check_self_conformance` purely to keep that function's body short."""
    sys_rules = frozenset(
        (SYS_UNDECLARED_INTERFACE, SYS_STALE_DESIGN, SYS_UNMODELED_CODE)
    )
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        # T-0174 REJECT round: SYS100/SYS101 fire once per capability kind
        # per node, so the sub-target IS the capability kind
        # (`SelfConformViolation.capability`); SYS102 has no sub-target
        # concept (one finding per unmodeled directory) and returns None.
        sub_target_of=lambda v: v.capability,
        # T-0174: this call only ever sees SYS100-102 findings -- a waiver
        # declared for any other rule (LINT004, THREAT002, ...) belongs to
        # `evaluate_exhaustiveness`'s pass, not this one (apply_waivers'
        # `in_scope` docstring: staleness must be judged only against
        # waivers this caller can actually match).
        in_scope=lambda rule: rule in sys_rules,
    )


def _stale_waiver_violations(applied) -> list[SelfConformViolation]:  # noqa: ANN001
    """One `STALE_WAIVER_RULE` finding per stale waiver in `applied`, for
    `check_self_conformance`."""
    return [
        SelfConformViolation(
            rule=STALE_WAIVER_RULE, node=stale.node, detail=stale_detail(stale)
        )
        for stale in applied.stale
    ]


def _fold_waived_violations(applied) -> tuple[SelfConformViolation, ...]:  # noqa: ANN001
    """Fold each waiver's reason/ticket into its matched violation's
    `detail` -- `report.waived` must show WHY, never just THAT (module
    docstring's "loud in output" requirement, mirrors `frob.gates`'s
    `WaiverRef`-annotated `Violation.waived`). T-0174 REJECT round: folds
    `wf.waiver.rule` (the RAW declared string, e.g. "SYS100:fs-write")
    into the printed detail, not just `wf.finding.rule` (the bare family)
    -- a reader must see the exact sub-target a waiver named, never just
    that SOME waiver on this rule matched (module docstring's "no blanket
    waivers"). Split out of `check_self_conformance` purely to keep that
    function's body short."""
    return tuple(
        wf.finding.model_copy(
            update={
                "detail": (
                    f"{wf.finding.detail} -- WAIVED[{wf.waiver.rule}]: "
                    f"{wf.waiver.reason!r}"
                    + (f" (ticket {wf.waiver.ticket})" if wf.waiver.ticket else "")
                )
            }
        )
        for wf in applied.waived
    )


__all__ = [
    "SYS_STALE_DESIGN",
    "SYS_UNDECLARED_INTERFACE",
    "SYS_UNMODELED_CODE",
    "SelfConformReport",
    "SelfConformViolation",
    "check_self_conformance",
]
