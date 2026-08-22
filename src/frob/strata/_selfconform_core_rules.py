"""SYS100/SYS101/SYS103 rule family (T-2729 layer 2, split out of
`_selfconform.py`): undeclared interface, stale design, and coverage
totality. Each function here computes ONE rule's violation list from the
shared observed-kinds layer (`_selfconform_kinds.py`) plus THREAT004's
`check_capability_conformance` -- see `_selfconform.py`'s own module
docstring for the full SYS100/SYS101/SYS103 design narrative (gap
statements, delegation boundaries); this module holds only the code."""

from __future__ import annotations

from pathlib import Path

from frob.logging import get_logger
from frob.vet._capability import is_self_pattern_path, scan_file_capabilities
from frob.vet._capability_modes import canonical_declared_kind, expand_declared_kind

from ._code_binding import FOREIGN, CodeBinding
from ._effects import (
    _declared_kinds,
    _may_kind,
    _via_matches,
    check_capability_conformance,
)
from ._models import KernelModel
from ._selfconform_ids import (
    SYS_COVERAGE_TOTALITY,
    SYS_STALE_DESIGN,
    SYS_UNDECLARED_INTERFACE,
)
from ._selfconform_kinds import (
    _EXTENDED_KINDS,
    _fully_excluded_node_ids,
    _node_owned_files,
    _observed_kinds_for_files,
    _raw_declared_kinds,
    _sorted_capability_files,
)
from ._selfconform_models import SelfConformViolation

_log = get_logger(__name__)


# frob:ticket T-2729
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


# frob:ticket T-2729
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



# frob:ticket T-2729
def _extended_kind_violations(
    model: KernelModel, observed_by_node: dict[str, frozenset[str]]
) -> list[SelfConformViolation]:
    """SYS100 for eval/process-control/ffi/install-hook/sql/deserialize/
    html_render/fetch_url/client_storage -- the slice `check_capability_conformance`
    structurally cannot see (module docstring's SYS100 gap statement).
    T-0717: `fs-read` moved OUT of `_EXTENDED_KINDS` into `_effects.py::
    _KIND_MAP` (it now has a real tier-2/THREAT004 analog as `fs.read`),
    so this function no longer needs a bare-`fs`-covers-`fs-read` special
    case -- `_declared_kinds` already expands a coarse `may "fs"`
    declaration to `{fs.read, fs.write}` generically (`expand_declared_
    kind`), and `_dedupe_sys100_extended_against_core` keeps the core
    (THREAT004-delegated) pass as the single source of truth for it.
    T-0830: `observed_by_node` is precomputed by the caller (an
    `_extended_kinds_view` derivation) instead of this function scanning
    the owned-file set itself, so `_collect_sys_violations` can share ONE
    raw scan with `_stale_design_violations` instead of two independent
    passes."""
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        declared = _declared_kinds(node) & _EXTENDED_KINDS
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


# frob:ticket T-2729
def _stale_grant_violation(
    node_id: str, raw_kind: str, via: tuple[str, ...]
) -> SelfConformViolation:
    """Build one SYS101 finding for a declared-but-unobserved atom, split
    out of `_stale_design_violations_for_node` (T-1450) purely to keep its
    loop body short. `via`, when present, is folded into `detail` so the
    finding names the specific surface that failed to discharge it -- not
    just the node, which per-via staleness (unlike the old whole-node
    join) can no longer imply on its own."""
    _log.warning(
        "selfconform: SYS101 %s declared but never observed on %s%s",
        raw_kind,
        node_id,
        f" via {list(via)}" if via else "",
    )
    detail = f"capability {raw_kind!r} declared but never observed"
    if via:
        detail += f" via {', '.join(via)}"
    return SelfConformViolation(
        rule=SYS_STALE_DESIGN,
        node=node_id,
        detail=detail,
        capability=raw_kind,
    )


