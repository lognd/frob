"""Ratchet pools (T-0569): freeze a warn-rule's EXISTING findings as a
tracked-in-git baseline (`frob-ratchet.lock.json`, same "committed summary
outside .gitignore's reach" posture as `frob-coverage.lock.json`, T-0545)
so every NEW finding of that rule reports at error severity instead of
silently joining an ever-growing warn pile. `frob pool snapshot RULE`
(docs/modules/gates.md#ratchet-pools-t-0569) is the only way to add an entry;
`clear_ratchet_entry` is the only way to remove one, and always demands a
disposition reason -- mirroring the `frob:waive` discipline this repo
already holds itself to elsewhere, applied to an entire baselined pool
instead of one inline comment.

Deliberately additive and self-contained: nothing in `frob.gates.__init__`
is modified to consume this yet (owned by a concurrent wave this ticket
does not touch) -- `resolve_ratchet_severity` is the integration point a
future change wires a real gate's severity resolution through, opt-in per
rule via `[gates.ratchet]` in `frob.toml`.

T-4240 (consumer F-326/H2-3): `baseline_overrun_violations` is the SAME
kind of additive, self-contained addition -- it reports BASE001 (a
tracked pool whose caller-measured current count exceeds its committed
baseline, named by rule id and both counts) but is not itself wired into
`frob check`'s land pre-sweep the way `SELFAUDIT001`
(`frob.gates._sys_selfaudit`) is; that wiring lives in `frob.gates.
__init__`'s `_ProcessJob` pipeline, which this ticket's declared scope
does not cover and which T-4540 held an in-progress lease over at the
time this was written (`frob ticket scope T-4240 --add
src/frob/gates/__init__.py` was refused: ScopeLeaseConflict). A follow-up
ticket must add the `_ProcessJob` wiring once that lease clears."""

from __future__ import annotations

import json
import tomllib
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, Ok
from typani.error_set import ErrorSet
from typani.result import Result

from frob.findings import Severity, Violation

_LOCK_REL = Path("frob-ratchet.lock.json")


# frob:ticket T-0569
# frob:doc docs/modules/gates.md#ratchet-pools-t-0569
class RatchetError(ErrorSet):
    """Fallible outcomes of ratchet-pool operations."""

    ClearReasonMissing = "clearing a baseline entry requires a non-empty reason"
    EntryNotFound = "no baselined entry with that key for that rule"
    WriteFailed = "atomic frob-ratchet.lock.json write failed"


# frob:ticket T-0569
# frob:doc docs/modules/gates.md#ratchet-pools-t-0569
class RatchetEntry(BaseModel):
    """One frozen (pre-existing) finding of a ratcheted rule: a stable
    location key (e.g. `path:line`) and the date it was baselined."""

    model_config = ConfigDict(frozen=True)

    key: str
    baselined: date


