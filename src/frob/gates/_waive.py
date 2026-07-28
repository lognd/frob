"""frob.gates._waive -- the WAIVE00x/DSL001/PLACE001 waiver-matching family.

Extracted from `frob.gates.__init__` (T-1072, T-0395 tier 1 split): every
rule that governs `frob:waive` directives themselves (malformed-directive
detection, unwaivable-channel enforcement, ceiling/scope matching, stale
ticket refs, placement) plus the shared `_match_waiver`/`_apply_waivers`
spine every other gate's violation list is filtered through, and the
`active_ticket`/`ticket_lease_pin` helpers that ride along with it in the
original module (T-1010's `known_gate_rule_ids` literal lives here too --
it is WAIVE002's own "every rule id that can ever appear" source of
truth). Re-exported from `frob.gates.__init__` unchanged so every existing
`frob.gates.<name>` call site keeps working.
"""

# frob:waive ARCH102 reason="fresh T-1072 tier-1 extraction: this module \
# deliberately carries the whole waiver-matching family PLUS the rule-id \
# literal and lease helpers that rode along with it in gates/__init__, so \
# its export clusters mirror the original module's own accepted shape; \
# further cohesion splits are exactly T-1076's (tier 2) remit -- waive at \
# the transitional module, do not block the split that shrank __init__ by \
# 1900 lines"
from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from typani import Err, Ok
from typani.option import Nothing, Option, Some
from typani.result import Result

if TYPE_CHECKING:
    from frob.tickets._leases import LeaseError

from frob.excludes import is_excluded, iter_files, load_exclude_globs
from frob.gates._models import Severity, Violation, WaiverRef
from frob.gitio import current_branch
from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.lang import SymbolKind
from frob.lang._models import ParsedFile, RawComment, RawSymbol
from frob.logging import get_logger
from frob.tickets import TicketQueue, TicketState

_log = get_logger(__name__)


def _waive_edges(snapshot: GraphSnapshot) -> tuple[Edge, ...]:
    """Every valid `frob:waive` edge in the snapshot (dsl.py already rejects a
    waive directive missing `reason=...` as a MalformedDirective, so every
    surviving WAIVE edge here is guaranteed to carry a reason)."""
    return tuple(e for e in snapshot.edges if e.kind == EdgeKind.WAIVE)


def _waivers_by_rule(snapshot: GraphSnapshot) -> dict[str, list[Edge]]:
    """Index WAIVE edges by their target rule id for O(1) rule lookup."""
    index: dict[str, list[Edge]] = {}
    for edge in _waive_edges(snapshot):
        index.setdefault(edge.target, []).append(edge)
    return index


