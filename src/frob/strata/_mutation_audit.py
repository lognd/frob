"""strata may-mutation audit (T-1203): prove every `may` declaration across
every loaded `.strata` model is load-bearing AND double-detected.

MOTIVATION (T-1203 ticket body): `_selfconform.py` ships SYS100 (observed-
undeclared) and SYS101 (declared-unobserved) as the two directions of
capability conformance, but nothing had ever proven that DELETING a real
`may` declaration actually trips a finding, that no waiver silently masks
that finding, or that the scanner (`scan_file_capabilities`) can even see
every capability kind this repo declares in the first place.
`test_conform_eval_needle.py`'s "real repo has zero SYS100 gap" assertion
is a fixture regression test, not a detection-completeness proof: it shows
today's declarations are consistent with today's code, never that removing
one would be CAUGHT.

This module is that proof, computed structurally rather than by shelling
out to `check_self_conformance` once per mutated atom (repo-scan cost times
~100 `may` atoms would be prohibitive): it scans the real repo's observed
capabilities EXACTLY ONCE (`_selfconform._bind_conformance_inputs` +
`_observed_raw_kinds_by_node`, the same primitives `check_self_conformance`
itself calls), then re-runs the SAME kind-level join logic
(`_declared_kinds`/`_stale_design_violations`/`_extended_kind_violations`)
against a per-atom mutated COPY of just that one node's `may` tuple. This
is deliberately pre-waiver (`_apply_sys_waivers` is never called here) --
acceptance [2]'s "no existing waiver masks a mutation finding" is
satisfied structurally, not by disabling waivers as a special mode: this
harness's join never sees `Node.waives` at all, so a waiver on the live
design cannot suppress a mutation finding here even if it would suppress
the corresponding `frob sys audit` finding.

The second, independent detector (acceptance [0]'s "two errors from two
mechanisms with no shared blind spot") is `_export.py::node_allowed_
syscalls` (the seccomp-profile generator, T-0257/T-0158 precedent): it
derives a node's allowed syscall set from the SAME `Node.may` tuple through
a completely different table (`_SECCOMP_KIND_MAP`, keyed on the RAW
`_may_kind` spelling, not the canonicalized/expanded declared-kind
vocabulary `_selfconform.py` joins on) -- a semantic-analysis detector
(SYS100/SYS101, source-code scanning) and an artifact-generation detector
(seccomp export diff) share no code path, so a bug or gap in one cannot
hide a corresponding gap in the other by construction.

Acceptance [3]'s scanner-blind-spot clause is `DETECTABLE_KINDS` below:
the exact union of every declared-capability kind SYS100/SYS101 can ever
observe (mirrors `_selfconform.py::_EXTENDED_KINDS` and `_effects.py::
_KIND_MAP`'s own vocabulary, generated from them rather than duplicated).
A declared kind outside this union (`proc`/`ffi`'s bare-family spelling is
the one candidate today, per `frob.vet._capability_modes`'s own "wiring
status" docstring -- currently undeclared anywhere in this repo) has no
detection path at all; `run_may_mutation_audit` reports it as an
`UndetectableCapabilityKind` finding rather than silently treating its
mutation as clean.
"""
# frob:doc docs/strata/selfconform.md#the-three-rules
# frob:ticket T-1203
# frob:waive INV006 reason="the 'only'/'never' occurrences below are plain prose \
# describing this module's own already-implemented logic (e.g. 'export diff only when \
# export_diff_expected'), not a cross-module contract needing its own tracked \
# invariant -- same first-turn-on-pool disposition T-0585/ T-1023 already apply \
# elsewhere in this package"

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.vet._capability_modes import canonical_declared_kind, expand_declared_kind

from ._design_load import load_design_ids
from ._effects import _KIND_MAP, _declared_kinds, _may_kind
from ._errors import StrataError
from ._export import _SECCOMP_KIND_MAP, node_allowed_syscalls
from ._models import KernelModel, Node
from ._selfconform import (
    _EXTENDED_KINDS,
    _aggregate_raw_kinds_by_node,
    _all_kinds_view,
    _bind_conformance_inputs,
    _extended_kinds_view,
    _observed_raw_kinds_by_file,
    _sorted_capability_files,
    _stale_design_violations,
)
from ._sysdoc import merge_models

