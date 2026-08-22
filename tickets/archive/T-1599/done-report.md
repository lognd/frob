## Done report

Rescoped per coordinator directive: original ticket text described a
capability matrix/conformance suite/gate that was already built (T-2365/
T-2494/T-2499/T-2411, confirmed by direct code reading before any work
started). Actual work this round: close the two real remaining gaps
(behavioral coverage for 2 of the 3 structural-only capabilities, and
the documented OPTIONAL-capability degradation story), fix a stale doc
paragraph found in the same reconnaissance, and remove the blocked_by
edge on T-1598 (deferred separately, unrelated to this ticket's real
scope).

Changed:
src/frob/gates/_lang_conformance.py::_BEHAVIORALLY_CHECKED_CAPABILITIES (added CAPABILITY_CALL_GRAPH, CAPABILITY_IMPORT_GRAPH)
src/frob/gates/_lang_conformance.py::_CAPABILITY_FIXTURE_SOURCES (every per-language fixture: public fn now calls private fn; added one real import/include/use statement each, except strata which is NOT_APPLICABLE for both)
src/frob/gates/_lang_conformance.py::_behavioral_capability_check (new CAPABILITY_CALL_GRAPH/CAPABILITY_IMPORT_GRAPH branches; restructured trailing branch to an explicit `if`)
src/frob/gates/_lang_conformance.py::capability_conformance_gate (docstring updated to describe 6-of-7 coverage, not 4-of-7)
tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck.test_unchecked_capability_is_named_not_silently_true (moved from call_graph, now checked, to test_discovery, the one capability still unchecked)
docs/modules/lang.md#adapter-capability-contract-t-2365 (fixed stale import_graph disclosure: said IMPLEMENTED for python/c/cpp only, T-2494 made it live-derived and IMPLEMENTED for all 6 registered languages months ago, prose never caught up)
docs/modules/lang.md#optional-capability-degradation-t-1599 (new section, deliverable 4: per-capability answer to what a user of an affected language experiences when call_graph/import_graph/test_discovery is a KNOWN_GAP -- loud at the registry layer, silent at each consumer's own output today)
docs/modules/lang.md#behavioral-conformance-lang004-t-2365 (updated stale "four capabilities... need a real multi-file repo tree" claim)
tickets/T-1598 (body note only: research deliverable deliberately not attempted, must not be attempted from model memory)
tickets/T-1599 (blocked_by=T-1598 removed via store API -- see below; rescope rationale recorded in body)

Evidence:
tests/test_lang_conformance_gate.py (57 node ids, full file, all pass, re-verified against merged main: `uv run pytest tests/test_lang_conformance_gate.py -p no:cacheprovider -q` -> collected=57 failed=0)
tests/test_lang_support.py (20 node ids, full file, all pass)
tests/test_lang.py (67 node ids, full file, all pass)

Filed: T-2681 (frob ticket unblock verb missing -- CLI gap found while
clearing T-1599's own blocked_by edge), T-2682 (LANG004 test_discovery
behavioral coverage, the one capability left structural-only, blocked
on this ticket), T-2683 (consumer-side self-disclosure of a live
OPTIONAL-capability gap, blocked on this ticket).

