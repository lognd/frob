# invariant spec: [INV-033](invariants/INV-033.md)
"""HOST001/HOST002: movement-impossibility proofs over `std.host`
manifests (T-0256, docs/strata/host.md#movement-impossibility-proofs).

## Module split (T-2844)

This module used to carry all three HOST001/HOST002 checks plus their
shared utilities in one file (T-2826's LARGE001 review found the real
seam but deliberately deferred acting on it -- see that ticket's Done
report). T-2844 splits along that seam, mirroring the leaf-module +
facade pattern `_selfconform.py`/`_selfconform_models.py` already set
(T-2729) for the same reason: `_host_isolation_shared.py` holds
`HostIsolationViolation`/`_PathClaim` and every utility more than one
check reads, with NO import of any sibling `_host_isolation_*` module
(so nothing here forms an import cycle); `_host_isolation_lateral.py`
holds HOST001, `_host_isolation_vertical.py` holds HOST002,
`_host_isolation_movement.py` holds `host_movement_flows`. This file
stays the facade: it owns the waiver plumbing
(`_apply_host_waivers`/`evaluate_host_isolation_waived`) and the
compromised-owner threat catalog, and imports + re-exports the pieces
that moved so every existing external import (`frob.strata.__init__`,
`_audit.py`, `_scenarios.py`, tests) keeps importing from
`frob.strata._host_isolation` unchanged.

No `design/frob.strata` via-list update was needed: this module makes no
capability-gated calls at all (no filesystem/process/network access --
it is pure `HostManifest` model logic, verified by grep before
splitting, not assumed), so none of the four files here needs a
capability grant either, and `stratamod`'s `interface=` attr is a
symbol-name list, not a per-file one, so it needed no edit either.
`code "src/frob/strata/**"` already covers new files under this
directory (T-2729's own via-list-update precedent, `may "fs.read"`
retargeted from `_selfconform.py` to `_selfconform_surface_rules.py`,
applies only to a split that MOVES a real capability-gated call -- this
one has none).

T-0254 child 2, the SECURITY CORE of the deploy epic: the red-team
scenario ("assume one service user's process is compromised -- what can
it reach?") as a first-class, DEMANDED obligation the moment a model
declares 2+ `runs_as` service users, not an optional afterthought.

HOST001 (lateral movement) fires per DISTINCT service-user PAIR: prove
no shared writable filesystem path, no shared listening port reachable
across users without a declared `Flow` between their nodes, and (T-0272)
no shared OS group. HOST002 (vertical movement)
fires PER service user: no setuid path owned, no sudoers grant, no
root-run unit whose owned paths are writable by a lower-trust user, and
no write access to a path a higher-trust node also owns.

Every sub-target is DERIVED from `HostManifest` intersection
(`_host.py::host_manifest_for`) -- there is no hand-written per-pair or
per-user table to fall out of sync with the model, mirroring
`_threat.py::_entries_by_capability_kind`'s "one join, every caller
reuses it" discipline.

## The (former) honest gap: two sub-targets now derived from HostManifest

`std.host` (T-0255) originally carried NO OS-group and NO sudoers-grant
vocabulary, so `shared group` and `sudoers` UNCONDITIONALLY fired for
every pair/user a HOST001/HOST002 obligation applied to (deny-by-default,
charter law 2), with a detail naming the missing grammar, until an
operator wrote an explicit `waive "HOST001:shared-group" reason="..."` /
`waive "HOST002:sudoers" reason="..."` clause. T-0272 added `group
"NAME"`+ and `sudoers "RULE"`+ to `std.host` (`strata-core/src/parse.rs`,
`_host.py::HostManifest.group`/`.sudoers`), so both sub-targets now
derive REAL findings from `HostManifest` intersection, the same
DERIVED-not-hand-written discipline every other sub-target in this
module follows: HOST001's shared-group fires when two service users'
`group` tuples intersect; HOST002's sudoers fires when a user's
`sudoers` tuple is non-empty. A user who declares no `group`/`sudoers`
at all now correctly proves nothing to report, exactly like `owns`/
`listens`'s absence -- this is the module's fired-until-declared
discipline (charter law 2) applied consistently, not a relaxation of it.

`setuid` (HOST002) IS derivable without new grammar: `owns "PATH"
"MODE"` already carries a full POSIX octal mode string
(`_host.py::HostOwns.mode`), and a 4-digit mode's leading digit encodes
the setuid/setgid/sticky bits (`_mode_owner_writable`/`_mode_has_setuid`
below) -- no grammar change needed, just reading a field that was
already there.

## Windows wiring (T-0606)

T-0261 shipped the Windows `std.host` surface (`service_account`/`acl`/
`pipe`, `docs/strata/host.md#windows-surface-grammar`) but explicitly
deferred wiring it into HOST001/HOST002 to a follow-up ticket (its Done
report and `docs/strata/host.md#scope-boundary-what-is-not-built-here`) --
until T-0606, a windows-only node declaring solely `service_account`/
`acl`/`pipe` produced NO HOST001/HOST002 findings at all, not because it
was proven isolated but because nothing read its windows-shaped facts.
T-0606 closes that gap by generalizing every identity/path/listening-
surface join this module performs to read EITHER platform's fields,
never branching the rule logic itself on `HostManifest.platform`:

- **Service-user identity** (`_identity_of`): a manifest's `runs_as`
  (linux) or `service_account` (windows) -- whichever is set -- is the
  ONE key `_nodes_by_user` groups nodes by. A manifest declaring neither
  contributes no identity, exactly like the pre-T-0606 `runs_as is None`
  skip.
- **Owned paths** (`_PathClaim`, `_owned_paths_by_user`): linux `owns`
  (`HostOwns`, POSIX MODE) and windows `acl` (`HostAcl`, NTFS DACL RULE)
  are merged into one `path -> _PathClaim(write_capable, descriptor)`
  index per user -- `write_capable` reads `_mode_owner_writable` for an
  `owns` entry or `_join_acl_entries` (this module's RULE-shaped analog,
  T-0792's real NTFS deny-overrides-allow join across every ACE declared
  for a path) for an `acl` entry. Every HOST001/HOST002 sub-target that
  intersects owned
  paths (shared-writable-path, root-unit-writable-by-user,
  write-to-higher-trust-path) reads this merged index instead of
  `HostManifest.owns` directly, so a linux/windows pair (or a
  windows/windows pair) proves the identical shape of finding a
  linux/linux pair does. `setuid` stays linux-only by construction, not
  by a platform branch: `_mode_has_setuid` only ever matches a 4-digit
  POSIX MODE string, so an `acl` RULE descriptor (which never parses as
  four decimal digits) structurally cannot trip it -- there is no NTFS
  ACL bit that maps onto POSIX setuid, so no windows finding is invented
  in its place (deny-by-default names the honest absence of an
  equivalent, it does not fabricate one).
- **Listening surface** (`_listening_surface_by_user`): linux `listens`
  (TCP/UDP PORT) and windows `pipe` (named pipe) are merged into one
  labeled string set per user (`"port:9000"` / `"pipe:api-ipc"`) so
  HOST001's cross-user-socket sub-target fires on a shared PORT, a
  shared PIPE, or one of each declared on either side -- the labels keep
  a port number and a same-named pipe from colliding. `host_movement_
  flows` mirrors the same union so `build_compromised_user_scenario`'s
  blast-radius claims stay non-vacuous over a windows pipe exactly like
  they already were over a linux port (module docstring above,
  T-0256's REJECT-round fix).
- **Root-run identity** (`_root_run_nodes`): a linux `unit` with no
  `runs_as` (systemd's own default `User=root`) OR a windows `service`
  with no `service_account` (SCM's own default LocalSystem) is treated
  as the root-equivalent identity HOST002's root-unit-writable-by-user
  sub-target guards against -- the identical "no way to declare root
  explicitly, absence of a dedicated identity on a unit/service IS the
  privileged case" reasoning, generalized to both platforms.

`group`/`sudoers` (T-0272) needed NO change here: neither field was ever
platform-gated in `HostManifest` -- a windows node declaring `group`/
`sudoers` already derived real HOST001/HOST002 findings before T-0606;
only the identity/path/listening-surface joins were linux-only.

## Multi-ACE deny-overrides-allow join (T-0792)

`_owned_paths_by_user`'s windows `acl` half used to collapse every ACE
declared for a path down to whichever one happened to land LAST in
node/field-declaration order (the same "last write wins" convention
`_owns_by_user` uses for POSIX `owns`, which is fine there -- a POSIX
path has exactly one MODE). NTFS ACLs are multi-ACE by design: a real
DACL can carry several ACEs for the SAME path naming different
principals, and evaluates them per-principal, not by picking one entry
and discarding the rest. A last-wins collapse could silently drop an
earlier ACE's real write grant to a principal OTHER than whichever
principal's ACE happened to be declared last -- under-reporting a
`shared-writable-path` finding the model should have caught (the T-0606
reviewer finding this ticket closes).

`_join_acl_entries` fixes this by joining EVERY ACE declared for a path
(across all of a user's nodes) instead of picking one: entries are
grouped by PRINCIPAL, an explicit `:deny` ACE always wins over an
explicit allow ACE for the SAME principal regardless of which was
declared first (real NTFS deny-overrides-allow evaluation order), and
the path is write-capable overall if ANY principal's net verdict is
allow -- a deny for one principal never reaches across to cancel a
different principal's real grant.

## Token-privilege classes: explicit out-of-scope disposition (T-0792)

`SeImpersonatePrivilege`/`SeDebugPrivilege`-class windows TOKEN
PRIVILEGES (as opposed to NTFS DACL/ACE filesystem permissions, which
`acl`/`_join_acl_entries` above DO model) are explicitly OUT OF SCOPE for
HOST001/HOST002, by design, not by oversight: `std.host`'s grammar
(`_host.py::HostManifest`) has no vocabulary for a service account's
granted Windows privileges at all -- there is no `privilege "NAME"`
clause parallel to `group`/`sudoers` (T-0272's precedent for closing a
similar gap) for a manifest to declare one, so there is no fact this
module could join against without inventing ungrounded data (deny-by-
default names the honest absence of an equivalent, module docstring's
"Owned paths" section makes the identical call for POSIX setuid on
windows). A compromised service account holding SeImpersonatePrivilege
or SeDebugPrivilege can escalate to SYSTEM via well-known token-
duplication / process-injection techniques regardless of what its
declared `acl` grants say -- a real vertical-movement vector this module
does NOT currently model, structurally, until `std.host` grows a
`privilege` clause (a `strata-core/src/parse.rs` grammar change, outside
`src/frob/strata/**`'s scope, mirroring the T-0272 precedent) for
HOST002 to derive a real finding from. Filed as a follow-up rather than
silently left unstated.

## Compromised-service-owner threat catalog rows

`COMPROMISED_OWNER_CATALOG` (below) adds the CWE-522/CWE-269/CWE-284
weakness rows this scenario class implicates, joining a SEPARATE
`compromised-owner-baseline` view (`COMPROMISED_OWNER_VIEWS`) rather
than widening `_threat.py::VIEWS`/`CWE_CATALOG` -- the SAME
separate-view precedent `QUALITY_VIEWS`/`CWE_TOP_25_VIEWS` already set
(`_threat.py` module docstring phase E / T-0143): a caller checking the
default OWASP baseline never silently starts being held to a HOST-only
obligation set it did not ask for.
"""

