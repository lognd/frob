"""T-0717 capability taxonomy: ONE mode-qualified capability vocabulary
shared between `frob.vet` (dependency-vetting) and `frob.strata` (`may`
declaration conformance), replacing the ambiguous pre-existing scheme
where `fs-write` (a SCANNER kind) normalized to bare `fs` (the `may`
vocabulary) while `fs-read` was bolted on later as a separate kind, and
`net` carried no mode split at all (user mandate 2026-07-22, tickets.md
T-0717).

Design (mandate points, verbatim intent):

1. ONE mode vocabulary, reusing T-0700's resource-mode names (read|
   append|write are capability-meaningful; `alpha`/`exclusive` are T-0700/
   T-0701's shared-resource-lease concepts, not capability modes, and are
   deliberately absent from `CAPABILITY_MODES` -- no forked mode enum,
   just a shared spelling). Capability families get `family.mode` ids
   (`_mode_qualified`): `fs.read`/`fs.write`, `net.connect`/`net.listen`,
   `env.read`/`env.write`, `proc.spawn`, `ffi.call`. Not every family has
   every mode -- `FAMILY_MODES` defines each family's valid set
   explicitly, never inferred.

2. Coarse declarations (a bare family name, e.g. `may "fs"`) stay legal
   forever and are interpreted fail-closed as the UNION of that family's
   modes for OBLIGATION purposes (`expand_declared_kind`): a coarse
   declarer answers for everything the family can do. An OBSERVED effect
   always maps to its most precise mode (`_normalize_observed_kind`).
   Conformance is "observed is a subset of declared" -- precision is
   REWARDED (a node that only ever reads and declares `fs.read` discharges
   a narrower SYS101 obligation and fails conformance the moment a write
   is observed) but never REQUIRED by fiat; the bare family spelling is
   not deprecated.

3. Migration: `LEGACY_CAPABILITY_ALIASES` maps old hyphenated spellings
   (`fs-write`, `fs-read`) to their precise `family.mode` replacement.
   `resolve_capability_kind` is the ONE place a legacy spelling is
   resolved for gate purposes: it keeps working (warns, naming the
   sunset date and migration target) while `today` is before the alias's
   `sunset`, and becomes a hard `Err` once the sunset has passed --
   mirrors T-0576's `frob:deprecated` shape (since/sunset/ticket) for a
   capability STRING, which `frob:deprecated` (a Python-symbol-only
   directive) cannot itself annotate.

4. SYS101's old `fs`/`fs-read` either-satisfies special case
   (`_selfconform.py::_alias_legacy_fs_observations`, now removed) is
   superseded by this module's generic `expand_declared_kind`: a coarse
   `may "fs"` declaration expands to `{fs.read, fs.write}` and is judged
   discharged the moment ANY of those modes is observed, with no
   fs-specific code left anywhere in the caller.

Wiring status (honest scope cut, not silently promised; T-0771 update):
`fs` and now `net` are wired into a LIVE join (`_effects.py::_KIND_MAP`/
`_declared_kinds`, `_selfconform.py`'s SYS100/SYS101) -- T-0771 gave the
vet scanner a real connect-vs-listen needle distinction for `net`
(`frob.vet._capability_registry`'s `net-connect`/`net-listen` entries,
one per language) mirroring T-0717's own `fs-write`/`fs-read` split, so a
bare `may "net"` declaration now expands to `{net.connect, net.listen}`
the same way `may "fs"` expands to `{fs.read, fs.write}`.

`env` ALSO got a real read-vs-write needle split in T-0771 (`env-read`/
`env-write` registry entries, per language, `env-write` excused rather
than patterned for c-cpp/kotlin where no clean single-process-mutation
idiom exists) -- but `env` is deliberately NOT in `WIRED_MODE_FAMILIES`
yet: unlike `net`/`fs`, `env` has no tier-2 (`_effects.py::_KIND_MAP`)
`may`-declaration join at all today (`env` is one of the vet-only kinds
`_effects.py`'s own module comment calls out as having "no `may`-
capability analog yet") -- there is no live conformance join for
`env.read`/`env.write` to feed, so exploding a coarse `may "env"`
declaration into modes now would be inert, not wrong, and is deferred to
the ticket that actually builds that join (T-0771 Done report files it).

`proc`/`ffi` remain unwired for a DIFFERENT reason, found during T-0771:
the vet registry has no `capability_kind="proc"` entries at all -- process-
spawn signals are registered under the pre-existing, unrelated `"exec"`
kind, not `"proc"` (`ffi` IS a real registry kind, `ctypes`/`cffi`/
`ExtensionFileLoader` entries, but again has no tier-2 join). `FAMILY_MODES`
still defines every family's mode set so the vocabulary is genuinely
single-source from day one; reconciling the `proc`/`exec` naming mismatch,
building the `env`/`proc`/`ffi` tier-2 joins, and sweeping this repo's own
`.strata` models plus the 8 sibling repos' declarations (mandate point 3's
"ESTATE" migration) are explicitly follow-up work, filed rather than
forced into this pass (T-0771 Done report).
"""
# frob:waive INV006 reason="T-1023 INV006 burn-down: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim, same \
# INV006 first-turn-on-pool disposition this repo already applies elsewhere (T-0585)"