# frob:enforces CHK-GATE-WAIVE001
def _waive001_violations(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """WAIVE001: a `frob:waive` directive missing `reason=...` -- surfaced from
    frob.graph's MalformedDirective list, since frob.graph.dsl already refuses
    to turn such a line into an edge."""
    violations: list[Violation] = []
    for md in snapshot.malformed:
        if "frob:waive" not in md.reason:
            continue
        _log.debug("WAIVE001: %s:%d %s", md.file, md.line, md.reason)
        violations.append(
            Violation(
                rule="WAIVE001",
                severity=Severity.ERROR,
                file=md.file,
                line=md.line,
                message=(
                    f'WAIVE001: {md.file}:{md.line} frob:waive missing reason="..."; '
                    f"add a reason attribute or remove the waiver"
                ),
            )
        )
    return tuple(violations)


# frob:ticket T-0404
# frob:tests tests/test_gates.py::TestDsl001.test_malformed_frob_doc_directive_flagged
# frob:tests tests/test_gates.py::TestDsl001.test_waive_reason_and_tests_kind_not_double_flagged  # noqa: E501
# frob:enforces CHK-GATE-DSL001
def _dsl001_violations(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DSL001: a malformed `frob:` directive not already claimed by a
    per-flavor check (WAIVE001/TEST010/DEBT001).

    T-0404 finding 5: before this rule existed, a malformed/typo'd
    `frob:doc` (or `frob:describes`/`frob:ticket`/`frob:invariant`/any
    other verb) line that `frob.graph.dsl` demotes to a `MalformedDirective`
    produced NO violation at all -- it silently lost its edge (and, for
    `frob:doc`, its drift tracking) with the symbol then just looking
    undocumented rather than "documented wrong". This is the generic
    catch-all WAIVE001/TEST010/DEBT001 were each hand-rolled duplicates of;
    it fires for anything they do not already claim, so no `frob:` comment
    that fails to parse into a real edge goes unreported.
    """
    violations: list[Violation] = []
    for md in snapshot.malformed:
        if any(
            flavor in md.reason for flavor in ("frob:waive", "frob:tests", "frob:debt")
        ):
            continue  # already surfaced by WAIVE001 / TEST010 / DEBT001
        _log.debug("DSL001: %s:%d %s", md.file, md.line, md.reason)
        violations.append(
            Violation(
                rule="DSL001",
                severity=Severity.ERROR,
                file=md.file,
                line=md.line,
                message=(
                    f"DSL001: {md.file}:{md.line} malformed frob: directive: "
                    f"{md.reason}"
                ),
            )
        )
    return tuple(violations)


# frob:ticket T-0101
# frob:ticket T-0399
# frob:ticket T-1010
# Every rule id any Violation-producing gate can emit. `frob:waive` only
# ever suppresses entries in the GateReport's `violations` tuple (see
# `_apply_waivers` below) -- a waiver targeting anything outside this set
# can never match, so WAIVE002 treats that as the definition of
# "unwaivable channel" rather than hardcoding a channel allowlist.
# T-0399 added DUP003 (dup_gate fail-closed when [dup].enforce=true but
# frob-core is unavailable).
#
# T-1010: this literal is the GENERATED-AND-VERIFIED artifact for the
# T-0964 constant/literal rule-id class -- `frob.gates._rule_id_scan.
# generated_gate_rule_ids(repo_root)` is the authority for which
# `rule="..."`/`rule=CONST_NAME` ids are live; when it reports one not
# listed here, paste it in (that is the "hand edit", not a re-derivation
# by inspection). Ids retired on purpose go in `_rule_id_scan.
# RETIRED_RULE_IDS`, never silently deleted here. Ids constructed via a
# bare positional arg or dict-literal value (`_secrets.py`'s `_pat(...)`
# tuples, `_arch.py`'s category dict, `_registry_exhaustiveness.py`'s bare
# returns) or defined outside `_rule_id_scan.SCANNED_BASES` entirely
# (`DUP001`/`DUP002` in `src/frob/dup`, `PERF001`-`PERF009` in `src/frob/
# perf`) are NOT covered by that scan (disclosed residual, see
# `_rule_id_scan`'s module docstring) and stay purely hand-maintained here
# as before this ticket.
# frob:tests tests/test_gates.py::TestKnownGateRuleIds.test_every_emitted_rule_literal_is_known  # noqa: E501
# frob-zone-start known-gate-rules T-1002
_KNOWN_GATE_RULES = frozenset(
    {
        "COV001",
        "COV002",
        "COV003",
        "COV004",
        "COV005",
        # T-0483: `frob:tests` call-graph reachability (COV006) and
        # a `frob:doc` anchor bound to a private helper (COV007).
        "COV006",
        "COV007",
        # T-0504: class-directive placement lint (a `frob:` directive that
        # class-falls-back but plausibly missed a nearby real symbol).
        "PLACE001",
        "DRIFT001",
        "DRIFT002",
        # T-0628: `affects()`-closure digest-drift (T-0325 follow-on) --
        # stale dependent doc anchor (AFFECT001) or stale dependent symbol
        # file (AFFECT002) untouched by the same diff that touched their
        # root.
        "AFFECT001",
        "AFFECT002",
        "SCOPE001",
        # T-0998: scope-declaration-time doc/code/private-helper closure
        # nudge (WARN turn-on, docs/modules/gates.md#new-gate-rule-
        # acceptance-policy-t-0756) -- distinct from SCOPE001 (a diff
        # actually touching an unscoped file).
        "SCOPE002",
        "PRE001",
        "INV001",
        "INV002",
        "INV003",
        "INV004",
        "INV005",
        "INV006",
        # T-0757: `frob:invariant no_import=`/`establishes=` obligation
        # forms -- see `frob.gates._design_invariants`.
        "INV007",
        "INV008",
        "TEST001",
        "TEST002",
        "TEST003",
        "TEST004",
        "TEST005",
        "TEST006",
        "TEST007",
        "TEST008",
        "TEST009",
        "TEST010",
        "TEST011",
        # T-0545: committed `frob-coverage.lock.json` missing/stale/drifted
        # relative to the live coverage.xml-derived data.
        "TEST012",
        # T-0552: a `frob:tests` edge credited toward TEST001-004 only via
        # the c/cpp structural (name/path) fallback, never executed
        # (T-0730: ts retired from this fallback, real vitest evidence now).
        "TEST013",
        # T-0547: two different files' same-leaf-name public symbols, both
        # relying only on the naming-convention fallback, credited by the
        # same collected test node id(s) (B6's def-parse-twice repro).
        "TEST014",
        # T-0548: a public symbol clears TEST001 only via test(s) with no
        # assertion-shaped construct at all (B1's vacuous-test repro).
        "TEST015",
        # T-0755: a ticket's bound evidence killed zero mutants of a
        # diff-touched file it claims to cover -- confirmatory-only.
        "TEST016",
        "TODO001",
        "TODO002",
        # T-0783: a frob:todo edge bound to a still-open ticket whose
        # deferral comment landed under an older project version than the
        # one on disk now (at least one release has shipped since).
        "TODO003",
        # T-0412: frob:debt (temporary, ticket-bound, collected-before-
        # release) vs frob:waive (permanent) -- malformed directive,
        # non-open ticket, expired `until` boundary.
        "DEBT001",
        "DEBT002",
        "DEBT003",
        # T-0576: frob:deprecated -- a ticket-bound sunset date on a public
        # symbol's continued existence. Malformed directive, non-open
        # ticket, still-in-window (warn), and past-sunset (error).
        "DEPR001",
        "DEPR002",
        "DEPR003",
        "DEPR004",
        # T-0639: a deprecated symbol's reference set (frob.exports
        # --consumers file-level import lines + frob.xref textual usages)
        # gains a member absent from the committed
        # frob-deprecated-baseline.lock.json -- a genuinely NEW caller of a
        # symbol already declared on its way out.
        "DEPR005",
        # T-0404 finding 5: catch-all for a malformed `frob:` directive not
        # already claimed by a per-flavor check (WAIVE001/TEST010/DEBT001).
        "DSL001",
        "WAIVE001",
        "WAIVE002",
        # T-0470: over-broad package-prefix waiver reach.
        "WAIVE003",
        # T-0753: a valid-rule waiver matching 0 findings this run (stale/
        # unnecessary waiver hygiene) and a `frob:waive`'s `until=` boundary
        # having passed (expiry, mirroring DEBT003/DEPR004).
        "WAIVE004",
        "WAIVE005",
        # T-0779: stale-waiver detection -- a waiver bound (via `ticket=`
        # or binding reason phrasing) to a now-DONE/DROPPED ticket.
        "WAIVE006",
        # T-0808: a waiver's binding ticket ref that resolves to NO ticket
        # at all (active or archive) -- a typo, or a draft id renumbered
        # at land (T-draft-8cd37914 -> T-0803) that left the waiver
        # pointing at a dead id forever. WARNING-tier: unlike WAIVE006's
        # provably-closed case, an unresolvable id could still be a
        # not-yet-synced ledger view, so this does not error.
        "WAIVE007",
        "DEC001",
        "DEC002",
        "REL001",
        # T-1009: .frob-release.json vs pyproject.toml/uv.lock coherence.
        "REL002",
        "DOC001",
        "DOC002",
        "DOC003",
        "DUP001",
        "DUP002",
        "DUP003",
        "FUZZ001",
        "FUZZ002",
        "FUZZ003",
        "PERF001",
        "PERF002",
        "PERF003",
        "PERF004",
        "PERF005",
        "PERF006",
        "PERF007",
        "PERF008",
        "PERF009",
        # T-1087: `frob vet`'s own rule ids (src/frob/vet/**) -- a
        # different CLI surface (`frob vet`, not `frob check`'s gate
        # family), outside `_rule_id_scan.SCANNED_BASES` entirely, same
        # hand-maintained-outside-scan-basis class as DUP00x/PERF00x
        # above. Widened so `docs/design/registry/*.yaml`'s
        # `handled_by:VET*` dispositions resolve against REG002.
        "VET001",
        "VET002",
        "VET003",
        "VET004",
        "VET005",
        "VET006",
        "VET011",
        "VET-JS",
        "VET-JS003",
        "VET-JS004",
        "VET-PY001",
        "VET-PY002",
        "VET-PY003",
        "VET-RS001",
        "VET-RS002",
        "VET-SOURCE-UNAVAILABLE",
        "VET-TIMEOUT",
        "SYS001",
        "SYS002",
        "SYS003",
        "SYS004",
        "SEC001",
        "SEC002",
        "SEC003",
        # frob:ticket T-0968
        # T-0968: a bare `frob:secret-fake` marker missing `reason="..."`
        # (mirrors WAIVE001's malformed-`frob:waive` contract).
        "SEC004",
        "TICK001",
        "TICK002",
        # T-0409: ledger-hygiene gate (frob.gates.tickets_gate's
        # _tick003_stale_archive) -- too many closed tickets sitting
        # un-archived in the active tickets.md ledger.
        "TICK003",
        # T-0411: queue-health/priority-rot gate (frob.gates.tickets_gate's
        # _tick004_queue_rot) -- a queued/planned ticket past its
        # priority-specific rot-day threshold.
        "TICK004",
        # T-0726: phantom-filing-claim gate (frob.gates.tickets_gate's
        # _tick006_phantom_filing) -- a Done report's "Filed: ..." claim
        # whose id resolves to no ledger block.
        "TICK006",
        # T-0820: undispatched-stale CRITICAL/HIGH alarm (frob.gates.
        # tickets_gate's _tick007_undispatched_stale) -- the frob check
        # half of T-0752's frob.tickets.undispatched_stale, reused verbatim.
        "TICK007",
        # T-0842: unknown/extra ledger field gate (frob.gates.tickets_gate's
        # _tick008_unknown_ledger_fields) -- a ticket carrying a field the
        # current Ticket model does not know (T-0838's extra="allow"
        # captured it as __pydantic_extra__ instead of hard-failing), most
        # often a typoed known field silently losing its value to a schema
        # default.
        "TICK008",
        # T-0714: over-broad-scope nudge (frob.gates.tickets_gate's
        # _tick009_scope_breadth_nudges) -- relocated from `frob ticket
        # doable`'s own per-invocation WARNING wall (T-0453's
        # `large_glob_warnings`, reused verbatim) so the doable listing
        # stays a clean queue and this diagnostic reports once per `frob
        # check` run instead of once per queue query.
        "TICK009",
        # T-0714: stale cross-worktree lease report (frob.gates.
        # tickets_gate's _tick010_stale_lease_report) -- one WARN per lease
        # file (`.git/frob-leases/*.json`, T-0473) whose recorded worktree
        # path no longer exists, naming the file and the remedy (delete
        # it, or let `frob ticket doable`'s own opportunistic prune handle
        # it next time that path is read). Complements TICK009: doable
        # stays quiet, `frob check` is the one place both diagnostics
        # surface with detail.
        "TICK010",
        # T-0788: COMPLIANCE005 (frob.gates.compliance_gate, dispatching
        # frob.strata._compliance.check_cmpl_registry built by T-0607) --
        # a checkable-control CMPL-* compliance-registry unit left
        # deferred/undispositioned. T-0607 built the check but could not
        # register it here nor dispatch it (out of that ticket's scope);
        # this closes the catalogued-is-not-enforced gap it disclosed.
        "COMPLIANCE005",
        # T-0894: COMPLIANCE006 (this module's compliance_gate) -- a
        # compliance.yaml that was committed on this branch's history and
        # has since been deleted, distinguished from "never adopted"
        # (frob.gates._registry_exhaustiveness.path_ever_tracked). Same
        # "adopted then deleted" family as REG012 below.
        "COMPLIANCE006",
        # T-0851: FMT001 (frob.gates.fmt_gate) -- a diff-touched frob:
        # directive comment line over the configured line length, with a
        # `frob fmt <path>` remediation hint. T-0441 built the underlying
        # canonicalizer/`frob fmt` CLI but left this half undone --
        # src/frob/check/ and this rule-catalog were outside that ticket's
        # declared scope.
        "FMT001",
        "PII010",
        "SEC110",
        # T-0665: fail-closed runtime-resolved capability-indirection
        # obligation (frob.gates._opaque.opaque_gate). WARN-tier at first
        # turn-on -- see that module's own docstring.
        "OPAQUE001",
        # T-0781: repo-writable-state (.git/.frob JSON or text) reaching a
        # subprocess argv position with no validator hop or `--`
        # terminator (frob.gates._taint_gate.taint_gate). WARN-tier at
        # first turn-on -- same opaque_gate/T-0688 promotion posture.
        "SEC005",
        # T-0289: long-function is the one frob-arch category channeled into
        # a real gate Violation (see frob.gates._arch's module docstring for
        # why only this one, not the whole ArchCategory surface).
        "ARCH001",
        # T-0728: T-0616's ARCH1xx SRP/cohesion family (frob.arch._srp),
        # now dispatched by analyze_project and channeled into Violations
        # by the same frob.gates._arch.arch_gate as ARCH001 (see that
        # module's docstring for the T-0728 design-decision note).
        "ARCH101",
        "ARCH102",
        "ARCH103",
        # T-1034: CPPTHROW001 (frob.arch._cpp_mayraise's cpp-noexcept-
        # throws category, T-0687), channeled into a real gate Violation
        # by the same frob.gates._arch.arch_gate as ARCH001/ARCH1xx --
        # the one category that channels at Severity.ERROR, see that
        # module's own docstring.
        "CPPTHROW001",
        # T-0396: anti-orphan file-reference gate (frob.gates._refs).
        "REF001",
        "REF002",
        "REF003",
        # T-0343: registry exhaustiveness drift-lock
        # (frob.gates._registry_exhaustiveness).
        "REG001",
        "REG002",
        "REG003",
        "REG004",
        "REG005",
        # T-0407: unified registry model -- malformed entry (REG006) and
        # cross-file id collision (REG007) early-exit closures.
        "REG006",
        "REG007",
        # T-0428: derived-coverage two-SSOT conformance -- REG008
        # (handled_by claim with no frob:enforces edge in code) / REG009
        # (a frob:enforces edge naming a concept id the registry doesn't
        # know).
        "REG008",
        "REG009",
        # T-0560: check-coverage.yaml gate-rule staleness (scheduled-audit
        # half of T-0424).
        "REG010",
        # T-0894: REG012 (frob.gates._registry_exhaustiveness.registry_gate)
        # -- docs/design/registry/ was committed on this branch's history
        # and has since been deleted, distinguished from "never adopted"
        # by path_ever_tracked. Same "adopted then deleted" family as
        # COMPLIANCE006 above.
        "REG012",
        # T-0436: unbound/stale fenced-code-block doc-drift heuristic
        # (frob.gates._docblocks).
        "DOC004",
        # T-0435: README command-table + checkable-count drift-lock
        # (frob.gates._docblocks.doc005_gate).
        "DOC005",
        # T-0437: doc-pointer resolution over a closed set of recognized
        # shapes (file/path, cli invocation, config reference, code symbol,
        # doc-anchor link) (frob.gates._docptr).
        "DOC006",
        # T-0986: split out of DOC006 -- the `frob:tests` target-form
        # hardening for the DRIFT002 dotted-vs-:: confusion class, shipped
        # at ERROR from birth (the other ~700 live DOC006 findings stay
        # WARN, a separate burn-down) (frob.gates._docptr).
        "DOC007",
        # T-0471: unpruned filesystem traversal (frob.gates._walk_lint).
        "WALK001",
        # T-0465: .git/info/exclude entry shadowing tracked source
        # (frob.gates._exclude_hazard).
        "EXCL001",
        # T-0439: CVE code-smell needle/fingerprint pattern-scan
        # (frob.gates._cve_fingerprint_scan).
        "SEC-CVE-FINGERPRINT-001",
        # T-0459: bare stdout write outside frob.render (frob.gates._render_lint).
        "RENDER001",
        # T-0405: language-extension conformance drift-lock
        # (frob.gates._lang_conformance) -- a registered frob.lang grammar
        # language missing an accounted-for facet.
        "LANG001",
        # T-0406: per-project language conformance -- a completely
        # unregistered candidate-language file present in this repo
        # (LANG002), or a registered-but-KNOWN_GAP facet whose language is
        # actually present here and whose tracking-ticket claim does not
        # verify (LANG003).
        "LANG002",
        "LANG003",
        # T-0753: dead_symbol_gate's DEAD001 was wired as a real, always-run
        # process job (see _ALL_GATES's "dead_symbols" entry) since before
        # this frozenset existed, but was never added here -- so every
        # `frob:waive DEAD001 reason="..."` in the tree (3 live instances at
        # T-0753's filing) was silently flagged WAIVE002-ineffective despite
        # targeting a perfectly real, matchable rule id. This was a listing
        # omission, not evidence DEAD001 was ever renamed or removed.
        "DEAD001",
        # T-0813: the production `mark_unresolved=True` wiring into
        # `compute_protocol_summaries` (frob.gates._protocol_summary) --
        # a frob:requires/frob:transition-tagged symbol whose transitive
        # call closure hits a genuinely unresolved callee.
        "PROTO001",
        # T-0746: PROTO002 (state-requirement violation) and PROTO003
        # (invalid transition) -- the ERROR-tier verification rules over
        # the same `frob.gates._protocol_summary` scan, sharing PROTO001's
        # per-package `compute_protocol_summaries` pass.
        "PROTO002",
        "PROTO003",
        # T-0747: PROTO005, cleanup obligations (release-postdominates-
        # acquisition on all exits, escape transfer, per-protocol
        # cleanup="always" deinit-never-called) -- same per-package
        # `frob.gates._protocol_summary` scan.
        "PROTO005",
        # T-0756: self-audit-at-land -- frob's own SYS100-102/SYS2xx/REL2xx
        # audit surface, folded into the ordinary gate pipeline so a land
        # that reddens it is blocked structurally (frob.gates.sys_gate's
        # _selfaudit_violations).
        "SELFAUDIT001",
        # frob:ticket T-0903
        # T-0903: 7 more real, currently-firing rule ids never added here --
        # the same DEAD001-class listing omission T-0753 already fixed once,
        # recurring for rules landed by later tickets that never circled
        # back to this frozenset.
        # PARSE001 (frob.gates._parse_failures): registered as an always-run
        # process job in _ALL_GATES's "parse_failures" entry.
        "PARSE001",
        # TICK005 (frob.gates.tickets_gate's _tick005_merge_state_regression).
        "TICK005",
        # REG011 (frob.gates._registry_exhaustiveness, T-0680's
        # out_of_scope-reason check).
        "REG011",
        # PII011/PII012 (frob.gates._pii_structural, dispatched from
        # pii_structural_gate).
        "PII011",
        "PII012",
        # SYSWAIVE002 (frob.strata._contention).
        "SYSWAIVE002",
        # THREAT006 (frob.strata._threat).
        "THREAT006",
        # frob:ticket T-0923
        # T-0923: PROTO004 (frob.gates._protocol_summary's
        # protocol_summary_gate, T-0840's per-call-site ordering check) --
        # never added alongside PROTO001/002/003/005, the same listing-
        # omission class as T-0903 above.
        "PROTO004",
        # frob:ticket T-0901
        # T-0901: DEC000 (this module's decisions_gate, a malformed
        # decisions/ record) -- surfaced by T-0901's own drift-lock test,
        # the same listing-omission class as the T-0903/T-0923 batches.
        "DEC000",
        # frob:ticket T-0894
        # T-0894: DEC003 (this module's decisions_gate) -- a decisions/
        # directory that was committed on this branch's history and has
        # since been deleted, distinguished from "never adopted". Same
        # "adopted then deleted" family as REG012/COMPLIANCE006.
        "DEC003",
        # frob:ticket T-0688
        # T-0688: EXHAUST001/EXHAUST002 (frob.gates._exhaustive_handling's
        # exhaustive_handling_gate) -- the exhaustive-exception gate over
        # frob.arch._mayraise.compute_may_raise's per-function may-raise
        # sets.
        "EXHAUST001",
        "EXHAUST002",
        # frob:ticket T-0690
        # T-0690: FFI001/FFI002 (frob.gates._ffi_boundary's
        # ffi_boundary_gate) -- the FFI-boundary exception-declaration
        # cross-check (pyo3 Rust/.pyi drift, mandatory ctypes/cffi
        # declaration).
        "FFI001",
        "FFI002",
        # frob:ticket T-0924
        # T-0924: the larger pre-existing batch T-0901's drift-lock test
        # surfaced beyond T-0903/T-0923's ids, carried in that test's
        # `_KNOWN_ISSUE_ALLOWLIST` until paid down here -- same listing-
        # omission class, no observed caught_by/handled_by symptom yet.
        # COMPLIANCE001-004 (frob.strata._compliance.check_cmpl_registry
        # and related checks, T-0607/T-0788).
        "COMPLIANCE001",
        "COMPLIANCE002",
        "COMPLIANCE003",
        "COMPLIANCE004",
        # HOST001/HOST002 (frob.strata._host_isolation).
        "HOST001",
        "HOST002",
        # HOST-BLAST (frob.strata._audit's blast-radius check).
        "HOST-BLAST",
        # KRB001-004 (frob.strata._krb_movement).
        "KRB001",
        "KRB002",
        "KRB003",
        "KRB004",
        # LINT001-005 (frob.strata._lint).
        "LINT001",
        "LINT002",
        "LINT003",
        "LINT004",
        "LINT005",
        # PII001-004 (frob.strata._pii).
        "PII001",
        "PII002",
        "PII003",
        "PII004",
        # RELWAIVE002 (frob.strata's reliability-family modules --
        # _circuit_breaker/_slo/_spof/_interactive_cost/_fallback/_txn/
        # _observability/_reliability/_ssot/_retry/_backpressure -- all
        # share this one rule id for an unresolved reliability waiver).
        "RELWAIVE002",
        # THREAT001-005 (frob.strata._threat; THREAT006 already registered
        # above by T-0903).
        "THREAT001",
        "THREAT002",
        "THREAT003",
        "THREAT004",
        "THREAT005",
        # PARSE002 (frob.gates._parse_failures) -- landed on main
        # concurrently with this ticket's own fix pass; same listing-
        # omission class as PARSE001 above, folded into T-0924 since it
        # is exactly this ticket's defect class and this file is already
        # in scope.
        "PARSE002",
        # frob:ticket T-0958
        # T-0958: the T-0331 epic's REL2xx/REL3xx obligation-family rule
        # ids (frob.strata's _reliability/_retry/_backpressure/
        # _observability/_slo/_message_schema/_delivery_semantics/
        # _distributed_txn/_clock_ordering modules) were never added to
        # this frozenset when landed -- the same listing-omission class
        # T-0903/T-0923/T-0924 already fixed for other batches. Adding
        # only the ids this ticket's system-design.yaml reconciliation
        # actually cites via `handled_by:<rule>` (REG002 needs them in
        # known_rules to resolve); the full REL2xx-REL38x family beyond
        # these was completed by T-0961 below.
        "REL200",
        "REL220",
        "REL221",
        "REL260",
        "REL270",
        "REL272",
        "REL280",
        "REL320",
        "REL330",
        "REL350",
        "REL370",
        # frob:ticket T-0961
        # T-0961: the rest of the T-0331 epic's REL2xx-REL38x
        # obligation-family rule ids, plus SYS204 -- these are built from
        # module-level `REL_*`/`SYS_*` string constants (e.g.
        # `frob.strata._retry.REL_MISSING_BACKOFF = "REL220"`) rather than
        # inline `rule="..."` literals, so T-0901's regex-based drift-lock
        # test cannot see them at all (a false-negative gap in the lock
        # itself, not a passing check) -- T-0958 only registered the 11
        # ids its own handled_by rows cited and left the rest unlisted.
        # Enumerated by grepping every `REL_* = "REL..."`/`SYS_* = "SYS..."`
        # assignment across src/frob/strata/*.py and cross-checking each
        # against its `rule=<CONSTANT>` use site:
        #   _reliability.py:   REL200/REL201/REL210/REL211
        #   _retry.py:         REL220/REL221/REL222
        #   _circuit_breaker.py: REL230/REL231
        #   _fallback.py:      REL240/REL241
        #   _spof.py:          REL250
        #   _backpressure.py:  REL260/REL261
        #   _observability.py: REL270/REL271/REL272
        #   _slo.py:           REL280/REL281
        #   _ssot.py:          REL290/REL291
        #   _txn.py:           REL300/REL301
        #   _interactive_cost.py: REL310/REL311
        #   _message_schema.py: REL320/REL321
        #   _delivery_semantics.py: REL330/REL331
        #   _sync_depth.py:    REL340
        #   _distributed_txn.py: REL350/REL351
        #   _shared_state.py:  REL360
        #   _clock_ordering.py: REL370/REL371/REL372
        #   _starvation.py:    REL380/REL381/REL382/REL383
        #   _access.py (SYS204 contention-proof entrypoint): SYS204
        "REL201",
        "REL210",
        "REL211",
        "REL222",
        "REL230",
        "REL231",
        "REL240",
        "REL241",
        "REL250",
        "REL261",
        "REL271",
        "REL281",
        "REL290",
        "REL291",
        "REL300",
        "REL301",
        "REL310",
        "REL311",
        "REL321",
        "REL331",
        "REL340",
        "REL351",
        "REL360",
        "REL371",
        "REL372",
        "REL380",
        "REL381",
        "REL382",
        "REL383",
        "SYS204",
        "SYS205",
        # frob:ticket T-0960
        # T-0960: the REL39x KERNEL-INTERFACE-CLASSIFICATION +
        # PROCESS-RESOURCE-BOUND obligation family (frob.strata.
        # _process_bounds) -- registered at the point this ticket's own
        # system-design.yaml re-disposition needs REG002 to resolve
        # handled_by:REL39x references (T-0961 is concurrently
        # registering the separate REL26x-38x backlog batch here; this
        # adds only T-0960's own new ids).
        "REL390",
        "REL391",
        "REL392",
        "REL393",
        # frob:ticket T-0962
        # T-0962: the REL39y ABI-COMPAT-WINDOW + BOOT-ATTESTATION
        # obligation family (frob.strata._supply_chain_boot), continuing
        # T-0960's REL39x block rather than opening a new REL4xx range.
        "REL394",
        "REL395",
        "REL396",
        "REL397",
        # frob:ticket T-0966
        # T-0964's constant-scan extension to
        # test_every_emitted_rule_literal_is_known resolves `rule=CONST_NAME`
        # references (not just inline `rule="..."` literals) and surfaced
        # a real, pre-existing gap: these seven ids are genuinely emitted
        # via module-level constants but were never added here.
        #   _selfconform.py:213  SYS_UNDECLARED_INTERFACE = "SYS100"
        #   _selfconform.py:559  SYS_STALE_DESIGN         = "SYS101"
        #   _selfconform.py:630  SYS_UNMODELED_CODE       = "SYS102"
        #   _contention.py:193   SYS_DUPLICATE_PORT       = "SYS200"
        #   _contention.py:291   SYS_OVERLAPPING_PATH     = "SYS201"
        #   _contention.py:341   SYS_SHARED_PIPE          = "SYS202"
        #   _contention.py:379   SYS_SHARED_STORE_WRITE   = "SYS203"
        "SYS100",
        "SYS101",
        "SYS102",
        "SYS103",
        "SYS200",
        "SYS201",
        "SYS202",
        "SYS203",
    }
)
# frob-zone-end known-gate-rules T-1002


# frob:ticket T-0499
# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/test_gates.py::TestKnownGateRuleIds.test_returns_known_rule_id
# frob:tests tests/test_gates.py::TestKnownGateRuleIds.test_is_frozenset
def known_gate_rule_ids() -> frozenset[str]:
    """Return every rule id a gate can emit, for strata `caught_by`
    resolution to recognize rule-id-shaped references (e.g. THREAT006's
    and COMPLIANCE004's `known_rule_ids` param) instead of treating them
    as unresolved by default.
    """
    return _KNOWN_GATE_RULES


# frob:ticket T-0148
# TEST008 (coverage.xml carried data but zero of it joined to a known repo
# path) is excluded from `_match_waiver` by construction, not merely by
# convention -- it exists specifically to make a silent-death coverage
# misconfiguration loud in EVERY sibling repo this gate runs in, so a
# `frob:waive TEST008 reason="..."` sitting in one repo's tree must never
# quietly suppress it there. `frob.toml`'s `[gates.severity]` override
# table is a different, explicit, per-repo mechanism (visible in the
# frob.toml diff, not a buried code comment) and is NOT blocked here --
# only the same-repo `frob:waive` directive path is.
#
# frob:ticket T-0157
# SEC003 (`frob.gates._secrets`): a live Stripe SECRET key (`sk_live_...`)
# or a private-key PEM header tracked in the repo. Written decision (the
# ticket asked for one explicitly): these two get the same unwaivable
# treatment as TEST008, NOT the broader `SEC001` rule id that the rest of
# the secrets-scan pattern table reports under. `SEC001` deliberately stays
# waivable -- it also carries lower-confidence, genuinely disputable
# findings (a JWT that may be a public ID token, Plaid's context-gated
# heuristic, Stripe TEST-mode keys) where a written `frob:waive` reason is
# the correct, honest outcome, not a workaround. A live Stripe secret key
# or a PEM private-key header have no such legitimate "yes, intentionally"
# case -- unlike a JWT, there is no reading of either shape that is
# supposed to be public, so silencing one with a comment is never correct
# and is now structurally impossible, the same way TEST008 makes a silent
# coverage misconfiguration impossible.
#
# frob:ticket T-0162
# TICK001/TICK002 join TEST008 for the identical reason: they exist
# specifically to make the T-0162 ticket-id collision invariant's failure
# modes loud. TICK001 (duplicate id active+archive) can already only be
# reached if ledger loading itself becomes more permissive than today's
# hard Err, and TICK002 (a draft id reaching the default branch) is exactly
# the "finalize step got skipped" failure this whole mechanism exists to
# catch -- a `frob:waive TICK002 reason="..."` sitting in the tree would
# let a live collision risk sit there quietly forever. See the decision
# record in docs/modules/tickets.md#decision-record-t-0162.
# T-0465: EXCL001 joins the same unwaivable set -- a `frob:waive` comment
# lives in a source file, but the violation's own "file" is
# `.git/info/exclude` itself; there is nowhere honest to attach a waiver,
# and the remedy is always the same (remove the entry, or use a
# genuinely untracked path). See docs/modules/gates.md#excl001-t-0465.
# T-0894: COMPLIANCE006/REG012 (an adopted-then-deleted registry, distinct
# from the ordinary waivable per-entry disposition violations they sit
# beside) are unwaivable -- deleting the registry entirely is a
# higher-stakes claim than any individual entry it might have carried.
_UNWAIVABLE_RULES = frozenset(
    {
        "TEST008",
        "SEC003",
        "TICK001",
        "TICK002",
        "EXCL001",
        "COMPLIANCE006",
        "REG012",
        "DEC003",
    }
)


def _unwaivable_channel_rules() -> frozenset[str]:
    """Rule/category ids from tool channels `frob:waive` can never reach.

    T-0101 decision (documented in docs/modules/gates.md#waive-boundary):
    honoring waivers in the `frob-arch` check stage would mean threading
    the waiver-matching machinery into `frob.check`'s Diagnostic pipeline
    (`analyze_project` produces `ArchSuggestion`s, never `Violation`s) --
    a bigger surface change than a WARN justifies today. Instead, a waiver
    that names one of `frob.arch`'s categories is flagged as ineffective
    rather than silently doing nothing.

    T-0289 narrows this: `long-function` is EXCLUDED here because
    `frob.gates._arch.arch_gate` now channels it into real `Violation`s
    (rule id `ARCH001`, not the bare category name `long-function`) that
    DO go through `_apply_waivers` -- a `frob:waive long-function
    reason="..."` still can't match anything (the rule id is `ARCH001`,
    not the category string), so it correctly stays flagged here, but the
    correct directive (`frob:waive ARCH001 reason="..."`) is no longer
    ineffective. Every other arch category is unchanged.
    """
    from typing import get_args

    from frob.arch._models import ArchCategory

    return frozenset(get_args(ArchCategory)) - {"long-function"}


def _waive002_violations(
    snapshot: GraphSnapshot, rule_ids: frozenset[str]
) -> tuple[Violation, ...]:
    """WAIVE002: a `frob:waive` targets a rule id that can never be matched
    by `_apply_waivers` -- neither a known gate rule nor a loaded policy
    rule id. T-0101: this is the "unwaivable channel" case made loud
    instead of a silent no-op; `rule_ids` is the run's loaded policy rule
    ids, since those are dynamic (frob.toml-defined) and not known statically.
    """
    known = _KNOWN_GATE_RULES | rule_ids
    if _waive_edges(snapshot) == ():
        return ()
    arch_categories = _unwaivable_channel_rules()
    return tuple(
        _waive002_violation_for(edge, arch_categories)
        for edge in _waive_edges(snapshot)
        if edge.target not in known
    )


# frob:enforces CHK-GATE-WAIVE002
def _waive002_violation_for(edge: Edge, arch_categories: frozenset[str]) -> Violation:
    """The single WAIVE002 `Violation` (already logged) for one ineffective
    `frob:waive` edge -- distinguishing the frob-arch-category case (whose
    stage never consults `frob:waive` at all) from an unrecognized rule id."""
    file = edge.src.split("::", 1)[0]
    if edge.target in arch_categories:
        detail = (
            f"'{edge.target}' is a frob-arch category, not a gates rule id; "
            f"the frob-arch check stage does not consult frob:waive"
        )
    else:
        detail = f"'{edge.target}' is not a recognized gate or policy rule id"
    # T-0753: promoted WARN -> ERROR. A waiver that can never match anything
    # is not a hygiene nit -- it is silently doing nothing while reading as
    # coverage, exactly the same "looks handled, isn't" failure mode WAIVE001
    # already treats as an ERROR for a missing reason=. See the DEAD001
    # listing-omission incident this promotion surfaced (T-0753's Done
    # report) for why this sat at WARN long enough to accumulate 3 live
    # instances unnoticed.
    _log.error(
        "WAIVE002: %s waives %s, which is ineffective: %s",
        edge.src,
        edge.target,
        detail,
    )
    return Violation(
        rule="WAIVE002",
        severity=Severity.ERROR,
        file=file,
        line=0,
        message=(
            f"WAIVE002: frob:waive on {edge.src} targeting "
            f"'{edge.target}' is ineffective -- {detail}"
        ),
    )


# frob:ticket T-0470
# frob:enforces CHK-GATE-WAIVE003
def _waive003_violations(
    violations: tuple[Violation, ...], snapshot: GraphSnapshot
) -> tuple[Violation, ...]:
    """WAIVE003: a single `frob:waive` edge on a package-scoped rule
    (`_PACKAGE_SCOPED_RULES`) that reaches MORE THAN ONE distinct violated
    package/system id via `_match_waiver`'s directory-prefix fallback.

    A waiver sitting in one file under `src/frob` matches every TEST003/
    TEST007 violation for every ancestor package prefix of that file's own
    path (`src/frob`, `src/frob/gates`, ...) simultaneously -- the same
    directive silently suppresses findings the author most likely never
    saw, let alone intended to waive, because they were reasoning about
    their own immediate package, not its ancestors. WARN severity: this is
    a scope-hygiene nudge (split into one waiver per package, or move each
    to its own package), not a correctness bug on its own.
    """
    waivers_by_rule = _waivers_by_rule(snapshot)
    reach: dict[tuple[str, str], set[str]] = {}
    for violation in violations:
        if violation.rule not in _PACKAGE_SCOPED_RULES:
            continue
        match = _match_waiver(violation, waivers_by_rule)
        if match is None:
            continue
        reach.setdefault((violation.rule, match.origin), set()).add(violation.file)
    out: list[Violation] = []
    for (rule, origin), files in reach.items():
        if len(files) <= 1:
            continue
        file, _, line_text = origin.rpartition(":")
        line = int(line_text) if line_text.isdigit() else 0
        # frob:waive PERF004 reason="own distinct files set per (rule, origin) reach entry, not a shared re-sort"  # noqa: E501
        packages = ", ".join(sorted(files))
        _log.warning(
            "WAIVE003: %s frob:waive %s reaches %d packages: %s",
            origin,
            rule,
            len(files),
            packages,
        )
        out.append(
            Violation(
                rule="WAIVE003",
                severity=Severity.WARN,
                file=file or origin,
                line=line,
                message=(
                    f"WAIVE003: {origin} frob:waive {rule} matches {len(files)} "
                    f"distinct packages ({packages}) via directory-prefix reach; "
                    f"likely broader than intended -- split into one waiver per "
                    f"package"
                ),
            )
        )
    return tuple(out)


# T-0753: WAIVE004 is the genuinely dangerous stale-waiver class WAIVE002
# cannot see -- WAIVE002 only catches a waiver whose RULE ID can never
# match anything at all; a waiver naming a perfectly valid, live rule but
# whose SITE has zero findings under that rule (the underlying issue was
# fixed, or never actually applied there) reads as "still ineffective" in
# exactly the same silently-pre-forgiving way, but WAIVE002's known-rules
# check cannot detect it -- the rule is known, only the site is stale.
# Left alone, that waiver keeps standing guard over nothing while
# pre-forgiving the NEXT regression at that site with no new review.
#
# WARNING tier, not ERROR: some rules are legitimately context-dependent
# (a diff-scoped rule like SCOPE001/POLICY's diff-bound checks, or any
# rule this run's `--only`/gate selection excluded) can show zero matches
# for reasons that have nothing to do with the waiver being stale -- a
# false WAIVE004 there is a known-flaky case, not a bug in the detector.
# Trust WAIVE004 findings from a full, unscoped `frob check` run; a
# scoped/`--only` run's WAIVE004 output should be read as advisory only.
# A ratchet-to-error path via the T-0569/T-0594 waivable-warning pool is a
# natural follow-up once the known-flaky set is characterized empirically,
# not built in this pass (T-0753's mandate: WARNING-tier first).
#
# T-1064: two structurally-distinct rule classes can read as "0 findings
# this run" in `all_violations` even while the waiver they carry is
# genuinely still live and still doing its job -- neither is a matching
# bug in `_match_waiver` itself (rule-id-exact matching stays untouched;
# a file-level waiver still cannot swallow a line-scoped finding of some
# OTHER rule), both are about `all_violations` never containing the
# finding to begin with:
#
# - SELF-SUPPRESSING rules: the rule's own gate function checks for a
#   covering `frob:waive` edge INTERNALLY, before ever constructing the
#   `Violation` (INV006's `_inv006_waived` in `frob.gates.__init__` is
#   the confirmed case -- `_inv006_src_violations` returns `()` the
#   moment a covering waiver exists, so the finding never reaches
#   `all_violations` for `_apply_waivers`/WAIVE004 to see, waived or
#   not). Empirically this was ~209 of ~216 WAIVE004 findings in this
#   repo's own full run (T-1064): every one of INV006's per-file
#   "first-turn-on pool" waivers (T-0585-style) read as permanently
#   zero-match, even though deleting them resurfaces the exact INV006
#   errors they were suppressing (confirmed by direct before/after
#   deletion in T-0874's investigation). WAIVE004 cannot see through
#   this from `all_violations` alone -- the finding was never generated,
#   not merely filtered downstream -- so these rules are exempted here
#   rather than mis-flagged every run.
# - TOUCHED/DIFF-SCOPED rules: the underlying gate only ever emits a
#   finding for symbols in the diff's OWN touched-ref set (DUP001/DUP002
#   via `frob.dup.touched_refs`, AFFECT001/AFFECT002 via the same
#   diff-scoped closure walk -- see their own "diff-scoped like
#   coverage/fmt" gate comments in `frob.gates.__init__`). A full,
#   unscoped `frob check` run's `diff` is whatever this invocation's
#   base/head resolve to, essentially never the exact diff that
#   originally triggered the waived finding -- so these rules read as
#   "0 findings" on nearly every run regardless of whether the waiver
#   is still earning its keep, for the same reason the existing
#   SCOPE001/COV002/TODO001 `SCOPED_RUN_FLAKY_RULE_IDS` class does.
#
# Neither exemption weakens WAIVE004 for any OTHER rule -- a waiver on a
# rule NOT in this set still needs a real, live, rule-id-exact match in
# `all_violations` or it is reported exactly as before.
_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES = frozenset(
    {"INV006", "DUP001", "DUP002", "AFFECT001", "AFFECT002"}
)


# frob:enforces CHK-GATE-WAIVE004
def _waive004_violations(
    all_violations: tuple[Violation, ...],
    snapshot: GraphSnapshot,
    rule_ids: frozenset[str],
) -> tuple[Violation, ...]:
    """WAIVE004: a `frob:waive` on a recognized rule id that matches ZERO
    findings in this run's full (pre-waiver) violation set -- the rule is
    real and reachable, but nothing at the waived site currently trips it.

    Evaluated against `all_violations` BEFORE `_apply_waivers` runs (the
    same "waivers ignored" set `_waive003_violations` already consumes), so
    this is genuinely "does the rule fire here at all right now", not an
    artifact of the waiver itself suppressing its own evidence. Skips edges
    WAIVE002 already flagged (an unrecognized rule id has no findings to
    compare against by construction, and WAIVE002 is the more actionable
    finding for that edge), the `_UNWAIVABLE_RULES`/arch-category cases
    `_match_waiver`/`_waive002_violation_for` already special-case, and
    (T-1064) rules in `_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES` whose own
    gate self-suppresses or diff-scopes findings out of `all_violations`
    before this check ever runs, making a "0 findings" read permanently
    false regardless of whether the waiver is still needed.
    """
    known = _KNOWN_GATE_RULES | rule_ids
    arch_categories = _unwaivable_channel_rules()
    violations_by_rule: dict[str, list[Violation]] = {}
    for violation in all_violations:
        violations_by_rule.setdefault(violation.rule, []).append(violation)
    out: list[Violation] = []
    for edge in _waive_edges(snapshot):
        rule = edge.target
        if (
            rule not in known
            or rule in arch_categories
            or rule in _WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES
        ):
            continue  # WAIVE002's territory, or structurally unverifiable
        candidates = violations_by_rule.get(rule, [])
        matched = any(_match_waiver(v, {rule: [edge]}) is edge for v in candidates)
        if matched:
            continue
        from frob.gates import _site_from_edge_origin  # local: avoids circularity

        file, line = _site_from_edge_origin(edge.origin)
        _log.warning(
            "WAIVE004: %s frob:waive %s matches 0 findings this run",
            edge.origin,
            rule,
        )
        out.append(
            Violation(
                rule="WAIVE004",
                severity=Severity.WARN,
                file=file,
                line=line,
                message=(
                    f"WAIVE004: {edge.src} frob:waive {rule} matches 0 findings "
                    f"in this run -- the waiver may be pre-forgiving a future "
                    f"regression with no live issue behind it; confirm the site "
                    f"still needs it, or remove the directive (known-flaky for "
                    f"diff-scoped rules and any `--only`-excluded gate; trust "
                    f"this only from a full, unscoped run)"
                ),
            )
        )
    return tuple(out)


# frob:ticket T-0850
# frob:doc docs/modules/gates.md#public-api
# The rule ids this codebase already documents in multiple places (this
# module's own COV002/SCOPE001/TODO001 diff-driven-gate comments, and
# WAIVE004's "known-flaky for diff-scoped rules" message text above) as
# legitimately unstable between two SCOPED runs of the same ticket taken
# at different times (a `--ticket` check's touched-file set is a function
# of the diff against `base`, which moves independently of whether this
# ticket's own work changed) -- a finding here appearing or disappearing
# reflects branch/base drift, not necessarily a real regression or fix
# this ticket introduced. T-0850: `frob.tickets._land`'s `ClaimDivergence`
# identity comparison (T-0846) must exclude findings under these rule ids
# from BOTH sides of the comparison (the captured claim AND the fresh
# post-merge re-check) -- filtering only one side would still diverge on
# pure base-drift noise, reintroducing the exact false-refusal class T-0846
# already fixed for the raw-count case. `frob.app.ticket_runner`'s
# `_check_gate_findings_fn`/`_check_gates_summary_fn` apply this exclusion
# at the single shared closure both `done-report` capture and `land`
# re-verification call, so the filter is symmetric by construction rather
# than by two call sites staying in sync by hand.
SCOPED_RUN_FLAKY_RULE_IDS = frozenset({"SCOPE001", "COV002", "TODO001"})


# T-0753: `frob:waive` gains an optional `until="YYYY-MM-DD"` boundary,
# reusing the same date-only grammar `frob:deprecated`'s `sunset=`/
# `frob:debt`'s date-shaped `until=` already established (T-0412/T-0576
# precedent) -- one convention for "a directive with a real-world expiry
# date", not a third bespoke format. Coordinate with T-0671 (strata's
# SYSWAIVE002, already at error tier) on this same grammar rather than
# diverging. Unlike `frob:debt`, a `frob:waive` carries no ticket=, so
# there is no ticket-open check here (WAIVE005 mirrors DEBT003's plain
# expiry escalation, not DEBT002's ticket-lifecycle check) -- an expired
# waiver still SUPPRESSES its matched violation (unlike an expired debt,
# which never suppressed anything to begin with); WAIVE005 only makes the
# expiry itself loud, on the same "forces re-review, does not auto-revoke"
# posture DEBT003/DEPR004 already established.
# frob:enforces CHK-GATE-WAIVE005
def _waive005_violations(
    snapshot: GraphSnapshot, *, current_date: str
) -> tuple[Violation, ...]:
    """WAIVE005: a `frob:waive`'s `until="YYYY-MM-DD"` boundary has passed --
    a permanent-by-default waiver that was explicitly time-boxed and outlived
    its own boundary must force a human re-review, not sit forgotten."""
    violations: list[Violation] = []
    for edge in _waive_edges(snapshot):
        until = edge.attrs.get("until", "")
        if not until or until.strip() > current_date:
            continue
        from frob.gates import _site_from_edge_origin  # local: avoids circularity

        file, line = _site_from_edge_origin(edge.origin)
        _log.error("WAIVE005: %s expired (until=%s)", edge.src, until)
        violations.append(
            Violation(
                rule="WAIVE005",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"WAIVE005: frob:waive {edge.target} at {edge.src} expired "
                    f"(until={until!r}); re-review the waiver -- extend `until` "
                    f"with a written reason, or remove the directive if the "
                    f"waiver is no longer warranted"
                ),
            )
        )
    return tuple(violations)


# T-0779 (audit H2): a waiver justified by "this is pending ticket T-XXXX"
# must not outlive T-XXXX -- the five LINT004 kill-switch waivers cited
# T-0200 as the follow-on ticket to build for months after T-0200 closed,
# and nothing re-litigated them. WAIVE006 resolves every ticket id a
# waiver BINDS ITSELF to (never a bare historical mention) against the
# ledger+archive; DONE or DROPPED there means the waiver has outlived its
# own justification and must be re-justified or removed.
#
# Calibration (the hard part): a waiver's reason prose routinely narrates
# history ("kill-switch mechanism exists (T-0200/T-0778) but ... -- tracked
# in T-draft-8cd37914") without the mention being a live claim that T-0200
# is still open or still the reason the gap is excused -- T-0778 rewrote
# exactly this class of waiver to cite an open follow-on while HISTORICALLY
# mentioning the now-closed T-0200 that built the underlying mechanism.
# WAIVE006 must not fire on that. Two things count as binding:
#   1. An explicit ticket attribute (`frob:waive RULE reason="..."
#      ticket="T-####"`, or a strata `waive "RULE" reason "..." ticket
#      "T-####";` clause) -- the author wrote down, structurally, "this is
#      what tracks the gap".
#   2. Specific "still pending on this ticket" phrasing INSIDE the reason
#      text itself (`_WAIVE006_BINDING_PHRASE_RES`) -- "pending T-####" and
#      "T-#### is the follow-on ticket" are the two shapes this repo's own
#      history (T-0412/T-0753 debt-style waivers, the pre-T-0778 LINT004
#      waivers) has actually produced. A bare `(T-0200/T-0778)` aside or a
#      `T-0200 built a real kill switch` narration is neither shape, so it
#      is never extracted -- only a ticket reference the reason text itself
#      claims is the live justification counts.
_WAIVE006_TICKET_ID_RE = r"T-\d+"
_WAIVE006_BINDING_PHRASE_RES = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        rf"\bpending\s+({_WAIVE006_TICKET_ID_RE})\b",
        rf"\bpending[\s-]+on\s+({_WAIVE006_TICKET_ID_RE})\b",
        rf"\b({_WAIVE006_TICKET_ID_RE})\s+is\s+the\s+follow-on\s+ticket\b",
        rf"\bfollow-on\s+ticket\s*(?:is|:)?\s*({_WAIVE006_TICKET_ID_RE})\b",
        rf"\bblocked\s+on\s+({_WAIVE006_TICKET_ID_RE})\b",
        rf"\bwaiting\s+on\s+({_WAIVE006_TICKET_ID_RE})\b",
    )
)


def _waive006_binding_ticket_refs(reason: str) -> set[str]:
    """Ticket ids `reason` BINDS ITSELF to via one of
    `_WAIVE006_BINDING_PHRASE_RES`'s explicit "still pending on this
    ticket" phrasings -- never a bare id mention in narration prose (the
    T-0778 calibration case this module docstring section explains)."""
    refs: set[str] = set()
    for pattern in _WAIVE006_BINDING_PHRASE_RES:
        refs.update(match.group(1) for match in pattern.finditer(reason))
    return refs


def _waive006_stale_ticket(ticket_ids: set[str], queue: TicketQueue) -> str | None:
    """The first `ticket_ids` entry that resolves in `queue` (active+archive)
    to a DONE/DROPPED ticket, or `None` if every reference is either open or
    unresolvable. Unresolvable ids (typos, draft ids not yet finalized) are
    deliberately NOT flagged here -- that is a different, separate honesty
    gap from "this ticket closed and nobody re-reviewed the waiver"."""
    for ticket_id in sorted(ticket_ids):
        target = queue.tickets.get(ticket_id)
        if target is not None and target.state in (
            TicketState.DONE,
            TicketState.DROPPED,
        ):
            return ticket_id
    return None


def _waive006_violation(
    *, file: str, line: int, site: str, rule_and_target: str, stale: str
) -> Violation:
    """The single WAIVE006 `Violation` for one stale-waiver site (shared by
    both the `frob:waive` comment channel and the `.strata` `waive` clause
    channel, so the message shape is identical regardless of directive
    flavor)."""
    _log.error(
        "WAIVE006: %s (%s) binds to closed ticket %s", site, rule_and_target, stale
    )
    return Violation(
        rule="WAIVE006",
        severity=Severity.ERROR,
        file=file,
        line=line,
        message=(
            f"WAIVE006: {site} waives {rule_and_target}, bound to ticket "
            f"{stale}, which is DONE/DROPPED; a waiver justified by a "
            f"pending ticket must not outlive it -- re-justify with a "
            f"current reason (and, if still needed, an open follow-on "
            f"ticket) or remove the waiver now that the gap it excused "
            f"has presumably been addressed"
        ),
    )


# frob:enforces CHK-GATE-WAIVE006
def _waive006_comment_violations(
    snapshot: GraphSnapshot, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE006 (`frob:waive` comment channel): a waiver whose `ticket=`
    attribute, or whose `reason=` text binds itself via
    `_waive006_binding_ticket_refs`, names a ticket that is DONE or DROPPED
    in the ledger+archive."""
    violations: list[Violation] = []
    for edge in _waive_edges(snapshot):
        reason = edge.attrs.get("reason", "")
        refs = _waive006_binding_ticket_refs(reason)
        attr_ticket = edge.attrs.get("ticket", "")
        if attr_ticket:
            refs.add(attr_ticket)
        if not refs:
            continue
        stale = _waive006_stale_ticket(refs, queue)
        if stale is None:
            continue
        from frob.gates import _site_from_edge_origin  # local: avoids circularity

        file, line = _site_from_edge_origin(edge.origin)
        violations.append(
            _waive006_violation(
                file=file,
                line=line,
                site=edge.src,
                rule_and_target=f"frob:waive {edge.target}",
                stale=stale,
            )
        )
    return tuple(violations)


# `waive "RULE[:SUBTARGET]" reason "..." [ticket "T-####"]` -- strata-core's
# `.strata` grammar (docs/strata/waive.md, `frob.strata._waive`'s module
# docstring). Deliberately a plain single-line regex scan here rather than
# a `strata_core` parse+elaborate: this rule only needs the literal
# `reason`/`ticket` string attrs off each clause (no capability/threat
# model reasoning), and scanning avoids paying the native-extension import
# cost (T-0135's standalone-install posture) just to read two string
# fields. Every live `waive` clause in this repo today is single-line
# (T-0778's own rewrite); a clause split across lines is not matched --
# documented limitation, not silently wrong (it simply finds nothing to
# flag there, same fail-open posture `_debt_is_expired` takes on an
# unparseable `until`).
_STRATA_WAIVE_RE = re.compile(
    r'waive\s+"(?P<rule>[^"]+)"\s+reason\s+"(?P<reason>(?:[^"\\]|\\.)*)"'
    r'(?:\s+ticket\s+"(?P<ticket>[^"]*)")?\s*;'
)


def _strata_waive_sites(root: Path) -> list[tuple[str, int, str, str, str]]:
    """Every `(file, line, rule, reason, ticket)` `waive` clause found by a
    line scan of every `.strata` file under this repo's design dir (opt-in:
    empty when no design dir exists), minus `[graph].exclude` matches --
    same exclusion posture every other file-walking gate in this module
    already applies (`is_excluded`/`load_exclude_globs`)."""
    root = Path(root)
    from frob.gates import _design_dir  # local: avoid init-time circularity

    design_dir = root / _design_dir(root)
    if not design_dir.is_dir():
        return []
    exclude_globs = load_exclude_globs(root)
    sites: list[tuple[str, int, str, str, str]] = []
    for path in sorted(iter_files(design_dir, suffix=".strata")):
        rel = path.relative_to(root).as_posix()
        if exclude_globs and is_excluded(rel, exclude_globs):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning("_strata_waive_sites: could not read %s: %s", rel, exc)
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = _STRATA_WAIVE_RE.search(line)
            if match is None:
                continue
            sites.append(
                (
                    rel,
                    lineno,
                    match.group("rule"),
                    match.group("reason"),
                    match.group("ticket") or "",
                )
            )
    return sites


# frob:enforces CHK-GATE-WAIVE006
def _waive006_strata_violations(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE006 (`.strata` `waive` clause channel): the same stale-waiver
    check `_waive006_comment_violations` runs for `frob:waive` comments,
    applied to every `waive "RULE" reason "..." [ticket "..."]` clause
    `_strata_waive_sites` finds."""
    violations: list[Violation] = []
    for rel, line, rule, reason, ticket in _strata_waive_sites(root):
        refs = _waive006_binding_ticket_refs(reason)
        if ticket:
            refs.add(ticket)
        if not refs:
            continue
        stale = _waive006_stale_ticket(refs, queue)
        if stale is None:
            continue
        violations.append(
            _waive006_violation(
                file=rel,
                line=line,
                site=f"{rel}:{line}",
                rule_and_target=f'waive "{rule}"',
                stale=stale,
            )
        )
    return tuple(violations)


# frob:doc docs/modules/gates.md#public-api
def waive006_gate(
    root: Path, snapshot: GraphSnapshot, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE006: every stale-waiver finding across both waiver channels
    (`frob:waive` comments and `.strata` `waive` clauses) -- see the module
    comment above `_waive006_binding_ticket_refs` for the full rule design
    and the binding-vs-historical-mention calibration."""
    return (
        *_waive006_comment_violations(snapshot, queue),
        *_waive006_strata_violations(root, queue),
    )


# T-0808 (T-0779 reviewer finding): WAIVE006 deliberately skips a binding
# ticket ref that does not resolve to any ticket at all (active or
# archive) -- that is a different honesty gap, not WAIVE006's "closed
# ticket" case, and was silently unflagged. The real incident this closes:
# four `design/frob.strata` waivers bound to `T-draft-8cd37914`, which was
# renumbered to `T-0803` at land -- the waivers kept citing a ticket id
# that no longer (and now never again) resolves, a permanent silent
# waiver with nothing left to re-litigate it.
#
# Exemption: EVERY `T-draft-*` id is exempt from WAIVE007, unconditionally
# -- not just ones referenced by a still-live worktree lease. A narrower
# "exempt only if a live lease still claims this draft id" rule was
# considered and rejected: it would require this gate to cross-reference
# `frob.tickets._leases` state that is worktree-local and routinely absent
# in the very run (a landed/merged checkout, CI, another agent's worktree)
# where the gate needs to be trustworthy, making the exemption itself flaky
# across environments -- exactly the kind of environment-dependent gate
# result this repo's gates avoid elsewhere. Drafts are worktree-local
# transients by construction (`frob.tickets._models` mints `T-draft-<hex>`
# only inside an active worktree, and `frob ticket land` always renumbers
# them to a real `T-####` id before the ledger is shared) -- so ANY
# `T-draft-*` id a gate run observes is either still in-progress (not yet
# landed, not a dangling reference at all -- the id simply has not been
# minted into the real ledger this checkout sees) or was already
# renumbered away and is now permanently unresolvable by design, a state
# WAIVE006 already treats as out of scope for the identical reason (see
# `_waive006_stale_ticket`'s docstring). Flagging a renumbered draft as
# "dangling" would fire on every merged waiver written before its own
# ticket landed, forever, which is noise WAIVE007 exists to avoid
# creating, not add.
def _waive007_is_exempt_dangling_ref(ticket_id: str) -> bool:
    """`True` for any `T-draft-*` id: worktree-local transient by
    construction (see the module comment above), never a WAIVE007
    finding regardless of whether it currently resolves."""
    return ticket_id.startswith("T-draft-")


def _waive007_violation(
    *, file: str, line: int, site: str, rule_and_target: str, dangling: str
) -> Violation:
    """The single WAIVE007 `Violation` for one waiver site whose binding
    ticket ref does not resolve to any ticket (shared by both waiver
    channels, mirroring `_waive006_violation`'s shape)."""
    _log.warning(
        "WAIVE007: %s (%s) binds to unresolvable ticket %s",
        site,
        rule_and_target,
        dangling,
    )
    return Violation(
        rule="WAIVE007",
        severity=Severity.WARN,
        file=file,
        line=line,
        message=(
            f"WAIVE007: {site} waives {rule_and_target}, bound to ticket "
            f"{dangling}, which does not resolve to any ticket (active or "
            f"archive) -- a typo, or a draft id renumbered at land; "
            f"re-point the waiver at the real ticket id or remove the "
            f"stale binding"
        ),
    )


# frob:enforces CHK-GATE-WAIVE007
def _waive007_comment_violations(
    snapshot: GraphSnapshot, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE007 (`frob:waive` comment channel): a waiver whose `ticket=`
    attribute, or whose `reason=` text binds itself via
    `_waive006_binding_ticket_refs` (the same binding-vs-mention
    extraction WAIVE006 uses), names a ticket id that resolves to nothing
    in the ledger+archive and is not `_waive007_is_exempt_dangling_ref`."""
    violations: list[Violation] = []
    for edge in _waive_edges(snapshot):
        reason = edge.attrs.get("reason", "")
        refs = _waive006_binding_ticket_refs(reason)
        attr_ticket = edge.attrs.get("ticket", "")
        if attr_ticket:
            refs.add(attr_ticket)
        if not refs:
            continue
        from frob.gates import _site_from_edge_origin  # local: avoids circularity

        file, line = _site_from_edge_origin(edge.origin)
        # frob:waive PERF004 reason="own distinct refs set per waive edge, not a shared re-sort"  # noqa: E501
        for ticket_id in sorted(refs):
            if ticket_id in queue.tickets:
                continue
            if _waive007_is_exempt_dangling_ref(ticket_id):
                continue
            violations.append(
                _waive007_violation(
                    file=file,
                    line=line,
                    site=edge.src,
                    rule_and_target=f"frob:waive {edge.target}",
                    dangling=ticket_id,
                )
            )
    return tuple(violations)


# frob:enforces CHK-GATE-WAIVE007
def _waive007_strata_violations(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE007 (`.strata` `waive` clause channel): the same dangling-
    binding-ref check `_waive007_comment_violations` runs for `frob:waive`
    comments, applied to every `waive "RULE" reason "..." [ticket "..."]`
    clause `_strata_waive_sites` finds."""
    violations: list[Violation] = []
    for rel, line, rule, reason, ticket in _strata_waive_sites(root):
        refs = _waive006_binding_ticket_refs(reason)
        if ticket:
            refs.add(ticket)
        if not refs:
            continue
        # frob:waive PERF004 reason="own distinct refs set per waive clause site, not a shared re-sort"  # noqa: E501
        for ticket_id in sorted(refs):
            if ticket_id in queue.tickets:
                continue
            if _waive007_is_exempt_dangling_ref(ticket_id):
                continue
            violations.append(
                _waive007_violation(
                    file=rel,
                    line=line,
                    site=f"{rel}:{line}",
                    rule_and_target=f'waive "{rule}"',
                    dangling=ticket_id,
                )
            )
    return tuple(violations)


# frob:doc docs/modules/gates.md#public-api
def waive007_gate(
    root: Path, snapshot: GraphSnapshot, queue: TicketQueue
) -> tuple[Violation, ...]:
    """WAIVE007: every dangling-binding-ref finding across both waiver
    channels (`frob:waive` comments and `.strata` `waive` clauses) -- see
    the module comment above `_waive007_is_exempt_dangling_ref` for the
    full rule design and the `T-draft-*` exemption rationale."""
    return (
        *_waive007_comment_violations(snapshot, queue),
        *_waive007_strata_violations(root, queue),
    )


# frob:ticket T-0504
# PLACE001 was first prototyped as "distance from the class's own span
# start" and DELIBERATELY DROPPED (T-0470) before landing: that heuristic
# fired on this repo's own widespread, legitimate idiom of per-field
# `frob:waive`/`frob:ticket` comments documenting one field deep inside a
# large pydantic config class (e.g. `src/frob/app/config.py`'s
# `AppConfig`, `frob:waive SCOPE001` at line 212, 150+ lines past the
# class's `class AppConfig:` line) -- fields are not `RawSymbol`s (only
# FUNCTION/METHOD/CLASS/CONST/TYPE are), so a directive above one always
# falls back to the enclosing class by construction, and doing so far
# from the class top is completely intentional there, not mis-scoped.
#
# T-0504 replaces that raw-distance signal with the materially different
# one this comment's own predecessor named as the real fix: does a
# nearby REAL symbol exist that the directive plausibly SHOULD have
# bound to via `following` but didn't reach, with nothing but blank
# lines/comments/decorators between the directive and that symbol? The
# per-field idiom always has genuine field-assignment CODE in that gap
# (the very thing that makes it a field and not a stray comment), so it
# is excluded by construction rather than by distance -- see
# `_place001_missed_symbol`'s docstring for the full argument and
# `TestPlace001Gate` for both the non-vacuous positive (a directive
# separated from its intended `def` by one blank line too many) and the
# AppConfig-shaped negative (a directive above a field, real code before
# the next real method).
_PLACE001_LOOKAHEAD = 10


# frob:ticket T-0504
def _place001_missed_symbol(
    comment: RawComment,
    symbols: tuple[RawSymbol, ...],
    lines: list[str],
) -> RawSymbol | None:
    """The nearby REAL symbol (within `_PLACE001_LOOKAHEAD` lines) that a
    class-fallback-bound `frob:` directive plausibly intended but missed
    via `_find_following_symbol`'s narrower window -- `None` if no such
    symbol exists, or if genuine code (anything other than a blank line,
    a `#`/`//` comment, or a decorator line) sits between the directive
    and the candidate.

    That "genuine code in between" check is the whole soundness argument
    (T-0504): the only way `following` can miss a REAL symbol that is
    still close by is a run of blank lines, stacked comments, or
    decorators wider than `_FOLLOWING_SYMBOL_WINDOW` -- none of which is
    itself an intervening obligation the directive could instead belong
    to. The per-field pydantic idiom this ticket must NOT fire on always
    has actual field-assignment code in that gap (that is what makes it
    a field), so it can never produce a candidate here regardless of how
    close or far the class's next real method sits.
    """
    end = comment.span[1]
    candidates = [
        sym for sym in symbols if end < sym.span[0] <= end + _PLACE001_LOOKAHEAD
    ]
    if not candidates:
        return None
    candidate = min(candidates, key=lambda sym: sym.span[0])
    for lineno in range(end + 1, candidate.span[0]):
        if lineno - 1 >= len(lines):
            break
        stripped = lines[lineno - 1].strip()
        if stripped == "" or stripped.startswith(("#", "//", "@")):
            continue
        return None
    return candidate


# frob:ticket T-0504
def _place001_bindings(
    comments: tuple[RawComment, ...], path: str
) -> dict[int, tuple[str, bool]]:
    """`comment_id -> (resolved_src, via_following)` for every comment in
    `comments`, mirroring `frob.graph.dsl._resolve_block_srcs`'s exact
    stacked-comment-propagation algorithm (order, carry state) but ALSO
    tagging whether the binding was reached via a `following` match
    (direct, or propagated backward from a later comment's own resolved
    `following` in the same contiguous block, T-0313) versus a genuine
    `enclosing`/bare-path fallback.

    This distinction is the entire soundness argument for PLACE001: a
    `frob:doc`/`frob:ticket` comment placed directly above `class Foo:`
    resolves via `following` straight to `Foo` (correct and intentional,
    `via_following=True`) even though `Foo` is a CLASS -- checking only
    "did this resolve to a class" (as `_resolve_block_srcs`'s plain
    output would tempt) cannot tell that apart from a directive genuinely
    stuck at the class-fallback because it sits somewhere INSIDE the
    class body with no reachable `following` target at all
    (`via_following=False`). Only the latter is what T-0504's placement
    check should ever consider.
    """
    from frob.graph.dsl import _enclosing_src

    order = sorted(range(len(comments)), key=lambda i: comments[i].span[0])
    resolved: dict[int, tuple[str, bool]] = {}
    carry_start: int | None = None
    carry_src: str | None = None
    for idx in reversed(order):
        comment = comments[idx]
        if comment.following is not None:
            src = f"{path}::{comment.following}"
        elif carry_src is not None and comment.span[1] + 1 == carry_start:
            src = carry_src
        else:
            resolved[idx] = (_enclosing_src(comment, path), False)
            carry_start = None
            carry_src = None
            continue
        resolved[idx] = (src, True)
        carry_start = comment.span[0]
        carry_src = src
    return resolved


# frob:ticket T-0504
# frob:enforces CHK-GATE-PLACE001
def _place001_file(root: Path, file: str) -> tuple[Violation, ...]:
    """PLACE001 findings for one file: a `frob:` directive whose fully
    resolved binding (`_place001_bindings`, the same stacked-comment-aware
    resolution `parse_directives` itself uses) is a genuine class
    FALLBACK (`via_following=False`, not a directive that correctly
    resolved via `following` straight to a class it precedes), where
    `_place001_missed_symbol` finds a real symbol the directive plausibly
    should have reached instead.

    Re-parses `file` directly (root-relative, like `_cov006`/`_cov005`)
    rather than reusing `GraphSnapshot` -- the snapshot only carries
    already-resolved `Edge`s, not the per-comment `following`/`enclosing`
    detail this check needs.
    """
    from frob.lang import parse_file

    result = parse_file(root / file)
    if result.is_err:
        return ()
    parsed = result.danger_ok
    try:
        lines = (root / file).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _log.warning("PLACE001: could not read %s: %s", file, exc)
        return ()
    symbol_by_qualname = {sym.qualname: sym for sym in parsed.symbols}
    resolved = _place001_bindings(parsed.comments, file)
    violations: list[Violation] = []
    for comment_id, comment in enumerate(parsed.comments):
        violation = _place001_comment_violation(
            file, comment_id, comment, resolved, symbol_by_qualname, parsed, lines
        )
        if violation is not None:
            violations.append(violation)
    return tuple(violations)


# frob:ticket T-0598
def _place001_comment_violation(
    file: str,
    comment_id: int,
    comment: RawComment,
    resolved: dict[int, tuple[str, bool]],
    symbol_by_qualname: dict[str, RawSymbol],
    parsed: ParsedFile,
    lines: list[str],
) -> Violation | None:
    """One `frob:` directive's PLACE001 finding, or `None` if it does not
    class-fall-back to a real missed symbol (`_place001_file`'s per-comment
    body, split out for ARCH001 -- T-0598)."""
    if not comment.text.startswith("frob:"):
        return None
    src, via_following = resolved[comment_id]
    if via_following:
        return None
    _prefix, sep, qualname = src.partition("::")
    if not sep:
        return None
    enclosing_sym = symbol_by_qualname.get(qualname)
    if enclosing_sym is None or enclosing_sym.kind != SymbolKind.CLASS:
        return None
    missed = _place001_missed_symbol(comment, parsed.symbols, lines)
    if missed is None:
        return None
    _log.debug(
        "PLACE001: %s:%s directive class-falls-back to %s, missed %s",
        file,
        comment.span[0],
        qualname,
        missed.qualname,
    )
    return Violation(
        rule="PLACE001",
        severity=Severity.WARN,
        file=file,
        line=comment.span[0],
        message=(
            f"PLACE001: {file}:{comment.span[0]} frob: directive "
            f"falls back to enclosing class {qualname!r}, but "
            f"{missed.qualname!r} starts at line {missed.span[0]} "
            f"with nothing but blank lines/comments/decorators in "
            f"between -- likely intended for that symbol; move "
            f"the directive within the following-window, or "
            f"confirm the class binding is intentional"
        ),
    )


# frob:ticket T-0504
def _place001(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """PLACE001 (advisory): a `frob:` directive that class-falls-back
    (`_place001_file`) instead of reaching a real, nearby symbol via
    `following` -- a likely mis-scoped directive, not raw distance from
    the class's own span start (T-0470's dropped prototype; see the
    comment above `_PLACE001_LOOKAHEAD` for the full history).

    WARN severity: best-effort, name/position-based (same tier as
    COV006) -- a finding is a prompt to double check, not proof the
    directive is wrong.
    """
    files = sorted({symref.split("::", 1)[0] for symref in snapshot.symbols})
    violations: list[Violation] = []
    for file in files:
        violations.extend(_place001_file(root, file))
    return tuple(violations)


# _match_waiver has three matching modes, chosen by `violation.symref`/
# `violation.rule` -- this comment (not the docstring) carries the
# historical detail so frob-arch's long-function line count reflects
# the code, not the explanation:
#
# - `violation.symref is not None` (currently only TEST005's per-symbol
#   branch-coverage check): the violation is about exactly one symbol,
#   so only an EXACT `waiver.src == violation.symref` counts -- a
#   `frob:waive` placed above a *different* symbol, or bare at file
#   top, does not match. Without this, placement above a specific
#   symbol is cosmetic: `frob.graph.dsl`'s `_enclosing_src` still binds
#   a `path::qualname` edge, but the old file-prefix comparison below
#   stripped the `::qualname` back off before comparing, so one
#   directive anywhere in a file silently waived every violation of
#   that rule in the whole file (the blanket-waiver bug T-0148's
#   review caught empirically: 102 file-top waivers absorbing 195
#   distinct findings).
# - `violation.symref is None` (every other rule, plus TEST005's own
#   per-module line-coverage and per-system checks, which have no
#   single symbol to bind to): the original file-scoped match -- a
#   waiver's `src` symbol/file equals the violation's `file` (either
#   the bare path or a `path::qualname` symref rooted at that path).
#   This is the CORRECT precision for those checks, not a shortcut:
#   one module-line violation per file has exactly one natural site.
#
# `violation.rule in _UNWAIVABLE_RULES` (currently just TEST008) short-
# circuits to `None` regardless of any matching `frob:waive` edge --
# by construction, not by omission; see `_UNWAIVABLE_RULES`'s comment.
#
# T-0276: a THIRD mode covers package/system-level violations (TEST003/
# TEST004, whose `violation.file` is an interface id like
# `crates/foo/src` or a system id, never a real single file) -- a
# waiver written in any file living under that package prefix also
# counts. Without this, such a violation's waiver could never match
# ANYTHING: no real source file's path is ever literally equal to a
# directory-shaped interface id, so the plain file-scoped comparison
# below always failed by construction (found while investigating why a
# `frob:waive TEST003 reason="..."` sitting in a rust integration test
# file reported `0 waived` in feldspar's adoption sweep -- traced to
# this, not to any check_type-based exclusion of `.rs` directives,
# which does not exist: `frob.graph.build_graph`/`_load_tests` are
# check_type-agnostic).
#
# T-0470: the package-prefix branch is gated to `_PACKAGE_SCOPED_RULES`
# ONLY -- it used to run for every symref-less violation regardless of
# rule, on the (empirically true today, but not future-proof) assumption
# that no other rule's `violation.file` is ever directory-shaped. TEST007
# also emits a directory-shaped `file` (a package id, `_test007_check_
# pair`), so it needed the same prefix reach TEST003/004 already had --
# but any FUTURE rule that reuses a bare directory/virtual id as `file`
# (a `[[system]]`-style id, a `design/...` construct id) would have
# silently inherited unbounded directory-prefix matching it was never
# reviewed for, purely because it happens to have no symref. Restricting
# the branch to an explicit allowlist means adding prefix reach to a new
# rule is a deliberate, reviewable one-line change, not a side effect of
# giving that rule a directory-shaped `file`.
# T-0289: a waiver may carry `ceiling="N"` (currently only meaningful for
# ARCH001) -- a reasoned "this long function is justified up to N lines"
# escape that re-fires once the function outgrows N, instead of muting the
# finding permanently. `_ceiling_ok` is generic (any rule whose Violation
# sets `metric` can use it), not ARCH001-specific, so a future rule with the
# same "reasoned up to a measured bound" shape does not need its own
# matching path.
# frob:ticket T-0470
# The only rules whose `Violation.file` is a directory/system id rather
# than a real leaf file with an extension -- see the T-0470 comment
# above `_match_waiver` for why this must be an explicit allowlist, not
# "every symref-less rule". Keep this in sync with any rule that starts
# emitting a package/system-shaped `file` (`_test003`, `_test004`,
# `_test007_check_pair` are the current three sites).
_PACKAGE_SCOPED_RULES = frozenset({"TEST003", "TEST004", "TEST007"})


# frob:invariant INV-006
# frob:tests tests/test_arch_gate.py::TestArchGateWaivers.test_ceiling_refires_when_grown_past_it  # noqa: E501
# frob:waive EXHAUST001 reason="T-1056: leaked Unknown traces to waiver.attrs.get \
# (plain dict access) and int(ceiling_text); the int() ValueError path is already \
# caught above, and the remaining TypeError path from the metric comparison is now \
# explicitly caught below -- no unhandled raise path remains, only the resolver's \
# inability to see that"
def _ceiling_ok(waiver: Edge, violation: Violation) -> bool:
    """Whether `waiver` still covers `violation` given its optional
    `ceiling=` attribute: always true when no ceiling is set (or the
    violation carries no `metric` to compare); otherwise true only while
    `violation.metric <= ceiling`."""
    ceiling_text = waiver.attrs.get("ceiling")
    if ceiling_text is None or violation.metric is None:
        return True
    try:
        ceiling = int(ceiling_text)
    except ValueError:
        # Malformed ceiling value: fail open to "still waived" rather than
        # a crash -- WAIVE002-style validation of the attribute's shape is
        # a separate concern from matching, and a garbled ceiling is not
        # reason to un-suppress a violation the author clearly meant to
        # waive.
        return True
    try:
        return violation.metric <= ceiling
    except TypeError:
        # `violation.metric` is typed as int|float|None and already checked
        # not-None above; a TypeError here would mean some caller built a
        # Violation with a non-numeric metric, which is a construction bug
        # elsewhere, not a reason to crash the waiver-matching gate itself
        # -- fail open to "still waived", same posture as the ValueError
        # branch above.
        return True


# invariant spec: [INV-006](invariants/INV-006.md)
def _match_waiver(
    violation: Violation, waivers_by_rule: dict[str, list[Edge]]
) -> Edge | None:
    """The first WAIVE edge whose site matches `violation` (symbol-exact,
    file-scoped, or package-prefix -- see the comment above) AND whose
    optional `ceiling=` still covers it (`_ceiling_ok`), or None."""
    if violation.rule in _UNWAIVABLE_RULES:
        return None
    candidates = waivers_by_rule.get(violation.rule, ())
    if violation.symref is not None:
        for waiver in candidates:
            if waiver.src == violation.symref and _ceiling_ok(waiver, violation):
                return waiver
        return None
    package_scoped = violation.rule in _PACKAGE_SCOPED_RULES
    package_prefix = violation.file.rstrip("/") + "/"
    for waiver in candidates:
        waiver_file = waiver.src.split("::", 1)[0]
        if (
            waiver.src == violation.file
            or waiver_file == violation.file
            or (package_scoped and waiver_file.startswith(package_prefix))
        ) and _ceiling_ok(waiver, violation):
            return waiver
    return None


def _apply_waivers(
    violations: tuple[Violation, ...], snapshot: GraphSnapshot
) -> tuple[tuple[Violation, ...], tuple[Violation, ...]]:
    """Split `violations` into (kept, waived) using the snapshot's WAIVE edges."""
    waivers_by_rule = _waivers_by_rule(snapshot)
    kept: list[Violation] = []
    waived: list[Violation] = []
    for violation in violations:
        match = _match_waiver(violation, waivers_by_rule)
        if match is None:
            kept.append(violation)
            continue
        _log.debug(
            "waived: %s at %s:%d (%s)",
            violation.rule,
            violation.file,
            violation.line,
            match.attrs.get("reason", ""),
        )
        waived.append(
            violation.model_copy(
                update={
                    "waived": WaiverRef(
                        site=match.src, reason=match.attrs.get("reason", "")
                    )
                }
            )
        )
    return tuple(kept), tuple(waived)


# T-0524: frob:doc removed -- feeds run_gates (public, via
# _apply_severity_overrides), which already carries the same
# docs/modules/gates.md#public-api anchor (COV007).
# frob:uses-contract src/frob/graph/__init__.py::build_graph
# frob:uses-contract src/frob/graph/lock.py::drift
# frob:uses-contract src/frob/tickets/_archive.py::load_queue
def _severity_overrides(root: Path | str) -> dict[str, Severity]:
    """The `[gates.severity]` table from frob.toml: rule id -> warn|error.

    This is how a legacy codebase adopts gates without a big-bang: noisy
    rules go to "warn" (visible, not blocking) and are flipped back to
    "error" as annotation coverage grows. Values other than warn/error are
    ignored with a warning -- never a crash on config typos.
    """
    toml_path = Path(root) / "frob.toml"
    if not toml_path.exists():
        return {}
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("severity overrides: could not read %s: %s", toml_path, exc)
        return {}
    raw = data.get("gates", {}).get("severity", {})
    overrides: dict[str, Severity] = {}
    for rule, value in raw.items():
        if value in ("warn", "error"):
            overrides[rule] = Severity.WARN if value == "warn" else Severity.ERROR
        else:
            _log.warning(
                "severity overrides: %s=%r is not warn|error; ignored", rule, value
            )
    if overrides:
        _log.info("severity overrides active: %s", overrides)
    return overrides


def _apply_severity_overrides(
    violations: tuple[Violation, ...], root: Path | str
) -> tuple[Violation, ...]:
    """Re-severity `violations` per the `[gates.severity]` frob.toml table."""
    overrides = _severity_overrides(root)
    if not overrides:
        return violations
    return tuple(
        (
            v.model_copy(update={"severity": overrides[v.rule]})
            if v.rule in overrides
            else v
        )
        for v in violations
    )


_BRANCH_TICKET_RE = re.compile(r"^(T-\d{4})-")


# frob:doc docs/modules/gates.md#public-api
def active_ticket(root: Path, explicit: str | None) -> Option[str]:
    """`--ticket` wins; else the branch name matching `^(T-\\d{4})-`; else Nothing."""
    if explicit:
        _log.debug("active_ticket: explicit=%s", explicit)
        return Some(explicit)
    branch_result = current_branch(root)
    if branch_result.is_err:
        _log.debug("active_ticket: no branch context")
        return Nothing()
    match = _BRANCH_TICKET_RE.match(branch_result.danger_ok)
    if match is None:
        _log.debug(
            "active_ticket: branch %r has no ticket prefix", branch_result.danger_ok
        )
        return Nothing()
    _log.debug("active_ticket: branch-derived %s", match.group(1))
    return Some(match.group(1))


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0787
# frob:tests tests/test_tickets_leases.py::TestTicketLeasePin.test_no_lease_mechanism_engaged_passes_through kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestTicketLeasePin.test_pinned_lease_for_this_worktree_passes kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestTicketLeasePin.test_lease_absent_for_this_worktree_refuses kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestTicketLeasePin.test_lease_recorded_elsewhere_refuses kind="unit"  # noqa: E501
def ticket_lease_pin(root: Path, ticket_id: str) -> Result[None, LeaseError]:
    """Validate `ticket_id`'s cross-worktree lease pins to `root` (T-0787,
    promoting T-0766's `resolve_lease` primitive into the live `--ticket`
    resolution path -- previously nothing in `frob check` consulted it at
    all, a reviewer-flagged hard dependency: the T-0695 stale/cross-worktree
    lease-resolution guard prevented nothing until something called it).

    `Ok(None)` both when the lease genuinely pins to `root`, AND when the
    cross-worktree lease mechanism has never been engaged for this repo at
    all: no shared git common dir (a non-git fixture, or a "plain" repo
    with no git worktree context), or a leases directory that has never
    been created because no ticket has ever been `frob ticket start`ed
    anywhere in this repo. Those are the no-lease paths T-0787 must leave
    working exactly as before -- non-agent/manual `--ticket` invocations of
    a repo that never opted into the lease side-channel at all.

    `Err(LeaseError.NoLeaseForTicket | LeaseError.LeaseWorktreeMismatch)`
    once the mechanism IS engaged elsewhere in this repo (the leases
    directory exists) but `ticket_id` itself has no lease recorded for
    `root` specifically -- absent entirely, or recorded for a different
    worktree. The caller (`frob check`'s CLI entry point) turns either into
    a loud refusal naming `frob ticket start <ticket_id>`, closing the
    T-0695 hole `resolve_lease` was built to fix but nothing invoked."""
    from frob.tickets._leases import leases_dir, resolve_lease

    leases_root_result = leases_dir(root)
    if leases_root_result.is_err:
        _log.debug(
            "ticket_lease_pin: no shared git common dir under %s; lease "
            "mechanism not engaged, skipping pin check for %s",
            root,
            ticket_id,
        )
        return Ok(None)
    leases_root = leases_root_result.danger_ok
    if not leases_root.is_dir():
        _log.debug(
            "ticket_lease_pin: %s never created (no ticket ever started in "
            "this repo); skipping pin check for %s",
            leases_root,
            ticket_id,
        )
        return Ok(None)
    lease_result = resolve_lease(root, ticket_id, root)
    if lease_result.is_err:
        return Err(lease_result.danger_err)
    return Ok(None)