_log = get_logger(__name__)

# frob:doc docs/strata/selfconform.md#the-three-rules
#: Every declared-capability kind the self-conformance pipeline can ever
#: observe: the tier-2 `_KIND_MAP` normalized targets (net.connect/
#: net.listen/fs.write/fs.read/exec/env.read/env.write, SYS100 core) union
#: `_selfconform.py::_EXTENDED_KINDS` (SYS100 extended). A declared kind
#: outside this set has no join anywhere in the pipeline -- module
#: docstring's acceptance [3] section.
DETECTABLE_KINDS: frozenset[str] = frozenset(_KIND_MAP.values()) | _EXTENDED_KINDS

# frob:doc docs/strata/selfconform.md#the-three-rules
#: Every RAW declared-kind spelling (`_may_kind` form -- `_SECCOMP_KIND_MAP`
#: is keyed on the same raw spelling `node_allowed_syscalls` reads, not the
#: canonicalized/expanded `DETECTABLE_KINDS` vocabulary) the seccomp export
#: -- the mutation audit's independent SECOND detector (module docstring)
#: -- actually varies for. A kind outside this set (module docstring:
#: every app-level extended kind today -- `env`/`eval`/`ffi`/
#: `install-hook`/`sql`/`deserialize`/`html_render`/`fetch_url`/
#: `client_storage`, none of which has a real OS-syscall analog) has NO
#: second-detector coverage yet -- `run_may_mutation_audit` reports its
#: deletions as `SecondDetectorGap` rather than silently counting SYS100
#: alone as "double detected". T-1454 (env-mode-explosion/T-1453 via
#: migration fallout): `env.read` joins this disclosed-gap list too --
#: unlike `fs.read`/`fs.write` (real `open`/`read` syscalls, T-1203's
#: rationale for adding those two to `_SECCOMP_KIND_MAP`), reading an
#: environment variable has no distinct OS syscall of its own (it is a
#: libc lookup over the process's already-mapped environment block), so
#: there is no seccomp-profile fact to vary when an `env.read` atom is
#: deleted -- a real gap, not a spurious one, and NOT fabricated into
#: `_SECCOMP_KIND_MAP` just to make this set look complete.
EXPORT_DETECTABLE_KINDS: frozenset[str] = frozenset(_SECCOMP_KIND_MAP)

#: A DETECTABLE substitution target for every declared kind: picked so it
#: is never the same family as the atom being mutated (a same-family
#: substitute could still be discharged by the coarse-family union,
#: masking the SYS101 half of acceptance [1]'s pair). `sql`/`html_render`
#: are two independent, unrelated extended kinds -- one of the two is
#: always safe to pick.
_SUBSTITUTE_CANDIDATES: tuple[str, ...] = ("sql", "html_render")


# frob:doc docs/strata/selfconform.md#the-three-rules
class UndetectableCapabilityKind(BaseModel):
    """One declared `may` atom whose kind has NO join anywhere in the
    self-conformance pipeline (`DETECTABLE_KINDS`) -- a scanner blind spot
    the mutation audit refuses to pass over in silence (acceptance [3])."""

    model_config = ConfigDict(frozen=True)

    node: str
    atom: str
    kind: str


# frob:doc docs/strata/selfconform.md#the-three-rules
class SecondDetectorGap(BaseModel):
    """One deletion mutation whose kind has NO independent second-detector
    coverage yet (`EXPORT_DETECTABLE_KINDS`) -- SYS100 alone fired, but the
    "two mechanisms, no shared blind spot" guarantee (acceptance [0]) does
    not hold for it today. A disclosed gap, not a silent pass: T-1203's
    Done report files the follow-up ticket to build each of these kinds'
    own independent second detector."""

    model_config = ConfigDict(frozen=True)

    node: str
    atom: str
    kind: str