from __future__ import annotations

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._host import manifests_by_node
from ._host_isolation_lateral import evaluate_lateral_isolation
from ._host_isolation_movement import host_movement_flows  # noqa: F401 -- re-exported
from ._host_isolation_shared import (
    HOST_MULTI_INSTANCE_WAIVER_FAMILIES,
    HostIsolationViolation,
    _join_acl_entries,  # noqa: F401 -- re-exported for existing callers
    _nodes_by_user,
    _rule_of,
    _sub_target_of,
)
from ._host_isolation_vertical import evaluate_vertical_isolation
from ._models import KernelModel, Rung
from ._threat import OutOfScopeEntry, WeaknessEntry
from ._waive import (
    WaiverApplication,
    apply_waivers,
)

_log = get_logger(__name__)


def _host_isolation_target_of(
    by_user: dict[str, list[str]], v: HostIsolationViolation
) -> str | None:
    """A HOST001/HOST002 finding waives against the node(s) declaring
    the implicated user -- the FIRST node id `_nodes_by_user` recorded
    for that `runs_as` (a `waive` clause on ANY of a user's nodes
    excuses that user's findings, matching `owns`'s "a user may
    declare more than one node" shape).

    A HOST001 PAIR finding is attributed to `v.user` only (the
    alphabetically-earlier user of the pair, per `evaluate_lateral_
    isolation`'s sorted iteration) -- ONE `waive` clause on that
    user's node discharges the pair finding; a matching `waive`
    clause also placed on the peer (`v.peer`) user's node correctly
    reports STALE (`_waive.py`'s drift-lock), since no HOST001
    finding is ever generated attributed to the peer for the same
    pair. This is intentional, not a gap: a pair has exactly one
    canonical owner for waiver purposes, chosen deterministically, so
    a caller never has two different valid places to write the same
    waiver (which would itself be a "which one is authoritative"
    ambiguity, charter: no duplication)."""
    candidates = by_user.get(v.user, ())
    return candidates[0] if candidates else None


