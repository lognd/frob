---
id: T-1916
title: 'REG002 red on main: CHK-GATE-SYS-IFACE-ORDER claims an enforced gate rule,
  but SYS-IFACE-ORDER is only a Tier-A auto-fix handler'
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine.py
- src/frob/gates/_fix_engine_sync.py
- docs/design/registry/check-coverage.yaml
- docs/strata/surface.md
- tests/unit/gates/test_sys_interface_canonical_order.py
- tests/test_registry_exhaustiveness.py
- tests/test_check_coverage_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: 'T-1916: retire the unbacked SYS-IFACE-ORDER Tier-A handler + registry row'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: 'T-1916: retire the unbacked SYS-IFACE-ORDER Tier-A handler + registry row'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'T-1916: retire the unbacked SYS-IFACE-ORDER Tier-A handler + registry row'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: docs/strata/surface.md
  reason: 'T-1916: retire the unbacked SYS-IFACE-ORDER Tier-A handler + registry row'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/gates/test_sys_interface_canonical_order.py
  reason: 'T-1916: retire the unbacked SYS-IFACE-ORDER Tier-A handler + registry row'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: 'T-1916: retire the unbacked SYS-IFACE-ORDER Tier-A handler + registry row'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_check_coverage_registry.py
  reason: 'T-1916: retire the unbacked SYS-IFACE-ORDER Tier-A handler + registry row'
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
designated_repro_test: null
acceptance:
- text: uv run frob check --only registry reports 0 errors on main
  evidence:
  - tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
- text: The resolution is justified by what SYS-IFACE-ORDER actually is -- either
    a real detector rule exists, or the handler and row are retired together with
    reasoning; not a row deletion to go green
  evidence:
  - tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
- text: A test proves a registry row dispositioned handled_by against an id that resolves
    ONLY to a Tier-A fix handler (no gate/policy rule) is reported by REG002; it must
    fail before the fix
  evidence:
  - tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails
- text: Re-measure --only registry unscoped after landing; the pre-existing REG008/REG011
    warnings are out of scope but must not increase
  evidence:
  - tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails
  - tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED on main at 2675e8c56, 2026-08-09:

    uv run frob check --only registry  ->  1 error
    [gate:REG] docs/design/registry/check-coverage.yaml:0 REG002
    CHK-GATE-SYS-IFACE-ORDER disposition handled_by:SYS-IFACE-ORDER names
    a rule that does not exist in the live gate/policy rule registry --
    dangling enforcement reference

The error floor on main is NOT zero. Every agent running a scoped
registry check sees a red it did not cause, which trains agents to
ignore REG output -- the exact harm T-1890 was filed about.

DO NOT ASSUME THIS IS A DANGLING CITATION. It is not the T-1890/T-1888
shape, and deleting the row would be wrong. MEASURED:

    git grep -n "SYS-IFACE-ORDER" -- src/
    src/frob/gates/_fix_engine.py:542       "SYS-IFACE-ORDER": (...)
    src/frob/gates/_fix_engine_sync.py:1096 rule="SYS-IFACE-ORDER"

SYS-IFACE-ORDER EXISTS and is live. It is a Tier-A deterministic
auto-fix HANDLER (T-1872 added it). What does not exist is a gate/policy
RULE of that id. The registry row at check-coverage.yaml:1490 asserts
name: "SYS-IFACE-ORDER is a live, enforced gate rule" -- and that
assertion is false. A fix handler rewrites interface= ordering; no
detector CHECKS the ordering.

HYPOTHESIS, CONFIRM BEFORE FIXING: T-1870 deleted SYS104 (the
bidirectional interface=-equals-real-surface mirror check) per an
explicit owner directive that no code path may auto-update declared
public-symbol surface. That deletion removed the detector while leaving
the Tier-A auto-fix handler in place, so the codebase now MUTATES
interface= ordering on land with nothing gating it. If true, the REG002
error is a correct report of a genuine enforcement hole, not a
bookkeeping wart.

Note the standing owner directive constrains the fix: no code path may
auto-update declared public-symbol surface. If the honest resolution is
that the auto-fix handler should not exist either, say so with evidence
rather than adding a detector that re-creates the mirror check T-1870
deliberately removed.

WHY THIS IS FILED SEPARATELY. T-1888 landed the same-class fix at
ffe3dfd774eb by removing the CHK-GATE-SYS104 row, and T-1890 was dropped
as its duplicate. Both treated ONE dangling instance. The sibling row
from the same T-1870 deletion was left behind and reds main today. The
fix here must address the CLASS: after it lands, no registry row may
claim handled_by against an id that is only a fix handler.

Also worth recording: T-1888 is a done bug ticket whose done-report
reads "### Evidence (no evidence recorded)". A bug closed with no
evidence is how this survived.

ACCEPTANCE
1. `uv run frob check --only registry` reports 0 errors on main.
2. The resolution is justified by what SYS-IFACE-ORDER actually is --
   either a real detector rule exists, or the handler and row are
   retired together with reasoning. Not a row deletion to go green.
3. A test proves a registry row dispositioned handled_by against an id
   that resolves ONLY to a Tier-A fix handler (no gate/policy rule) is
   reported by REG002. It must fail before the fix.
4. Re-measure `--only registry` unscoped after landing; the 7 REG008/
   REG011 warnings are out of scope but must not increase.

## Done report

REG002 was red because docs/design/registry/check-coverage.yaml's
CHK-GATE-SYS-IFACE-ORDER row asserted "SYS-IFACE-ORDER is a live,
enforced gate rule" (disposition handled_by:SYS-IFACE-ORDER) while
SYS-IFACE-ORDER only ever existed as a Tier-A auto-fix handler
(fix_sys_interface_canonical_order, T-1872) -- confirmed absent from
frob.gates._waive._KNOWN_GATE_RULES and from frob.gates.
_KNOWN_RULE_FIXABILITY (grep across src/ and both known-rule registries
before making any change).