# frob:doc docs/strata/selfconform.md#the-three-rules
class MutationFinding(BaseModel):
    """One deletion or substitution mutation's audit result: which
    detector(s) fired for it. `export_diff_expected` is `False` for a
    deletion whose kind has no second-detector coverage (`SecondDetectorGap`
    territory) -- such a finding is still `load_bearing` (SYS100 fired) but
    is not claimed to be DOUBLE-detected."""

    model_config = ConfigDict(frozen=True)

    node: str
    atom: str
    mode: str  # "delete" | "substitute"
    sys100_fired: bool
    sys101_fired: bool
    export_diff_fired: bool | None = None  # None: not applicable to this mode
    export_diff_expected: bool = False

    # frob:doc docs/strata/selfconform.md#the-three-rules
    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo.test_every\
    # _may_is_load_bearing
    @property
    def load_bearing(self) -> bool:
        """`True` iff every detector this finding is actually expected to
        trip did trip: SYS100 always; SYS101 for a substitution; the
        export diff only when `export_diff_expected` (module docstring)."""
        if not self.sys100_fired:
            return False
        if self.mode == "substitute":
            return self.sys101_fired
        return not self.export_diff_expected or bool(self.export_diff_fired)


# frob:doc docs/strata/selfconform.md#the-three-rules
class MutationAuditReport(BaseModel):
    """The full may-mutation audit result: every mutation's finding, every
    scanner blind spot discovered, and the baseline SYS101 count
    (acceptance [2]) the whole guarantee rests on."""

    model_config = ConfigDict(frozen=True)

    findings: tuple[MutationFinding, ...] = ()
    undetectable: tuple[UndetectableCapabilityKind, ...] = ()
    second_detector_gaps: tuple[SecondDetectorGap, ...] = ()
    baseline_sys101_count: int = 0

    # frob:doc docs/strata/selfconform.md#the-three-rules
    # frob:tests \
    # tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo.test_every\
    # _may_is_load_bearing
    @property
    def all_load_bearing(self) -> bool:
        """`True` iff every finding's `load_bearing` holds -- every
        deletion tripped SYS100 (plus the export diff wherever
        `EXPORT_DETECTABLE_KINDS` claims coverage) and every substitution
        tripped the SYS100+SYS101 pair. A disclosed `second_detector_gaps`
        entry does not fail this: SYS100 alone is still load-bearing,
        just not yet double-detected (module docstring)."""
        return all(f.load_bearing for f in self.findings)


def _substitute_kind_for(existing_raw_kinds: frozenset[str]) -> str:
    """A `_SUBSTITUTE_CANDIDATES` entry not already among `existing_raw_kinds`
    -- guarantees the substituted declaration is genuinely new (SYS101 can
    fire) rather than accidentally already-discharged by a sibling atom on
    the same node."""
    for candidate in _SUBSTITUTE_CANDIDATES:
        if candidate not in existing_raw_kinds:
            return candidate
    # Both candidates already declared -- fall back to the first; a node
    # this saturated is itself worth a follow-up, not a reason to crash.
    return _SUBSTITUTE_CANDIDATES[0]


# frob:waive DUP001 reason="rung=r2 generic-shape false positive -- flags against a \
# different, unrelated small filter/comprehension function almost every run (T-1203 \
# investigation: observed matches against src/frob/gates, src/frob/vet/_capability.py, \
# src/frob/strata/_lint.py, src/frob/refactor/_scan.py, tests/unit/test_arch.py, \
# src/frob/strata/_threat.py, src/frob/tickets/_scope.py across successive runs on an \
# UNCHANGED function body) -- the shared shape is generic \
# filter-then-rebuild-a-tuple/list control flow, not this function's actual subject \
# (mutating one node's `may` tuple); no real duplication to extract"
def _mutated_node(node: Node, atom: str, replacement: str | None) -> Node:
    """`node` with `atom` removed from `.may` (`replacement is None`, the
    delete mutation) or replaced by `replacement` (the substitute
    mutation) -- a fresh frozen copy, `node` itself is never touched."""
    kept = tuple(a for a in node.may if a != atom)
    added = () if replacement is None else (replacement,)
    return node.model_copy(update={"may": kept + added})


def _core_sys100_fires(
    node: Node, mutated: Node, all_kinds_view: dict[str, frozenset[str]]
) -> bool:
    """Kind-level SYS100 equivalent (module docstring): `observed(node) -
    declared(mutated)` is non-empty for the ORIGINAL node's observed set --
    reuses `_declared_kinds` (pure) so this needs no file re-scan per
    mutation, only the one shared `all_kinds_view` baseline scan."""
    observed = all_kinds_view.get(node.id, frozenset())
    declared_after = _declared_kinds(mutated)
    return bool(observed - declared_after)