# Each call's `in_scope` names ONLY the rule family it is checking --
# not the union `HOST_MULTI_INSTANCE_WAIVER_FAMILIES` -- exactly the
# `_waive.py::apply_waivers` "each caller passes an `in_scope`
# predicate naming exactly the rule ids it owns" contract
# (`_audit.py`/`_selfconform.py`'s SYS-only vs THREAT/LINT-only split
# is the same precedent): a `HOST002:sudoers` waiver considered by
# THIS call's HOST001 pass would otherwise be reported STALE here too
# (it fires nothing HOST001-shaped), double-counting one waiver as
# two different findings across the two returned `WaiverApplication`s.
def _apply_host_waivers(
    model: KernelModel,
    lateral_violations: tuple[HostIsolationViolation, ...],
    vertical_violations: tuple[HostIsolationViolation, ...],
    by_user: dict[str, list[str]],
) -> tuple[
    WaiverApplication[HostIsolationViolation], WaiverApplication[HostIsolationViolation]
]:
    """Run HOST001 and HOST002 findings each through `apply_waivers`,
    scoped to their own rule family only (see `evaluate_host_isolation_
    waived` for why `in_scope` must not use the union of both families)."""

    def target_of(v: HostIsolationViolation) -> str | None:
        return _host_isolation_target_of(by_user, v)

    host001 = apply_waivers(
        model,
        lateral_violations,
        rule_of=_rule_of,
        target_of=target_of,
        sub_target_of=_sub_target_of,
        in_scope=lambda family: family == "HOST001",
    )
    host002 = apply_waivers(
        model,
        vertical_violations,
        rule_of=_rule_of,
        target_of=target_of,
        sub_target_of=_sub_target_of,
        in_scope=lambda family: family == "HOST002",
    )
    return host001, host002