# frob:ticket T-2729
def _stale_design_violations_for_node(
    node,  # noqa: ANN001
    binding: CodeBinding,
    all_kinds_by_file: dict[str, frozenset[str]],
) -> list[SelfConformViolation]:
    """One node's SYS101 findings (T-1450): iterates `node.may_grants`
    (populated for every parsed `may` clause, with or without `via` --
    `strata-core/src/parse/grammar_node.rs`) rather than the flat, kind-
    deduped `_raw_declared_kinds(node)` set the old whole-node join used,
    so a `via`-scoped grant is judged only against the files its own glob
    covers while a via-less grant on the SAME kind keeps the old whole-
    node join -- the exact "a dead grant on one file is flagged even
    while another file legitimately uses the same kind" acceptance clause
    this ticket exists for. `node.may_grants` empty entirely (a `Node`
    built directly, bypassing the parser -- most unit-test fixtures) falls
    back to the pre-T-1450 whole-node-only join over
    `_raw_declared_kinds`, an exact behavior-preserving path (mirrors
    `_effects.py::_declared_kinds_for_file`'s own legacy fallback)."""
    owned_files = _node_owned_files(binding, node.id)
    whole_node_observed = _observed_kinds_for_files(owned_files, all_kinds_by_file)
    found: list[SelfConformViolation] = []
    if not node.may_grants:
        # frob:waive PERF004 reason="distinct small per-node diff set, not repeated"
        for raw_kind in sorted(_raw_declared_kinds(node)):
            canonical = canonical_declared_kind(raw_kind)
            expanded = expand_declared_kind(canonical)
            if expanded & whole_node_observed:
                continue
            found.append(_stale_grant_violation(node.id, raw_kind, ()))
        return found
    seen: set[tuple[str, tuple[str, ...]]] = set()
    # frob:waive PERF004 reason="distinct small per-node grant list, not repeated"
    for grant in node.may_grants:
        raw_kind = _may_kind(grant.atom)
        key = (raw_kind, grant.via)
        if key in seen:
            continue  # duplicate (kind, via) grant -- already judged
        seen.add(key)
        if grant.via:
            matched_files = [rel for rel in owned_files if _via_matches(rel, grant.via)]
            observed = _observed_kinds_for_files(matched_files, all_kinds_by_file)
        else:
            observed = whole_node_observed
        canonical = canonical_declared_kind(raw_kind)
        expanded = expand_declared_kind(canonical)
        if expanded & observed:
            continue
        found.append(_stale_grant_violation(node.id, raw_kind, grant.via))
    return found


# frob:invariant INV-026
# invariant spec: [INV-026](invariants/INV-026.md)
# frob:tests tests/unit/strata/test_selfconform.py::TestStaleDesign.test_stale_design_skips_node_fully_within_graph_exclude  # noqa: E501
# frob:tests tests/unit/strata/test_selfconform.py::TestStaleDesign.test_via_scoped_grant_stale_while_other_surface_uses_same_kind  # noqa: E501
# frob:ticket T-2729
def _stale_design_violations(
    model: KernelModel,
    root: Path,
    binding: CodeBinding,
    all_kinds_by_file: dict[str, frozenset[str]],
) -> list[SelfConformViolation]:
    """SYS101 over every kind (net/fs/exec included) -- new code, since no
    shipped join checks this direction (module docstring's SYS101 gap
    statement). T-0310: skips any node in `_fully_excluded_node_ids` --
    a node whose entire code-glob set is graph-excluded has nothing
    observable, so 'declared but never observed' is a category error, not
    real design drift (docs/strata/selfconform.md#sys101-fully-excluded-nodes).

    T-0717: judged PER RAW DECLARED ATOM, not over the flat expanded-kind
    set difference -- a declared atom is stale only if NONE of the precise
    modes it covers (`expand_declared_kind`) was ever observed. This is
    what makes a precise `may "fs.read"` declaration discharge NARROWLY
    (acceptance clause 1: only `fs.read` itself can satisfy it) while a
    coarse `may "fs"` declaration keeps discharging on EITHER mode being
    observed (mandate point 2/old `_alias_legacy_fs_observations`
    backward-compat behavior, now a natural consequence of this generic
    per-atom join rather than fs-specific code).

    T-1450: judged PER MAY-VIA SURFACE, not per whole-node kind -- delegated
    to `_stale_design_violations_for_node` per node (see its docstring for
    the per-grant join and the legacy whole-node fallback). `binding` is
    the T-0169 capability-binding superset (needed to resolve each node's
    owned-file set for the per-`via` narrowing); `all_kinds_by_file` is
    precomputed by the caller (an `_all_kinds_view` derivation over
    `_observed_raw_kinds_by_file`, T-0830's single-scan discipline
    extended to file granularity) instead of this function scanning the
    owned-file set itself -- see `_extended_kind_violations`'s docstring
    for why."""
    skip_nodes = _fully_excluded_node_ids(model, root)
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        if node.id in skip_nodes:
            continue
        found.extend(
            _stale_design_violations_for_node(node, binding, all_kinds_by_file)
        )
    return found