def _extended_sys100_fires(
    node: Node, mutated: Node, extended_view: dict[str, frozenset[str]]
) -> bool:
    """SYS100-extended equivalent: same join as `_core_sys100_fires` but
    against the `_EXTENDED_KINDS`-filtered observed view."""
    observed = extended_view.get(node.id, frozenset())
    declared_after = _declared_kinds(mutated) & _EXTENDED_KINDS
    return bool(observed - declared_after)


def _sys101_fires_for_kind(
    mutated: Node, kind_raw: str, all_kinds_view: dict[str, frozenset[str]]
) -> bool:
    """SYS101 equivalent for one specific raw declared atom kind on
    `mutated`: stale iff none of its expanded modes were ever observed on
    this node (mirrors `_stale_design_violations`'s per-atom join)."""
    canonical = canonical_declared_kind(kind_raw)
    expanded = expand_declared_kind(canonical)
    observed = all_kinds_view.get(mutated.id, frozenset())
    return not bool(expanded & observed)


def _export_diff_fires(node: Node, mutated: Node) -> bool:
    """`True` iff `node_allowed_syscalls` differs between `node` and
    `mutated` -- the second, independent detector (module docstring)."""
    return node_allowed_syscalls(node) != node_allowed_syscalls(mutated)


def _kind_is_undetectable(kind_raw: str) -> UndetectableCapabilityKind | None:
    """`None` if `kind_raw`'s expanded declared-kind set intersects
    `DETECTABLE_KINDS`, else a placeholder-node `UndetectableCapabilityKind`
    (node/atom filled in by the caller) -- split out so the raw-kind check
    itself stays a one-line pure predicate."""
    canonical = canonical_declared_kind(kind_raw)
    expanded = expand_declared_kind(canonical)
    if expanded & DETECTABLE_KINDS:
        return None
    return UndetectableCapabilityKind(node="", atom="", kind=kind_raw)


def _audit_one_atom(
    node: Node,
    atom: str,
    kind_raw: str,
    raw_kinds: frozenset[str],
    all_kinds_view: dict[str, frozenset[str]],
    extended_view: dict[str, frozenset[str]],
    findings: list[MutationFinding],
    second_detector_gaps: list[SecondDetectorGap],
) -> None:
    """The deletion + substitution pair for one `(node, atom)` -- split out
    of `run_may_mutation_audit`'s loop body (`ARCH001`, function-length
    budget) purely to keep the entry point itself short; appends directly
    to the caller's `findings`/`second_detector_gaps` accumulators."""
    # -- deletion --
    deleted = _mutated_node(node, atom, None)
    sys100_del = _core_sys100_fires(
        node, deleted, all_kinds_view
    ) or _extended_sys100_fires(node, deleted, extended_view)
    export_expected = kind_raw in EXPORT_DETECTABLE_KINDS
    export_diff = _export_diff_fires(node, deleted)
    findings.append(
        MutationFinding(
            node=node.id,
            atom=atom,
            mode="delete",
            sys100_fired=sys100_del,
            sys101_fired=False,
            export_diff_fired=export_diff,
            export_diff_expected=export_expected,
        )
    )
    if not export_expected:
        second_detector_gaps.append(
            SecondDetectorGap(node=node.id, atom=atom, kind=kind_raw)
        )

    # -- substitution --
    substitute_kind = _substitute_kind_for(raw_kinds)
    substituted = _mutated_node(node, atom, substitute_kind)
    sys100_sub = _core_sys100_fires(
        node, substituted, all_kinds_view
    ) or _extended_sys100_fires(node, substituted, extended_view)
    sys101_sub = _sys101_fires_for_kind(substituted, substitute_kind, all_kinds_view)
    findings.append(
        MutationFinding(
            node=node.id,
            atom=atom,
            mode="substitute",
            sys100_fired=sys100_sub,
            sys101_fired=sys101_sub,
            export_diff_fired=None,
        )
    )