from __future__ import annotations

from datetime import date, datetime
from typing import Final

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/strata/selfconform.md#fs-read-fs-write
#: T-0700's resource-mode vocabulary, reused verbatim (mandate point 4 --
#: "do not fork a second mode enum anywhere"). Only the subset that is
#: ever capability-meaningful is listed; `alpha`/`exclusive` are T-0700/
#: T-0701's shared-resource-lease concepts and never appear in
#: `FAMILY_MODES` below.
CAPABILITY_MODES: Final[tuple[str, ...]] = (
    "read",
    "append",
    "write",
    "connect",
    "listen",
    "spawn",
    "call",
)

# frob:doc docs/strata/selfconform.md#fs-read-fs-write
#: Every capability FAMILY's explicitly-defined valid mode set (mandate
#: point 1: "not every family has every mode -- define each family's
#: valid mode set explicitly"). A family absent from this dict (e.g.
#: `exec`, `eval`, `env` before its own mode split lands) has no modes
#: defined yet -- `expand_declared_kind`/`_normalize_observed_kind` leave
#: such a kind unchanged rather than guessing at a split this module has
#: not been told exists.
FAMILY_MODES: Final[dict[str, tuple[str, ...]]] = {
    "fs": ("read", "write"),
    "net": ("connect", "listen"),
    "env": ("read", "write"),
    "proc": ("spawn",),
    "ffi": ("call",),
}

