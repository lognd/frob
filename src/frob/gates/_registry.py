"""frob.gates._registry -- one registration interface for gate detectors.

T-4661 (kernel decoupling, GATES story): today adding one detector means
hand-editing four separate places -- the job list (`frob.gates.__init__`'s
`_ALL_GATES`/`_CANONICAL_GATE_ORDER`/`_GATE_STAGE_GROUPS`), the rule-id
registry (`frob.gates._waive._KNOWN_GATE_RULES`), the rule table in
`docs/modules/gates.md`, and `docs/design/registry/check-coverage.yaml`.
All four are shared, whole-file lease hotspots, so two gate tickets can
never run in parallel, and a finished detector can sit unwired for weeks
(measured: T-3997/T-3953/T-3964/T-4230/T-4612 each shipped unregistered
because `gates/__init__.py` and `_waive.py` were leased elsewhere,
spawning the T-4647/T-4605 fold-in tickets to wire them in after the
fact).

This module is the fix: ONE place a detector declares itself --
`register_gate()`, called once per job, naming its rule ids, severity,
stage groups and the files it reads. The job list, the known-rule-id
set, the doc rule table and the check-coverage entries all become pure
DERIVED views (`derive_*` functions below) over this one registry, so
adding a detector is a one-file change: this module gains a
`register_gate` call, nothing else.

MIGRATION POSTURE (deliberate, this leaf's own scope boundary): this
leaf builds the registry and proves the derivation is sound -- it does
NOT migrate every existing hand-maintained gate to call `register_gate`
itself (that touches `gates/__init__.py` and `_waive.py`, both leased by
concurrent tickets at filing time -- see the Done report). Instead
`seed_legacy_bulk()` registers the CURRENT hand-maintained job set and
rule-id set as one bulk "legacy" entry, so `derive_known_rule_ids()` and
`derive_job_names()` already equal today's `_ALL_GATES`/
`_KNOWN_GATE_RULES` byte-for-byte (tested against a fresh scan). A new
detector never needs to touch the legacy bulk entry -- it calls
`register_gate()` directly, exactly like the positive-control fake
detector in this leaf's own test suite does. Migrating each existing
gate module off the bulk entry one at a time, and opening registration
to a consumer repo's own rule ids (currently a closed frozenset), are
follow-up leaves (T-3854 and friends) that become one-file changes
precisely because this registry exists.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from pydantic import BaseModel
from typani import Err, Ok, Result
from typani.error_set import ErrorSet

from frob.gates._models import Severity
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/gate-registration.md#registryerror
# frob:tests tests/unit/test_gate_registry.py::TestRegisterGate.test_duplicate_job_name_is_refused  # noqa: E501
class RegistryError(ErrorSet):
    """Fallible outcomes of registering a gate job with the registry."""

    DuplicateJob = "a job with this name is already registered"
    DuplicateRuleId = "a rule id is already claimed by a different job"
    EmptyRuleIds = "a registration must declare at least one rule id"


# frob:doc docs/modules/gate-registration.md#gateregistration
# frob:tests tests/unit/test_gate_registry.py::TestRegisterGate.test_register_returns_the_stored_registration  # noqa: E501
class GateRegistration(BaseModel):
    """One detector's self-declaration: its job name, the rule ids it can
    emit, the `frob check --only <group>` stage groups it runs under, the
    files it reads (for SELFAUDIT001/`via` bookkeeping), and its default
    severity -- the single source every derived view reads from."""

    model_config = {}

    job: str
    rule_ids: frozenset[str]
    stage_groups: frozenset[str]
    severity: Severity = Severity.ERROR
    reads: tuple[str, ...] = ()


@dataclass
class _Registry:
    """Process-wide gate registration table: job name to `GateRegistration`,
    plus a reverse rule-id index kept in lockstep so a duplicate rule id
    claimed by two jobs is refused at registration time, not discovered
    later by a drifted derived view."""

    by_job: dict[str, GateRegistration] = field(default_factory=dict)
    rule_owner: dict[str, str] = field(default_factory=dict)


_REGISTRY = _Registry()


# frob:doc docs/modules/gate-registration.md#register_gate
# frob:tests tests/unit/test_gate_registry.py::TestRegisterGate.test_register_returns_the_stored_registration  # noqa: E501
def register_gate(
    job: str,
    rule_ids: Iterable[str],
    stage_groups: Iterable[str],
    severity: Severity = Severity.ERROR,
    reads: Iterable[str] = (),
) -> Result[GateRegistration, RegistryError]:
    """Register one detector job under `job`, claiming `rule_ids`. Refuses
    (`RegistryError.DuplicateJob`) a job name already registered, and
    (`RegistryError.DuplicateRuleId`) a rule id already claimed by a
    DIFFERENT job -- the two failure modes T-3997/T-3953/T-3964 each
    risked being silently invisible to before this registry existed.
    Returns the stored `GateRegistration` on success."""
    rule_id_set = frozenset(rule_ids)
    if not rule_id_set:
        _log.error("register_gate: %s declared zero rule ids", job)
        return Err(RegistryError.EmptyRuleIds)
    if job in _REGISTRY.by_job:
        _log.error("register_gate: %s already registered", job)
        return Err(RegistryError.DuplicateJob)
    for rule_id in rule_id_set:
        owner = _REGISTRY.rule_owner.get(rule_id)
        if owner is not None and owner != job:
            _log.error(
                "register_gate: %s claims rule %s already owned by %s",
                job,
                rule_id,
                owner,
            )
            return Err(RegistryError.DuplicateRuleId)
    registration = GateRegistration(
        job=job,
        rule_ids=rule_id_set,
        stage_groups=frozenset(stage_groups),
        severity=severity,
        reads=tuple(reads),
    )
    _REGISTRY.by_job[job] = registration
    for rule_id in rule_id_set:
        _REGISTRY.rule_owner[rule_id] = job
    _log.info("register_gate: registered %s with %d rule id(s)", job, len(rule_id_set))
    return Ok(registration)


# frob:doc docs/modules/gate-registration.md#gate
# frob:tests tests/unit/test_gate_registry.py::TestGateDecorator.test_decorator_registers_and_returns_function_unchanged  # noqa: E501
def gate(
    *,
    job: str,
    rule_ids: Iterable[str],
    stage_groups: Iterable[str],
    severity: Severity = Severity.ERROR,
    reads: Iterable[str] = (),
):
    """Decorator form of `register_gate`: wraps a detector function,
    registering it as a side effect of module import and returning the
    function unchanged. Raises `RuntimeError` on a registration conflict
    (`register_gate`'s `Err`) -- a decorator has no caller to hand a
    `Result` back to, so a conflict here is an import-time programmer
    bug, not a recoverable runtime condition."""

    def _decorate(func):
        result = register_gate(
            job=job,
            rule_ids=rule_ids,
            stage_groups=stage_groups,
            severity=severity,
            reads=reads,
        )
        if result.is_err:
            raise RuntimeError(
                f"gate registration for {job!r} failed: {result.danger_err.value}"
            )
        return func

    return _decorate


_LEGACY_JOB = "legacy"


# frob:doc docs/modules/gate-registration.md#seed_legacy_bulk
# frob:tests tests/unit/test_gate_registry.py::TestSeedLegacyBulk.test_seed_is_idempotent  # noqa: E501
def seed_legacy_bulk(
    job_names: Iterable[str],
    rule_ids: Iterable[str],
    reads: Iterable[str] = (),
) -> Result[GateRegistration, RegistryError]:
    """One-time bulk seed (T-4661's migration posture, see module
    docstring) registering the CURRENT hand-maintained `_ALL_GATES` job
    names and `_KNOWN_GATE_RULES` rule ids as a single legacy entry, so
    the derived views equal today's hand-maintained lists exactly before
    any individual detector has migrated. Idempotent: calling it again
    with the same arguments after a prior successful seed is a no-op
    Ok, not a DuplicateJob refusal, since a process may import multiple
    gate-adjacent modules that each want the legacy baseline present."""
    existing = _REGISTRY.by_job.get(_LEGACY_JOB)
    rule_id_set = frozenset(rule_ids)
    job_name_set = frozenset(job_names)
    if existing is not None:
        if existing.rule_ids == rule_id_set:
            _log.debug("seed_legacy_bulk: legacy entry already present, no-op")
            return Ok(existing)
        _log.error("seed_legacy_bulk: legacy entry already seeded with different data")
        return Err(RegistryError.DuplicateJob)
    _log.info(
        "seed_legacy_bulk: seeding %d legacy job name(s), %d legacy rule id(s)",
        len(job_name_set),
        len(rule_id_set),
    )
    return register_gate(
        job=_LEGACY_JOB,
        rule_ids=rule_id_set,
        stage_groups=job_name_set,
        reads=reads,
    )


# frob:doc docs/modules/gate-registration.md#reset_registry_for_tests
# frob:tests tests/unit/test_gate_registry.py::TestRegisterGate.test_empty_rule_ids_is_refused  # noqa: E501
def reset_registry_for_tests() -> None:
    """Test-only escape hatch: clears the process-wide registry so each
    test starts from an empty table instead of accumulating registrations
    across the suite (the registry is deliberately module-global state,
    matching `_KNOWN_GATE_RULES`'s own import-time-singleton posture)."""
    _log.debug("reset_registry_for_tests: clearing %d job(s)", len(_REGISTRY.by_job))
    _REGISTRY.by_job.clear()
    _REGISTRY.rule_owner.clear()


# frob:doc docs/modules/gate-registration.md#derive_job_names
# frob:tests tests/unit/test_gate_registry.py::TestDerivedViewsMatchLegacyExactly.test_derived_job_names_equal_all_gates  # noqa: E501
def derive_job_names() -> frozenset[str]:
    """The job-list DERIVED view: every registered job name, legacy bulk
    entry's `stage_groups` (which doubles as the legacy job-name set,
    see `seed_legacy_bulk`) included via that one entry."""
    names: set[str] = set()
    for registration in _REGISTRY.by_job.values():
        if registration.job == _LEGACY_JOB:
            names |= registration.stage_groups
        else:
            names.add(registration.job)
    return frozenset(names)


# frob:doc docs/modules/gate-registration.md#derive_known_rule_ids
# frob:tests tests/unit/test_gate_registry.py::TestGateDecorator.test_decorator_registers_and_returns_function_unchanged  # noqa: E501
def derive_known_rule_ids() -> frozenset[str]:
    """The rule-id-registry DERIVED view: every rule id claimed by any
    registered job, `_KNOWN_GATE_RULES`'s direct successor."""
    return frozenset(_REGISTRY.rule_owner)


# frob:doc docs/modules/gate-registration.md#checkcoverageentry
# frob:tests tests/unit/test_gate_registry.py::TestAddingADetectorTouchesOneFile.test_adding_a_detector_touches_one_file  # noqa: E501
@dataclass(frozen=True)
class CheckCoverageEntry:
    """One `docs/design/registry/check-coverage.yaml` `gate_rule_entries`
    row, derived rather than hand-authored -- see `derive_check_coverage_
    entries`."""

    id: str
    disposition: str
    name: str


# frob:doc docs/modules/gate-registration.md#derive_check_coverage_entries
# frob:tests tests/unit/test_gate_registry.py::TestAddingADetectorTouchesOneFile.test_adding_a_detector_touches_one_file  # noqa: E501
def derive_check_coverage_entries() -> tuple[CheckCoverageEntry, ...]:
    """The check-coverage.yaml DERIVED view: one `CHK-GATE-<rule>` entry
    per known rule id, `disposition="handled_by:<rule>"` -- matching the
    existing hand-authored shape in `docs/design/registry/
    check-coverage.yaml` exactly, sorted for deterministic output."""
    return tuple(
        CheckCoverageEntry(
            id=f"CHK-GATE-{rule_id}",
            disposition=f"handled_by:{rule_id}",
            name=f"{rule_id} is a live, enforced gate rule",
        )
        for rule_id in sorted(derive_known_rule_ids())
    )


# frob:doc docs/modules/gate-registration.md#derive_doc_rule_table
# frob:tests tests/unit/test_gate_registry.py::TestAddingADetectorTouchesOneFile.test_adding_a_detector_touches_one_file  # noqa: E501
def derive_doc_rule_table() -> tuple[str, ...]:
    """The `docs/modules/gate-registration.md` (and, once T-4647's
    wiring lands, `gates.md`) DERIVED view: every known rule id, sorted,
    matching the `<!-- frob:enumerates ... members="..." -->` comma list
    shape `docs/modules/gates.md` already uses for `_KNOWN_GATE_RULES`."""
    return tuple(sorted(derive_known_rule_ids()))


# frob:doc docs/modules/gate-registration.md#find_unregistered_live_rule_ids
# frob:tests tests/unit/test_gate_registry.py::TestUnregisteredLiveRuleIsReported.test_registered_ids_are_not_reported  # noqa: E501
def find_unregistered_live_rule_ids(
    repo_root,
    scan_candidates,
) -> frozenset[str]:
    """T-4661 acceptance [2]: given `scan_candidates` (a callable
    returning the mapping `frob.gates._rule_id_scan.
    scan_candidate_rule_id_literals` would, kept as an injected callable
    here rather than importing `_rule_id_scan` directly so this module
    stays independent of the legacy scan's own leased-file neighbors),
    every candidate rule id live in source but absent from the registry
    -- the same "detected but not silently accepted" contract
    `frob.gates._rule_id_scan.find_unregistered_rule_ids` already
    enforces, now sourced from THIS registry's `derive_known_rule_ids()`
    instead of a second hand-maintained literal."""
    known = derive_known_rule_ids()
    candidates = scan_candidates(repo_root)
    unregistered = frozenset(candidates) - known
    if unregistered:
        _log.warning(
            "find_unregistered_live_rule_ids: %d id(s) live but unregistered: %s",
            len(unregistered),
            sorted(unregistered),
        )
    return unregistered
