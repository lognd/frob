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
  - eval/process-control/ffi/install-hook: NEW code
    (`_extended_kind_violations`). GAP STATEMENT: `_effects.py::
    _KIND_MAP` is scoped (by its own docstring, T-0079) to net/
    fs-write/exec only -- "eval/process-control/ffi/install-hook are
    vet-specific dependency-vetting signals with no `may`-capability
    analog yet" -- so THREAT004 structurally cannot see these four
    kinds no matter what `may` declares. `scan_file_
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

SYS103 (SYS-COV, T-0667) coverage totality -- every file with an OBSERVED
capability effect (`scan_file_capabilities`, T-0328's import/binding-
aware resolver, not a bare substring guess) that is `FOREIGN` to the
`_capability_binding` partition. NEW code (`_coverage_totality_
violations`). GAP STATEMENT: SYS102 already flags every `FOREIGN` file
under `src/frob/` (capable or not), but it is HARDCODED to `_PACKAGE_ROOT`
("src/frob") -- module docstring's own T-0211 note: "every OTHER repo
running `frob sys audit` structurally lacks `src/frob/` by design", so
SYS102 is silent by construction on any tree that is not frob's own. The
T-0341 epic's coverage-totality acceptance criterion ("every deployable/
public module -- and every module the binding-aware scanner finds ANY
capability in -- must bind to exactly one strata node; unbound-but-
capable code is a hard failure") needs to hold for ANY audited repo, not
just frob's own -- `docs/design/structural-linter-adversarial-hardening.md`
draws the "like COV001 for docs" analogy: a capable module that escapes
the model is exactly as unacceptable as an undocumented public symbol.
SYS103 is that root-general form: it runs over the SAME `_capability_
binding` superset (any root, any repo layout) and fires ONLY for a
`FOREIGN` file the scanner observes at least one capability in -- a
`FOREIGN` file with zero observed capabilities (a pure-data module, an
`__init__.py` with nothing but re-exports) is not dangerous code escaping
an obligation, so SYS103 stays silent for it exactly as SYS-COV's own
acceptance criterion requires ("every module bound to a node" is silent;
narrower still, a capability-free FOREIGN file was never the threat this
rule exists to catch). SYS102 is UNCHANGED and still runs alongside
SYS103 for frob's own tree -- SYS103 does not replace it, it closes the
gap SYS102's `_PACKAGE_ROOT` scope leaves on every OTHER repo.

SYS104 (T-0668) exact interface conformance -- a node's declared
`interface=<symbol>` attrs (this ticket's convention, same "opaque attr
string" mechanism `code=`/`managed` already use, T-0078/T-0172; no
grammar change) must EQUAL the REQUIRED interface surface: the subset of
the node's real public symbols (`__all__` if the module declares one,
else every non-underscore-prefixed module-level `def`/`class`/assignment
target across the node's `code=`-bound `.py` files, `_node_real_public_
surface`) that is ALSO imported by name (`from <module> import <name>`,
resolved in-repo) from at least one file owned by a DIFFERENT node
(`_cross_node_referenced_symbols`). Fires TWO ways: a declared symbol
absent from the required surface (`docs/design/structural-linter-
adversarial-hardening.md` "declared-but-absent declaration" row), and a
required-but-undeclared symbol (the same doc's "undeclared public
surface" row -- `secret_backdoor` example, assuming some OTHER node
imports it by name; module-internal-only symbols are simply not part of
the contract at all, T-1625). MANDATORY as of T-1113 (closes the T-0668
disclosed opt-in scope cut): every node whose REQUIRED surface is
non-empty is evaluated, whether or not it has declared any `interface=`
attr yet.

T-1625 (option 3 of that ticket's three, chosen over exempting tests --
see the ticket for the full reasoning): before this, `interface=`
declared the WHOLE real public surface, verbatim, node by node -- and
`design/frob.strata`'s `testsuite` node, whose real surface is every
top-level test class/function name across `tests/**`, had grown to 5277
declared symbols (more than half of the ~9000 across the whole file) even
though NOTHING ever imports a test by name; a test exposes no contract to
any consumer. Narrowing to "actually referenced across a node boundary"
fixes the general problem, not just testsuite's instance of it: every
node's declared list shrinks to the names some OTHER node's code genuinely
depends on, matching what "interface" is supposed to mean (a CONTRACT,
not an inventory), while `_node_real_public_surface` itself (SYS106's own
side, `_module_public_symbols`, and every other consumer) is UNCHANGED --
only SYS104's comparison and `sync-interface`'s writer narrow. A node
with an EMPTY required surface (no bound `.py` files, files with nothing
public, or a real surface nothing outside the node ever imports by name --
true of every pure test-tree node) stays exempt. Python-only, same
boundary `bind_code` itself already draws (module docstring above); the
cross-reference walk is also Python-`from`-import-only (module docstring's
"dominant intra-package style" note on `_python_imports_with_lines`) --
a bare `import module` followed by `module.symbol` attribute access is a
disclosed scope cut, not tracked as a reference (rare in this codebase's
own style; T-1625 follow-up if it ever matters in practice).

SYS105 (T-0669) purpose contract -- a node's declared `purpose=<profile>`
attr (same opaque-attr convention, at most one per node) names a fixed,
closed vocabulary of allowed-effect profiles (`_PURPOSE_PROFILES`); any
observed effect kind (the SAME `_observed_raw_kinds_by_node`/
`_all_kinds_view` union SYS101 already computes) outside the declared
profile's allowed set fires. An unrecognized profile name is itself a
finding (a typo'd purpose is not silently permissive). Disclosed scope
cut, UNCHANGED by T-1113 (which flipped only SYS104 to mandatory, per its
own declared follow-up): only a node that HAS declared a `purpose=` attr
is checked; making every node declare one is a disclosed follow-up, not
forced here.

SYS106 (T-0670) binding totality / laundering -- code laundered into an
unbound (`FOREIGN`) file that is nonetheless *reachable* (via resolved
local python imports, `_code_binding.py::resolve_local_import`, followed
transitively) from a bound node's own files. SYS103 already flags any
`FOREIGN` file with an observed capability over its own scan (whole
root, unconditionally, as of T-1091 -- `_coverage_totality_scan_prefix`'s
own docstring has the T-0667-restricted-then-dropped history); SYS106
closes the specific evasion the design doc names ("binding need not be
total, so logic can be laundered into an unbound file") by following the
REACHABILITY edge itself, which stays independently useful even now that
SYS103 itself is unrestricted: SYS103 only fires when it actually WALKS
to a capable FOREIGN file, whereas SYS106 fires from the opposite
direction (starting at a bound node and following its real import
edges), so a file some future exclude-glob or walk boundary hides from
SYS103's own walk but that a bound node still imports at runtime is
still caught. Cycle-safe (visited-set BFS over resolved import targets).

SYS108 (T-1624) duplicate interface declaration -- a node whose
`interface=` attrs contain the SAME symbol name more than once (module
attrs preserve every declared entry verbatim, T-1198's `interface=[...]`
compact-block form included, so two byte-identical `attr interface=[...]`
blocks on one node elaborate into every symbol appearing twice). Found and
fixed for real in `design/frob.strata` itself: 45 duplicated blocks across
~17 nodes, long-standing (predates any single sync-interface run), silent
because the parser tolerates duplicate attrs and `_node_attr_values`
(SYS104's own reader) never deduped its list -- a declaration language
whose own declarations can silently duplicate cannot be the source of
truth it is meant to be. ALWAYS ERROR (no advisory tier, unlike SYS107):
there is no legitimate reason for a node to declare the same interface
symbol twice.

SYS107 (T-1451) via-less-may-on-a-large-node advisory -- a node whose
`code=` glob(s) bind more than `_LARGE_NODE_FILE_THRESHOLD` real files but
declares at least one `may` atom with NO `via` (a T-1440 whole-node
grant) is an advisory (WARN by default) finding: the bigger a node's
bound surface, the less a whole-node grant actually tells a reviewer
about which files really need the capability, and the more valuable
narrowing it to `via` globs would be. Deliberately WARN, not ERROR, by
default (an advisory nudge toward scoping, not a new hard requirement on
every pre-existing declaration) -- `[strata] require_may_scope` in
`frob.toml` (`_scope_config.py`) escalates it to ERROR for a repo whose
owner is ready to commit. GAP STATEMENT: nothing else in this module (or
`_effects.py`) evaluates a node's OWN size against its grants' `via`
coverage -- SYS100/SYS101 both join declared-vs-observed per file or per
node, never asking whether a via-less grant's blast radius is large
enough to be worth narrowing at all.

SYS109 (T-1627) stale via symbol -- a symbol-form `via` entry
(`"glob::qualname"`, T-1627) whose named symbol resolves to NOTHING in
any of the node's own bound files: renamed, moved, or deleted since the
grant was written. ALWAYS ERROR: a `via` naming a symbol that no longer
exists is worse than no `via` at all -- it reads as a deliberate, narrow
grant while authorizing nothing real, exactly the failure mode a stale
declaration must never be allowed to hide as ("cannot resolve the named
symbol" must be its own loud outcome, never a silent pass or a silent
deny). `_effects.py::check_stale_via_symbols` implements the check and is
independently unit-tested; GAP STATEMENT: it is not yet wired into `frob
sys audit`'s own CLI/gate surface (`_audit.py`, `frob.gates._sys_
selfaudit`) -- both live outside this ticket's declared scope, so the
wiring is filed as its own follow-up ticket rather than silently folded
in here.

SYS110 (T-1629) undeclared intended surface -- the INTENT-not-mirror
replacement for the deleted SYS104 (T-1870: SYS104's bidirectional
equality against a MIRROR `interface=` list, kept in sync by an auto-
writer, was deleted per an explicit owner directive that no code path may
auto-update declared public-symbol surface; a generated mirror cannot be
"violated" in any meaningful sense -- disagreement just means "the writer
has not run yet"). SYS110 flips the relationship: `interface=` is now
read purely as HAND-DECLARED INTENT, never written by any code path, and
a node's REAL public surface (`_node_real_public_surface`, unchanged)
must be a SUBSET of what it declares -- any real public symbol outside
the declared set is a violation, an accidental surface leak turned into a
build failure instead of a silent regeneration prompt. PHASED-MIGRATION
DESIGN (deliberate, not a gap): a node with ZERO `interface=` attrs has
not yet opted into hand-declared intent and is silently skipped, rather
than treated as "declares an empty surface" (which would force one
repo-wide big-bang migration of the current ~800-symbol sprawl into
hand-curated lists) -- migrating each node's declared intent by hand,
one at a time, is real follow-up work this ticket does not attempt to
finish in one sweep. `_node_attr_values`/`_INTERFACE_PREFIX` (T-0668,
survived T-1870's SYS104 deletion because SYS106/SYS108 also depend on
them) are reused verbatim, so a node's declared set reads identically
to how SYS108's duplicate-detection already reads it."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import CodeBinding, bind_code
from ._errors import StrataError
from ._models import KernelModel
from ._scope_config import load_strata_scope_config
from ._selfconform_ids import (
    _LARGE_NODE_FILE_THRESHOLD,
    SYS107_FAIL_CLOSED_ATOMS,
    SYS110_UNAUDITED_NODES,
    SYS_BINDING_TOTALITY,
    SYS_COVERAGE_TOTALITY,
    SYS_DUPLICATE_INTERFACE,
    SYS_PURPOSE_CONTRACT,
    SYS_STALE_DESIGN,
    SYS_UNDECLARED_INTENDED_SURFACE,
    SYS_UNDECLARED_INTERFACE,
    SYS_UNMODELED_CODE,
    SYS_VIA_LESS_LARGE_NODE,
)
from ._selfconform_kinds import (
    _EXTENDED_KINDS,
    _aggregate_raw_kinds_by_node,
    _all_kinds_view,
    _capability_binding,
    _extended_kinds_view,
    _observed_all_kinds_by_node,
    _observed_extended_kinds_by_node,
    _observed_raw_kinds_by_file,
    _sorted_capability_files,
)
from ._selfconform_models import SelfConformReport, SelfConformViolation
from ._waive import (
    CONFORMANCE_WAIVER_EXPIRED_RULE,
    STALE_WAIVER_RULE,
    WaiverApplication,
    _split_waiver_rule,
    _stale_detail,
    apply_waivers,
    parse_waiver_expiry,
)

#: T-2729: these SYS1xx symbols are not referenced below -- they are kept
#: as re-exports on `frob.strata._selfconform`'s own namespace, the
#: import path external consumers (`frob.gates._sys_selfaudit`,
#: `_mutation_audit.py`, `_sync_may.py`, `test_selfconform.py`) already
#: use, so the file split does not move the public import surface out
#: from under them.
__all__ = [
    "SYS107_FAIL_CLOSED_ATOMS",
    "SYS110_UNAUDITED_NODES",
    "SYS_BINDING_TOTALITY",
    "SYS_COVERAGE_TOTALITY",
    "SYS_DUPLICATE_INTERFACE",
    "SYS_PURPOSE_CONTRACT",
    "SYS_STALE_DESIGN",
    "SYS_UNDECLARED_INTENDED_SURFACE",
    "SYS_UNDECLARED_INTERFACE",
    "SYS_UNMODELED_CODE",
    "SYS_VIA_LESS_LARGE_NODE",
    "SelfConformReport",
    "SelfConformViolation",
    "_EXTENDED_KINDS",
    "_observed_all_kinds_by_node",
    "_observed_extended_kinds_by_node",
    "_sorted_capability_files",
    "_stale_design_violations",
    "_extended_kind_violations",
    "_bind_conformance_inputs",
    "_dedupe_sys100_extended_against_core",
    "check_self_conformance",
]
from ._selfconform_binding_rules import (
    _binding_totality_violations,
    _unmodeled_violations,
    _via_less_large_node_violations,
)
from ._selfconform_core_rules import (
    _core_undeclared_violations,
    _coverage_totality_violations,
    _extended_kind_violations,
    _stale_design_violations,
)
from ._selfconform_surface_rules import (
    _duplicate_interface_violations,
    _purpose_contract_violations,
    _undeclared_intended_surface_violations,
)

_log = get_logger(__name__)


# frob:doc docs/strata/selfconform.md#the-three-rules
# frob:enforces CHK-GATE-SYS100
# frob:enforces CHK-GATE-SYS101
# frob:enforces CHK-GATE-SYS102
# SYS103 edge added at T-0667's coordinator close-out, once the registry
# entry existed and SYS103 registered in the live rule set (the follow-up
# T-0667's Done report deferred).
# frob:enforces CHK-GATE-SYS103
# T-1113: CHK-GATE-SYS104/105/106 registry entries added alongside the
# SYS104 opt-in-to-mandatory flip, mirroring the CHK-GATE-SYS103
# precedent above.
# frob:enforces CHK-GATE-SYS105
# frob:enforces CHK-GATE-SYS106
# T-1451: CHK-GATE-SYS107 registry entry added alongside the via-less-
# may-on-a-large-node advisory (_via_less_large_node_violations below),
# mirroring the CHK-GATE-SYS105/106 precedent above.
# frob:enforces CHK-GATE-SYS107
# frob:enforces CHK-SUBSYS-STRATA
# T-0672: SLH-SYS-EVA-* edges bind this function directly to the
# structural-linter-adversarial-hardening.md denominator rows T-0668/
# T-0669/T-0670 close (docs/design/registry/arch-checks.yaml's
# `handled_by:SYS100`/`SYS105`/`SYS106` dispositions). T-1870: the
# CHK-GATE-SYS104 registry entry and the SLH-SYS-EVA-03-UNDECLARED-
# PUBLIC-SURFACE `frob:enforces` edge that used to sit here are both
# removed -- SYS104 (and its writer) are deleted, per an explicit owner
# directive that no code path may auto-update declared public-symbol
# surface; SLH-SYS-EVA-03 is re-dispositioned `out_of_scope:reasoned-
# deferral` in arch-checks.yaml pending T-1629.
# frob:enforces SLH-SYS-EVA-01-UNMODELED-MODULE
# frob:enforces SLH-SYS-EVA-02-UNDER-DECLARED-CAPABILITY
# frob:enforces SLH-SYS-EVA-04-PURPOSE-DRIFT
# frob:enforces SLH-SYS-EVA-05-BINDING-LAUNDERING
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
    default, never a silent partial scan.

    T-1449: `_sorted_capability_files(root)` -- a full, `[graph].exclude`-
    filtered tree walk -- used to run TWICE per call (once inside
    `_capability_binding`, again inside `_coverage_totality_violations`),
    doubling the walk cost of every `check_self_conformance` invocation,
    including the two full-repo-scan tests
    (`TestRealGateGreen`/`TestCoverageTotality`) whose back-to-back peak
    memory/wall time motivated pinning them to one xdist worker. Walked
    exactly ONCE here and threaded through both call sites instead."""
    capability_files = _sorted_capability_files(root)
    bound_binding = _bind_conformance_inputs(model, root, capability_files)
    if bound_binding.is_err:
        return Err(bound_binding.danger_err)
    capability_binding = bound_binding.danger_ok

    violations = _collect_sys_violations(
        model, capability_binding, root, capability_files
    )
    applied = _apply_sys_waivers(model, violations)
    applied = _apply_conformance_waiver_staleness(applied)
    return Ok(_finalize_self_conform_report(applied, root))


#: SYS105/SYS106 -- the conformance-obligation waiver families T-0671's
#: staleness gate applies to (module docstring's T-0671 section).
#: SYS100-103 are UNCHANGED: their own bounded-escape-hatch treatment is
#: out of this ticket's scope (T-0341's acceptance criterion [4] names
#: "interface/purpose/binding waivers" specifically, the conformance
#: checks T-0668/T-0669/T-0670 built). T-1870: SYS104 (interface
#: conformance) used to join this set for the identical reason; deleted
#: along with the rule itself, per an explicit owner directive that no
#: code path may auto-update declared public-symbol surface.
_CONFORMANCE_WAIVER_RULES: frozenset[str] = frozenset(
    {SYS_PURPOSE_CONTRACT, SYS_BINDING_TOTALITY}
)


# frob:enforces CHK-GATE-SYSWAIVE003
# frob:tests tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness.test_expired_waiver_refires_and_is_flagged  # noqa: E501
# frob:tests tests/unit/strata/test_selfconform.py::TestConformanceWaiverStaleness.test_missing_expiry_marker_treated_as_expired  # noqa: E501
def _apply_conformance_waiver_staleness(
    applied: WaiverApplication[SelfConformViolation],
    today: date | None = None,
) -> WaiverApplication[SelfConformViolation]:
    """T-0671 acceptance criterion [0]: a SYS104/SYS105/SYS106 waiver
    older than its `expires:YYYY-MM-DD` staleness bound (module
    docstring's T-0671 section, `_waive.py::parse_waiver_expiry`) is
    EXPIRED -- its finding moves back into `kept` (the underlying
    obligation re-fires, unchanged from what it would have been with no
    waiver at all) and a new `CONFORMANCE_WAIVER_EXPIRED_RULE`
    (SYSWAIVE003) finding names the expired waiver. A conformance waiver
    with NO `expires:` marker at all is treated identically to one whose
    date has passed (fail closed -- staleness-dating is mandatory for
    these three families, not optional). Every OTHER family's waiver
    (SYS100-103, THREAT002/003, LINT004, ...) passes through `waived`
    unchanged -- this gate is scoped to `_CONFORMANCE_WAIVER_RULES` only.
    `today` is injectable for deterministic tests; `None` (the production
    default) resolves to the real wall-clock date at call time."""
    today = today if today is not None else date.today()
    still_valid: list = []
    reopened: list[SelfConformViolation] = []
    for wf in applied.waived:
        family, _sub_target = _split_waiver_rule(wf.waiver.rule)
        if family not in _CONFORMANCE_WAIVER_RULES:
            still_valid.append(wf)
            continue
        expiry = parse_waiver_expiry(wf.waiver.reason)
        if expiry is not None and expiry >= today:
            still_valid.append(wf)
            continue
        _log.warning(
            "selfconform: SYSWAIVE003 expired conformance waiver %s on %s "
            "(expiry=%s) -- underlying obligation re-fires",
            wf.waiver.rule,
            wf.waiver.node,
            expiry,
        )
        reopened.append(wf.finding)
        reopened.append(
            SelfConformViolation(
                rule=CONFORMANCE_WAIVER_EXPIRED_RULE,
                node=wf.waiver.node,
                detail=(
                    f"waive {wf.waiver.rule!r} on node {wf.waiver.node} is "
                    f"expired (reason={wf.waiver.reason!r}, "
                    + (
                        f"declared expiry {expiry.isoformat()}"
                        if expiry is not None
                        else "no expires:YYYY-MM-DD marker"
                    )
                    + ") -- underlying obligation re-fires"
                ),
            )
        )
    return WaiverApplication(
        kept=tuple(applied.kept) + tuple(reopened),
        waived=tuple(still_valid),
        stale=applied.stale,
    )


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
    model: KernelModel, root: Path, capability_files: list[Path]
) -> Result[CodeBinding, StrataError]:
    """`bind_code` then `_capability_binding`, in order -- the two fallible
    binding steps `check_self_conformance` needs before any SYS rule can
    run, split out purely to keep that function's body short.
    `capability_files` (T-1449): threaded straight through to
    `_capability_binding` -- `check_self_conformance`'s one shared walk,
    see that function's docstring."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    capability_bound = _capability_binding(
        model, bound.danger_ok, root, capability_files
    )
    if capability_bound.is_err:
        return Err(capability_bound.danger_err)
    return Ok(capability_bound.danger_ok)


def _dedupe_sys100_extended_against_core(
    core: list[SelfConformViolation], extended: list[SelfConformViolation]
) -> list[SelfConformViolation]:
    """T-0266: `_core_undeclared_violations` (THREAT004 delegate, real
    file:line evidence per observed site) and `_extended_kind_violations`
    (one coarse node-level finding per capability kind, module docstring's
    SYS100 gap statement) are two INDEPENDENT SYS100 producers joined
    against the same `(node, capability)` space -- today's `_KIND_MAP`
    (net/fs/exec) and `_EXTENDED_KINDS` (eval/process-control/ffi/
    install-hook/sql/deserialize/html_render/fetch_url/client_storage/
    fs-read) vocabularies
    happen not to overlap, but nothing enforces that split staying true as
    either registry grows (T-0158/T-0304 already moved capability strings
    between the two more than once), so a future/config-drift kind landing
    in both tables would silently double-report the SAME site under one
    rule id. Filters `extended` down to findings whose `(node, capability)`
    is NOT already present in `core` -- `core` is kept whole (it is the
    ONLY one of the two that can legitimately report multiple real sites
    for the same node+kind, one per observed file:line, and those must all
    survive), `extended` (one entry per node+kind by construction, module
    docstring's `_extended_kind_violations`) is the one filtered since it
    carries strictly less evidence than a matching core finding for the
    same `(node, capability)`."""
    core_keys = {(v.node, v.capability) for v in core}
    return [v for v in extended if (v.node, v.capability) not in core_keys]


def _collect_sys_violations(
    model: KernelModel,
    capability_binding: CodeBinding,
    root: Path,
    capability_files: list[Path] | None = None,
) -> list[SelfConformViolation]:
    """Every SYS100/SYS100-extended/SYS101/SYS102/SYS103 finding, in that
    order, for `check_self_conformance`. T-0266: the extended SYS100 pass is
    deduped against the core pass (`_dedupe_sys100_extended_against_core`)
    before being appended, so a `(node, capability)` observed by BOTH
    passes surfaces as ONE finding, not two. T-0830 (H5): the extended
    (SYS100) and all-kinds (SYS101) observed-kinds views used to be two
    independent full scans of every owned file (`_observed_extended_kinds_
    by_node` and `_observed_all_kinds_by_node` each calling
    `scan_file_capabilities` on the same files); `raw_by_node` is now
    scanned ONCE here and both cheap set views (`_extended_kinds_view`,
    `_all_kinds_view`) are derived from it before being handed to the two
    violation functions. `capability_files` (T-1449): threaded through to
    `_coverage_totality_violations` -- `check_self_conformance`'s one
    shared walk, see that function's docstring. `None` (every direct
    caller/test with no walk handy) falls back to a fresh walk there."""
    core_violations = _core_undeclared_violations(model, capability_binding, root)
    raw_by_file = _observed_raw_kinds_by_file(capability_binding, root)
    raw_by_node = _aggregate_raw_kinds_by_node(capability_binding, raw_by_file)
    extended_violations = _extended_kind_violations(
        model, _extended_kinds_view(raw_by_node)
    )
    violations = list(core_violations)
    violations.extend(
        _dedupe_sys100_extended_against_core(core_violations, extended_violations)
    )
    violations.extend(
        _stale_design_violations(
            model, root, capability_binding, _all_kinds_view(raw_by_file)
        )
    )
    violations.extend(_unmodeled_violations(root, capability_binding))
    violations.extend(
        _coverage_totality_violations(capability_binding, root, capability_files)
    )
    violations.extend(_duplicate_interface_violations(model))
    violations.extend(
        _undeclared_intended_surface_violations(model, capability_binding, root)
    )
    violations.extend(_purpose_contract_violations(model, _all_kinds_view(raw_by_node)))
    violations.extend(_binding_totality_violations(model, capability_binding, root))
    scope_config = load_strata_scope_config(root)
    threshold = scope_config.require_may_scope_threshold or _LARGE_NODE_FILE_THRESHOLD
    violations.extend(
        _via_less_large_node_violations(model, capability_binding, threshold)
    )
    return violations


def _apply_sys_waivers(model: KernelModel, violations: list[SelfConformViolation]):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174): a
    matched waiver moves its finding into `waived` (still visible, never
    dropped); a waiver that matched nothing is STALE and becomes a new
    SYSWAIVE002 violation so drift fails the audit rather than silently
    going stale forever (`_waive.py` module docstring). Split out of
    `check_self_conformance` purely to keep that function's body short."""
    sys_rules = frozenset(
        (
            SYS_UNDECLARED_INTERFACE,
            SYS_STALE_DESIGN,
            SYS_UNMODELED_CODE,
            SYS_COVERAGE_TOTALITY,
            SYS_PURPOSE_CONTRACT,
            SYS_BINDING_TOTALITY,
        )
    )
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        # T-0174 REJECT round: SYS100/SYS101 fire once per capability kind
        # per node, so the sub-target IS the capability kind
        # (`SelfConformViolation.capability`); SYS102/SYS103 have no
        # sub-target concept (one finding per unmodeled directory/file) and
        # leave `capability` `None`, so both accept only the bare-rule
        # waiver form (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` excludes
        # them -- see `_coverage_totality_violations`'s docstring for why
        # SYS103 must not populate `capability`).
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
            rule=STALE_WAIVER_RULE, node=stale.node, detail=_stale_detail(stale)
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
    "SYS_BINDING_TOTALITY",
    "SYS_COVERAGE_TOTALITY",
    "SYS_PURPOSE_CONTRACT",
    "SYS_STALE_DESIGN",
    "SYS_UNDECLARED_INTERFACE",
    "SYS_UNMODELED_CODE",
    "SelfConformReport",
    "SelfConformViolation",
    "check_self_conformance",
]