Checked the hypothesis in the ticket body directly: every OTHER id in
TIER_A_HANDLERS is backed by a real detector somewhere -- REG010/DOC002/
FMT001/COV002/TICK002/TICK006/REL002/SUPPRESS001/SYS100 all appear as
`rule="<ID>"` in a real gate/audit module outside the fix-engine files
(SYS100's detector lives in frob.strata._selfconform, the SYS100/SYS108
detector-in-strata/fixer-in-gates split); E501 is checked by ruff itself.
SYS-IFACE-ORDER was the one exception: a code path silently mutating a
design/*.strata file's declared interface= presentation on every `frob
ticket land`, with zero detector a human could see, waive, or
investigate first.

Building the missing detector properly would mean sharing the ~150 lines
of parsing/kind-resolution logic this handler already carries (bind_code,
_node_symbol_kinds, _iface_find_spans, _canonical_interface_key) with a
NEW self-conformance rule following the SYS100/SYS108 detector/fixer
split, wired into check_self_conformance's existing SYS100-108 pipeline,
plus new entries in _KNOWN_GATE_RULES/_KNOWN_RULE_FIXABILITY and new
waiver/doc/test coverage. That is a genuine new feature, not a bug fix,
and it multiplies the exact class of machinery (auto-mutating design/
interface= presentation with no prior human-visible signal) the standing
owner directive already ruled out once for the membership side of the
same attribute (T-1870). Retiring the handler and the false row together
is the narrower, more consistent fix -- explicitly permitted by the
ticket's acceptance criterion 2 -- and it does not touch the T-1872
land-time Tier-A absorption machinery itself (data-driven off
TIER_A_HANDLERS, unaffected by removing one entry).

Retired together:
- src/frob/gates/_fix_engine.py: TIER_A_HANDLERS["SYS-IFACE-ORDER"] entry
  + the now-dead import, with the retirement reasoning recorded in the
  comment block above TIER_A_HANDLERS.
- src/frob/gates/_fix_engine_sync.py: the whole SYS-interface-canonical-
  order section (_IFACE_* regexes/constants, _iface_find_spans,
  _node_symbol_kinds, _canonical_interface_key, _render_interface_block,
  _reorder_node_interface_block, _iface_rewrite_parses,
  _reorder_iface_one_file, fix_sys_interface_canonical_order) plus the
  now-unused `ast`/`Counter` imports; retirement reasoning added to the
  module docstring.
- docs/design/registry/check-coverage.yaml: CHK-GATE-SYS-IFACE-ORDER row
  deleted, gate_rule_total 294 -> 293 (matches the real gate_rule_entries
  count).
- docs/strata/surface.md: the T-1872 section rewritten to record the
  retirement (kept, not deleted -- explains what the handler was and why
  it is gone, per the playbook's "a disclosed cut with no record is a
  finding" posture).
- tests/unit/gates/test_sys_interface_canonical_order.py: deleted (tested
  only the removed handler; confirmed no other file imports from it).
- tests/test_registry_exhaustiveness.py: added
  TestDisposition.test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails
  (acceptance criterion 3) -- asserts SYS-IFACE-ORDER is absent from the
  REAL production known_gate_rule_ids() (so this can't silently
  regress) and that a synthetic handled_by:SYS-IFACE-ORDER row is
  reported by REG002 against the real known-rules set.

Side effect (not separately scoped, not touched beyond what removing the
dict entry naturally fixed): tests/test_gates.py::TestFixEngineTierABatch2
.test_tier_a_handlers_dict_covers_every_batch_rule was ALREADY red on
main (its hardcoded expected set never included "SYS-IFACE-ORDER", so
main's TIER_A_HANDLERS containing that key already failed it) --
removing the key makes the dict match the test's pre-existing expected
set again, with no edit to the test needed. Measured directly: red on
main, green in this worktree.

Pre-existing, unrelated red confirmed NOT caused or touched by this
ticket: tests/test_registry_exhaustiveness.py::
TestCheckCoverageReg008BurnDown.test_no_reg008_findings_for_check_coverage_yaml
fails identically on main and in this worktree (9 violations on main,
7 here after this fix -- the assertion itself, that check-coverage.yaml
carries zero REG008 findings, was already false on main against
PERF012/TEST018/SYS108/INV051/GITIGNORED-TRUST, none of which this
ticket's scope touches). Left alone; out of scope.

Fail-then-pass proof (acceptance 3), read directly:
- On main: tests/test_check_coverage_registry.py::
  TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
  FAILS -- AssertionError: assert 294 == 293 (293 = len(known_gate_rule_ids())
  on main too, since SYS-IFACE-ORDER was never registered there either;
  294 = the check-coverage.yaml row count including the false row).
- In this worktree (fix applied): same test PASSES.

Measured `uv run frob check --only registry` in this worktree: 0 errors,
6 warnings (was 7 REG008/REG011 warnings on main -- decreased by one,
since the retired row itself no longer needs a frob:enforces edge to
avoid a REG008 candidate; does not increase per acceptance 4).

### Changed
```
 tickets/T-1916/ticket.md | 66 +++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 65 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 8 error(s), 968 warning(s), 696 waived
- error-findings: COV003@tickets/T-1872, COV003@tickets/T-1895, COV003@tickets/T-1896, COV003@tickets/T-1900, COV003@tickets/T-1906, F401@/home/logan/projects/frob/.claude/worktrees/reg-enforce/src/frob/gates/_fix_engine_sync.py, PARSE001@tests/unit/gates/test_sys_interface_canonical_order.py, PRE001@tickets/T-1916
