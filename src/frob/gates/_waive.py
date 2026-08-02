# frob:waive SCOPE001 reason="T-1402: this file needed only a mechanical, necessary \
# rename of a stale frob:waive EXHAUST001 comment to EXHAUST003 (the EXHAUST001 \
# precision fix, declared scope src/frob/gates/_exhaustive_handling.py) or (this file, \
# _tickets_gate.py, _waive.py) is the actual TICK011 fix itself -- frob ticket scope \
# --add refuses it: T-1279 (TEST005 burn-down) holds a concurrent in-progress lease on \
# src/frob/gates/** for the whole package, so this ticket cannot formally register the \
# file in its own declared scope until T-1279 closes or narrows; see this ticket's \
# Done report for the full disclosure"
"""frob.gates._waive -- WAIVE001-005/DSL001 directive validation plus the
shared `_match_waiver`/`_apply_waivers` matching spine.

Extracted from `frob.gates.__init__` (T-1072, T-0395 tier 1 split), then
further cohered (T-1081, clearing the T-1072 transitional ARCH102 waiver):
the WAIVE006/007/PLACE001 "is this directive comment placed/bound
soundly" family moved to `frob.gates._waive_comments`, and the
`active_ticket`/`ticket_lease_pin` lease helpers (unrelated to waiver
matching -- they just rode along in the T-1072 extraction) moved to
`frob.gates._waive_lease`. What remains here is one cluster: validating a
`frob:waive` directive itself (malformed-directive detection, unwaivable-
channel enforcement, the rule-id registry) and the `_match_waiver`/
`_apply_waivers`/`_ceiling_ok`/`_severity_overrides` spine every other
gate's violation list is filtered through. Re-exported from
`frob.gates.__init__` unchanged so every existing `frob.gates.<name>`
call site keeps working.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from frob.gates._models import Severity, Violation, WaiverRef
from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)


def _waive_edges(snapshot: GraphSnapshot) -> tuple[Edge, ...]:
    """Every valid `frob:waive` edge in the snapshot (dsl.py already rejects a
    waive directive missing `reason=...` as a MalformedDirective, so every
    surviving WAIVE edge here is guaranteed to carry a reason)."""
    from frob.gates import _edges_of_kind

    return _edges_of_kind(snapshot, EdgeKind.WAIVE)


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
        # T-1340: suppression-dialect mismatch (a line carrying one
        # checker's suppression while another configured checker reports
        # an unsuppressed diagnostic on it). Registered here so the gate
        # landed by T-1340 is waivable and known to TestKnownGateRuleIds.
        "SUPPRESS001",
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
        # T-1421/T-1427: a bug/security ticket's designated evidence test
        # must have genuinely FAILED at its parent commit (the mechanical
        # "the defect no longer reproduces" check); see
        # `frob.gates._mutation_evidence.bug_repro_violations`.
        "BUG002",
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
        # T-1088: four project-tree-wide supply-chain structural detectors
        # (src/frob/vet/_supplychain.py), same hand-maintained class as the
        # rest of this VET block.
        "VET007",
        "VET008",
        "VET009",
        "VET010",
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
        # T-1148: a declared `[[native]]` extension fails to import right
        # now (`run_gates`'s early `_native_unavailable_report` short-
        # circuit) -- see `frob.gates.__init__._native_unavailable_report`.
        "NATIVE001",
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
        # T-1129: disclosed-cut-without-ticket (frob.gates.tickets_gate's
        # _tick011_disclosed_cuts_without_ticket) -- a Done report's prose
        # admits deferred/cut work (a conservative disclosure-phrase scan,
        # T-1085/T-0321/T-1140/T-1150's incidents) with no ticket id
        # resolving nearby and no explicit no-ticket-needed reason. WARN,
        # first turn-on.
        "TICK011",
        # T-0788: COMPLIANCE005 (frob.gates.compliance_gate, dispatching
        # frob.strata._compliance.check_cmpl_registry built by T-0607) --
        # a checkable-control CMPL-* compliance-registry unit left
        # deferred/undispositioned. T-0607 built the check but could not
        # register it here nor dispatch it (out of that ticket's scope);
        # this closes the catalogued-is-not-enforced gap it disclosed.
        "COMPLIANCE005",
        # T-1244: COMPLIANCE007 (frob.gates.compliance_gate, dispatching
        # frob.strata._compliance._check_cmpl_registry_unit_backing) -- a
        # CMPL-* unit whose handled_by:COMPLIANCE005 disposition is a
        # vacuous self-reference (proves a string exists, not that a real
        # RegulationEntry/attestation backs the framework). WARN-tier,
        # waivable per-row like COMPLIANCE001-003, unlike COMPLIANCE006.
        "COMPLIANCE007",
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
        # T-1102: LARGE001 (frob.arch._check_large_file's large-file
        # category), channeled into a real gate Violation by the same
        # frob.gates._arch.arch_gate as ARCH001/ARCH1xx/CPPTHROW001 --
        # a dict-value rule id `_rule_id_scan.py`'s scanner cannot detect
        # (same disclosed gap CPPTHROW001 above hits), hand-added here
        # per that module's own docstring convention (T-1111 REG002 fix,
        # same CHK-GATE-CPPTHROW001 auto-sync gap class noted at T-1042).
        "LARGE001",
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
        # T-1227: `frob:enumerates` doc-claimed member-list AST-diff, ack-
        # immune (frob.gates._docenum).
        "DOCENUM001",
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
        # T-1428: a ticket's own diff adds a symbol, gate-rule-id literal,
        # or CLI flag `dest` that nothing outside the diff's own tests can
        # reach -- the repeat-offender "landed, passed every gate, did
        # nothing" defect (`frob.gates._wire.wire_gate`).
        "WIRE001",
        # T-1428: a `frob:waive WIRE001` present but its `follow_up=`
        # attribute is missing or does not name a real, still-open ticket
        # -- the escape hatch must bind an enforced obligation, not just
        # carry free-text prose nobody has to act on.
        "WIRE002",
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
        # frob:ticket T-1139
        # SYSWAIVE003 (frob.strata._selfconform, T-0671's staleness-gated
        # waiver mechanism) -- T-0671 registration gap, found while
        # verifying T-1115's gates/__init__.py family split.
        "SYSWAIVE003",
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
        # frob:ticket T-1402
        # T-1402: EXHAUST003 (frob.gates._exhaustive_handling's
        # exhaustive_handling_gate) -- the quieter resolution-coverage
        # signal the EXHAUST001 precision fix demoted an unresolved-callee
        # leak into, split out of EXHAUST001 (declared scope:
        # src/frob/gates/_exhaustive_handling.py; this one-line addition to
        # this module's known-rule allowlist is the minimal out-of-scope
        # widening needed for the new rule id to be `frob:waive`-able at
        # all -- WAIVE002 would otherwise flag any waiver naming it as
        # targeting a rule that can never match).
        "EXHAUST003",
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
        # T-0668 (post-merge, T-1081): SYS104/105/106 (exact interface-
        # conformance -- src/frob/strata/_selfconform.py) landed on main
        # after this ticket's own _waive.py split diverged; picked up here
        # via the same "generated_gate_rule_ids reports it, paste it in"
        # discipline this literal's own comment documents.
        "SYS104",
        "SYS105",
        "SYS106",
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
        # T-1428: WIRE002 is a finding ABOUT a `frob:waive WIRE001`'s own
        # escape hatch being malformed/unbound -- waiving it away would
        # let the exact honest-but-unenforceable disclosure this ticket
        # exists to close back in through its own side door.
        "WIRE002",
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
# for reasons that have nothing to do with the waiver being stale.
# T-1133: rather than emit those as a known-flaky advisory a caller must
# mentally filter (the pre-T-1133 posture, ~400-447 such advisories per
# scoped run this drive, each carrying its own "trust this only from a
# full run" disclaimer baked into the message text), `_waive004_
# violations` now skips entirely on any `--only`/`--ticket` scoped run
# (`full_unscoped_run=False`) -- WAIVE004 only ever fires on a full,
# unscoped `frob check`, where match-absence is actually meaningful. A
# ratchet-to-error path via the T-0569/T-0594 waivable-warning pool is a
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
    *,
    full_unscoped_run: bool = True,
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

    T-1133: `full_unscoped_run=False` (the caller's `--only`/`--ticket`
    scoped-run signal, `not cfg.gates and cfg.ticket is None` at the
    `_assemble_gate_report` call site) short-circuits to `()` before any
    per-edge work -- on a scoped run, "matches 0 findings" is
    indistinguishable from "the gate that would have produced a match
    simply did not run this time", so EVERY waiver on an excluded rule (or
    a rule this diff's touched set happens not to cover) read as
    permanently stale, ~400-447 advisories per scoped run this drive, each
    carrying its own "trust this only from a full run" disclaimer baked
    into the message text -- tribal knowledge every caller had to filter
    by hand instead of the check simply not firing where it cannot be
    trusted. Full, unscoped `frob check` behavior (T-1021's sweep depends
    on it) is unchanged."""
    if not full_unscoped_run:
        return ()
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
                    f"still needs it, or remove the directive (T-1133: this "
                    f"rule only fires on a full, unscoped run, so match-absence "
                    f"here is meaningful, not a scoped-run artifact)"
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
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1056: leaked Unknown traces to waiver.attrs.get (plain dict \
# access) and int(ceiling_text); the int() ValueError path is already caught above, \
# and the remaining TypeError path from the metric comparison is now explicitly caught \
# below -- no unhandled raise path remains, only the resolver's inability to see that"
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