# frob:doc docs/strata/host.md#movement-impossibility-proofs
# frob:enforces CHK-GATE-HOST001
# frob:enforces CHK-GATE-HOST002
def evaluate_host_isolation_waived(
    model: KernelModel,
) -> Result[
    tuple[
        WaiverApplication[HostIsolationViolation],
        WaiverApplication[HostIsolationViolation],
    ],
    StrataError,
]:
    """HOST001 + HOST002, each run through the SAME `_waive.py::
    apply_waivers` T-0174 waiver channel every other multi-instance-per-
    node rule family uses -- returns `(host001_application,
    host002_application)`. A `waive "HOST001:shared-group" reason="..."`
    (or `HOST002:sudoers`) clause on the node that OWNS the user (any
    node declaring that `runs_as`) suppresses that user's/pair's finding
    for that sub-target only, per `RULE:SUBTARGET` discipline (module
    docstring's `HOST_MULTI_INSTANCE_WAIVER_FAMILIES`)."""
    lateral = evaluate_lateral_isolation(model)
    if lateral.is_err:
        return Err(lateral.danger_err)
    vertical = evaluate_vertical_isolation(model)
    if vertical.is_err:
        return Err(vertical.danger_err)

    by_user = _nodes_by_user({n.id: n for n in model.nodes}, manifests_by_node(model))
    host001, host002 = _apply_host_waivers(
        model, lateral.danger_ok, vertical.danger_ok, by_user
    )
    return Ok((host001, host002))