# frob:doc docs/strata/selfconform.md#fs-read-fs-write
#: Families whose mode split is WIRED into a live join this pass (module
#: docstring's "wiring status"): `expand_declared_kind`/`normalize_
#: observed_kind` only ever explode a bare family name from THIS set into
#: its `FAMILY_MODES` union -- a family present in `FAMILY_MODES` but NOT
#: here (net/env/proc/ffi today) has its vocabulary DEFINED but its
#: scanner/declaration join still coarse (a bare `may "net"` stays exactly
#: `{"net"}`, never silently exploded into `{"net.connect", "net.listen"}`
#: that no scanner-observed kind could ever match, which would make every
#: existing bare `may "net"` declaration spuriously go SYS101-stale).
#: Extending this set is the sibling ticket's job (module docstring).
WIRED_MODE_FAMILIES: Final[frozenset[str]] = frozenset({"fs", "net"})


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
# frob:tests tests/unit/vet/test_capability_modes.py::TestModeQualified.test_joins_family_and_mode kind="unit"  # noqa: E501
# frob:waive COV007 reason="T-0871: same -- see COV005 waiver above"
def _mode_qualified(family: str, mode: str) -> str:
    """The ONE `"family.mode"` construction site -- every caller that
    needs a mode-qualified capability id goes through this, never a
    hand-formatted f-string, so the separator cannot drift."""
    return f"{family}.{mode}"


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
#: Every `family.mode` id this vocabulary defines, GENERATED from
#: `FAMILY_MODES` (never hand-duplicated) so the two structures cannot
#: diverge.
CAPABILITY_MODE_KINDS: Final[tuple[str, ...]] = tuple(
    _mode_qualified(family, mode)
    for family, modes in sorted(FAMILY_MODES.items())
    for mode in modes
)


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
# frob:waive COV007 reason="T-0871: same -- see COV005 waiver above"
class _DeprecatedCapabilityAlias(BaseModel):
    """One legacy capability spelling's migration record: the precise
    `family.mode` id it now means, the `since`/`sunset` window, and the
    tracking ticket -- the T-0576 `frob:deprecated` shape (since/sunset/
    ticket) applied to a capability STRING rather than a Python symbol."""

    model_config = ConfigDict(frozen=True)

    alias: str
    target: str
    since: str
    sunset: str
    ticket: str
    reason: str


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
# frob:ticket T-0717
#: T-0717 migration table: legacy scanner/declaration spellings -> their
#: precise `family.mode` replacement. Bare family names ("fs", "net", ...)
#: are DELIBERATELY absent -- mandate point 2 keeps them legal, coarse
#: declarations forever; only spellings that were themselves an attempt at
#: mode-precision (`fs-write`, `fs-read`) are deprecated aliases here.
LEGACY_CAPABILITY_ALIASES: Final[dict[str, _DeprecatedCapabilityAlias]] = {
    "fs-write": _DeprecatedCapabilityAlias(
        alias="fs-write",
        target="fs.write",
        since="2026-07-22",
        sunset="2026-10-20",
        ticket="T-0717",
        reason="fs-write conflated the scanner's write-derived kind with "
        "the bare 'fs' may-declaration vocabulary (SYS101 backward-"
        "compatibly satisfied bare 'fs' with either observed kind); "
        "fs.write is the precise, mode-qualified replacement",
    ),
    "fs-read": _DeprecatedCapabilityAlias(
        alias="fs-read",
        target="fs.read",
        since="2026-07-22",
        sunset="2026-10-20",
        ticket="T-0717",
        reason="fs-read was bolted on (T-0018) ahead of a real mode "
        "vocabulary; fs.read is the precise, mode-qualified replacement",
    ),
}


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
# frob:tests tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind.test_legacy_alias_past_sunset_is_gate_error kind="unit"  # noqa: E501
class CapabilityModeError(ErrorSet):
    """Fallible outcomes of resolving a capability kind through the T-0717
    mode vocabulary."""

    AliasSunset = "a legacy capability alias's sunset date has passed"