Gates: `frob check --ticket T-1599 --no-cache` re-run AFTER merging main
(main had advanced substantially -- T-2134/T-2128/T-2311/T-2685 and a
batch of filings -- merge was clean, no conflicts, `git merge-base
--is-ancestor main HEAD` confirms current) over lang_conformance/
capability_conformance/lang_project_conformance/docanchor/doclink/
docblocks/scope/prework/fmt/affect_drift: 4 error(s), 130 warning(s)
total in this --only slice. Of those 4: gate:LANG 0 errors 3 warnings
(pre-existing arch KNOWN_GAP, T-0329, unrelated to this diff); gate:SCOPE
0 errors 106 warnings (pre-existing consider-adding notes, unrelated);
gate:PRE 0 errors (fresh sweep after commit, --no-cache bypassed a
gate-result replay cache that was masking this); gate:DOC 1 error
(gates.md anchor mismatch, unrelated file) and gate:DRIFT 3 errors
(three DRIFT001 digests in src/frob/_cli_parsers/_ticket/_new.py,
src/frob/app/ticket_runner/_verify.py, src/frob/tickets/__init__.py --
none of the 3 files this ticket touched) plus claude-config-drift (1,
a standing repo-wide condition present before this ticket started) --
all 4 are 0 attributable to any file this ticket's diff touches,
confirmed by cross-referencing each finding's path against `git show
--stat` on this ticket's own commit.

blocked_by=T-1598 removed: no CLI `unblock` verb exists (confirmed by
reading `frob.tickets._doable._open_blockers`'s own docstring, which
documents this exact gap from a prior incident, T-2076). Cleared via
`frob.tickets._store.write_ticket` directly, mirroring `frob.app.
ticket_runner._lifecycle._block`'s write path in reverse, then
committed via `_add_and_commit_tickets_md` -- the same store-API
precedent that prior incident's own docstring names, not a hand-edit
of the ledger YAML. Filed T-2681 so the next agent does not have to
re-derive this.

### Acceptance criteria resolution
The three original acceptance entries were 2026-08-17 MEASUREMENT NOTES,
not testable given/when/then criteria, and their own premises were
already false before this round's work started (ADAPTER_CAPABILITIES/
derive_capability_registry and LANG004/capability_conformance_gate were
already built under T-2365, not by this ticket). Per the coordinator's
explicit instruction not to bind evidence to a criterion it does not
actually prove: amended all three in place to record why (citing
T-2365/T-2494/T-2499/T-2411), then removed the two that named prior
work this ticket did not do, keeping the one that describes this
ticket's own real, testable, delivered result -- rewritten as a GIVEN/
WHEN/THEN and bound to real evidence: LANG004's behavioral conformance
suite extended from 4/7 to 6/7 capabilities (call_graph, import_graph
added this round; test_discovery remains disclosed structural-only,
T-2682).

### Changed
```
 docs/modules/lang.md                | 106 +++++++++++++++++----
 src/frob/gates/_lang_conformance.py | 181 +++++++++++++++++++++++++++---------
 tests/test_lang_conformance_gate.py |   9 +-
 tickets/T-1599/done-report.md       |  86 +++++++++++++++++
 4 files changed, 317 insertions(+), 65 deletions(-)
```

### Evidence
- `tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_implemented_capability_behaves_as_claimed[python-call_graph]` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_implemented_capability_behaves_as_claimed[python-import_graph]` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_every_registered_language_is_covered` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_unchecked_capability_is_named_not_silently_true` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_real_registry_is_behaviorally_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 35 error(s), 833 warning(s), 702 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1599/src/frob/gates/_fix_engine.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