# frob:doc docs/guides/extending/threat-catalog.md#threat-catalog
# The compromised-service-owner class (module docstring): CWE-522
# (insufficiently protected credentials -- a compromised owner's writable
# paths may hold secrets), CWE-269 (improper privilege management -- the
# HOST002 vertical class), CWE-284 (improper access control -- the
# HOST001 lateral class). Kept in its OWN catalog/view, never appended to
# `_threat.py::CWE_CATALOG`/`VIEWS` -- the same separate-view precedent
# `QUALITY_CATALOG`/`CWE_TOP_25_CATALOG` set (module docstring).
COMPROMISED_OWNER_CATALOG: tuple[WeaknessEntry, ...] = (
    WeaknessEntry(
        id="CWE-284",
        title="Improper Access Control",
        cite="https://cwe.mitre.org/data/definitions/284.html",
        family="security",
        capability_kind=None,  # fired by HOST001, not a `may` capability join
        mitigation="host_isolation",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-269",
        title="Improper Privilege Management",
        cite="https://cwe.mitre.org/data/definitions/269.html",
        family="security",
        capability_kind=None,  # fired by HOST002, not a `may` capability join
        mitigation="host_isolation",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-522",
        title="Insufficiently Protected Credentials",
        cite="https://cwe.mitre.org/data/definitions/522.html",
        family="security",
        capability_kind=None,  # a compromised owner's writable-path blast radius
        # may include resting credentials; no `may` capability names this --
        # HOST001's shared-writable-path finding is the structural signal.
        mitigation="host_isolation",
        rung=Rung.L4,
    ),
)

#: No `OutOfScopeEntry` rows: the compromised-owner class names exactly
#: three ids, all cataloged above -- an empty tuple is the honest
#: "nothing excluded" answer for THREAT001-shaped completeness checks
#: run against this view (mirrors `CWE_CATALOG`'s own empty `out_of_scope`
#: default).
# frob:doc docs/strata/host.md#compromised-service-owner-threat-catalog
COMPROMISED_OWNER_OUT_OF_SCOPE: tuple[OutOfScopeEntry, ...] = ()

#: Baseline view for the compromised-service-owner class (module
#: docstring's separate-view precedent) -- a caller checking this class
#: passes `view="compromised-owner-baseline"` plus `COMPROMISED_OWNER_
#: CATALOG` to `_threat.py::check_catalog_completeness`'s `views`
#: override, exactly `CWE_TOP_25_VIEWS`'s convention.
# frob:doc docs/strata/host.md#compromised-service-owner-threat-catalog
COMPROMISED_OWNER_VIEWS: dict[str, frozenset[str]] = {
    "compromised-owner-baseline": frozenset(
        entry.id for entry in COMPROMISED_OWNER_CATALOG
    ),
}


__all__ = [
    "COMPROMISED_OWNER_CATALOG",
    "COMPROMISED_OWNER_OUT_OF_SCOPE",
    "COMPROMISED_OWNER_VIEWS",
    "HOST_MULTI_INSTANCE_WAIVER_FAMILIES",
    "HostIsolationViolation",
    "evaluate_host_isolation_waived",
    "evaluate_lateral_isolation",
    "evaluate_vertical_isolation",
]