def _today() -> date:
    """The current local date, isolated behind a function (not a module-
    level constant) so `resolve_capability_kind`'s `today=` parameter is
    the only thing a caller/test ever needs to inject -- no monkeypatching
    a frozen import."""
    return datetime.now().astimezone().date()


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
# frob:tests tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind.test_precise_kind_passes_through kind="unit"  # noqa: E501
def resolve_capability_kind(
    raw: str, *, today: date | None = None
) -> Result[str, CapabilityModeError]:
    """Resolve one raw capability-kind spelling (a `may` atom's kind
    segment, or a scanner-observed kind) against the T-0717 alias table
    for GATE purposes (unlike `expand_declared_kind`/`normalize_observed_
    kind`, this is the one call site that WARNS or ERRORS on a legacy
    spelling rather than silently canonicalizing it).

    A `family.mode` id or any non-aliased spelling (including a bare
    family name -- mandate point 2, coarse declarations are never
    deprecated) passes through unchanged as `Ok`. A LEGACY alias
    (`LEGACY_CAPABILITY_ALIASES`) resolves to its precise target: while
    `today` is before the alias's `sunset`, this logs a WARNING naming the
    sunset date and migration target and returns `Ok(target)` (T-0717
    acceptance clause 2 -- legacy spellings keep working); once `today` is
    on or past `sunset`, this returns `Err(CapabilityModeError.
    AliasSunset)` (acceptance clause 3 -- a gate error, not a silent
    pass)."""
    alias = LEGACY_CAPABILITY_ALIASES.get(raw)
    if alias is None:
        return Ok(raw)
    effective_today = today if today is not None else _today()
    sunset_date = date.fromisoformat(alias.sunset)
    if effective_today >= sunset_date:
        _log.error(
            "capability modes: legacy alias %r sunset %s has passed -- migrate to "
            "%r (%s)",
            raw,
            alias.sunset,
            alias.target,
            alias.ticket,
        )
        return Err(CapabilityModeError.AliasSunset)
    _log.warning(
        "capability modes: %r is a deprecated alias of %r, sunset %s (%s) -- "
        "migrate now",
        raw,
        alias.target,
        alias.sunset,
        alias.ticket,
    )
    return Ok(alias.target)


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
# frob:tests tests/unit/vet/test_capability_modes.py::TestCanonicalAndNormalize.test_canonical_declared_kind_resolves_alias_regardless_of_sunset kind="unit"  # noqa: E501
def canonical_declared_kind(raw: str) -> str:
    """The PURE (non-logging, never-`Err`) canonicalization of one raw
    declared-kind spelling: a legacy alias always resolves to its precise
    target regardless of sunset window, everything else passes through
    unchanged. Used by conformance JOINS (`_effects.py::_declared_kinds`),
    which must keep working identically on both sides of an alias's
    sunset -- the sunset is a GATE finding (`resolve_capability_kind`,
    wired separately), never a silent capability-conformance regression."""
    alias = LEGACY_CAPABILITY_ALIASES.get(raw)
    return alias.target if alias is not None else raw


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
# frob:tests tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind.test_coarse_fs_covers_union_of_modes kind="unit"  # noqa: E501
def expand_declared_kind(kind: str) -> frozenset[str]:
    """Every precise `family.mode` id a DECLARED capability kind covers
    for conformance-join purposes (mandate point 2): a precise
    `family.mode` id covers only itself; a bare family name with a
    defined mode set (`FAMILY_MODES`) covers the UNION of that family's
    modes (a coarse declarer answers for everything); anything else (a
    family with no defined mode set, e.g. `exec`/`eval`) covers only
    itself, unchanged -- this module never invents modes for a family it
    has not been explicitly told about (module docstring's "wiring
    status")."""
    if "." in kind:
        return frozenset({kind})
    if kind not in WIRED_MODE_FAMILIES:
        return frozenset({kind})
    modes = FAMILY_MODES.get(kind, ())
    return frozenset(_mode_qualified(kind, mode) for mode in modes)


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
# frob:tests tests/unit/vet/test_capability_modes.py::TestCanonicalAndNormalize.test_normalize_observed_kind_matches_canonical kind="unit"  # noqa: E501
# frob:waive COV007 reason="T-0871: same -- see COV005 waiver above"
def _normalize_observed_kind(raw: str) -> str:
    """The precise canonical kind a scanner-OBSERVED capability spelling
    maps to: a legacy alias resolves to its target with no deprecation
    warning (an observation is not a declaration choice -- there is
    nothing for a scanner finding to itself migrate away from), anything
    else passes through unchanged."""
    return canonical_declared_kind(raw)


__all__ = [
    "CAPABILITY_MODES",
    "CAPABILITY_MODE_KINDS",
    "FAMILY_MODES",
    "LEGACY_CAPABILITY_ALIASES",
    "WIRED_MODE_FAMILIES",
    "CapabilityModeError",
    "_DeprecatedCapabilityAlias",
    "canonical_declared_kind",
    "expand_declared_kind",
    "_mode_qualified",
    "_normalize_observed_kind",
    "resolve_capability_kind",
]