# frob:ticket T-0569
# frob:doc docs/modules/gates.md#ratchet-pools-t-0569
class RatchetPool(BaseModel):
    """The baselined findings of one rule id -- every entry here resolves
    to WARN (`resolve_ratchet_severity`); anything NOT here for a rule
    under active ratcheting resolves to ERROR."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    entries: tuple[RatchetEntry, ...] = ()

    # frob:doc docs/modules/gates.md#ratchet-pools-t-0569
    @property
    def keys(self) -> frozenset[str]:
        """The baselined finding keys, for an O(1) membership check."""
        return frozenset(e.key for e in self.entries)


# frob:ticket T-0569
# frob:doc docs/modules/gates.md#ratchet-pools-t-0569
class RatchetLock(BaseModel):
    """The whole committed `frob-ratchet.lock.json` document: one
    `RatchetPool` per rule id that has ever been snapshotted."""

    model_config = ConfigDict(frozen=True)

    pools: tuple[RatchetPool, ...] = ()

    # frob:doc docs/modules/gates.md#ratchet-pools-t-0569
    def pool_for(self, rule_id: str) -> RatchetPool | None:
        """The `RatchetPool` for `rule_id`, or `None` if never snapshotted."""
        for pool in self.pools:
            if pool.rule_id == rule_id:
                return pool
        return None


# frob:ticket T-0569
# frob:doc docs/modules/gates.md#ratchet-pools-t-0569
def load_ratchet_lock(root: Path) -> RatchetLock:
    """The committed `frob-ratchet.lock.json` at `root`, or an empty
    `RatchetLock` if it does not exist yet or fails to parse (T-0569) --
    "no baseline for any rule" is a valid, unremarkable starting state,
    not an error."""
    path = root / _LOCK_REL
    if not path.is_file():
        return RatchetLock()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RatchetLock.model_validate(data)
    except (OSError, ValueError) as exc:
        from frob.logging import get_logger

        get_logger(__name__).warning(
            "load_ratchet_lock: %s unreadable/malformed, treating as empty: %s",
            path,
            exc,
        )
        return RatchetLock()


# frob:ticket T-0569
def _write_ratchet_lock(root: Path, lock: RatchetLock) -> Result[None, RatchetError]:
    """Atomically write `lock` to `root/frob-ratchet.lock.json` (T-0569),
    sorted by rule id then entry key so the diff a reviewer sees is
    minimal and deterministic run-to-run."""
    path = root / _LOCK_REL
    sorted_pools = tuple(
        sorted(
            (
                pool.model_copy(
                    update={"entries": tuple(sorted(pool.entries, key=lambda e: e.key))}
                )
                for pool in lock.pools
            ),
            key=lambda p: p.rule_id,
        )
    )
    payload = RatchetLock(pools=sorted_pools).model_dump(mode="json")
    try:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError:
        return Err(RatchetError.WriteFailed)
    except Exception:
        # This function's own contract is a `Result` -- a genuinely
        # unresolvable write-time surprise belongs in `RatchetError.
        # WriteFailed`, not an escaping exception (EXHAUST001, T-1371).
        return Err(RatchetError.WriteFailed)
    return Ok(None)


# frob:ticket T-0569
# frob:doc docs/modules/gates.md#ratchet-pools-t-0569
def snapshot_ratchet(
    root: Path, rule_id: str, finding_keys: list[str]
) -> Result[RatchetPool, RatchetError]:
    """`frob pool snapshot RULE`: merge `finding_keys` (every CURRENT
    finding of `rule_id`, as the caller observed them) into `rule_id`'s
    baseline, stamping any genuinely NEW key with today's date -- an
    already-baselined key keeps its original `baselined` date (re-running
    snapshot is idempotent, not a bulk re-date). Returns the updated pool;
    writes `frob-ratchet.lock.json` as a side effect."""
    lock = load_ratchet_lock(root)
    existing = lock.pool_for(rule_id)
    existing_keys = existing.keys if existing is not None else frozenset()
    today = date.today()

    entries = list(existing.entries) if existing is not None else []
    for key in finding_keys:
        if key not in existing_keys:
            entries.append(RatchetEntry(key=key, baselined=today))

    updated_pool = RatchetPool(rule_id=rule_id, entries=tuple(entries))
    other_pools = tuple(p for p in lock.pools if p.rule_id != rule_id)
    write_result = _write_ratchet_lock(
        root, RatchetLock(pools=(*other_pools, updated_pool))
    )
    if write_result.is_err:
        return Err(write_result.danger_err)
    return Ok(updated_pool)


# frob:ticket T-0569
# frob:doc docs/modules/gates.md#ratchet-pools-t-0569
def clear_ratchet_entry(
    root: Path, rule_id: str, key: str, reason: str
) -> Result[RatchetPool, RatchetError]:
    """Remove one baselined entry (`key`) from `rule_id`'s pool -- the
    TICK004-style disposition step every ratcheted finding eventually
    needs. `Err(ClearReasonMissing)` if `reason` is blank: clearing a
    baseline entry with no reason is a silent discard, the exact failure
    mode ratchet pools exist to prevent. `Err(EntryNotFound)` if `key`
    is not currently baselined for `rule_id`."""
    if not reason.strip():
        return Err(RatchetError.ClearReasonMissing)

    lock = load_ratchet_lock(root)
    existing = lock.pool_for(rule_id)
    if existing is None or key not in existing.keys:
        return Err(RatchetError.EntryNotFound)

    from frob.logging import get_logger

    get_logger(__name__).info(
        "ratchet: %s clearing baselined entry %s: %s", rule_id, key, reason
    )
    remaining = tuple(e for e in existing.entries if e.key != key)
    updated_pool = RatchetPool(rule_id=rule_id, entries=remaining)
    other_pools = tuple(p for p in lock.pools if p.rule_id != rule_id)
    write_result = _write_ratchet_lock(
        root, RatchetLock(pools=(*other_pools, updated_pool))
    )
    if write_result.is_err:
        return Err(write_result.danger_err)
    return Ok(updated_pool)


# frob:ticket T-0569
# frob:doc docs/modules/gates.md#ratchet-pools-t-0569
def resolve_ratchet_severity(rule_id: str, finding_key: str, lock: RatchetLock) -> str:
    """The ratchet-adjusted severity for one finding (T-0569): `"warn"` if
    `finding_key` is already baselined for `rule_id`, `"error"` if it is
    NEW. This is the integration point a real gate's severity resolution
    calls for any rule opted into `[gates.ratchet]` (`ratchet_enabled_rules`)
    -- it does not itself decide WHICH rules are ratcheted, only what
    severity a baselined-vs-fresh finding gets once a rule is."""
    pool = lock.pool_for(rule_id)
    if pool is not None and finding_key in pool.keys:
        return "warn"
    return "error"


# frob:ticket T-0569
# frob:doc docs/modules/gates.md#ratchet-pools-t-0569
# frob:waive AFFECT001 reason="T-1371 only widens internal exception handling; the documented missing-is-default behavior is unchanged, so docs/modules/gates.md#ratchet-pools-t-0569 needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
def ratchet_enabled_rules(root: Path) -> frozenset[str]:
    """The rule ids opted into ratcheting via `[gates.ratchet] rules =
    [...]` in `root/frob.toml` (T-0569) -- empty (no rule ratcheted) if
    the file, table, or key is absent, matching every other per-section
    `frob.toml` reader's missing-is-default posture (`load_arch_config`
    precedent)."""
    toml_path = root / "frob.toml"
    if not toml_path.is_file():
        return frozenset()
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
        rules = data.get("gates", {}).get("ratchet", {}).get("rules", [])
        return frozenset(str(r) for r in rules)
    except (OSError, tomllib.TOMLDecodeError):
        return frozenset()
    except Exception:
        # Missing-is-default (this function's own docstring) over a
        # genuinely malformed `[gates.ratchet]` shape too (a non-dict
        # `gates`/`ratchet` table, a non-list `rules`), not just the two
        # named load failures (EXHAUST001, T-1371).
        return frozenset()


# frob:ticket T-4240
# frob:doc docs/modules/gates.md#base001-a-baseline-overrun-blocks-land-reported-by-name-t-4240  # noqa: E501
# frob:todo T-draft-daef879a wire into gate pipeline once T-4540/T-4214 release their leases  # noqa: E501
# frob:enforces CHK-GATE-BASE001
def baseline_overrun_violations(
    root: Path, current_counts: dict[str, int]
) -> list[Violation]:
    """BASE001 (T-4240, consumer F-326/H2-3): a tracked
    `frob-ratchet.lock.json` pool whose CALLER-measured current live
    finding count (`current_counts[rule_id]`, the caller's own honest
    count for `rule_id` -- this function takes no opinion on how it was
    produced, the SAME "caller decides, this function only judges"
    contract `resolve_ratchet_severity` already uses one call above)
    exceeds that pool's committed baseline size (`len(pool.entries)`) is
    reported as ONE named `BASE001` finding per over-baseline rule,
    naming the lock file, the rule id, and both counts -- the pool-level
    sibling `resolve_ratchet_severity`'s per-finding-key warn/error
    resolution does not itself surface: a caller could apply
    `resolve_ratchet_severity` to every current key and still never emit
    a single finding that says "this rule's baseline no longer holds",
    if every new key happened to individually recover to warn by some
    other path (config drift, a partial re-snapshot) -- BASE001 is the
    aggregate fact a red ratchet exists at all, named so a land-time
    reader does not have to re-derive it from a raw count delta
    (T-3985's own SUBJECT001 "silent zero"/silent-drift lesson, applied
    here to "silent growth" instead).

    A rule absent from `current_counts` is not judged (the caller did
    not measure it this run). A rule present in `current_counts` but
    with NO committed pool at all (`pool_for` returns `None`, i.e.
    `frob pool snapshot` has never run for it) is likewise silent here
    -- an un-ratcheted rule has no "accepted_count" to exceed, and
    forcing one into existence is `frob pool snapshot`'s job, not this
    finding's (mirrors this module's own `resolve_ratchet_severity`,
    which only ever applies to a rule with a real pool; a rule with no
    pool is simply not opted into ratcheting yet, `ratchet_enabled_
    rules`'s territory, not BASE001's)."""
    lock = load_ratchet_lock(root)
    violations: list[Violation] = []
    for rule_id in sorted(current_counts):
        pool = lock.pool_for(rule_id)
        if pool is None:
            continue
        current = current_counts[rule_id]
        baseline = len(pool.entries)
        if current <= baseline:
            continue
        from frob.logging import get_logger

        get_logger(__name__).warning(
            "ratchet: BASE001 %s current %d exceeds baseline %d in %s",
            rule_id,
            current,
            baseline,
            _LOCK_REL,
        )
        violations.append(
            Violation(
                rule="BASE001",
                severity=Severity.ERROR,
                file=str(_LOCK_REL),
                line=1,
                message=(
                    f"BASE001: {_LOCK_REL} rule={rule_id} current {current} "
                    f"exceeds baseline {baseline} -- this ratchet pool has "
                    "grown past its committed baseline; snapshot the new "
                    f"findings deliberately (`frob pool snapshot {rule_id}`) "
                    "or fix them before landing"
                ),
                symref=rule_id,
            )
        )
    return violations