# frob:tests tests/unit/strata/test_selfconform.py::TestCoverageTotality.test_foreign_file_with_capability_fires_sys103  # noqa: E501
# frob:ticket T-2729
def _coverage_totality_scan_prefix(root: Path) -> str | None:
    """UNRESTRICTED as of T-1091: always returns `None` -- SYS103 scans
    `root` in full on every tree, frob's own included, with no
    `_PACKAGE_ROOT` carve-out. Kept as a named function (rather than
    inlining `None` at its one call site) so its docstring stays the
    single place this history lives, and so a future re-restriction (if
    one is ever needed) has an obvious hook to land on.

    HISTORY (why this used to restrict, and why that is now safe to
    drop): T-0667 shipped SYS103 scoped to `_PACKAGE_ROOT` ("src/frob")
    on frob's own tree specifically, because an unrestricted `root`-wide
    walk surfaced 264 real, then-unmodeled findings under `tests/**`,
    `scripts/**`, `frob-core/src/**`, `strata-core/src/**` --
    `design/frob.strata` only ever declared `code=`/`may` for `src/frob/`
    at that point (same T-0211 fact SYS102 already lived with), so
    wiring SYS103 unrestricted then would have regressed the live
    `SELFAUDIT001` gate from green to 264 errors. T-1079 closed that gap
    directly: `design/frob.strata` now models `tests/**` (`testsuite`),
    `scripts/**` (`scripts_ops`), `frob-core/src/**`
    (`frob_core_native`), and `strata-core/src/**` (`strata_core_native`)
    as real nodes with real `code=` bindings, so those 264 files are no
    longer `FOREIGN` at all -- `TestCoverageTotality::
    test_repo_unrestricted_scan_is_clean` (T-1079) already proved a
    prefix-bypassed scan against the live repo returns zero findings.
    T-1091 makes that the LIVE gate's own behavior, not just a test
    harness's: dropping the `_PACKAGE_ROOT` carve-out here means
    `SELFAUDIT001` now checks exactly what `design/frob.strata` claims to
    cover (the WHOLE repo), closing the gap for real. If a genuinely new,
    still-unmodeled tree is ever added back to this repo, SYS103 will
    correctly regress to non-zero on that tree -- that is the point of
    the rule, not a bug in this change."""
    return None


# frob:invariant INV-048
# invariant spec: [INV-048](invariants/INV-048.md)
# frob:tests tests/unit/strata/test_selfconform.py::TestCoverageTotality.test_foreign_file_with_capability_fires_sys103  # noqa: E501
# frob:ticket T-2729
def _coverage_totality_violations(
    capability_binding: CodeBinding,
    root: Path,
    capability_files: list[Path] | None = None,
) -> list[SelfConformViolation]:
    """SYS103 (SYS-COV, T-0667, unrestricted as of T-1091): every
    `FOREIGN` file under `root` whose `root`-relative path starts with
    `_coverage_totality_scan_prefix(root)` (ALWAYS the whole root now --
    see that function's docstring for the T-0667-restricted-then-T-1091-
    dropped history) that `scan_file_capabilities` observes ANY
    capability in.
    `is_self_pattern_path` files are skipped
    (T-0201, same self-match exclusion every other observed-side join in
    this module already applies) -- a pattern-catalog data file's needle
    literals are not code exercising a capability. One finding per
    FOREIGN file, `capability` set to the sorted, comma-joined kind list
    observed there, folded into `detail` only -- `capability` (the
    `apply_waivers` sub-target field) is left `None`, exactly like
    SYS102's findings, since SYS103 has no per-kind waiver granularity of
    its own (the whole FILE is unbound, not one specific capability kind
    of it) and is NOT in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`;
    setting `capability` here would make a bare `waive "SYS103"` clause
    (sub_target=None) never match a finding whose computed sub_target is
    a non-None kind string -- `_apply_sys_waivers` below relies on this
    staying `None`.

    Deliberately walks `_sorted_capability_files(root)` directly rather
    than `capability_binding.owner.items()`: `bind_code` takes a fast
    path when NO node in the whole model declares any `code=` glob at
    all (`globs` empty) and returns an entirely EMPTY owner mapping -- no
    file gets a `FOREIGN` entry, not just no bound ones -- which would
    silently blind a dict-keyed join to every file in that degenerate-
    but-real state (a model with zero `code=` declarations, e.g. before
    anyone has written any, is exactly the un-modeled case SYS-COV exists
    to catch, not a state it can afford to go quiet in). Reading
    `capability_binding.owner.get(rel, FOREIGN)` per real file sidesteps
    that gap: a file absent from the mapping is treated identically to
    one explicitly marked `FOREIGN`, which is what its absence always
    means.

    `capability_files` (T-1449): the caller's already-walked
    `_sorted_capability_files(root)` result, reused instead of re-walking
    -- see `_capability_binding`'s matching parameter docstring for the
    full rationale. Falls back to a fresh walk when `None`."""
    found: list[SelfConformViolation] = []
    prefix = _coverage_totality_scan_prefix(root)
    files = (
        capability_files
        if capability_files is not None
        else _sorted_capability_files(root)
    )
    for path in files:
        rel = path.relative_to(root).as_posix()
        if prefix is not None and not rel.startswith(prefix):
            continue
        owner = capability_binding.owner.get(rel, FOREIGN)
        if owner != FOREIGN:
            continue
        if is_self_pattern_path(path, root):
            continue
        kinds = scan_file_capabilities(path)
        if not kinds:
            continue
        capability = ", ".join(sorted(kinds))
        _log.warning(
            "selfconform: SYS103 (SYS-COV) unbound-but-capable %s (%s)",
            rel,
            capability,
        )
        found.append(
            SelfConformViolation(
                rule=SYS_COVERAGE_TOTALITY,
                node=rel,
                detail=(
                    f"{rel} has an observed capability ({capability}) but no "
                    "node's code= glob binds it"
                ),
            )
        )
    return found