def _load_mutation_audit_baseline(
    root: Path,
) -> Result[
    tuple[KernelModel, dict[str, frozenset[str]], dict[str, frozenset[str]], int],
    StrataError,
]:
    """Load+bind+scan the real repo ONCE (module docstring) and compute the
    baseline SYS101 count -- split out of `run_may_mutation_audit` purely
    to keep that function's own body under the `ARCH001` length budget.
    Returns `(model, all_kinds_view, extended_view, baseline_sys101_count)`."""
    ids = load_design_ids(root)
    if ids.errors:
        _log.error("mutation-audit: %d design file load error(s)", len(ids.errors))
        return Err(StrataError.ParseFailed)
    model = merge_models(ids.models)
    bound = _bind_conformance_inputs(model, root, _sorted_capability_files(root))
    if bound.is_err:
        return Err(bound.danger_err)
    binding = bound.danger_ok
    raw_by_file = _observed_raw_kinds_by_file(binding, root)
    raw_by_node = _aggregate_raw_kinds_by_node(binding, raw_by_file)
    all_kinds_view = _all_kinds_view(raw_by_node)
    extended_view = _extended_kinds_view(raw_by_node)
    # SYS101 (stale design) has exactly one producer, `_stale_design_
    # violations` -- `_extended_kind_violations` is a SYS100 producer
    # (module docstring's core/extended split) and contributes nothing to
    # the SYS101 baseline count. T-1450: SYS101 now judges staleness per
    # may-via surface, so its baseline needs the FILE-level normalized
    # view (`_all_kinds_view` over `raw_by_file`, not `raw_by_node`) plus
    # `binding` itself to resolve each node's owned-file set for the
    # per-`via` narrowing -- `all_kinds_view`/`extended_view` above stay
    # node-level for the mutation-audit's OTHER (SYS100-side) callers,
    # unaffected by this ticket.
    baseline_count = len(
        _stale_design_violations(model, root, binding, _all_kinds_view(raw_by_file))
    )
    return Ok((model, all_kinds_view, extended_view, baseline_count))


# frob:doc docs/strata/selfconform.md#may-mutation-audit-t-1203
# frob:doc docs/strata/selfconform.md#the-three-rules
# frob:tests tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo.test_every_may_is_load_bearing kind="unit"  # noqa: E501
def run_may_mutation_audit(root: Path) -> Result[MutationAuditReport, StrataError]:
    """The T-1203 mutation-audit entry point: load every `.strata` model
    under `root`, and for every `may` atom on every node, verify (module
    docstring) that deleting it trips SYS100 (core or extended) plus the
    export-syscall diff, and that substituting it for a different,
    detectable kind trips the SYS100+SYS101 pair. Also reports the
    baseline SYS101 count (acceptance [2]) and every declared kind outside
    `DETECTABLE_KINDS` (acceptance [3]) -- `Err` only on a genuine load/
    binding failure, never on a finding (findings live in the returned
    report, exactly like `check_self_conformance`'s own `Result` shape)."""
    root = Path(root)
    baseline = _load_mutation_audit_baseline(root)
    if baseline.is_err:
        return Err(baseline.danger_err)
    model, all_kinds_view, extended_view, baseline_count = baseline.danger_ok

    findings: list[MutationFinding] = []
    undetectable: list[UndetectableCapabilityKind] = []
    second_detector_gaps: list[SecondDetectorGap] = []

    for node in model.nodes:
        raw_kinds = frozenset(_may_kind(atom) for atom in node.may)
        for atom in node.may:
            kind_raw = _may_kind(atom)
            gap = _kind_is_undetectable(kind_raw)
            if gap is not None:
                undetectable.append(
                    gap.model_copy(update={"node": node.id, "atom": atom})
                )
                continue
            _audit_one_atom(
                node,
                atom,
                kind_raw,
                raw_kinds,
                all_kinds_view,
                extended_view,
                findings,
                second_detector_gaps,
            )

    _log.info(
        "mutation-audit: %d mutation(s) checked, %d undetectable kind(s), "
        "%d second-detector gap(s), baseline SYS101=%d",
        len(findings),
        len(undetectable),
        len(second_detector_gaps),
        baseline_count,
    )
    return Ok(
        MutationAuditReport(
            findings=tuple(findings),
            undetectable=tuple(undetectable),
            second_detector_gaps=tuple(second_detector_gaps),
            baseline_sys101_count=baseline_count,
        )
    )