### Acceptance amendments
- [0] replace: "MEASURED 2026-08-17: significant relevant infrastructure already landed (T-0405/T-0406, src/frob/lang/_support.py) before this ticket's own filing predates it (filed 2026-08-05) -- LanguageSupport/FacetState/FacetStatus already give every registered language a typed per-facet IMPLEMENTED/NOT_APPLICABLE(reason)/KNOWN_GAP(tracking ticket) cell, derived live from each subsystem's own registry (frob.lang/frob.vet/frob.dup/frob.arch/frob.gates._docblocks); LANG001 (lang_conformance_gate) already fails the build when a cell is unaccounted for; LANG002/LANG003 already cover the per-PROJECT half (a repo language frob does not parse at all, or a KNOWN_GAP present in the tree with a stale/unverifiable ticket ref). Deliverables 3 and 4 as originally written are LARGELY already satisfied by this existing mechanism -- re-verify against it before building anything parallel." -> "MEASUREMENT NOTE, superseded (T-1599 own investigation, this round): ADAPTER_CAPABILITIES/derive_capability_registry (src/frob/lang/_support.py) and LANG004 capability_conformance_gate (src/frob/gates/_lang_conformance.py) were already built under T-2365, before this ticket's own scoping work started, and LANG004 was already wired into frob check's job table (T-2411, done). This ticket's real remaining scope, confirmed against that live state rather than this stale note: extend LANG004's behavioral coverage and write the OPTIONAL-capability degradation story (see criterion [2])." (reason: The three original acceptance entries are 2026-08-17 MEASUREMENT NOTES,
not given/when/then criteria -- they describe what a prior sweep found
missing, not a testable claim this ticket's own work can resolve with
pytest evidence. Direct code reading before any work started this round
found their premise stale in frob's favor: ADAPTER_CAPABILITIES /
derive_capability_registry (src/frob/lang/_support.py, T-2365) and
LANG004 / capability_conformance_gate (src/frob/gates/_lang_
conformance.py, T-2365) both already existed -- built before this
ticket's own filing predates them, contradicting criteria [1]/[2]'s own
"no facet or registry exists" / "conformance suite does not exist"
claims. Amending rather than binding evidence to a false premise, per
the coordinator's explicit instruction not to bind evidence to a
criterion it does not actually prove.
; logan, 2026-08-19)
- [1] replace: "MEASURED 2026-08-17: the existing FACETS axis (grammar/capability/dup/arch/docblock, src/frob/lang/_support.py FACETS tuple) is SUBSYSTEM-INTEGRATION coverage (does frob.vet/frob.dup/frob.arch/frob.gates._docblocks have an entry for this language), a DIFFERENT axis than this ticket's own deliverable 1 (symbol walk, public/private determination, docstring/doc-comment extraction, comment/directive parsing incl. continuations, call graph edges, import/dependency edges, test discovery) -- an ADAPTER-CAPABILITY axis. No facet or registry for that axis exists today; this remains real, unbuilt work." -> 'MEASUREMENT NOTE, superseded: this criterion\'s own premise ("No facet or registry for [the adapter-capability] axis exists today") was already false by the time this ticket\'s own scoping work started -- ADAPTER_CAPABILITIES/CapabilityRequirement/CapabilityStatus/AdapterCapabilitySupport/derive_capability_registry (src/frob/lang/_support.py) already give every registered language a typed cell for all seven capabilities this criterion names, built under T-2365. Not this ticket\'s own work; found already built during reconnaissance and confirmed by direct code reading before writing anything.' (reason: The three original acceptance entries are 2026-08-17 MEASUREMENT NOTES,
not given/when/then criteria -- they describe what a prior sweep found
missing, not a testable claim this ticket's own work can resolve with
pytest evidence. Direct code reading before any work started this round
found their premise stale in frob's favor: ADAPTER_CAPABILITIES /
derive_capability_registry (src/frob/lang/_support.py, T-2365) and
LANG004 / capability_conformance_gate (src/frob/gates/_lang_
conformance.py, T-2365) both already existed -- built before this
ticket's own filing predates them, contradicting criteria [1]/[2]'s own
"no facet or registry exists" / "conformance suite does not exist"
claims. Amending rather than binding evidence to a false premise, per
the coordinator's explicit instruction not to bind evidence to a
criterion it does not actually prove.
; logan, 2026-08-19)
- [2] replace: "MEASURED 2026-08-17: deliverable 2 (a conformance test suite parameterized over every registered adapter, failing when a language declares a capability it does not implement) does not exist -- tests/test_lang_support.py and tests/test_lang_conformance_gate.py test the EXISTING facet-registry-derivation and gate logic (does a registry entry exist), not adapter BEHAVIOR against a capability declaration. This remains real, unbuilt work, and is the load-bearing gap for the epic's stated purpose (batch-adding 20-50 languages safely)." -> 'GIVEN LANG004\'s behavioral conformance suite (capability_conformance_gate, src/frob/gates/_lang_conformance.py, built under T-2365 -- this criterion\'s own prior claim that it "does not exist" was already false before this ticket\'s work started), WHEN a registered language\'s capability cell is IMPLEMENTED for symbol_walk/publicness/doc_extract/directive_parse/call_graph/import_graph (6 of the 7 axis members; test_discovery remains disclosed structural-only, filed T-2682), THEN _behavioral_capability_check actually exercises it against a real per-language fixture and the parameterized suite (tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck) passes for every such cell -- this ticket\'s real, delivered work: extending that suite\'s own coverage from 4/7 to 6/7 capabilities (call_graph, import_graph newly added this round).' (reason: The three original acceptance entries are 2026-08-17 MEASUREMENT NOTES,
not given/when/then criteria -- they describe what a prior sweep found
missing, not a testable claim this ticket's own work can resolve with
pytest evidence. Direct code reading before any work started this round
found their premise stale in frob's favor: ADAPTER_CAPABILITIES /
derive_capability_registry (src/frob/lang/_support.py, T-2365) and
LANG004 / capability_conformance_gate (src/frob/gates/_lang_
conformance.py, T-2365) both already existed -- built before this
ticket's own filing predates them, contradicting criteria [1]/[2]'s own
"no facet or registry exists" / "conformance suite does not exist"
claims. Amending rather than binding evidence to a false premise, per
the coordinator's explicit instruction not to bind evidence to a
criterion it does not actually prove.
; logan, 2026-08-19)
- [1] remove: removed 'MEASUREMENT NOTE, superseded: this criterion\'s own premise ("No facet or registry for [the adapter-capability] axis exists today") was already false by the time this ticket\'s own scoping work started -- ADAPTER_CAPABILITIES/CapabilityRequirement/CapabilityStatus/AdapterCapabilitySupport/derive_capability_registry (src/frob/lang/_support.py) already give every registered language a typed cell for all seven capabilities this criterion names, built under T-2365. Not this ticket\'s own work; found already built during reconnaissance and confirmed by direct code reading before writing anything.' (reason: Not testable given/when/then criteria -- both are 2026-08-17
MEASUREMENT NOTES whose own premises this ticket's reconnaissance found
already false before any work started (ADAPTER_CAPABILITIES/
derive_capability_registry and LANG004/capability_conformance_gate
were already built under T-2365, not by this ticket). No pytest
evidence id can honestly "resolve" a negative-existence claim about
prior work this ticket did not do. The one criterion that IS this
ticket's own real, testable, delivered claim (LANG004's behavioral
coverage extended 4/7 -> 6/7) is retained as acceptance[2] (now [0]
after this removal) and bound to real evidence. Superseding text is
preserved in each removed criterion's own amendment history (both were
already amended in place before this removal, recording exactly why
their premise was stale) plus the ticket body's own rescope note.
; logan, 2026-08-19)
- [0] remove: removed "MEASUREMENT NOTE, superseded (T-1599 own investigation, this round): ADAPTER_CAPABILITIES/derive_capability_registry (src/frob/lang/_support.py) and LANG004 capability_conformance_gate (src/frob/gates/_lang_conformance.py) were already built under T-2365, before this ticket's own scoping work started, and LANG004 was already wired into frob check's job table (T-2411, done). This ticket's real remaining scope, confirmed against that live state rather than this stale note: extend LANG004's behavioral coverage and write the OPTIONAL-capability degradation story (see criterion [2])." (reason: Not testable given/when/then criteria -- both are 2026-08-17
MEASUREMENT NOTES whose own premises this ticket's reconnaissance found
already false before any work started (ADAPTER_CAPABILITIES/
derive_capability_registry and LANG004/capability_conformance_gate
were already built under T-2365, not by this ticket). No pytest
evidence id can honestly "resolve" a negative-existence claim about
prior work this ticket did not do. The one criterion that IS this
ticket's own real, testable, delivered claim (LANG004's behavioral
coverage extended 4/7 -> 6/7) is retained as acceptance[2] (now [0]
after this removal) and bound to real evidence. Superseding text is
preserved in each removed criterion's own amendment history (both were
already amended in place before this removal, recording exactly why
their premise was stale) plus the ticket body's own rescope note.
; logan, 2026-08-19)
