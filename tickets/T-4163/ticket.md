---
id: T-4163
title: 'eight ubuntu failures after the self-gate batch: a new gate, rule literal,
  package and exports were added without reaching the registries that enumerate them'
state: in-progress
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- src/frob/gates/_bare_toolchain.py
- src/frob/gates/__init__.py
- src/frob/gates/_package_audit*.py
- src/frob/check/__init__.py
- src/frob/vet/__init__.py
- src/frob/process/_project_tool.py
- src/frob/gates/_rule_id_scan.py
- tests/unit/test_project_tool.py
- docs/design/registry/check-coverage.yaml
- docs/modules/lang.md
- docs/modules/process.md
- src/frob/lang/_support.py
scope_breadth_ack: true
scope_breadth_ack_reason: T-4163 must touch src/frob/gates/_waive.py, src/frob/gates/__init__.py,
  and src/frob/check/__init__.py to register a new gate rule id -- these are foundational,
  hundreds-of-symbols files whose SCOPE002 doc/test closure pulls in a large, pre-existing
  and unrelated set of docs (docs/commands/check.md, docs/modules/app.md, docs/modules/perf.md,
  docs/modules/release.md, docs/modules/serve.md, docs/modules/gates.md) and source
  files that this ticket does not touch or intend to own; expanding scope to cover
  them would misrepresent this ticket's actual footprint
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: register BARETOOL001 in known-rules, package audit, exports, stage groups;
    fix advisory exit-code
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/gates/_bare_toolchain.py
  reason: register BARETOOL001 in known-rules, package audit, exports, stage groups;
    fix advisory exit-code
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/gates/__init__.py
  reason: register BARETOOL001 in known-rules, package audit, exports, stage groups;
    fix advisory exit-code
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/gates/_package_audit*.py
  reason: register BARETOOL001 in known-rules, package audit, exports, stage groups;
    fix advisory exit-code
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/vet/**
  reason: register BARETOOL001 in known-rules, package audit, exports, stage groups;
    fix advisory exit-code
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/check/__init__.py
  reason: register BARETOOL001 in known-rules, package audit, exports, stage groups;
    fix advisory exit-code
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: src/frob/vet/**
  reason: narrow to the one file needing the new re-export
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/vet/__init__.py
  reason: narrow to the one file needing the new re-export
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/process/_project_tool.py
  reason: uv run --project side-effect creates untracked uv.lock in target repo, tripping
    PRE001/SCOPE001 on a clean check
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/gates/_rule_id_scan.py
  reason: name every gate-registration list in GATERULE001's message; document the
    registration surface and single-point-of-registration decision
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/modules/gates.md
  reason: name every gate-registration list in GATERULE001's message; document the
    registration surface and single-point-of-registration decision
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/test_project_tool.py
  reason: shape test updated for --no-sync
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: docs/modules/gates.md
  reason: scoping the whole shared doc file pulls every symbol documenting into it
    into SCOPE002 -- narrower than intended, reverting; the new section rides along
    on the code-file scope instead
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: docs touched to satisfy AFFECT001/DOCENUM001, registry synced for BARETOOL001,
    package-audit registration
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/modules/lang.md
  reason: docs touched to satisfy AFFECT001/DOCENUM001, registry synced for BARETOOL001,
    package-audit registration
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/modules/process.md
  reason: docs touched to satisfy AFFECT001/DOCENUM001, registry synced for BARETOOL001,
    package-audit registration
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/lang/_support.py
  reason: docs touched to satisfy AFFECT001/DOCENUM001, registry synced for BARETOOL001,
    package-audit registration
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: docs touched to satisfy AFFECT001/DOCENUM001, registry synced for BARETOOL001,
    package-audit registration
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/modules/lang.md
  reason: docs touched to satisfy AFFECT001/DOCENUM001, registry synced for BARETOOL001,
    package-audit registration
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/modules/process.md
  reason: docs touched to satisfy AFFECT001/DOCENUM001, registry synced for BARETOOL001,
    package-audit registration
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/lang/_support.py
  reason: docs touched to satisfy AFFECT001/DOCENUM001, registry synced for BARETOOL001,
    package-audit registration
  actor: logan
  at: '2026-09-07'
designated_repro_test: null
acceptance:
- text: given a gate rule literal added without registering it, when a check runs,
    then it fails with a message naming every list the rule must appear in
  evidence: []
- text: given the previously green ubuntu suite, when it runs after this fix, then
    it reports zero failures
  evidence: []
- text: given a check run while another check runs on the same host, when it completes,
    then it exits zero and the concurrency advisory is still printed
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
EIGHT UBUNTU FAILURES AFTER THE SELF-GATE BATCH LANDED, on a tree whose suite was
GREEN one run earlier (13610 collected, 0 failed). CI run 34102812243:
collected=13639, failed=8. Six are the same class; two were mine and are already
fixed; one is not a real failure at all.

SIX ARE "A NEW THING WAS ADDED AND NOT REGISTERED WHERE THE REGISTRIES ENUMERATE
IT". Every one names its own remedy:

    rule id constructed but missing from the known-rules set:
      BARETOOL001 at src/frob/gates/_bare_toolchain.py:79
    package audit: source tree not fully registered
      ('frob.process',) expected ()
    exports policy residue: missing symbols
      src/frob/vet -> vet._bare_toolchain.bare_toolchain_findings,
                      vet._bare_toolchain.BareToolchainFinding
    stage groups do not cover every gate and tool
      (a frozenset comparison of stage coverage against the gate set)
    frob check on a CLEAN project exits 1 with 2 errors
    frob check unaffected-when-no-strata-files

This is the producer/validator desync class again, and it is the SECOND time in
this session that landing work broke CI in exactly this shape. The earlier
instance was test doubles drifting from their producers; this one is new modules
and a new rule not reaching the registries that enumerate them. The common
property is that the addition is correct in isolation and incomplete against a
list somewhere else.

NOTE THE IRONY WORTH LEARNING FROM: the new rule that did not get registered is
BARETOOL001, and T-4146 existed specifically because that gate had been written
and not wired into the job registry. It got wired -- and its rule LITERAL still
did not reach the known-rules set. One registry was found; the others were not.
The lesson is not "remember the registries", it is that a new gate must be
impossible to add without satisfying every list that claims to enumerate gates.
Determine how many such lists exist and report the number; that count IS the
finding.

TWO OF THE EIGHT WERE MY OWN TICKET PROSE AND ARE ALREADY FIXED. Two DOC006
errors fired on ticket bodies I wrote in this batch, because I quoted a
consumer's file path and an illustrative example path in path syntax, and both
parsed as live pointers into THIS repository where neither resolves. That is the
exact rule this repo already carries -- a thing that does not exist here is named
in prose, never in its native syntax -- and I broke it twice in one session. Both
bodies are rewritten. They are recorded here so the count reconciles, not as work.

ONE IS NOT A FAILURE AT ALL AND MUST NOT BE "FIXED":

    frob check: 1 other check(s) already running on this host -- see
    fleet_status.py for swap/load before dispatching more (advisory only)

A test asserting a clean exit got a non-zero exit because an ADVISORY concurrency
notice was emitted while another check ran on the same machine. That is the test
observing the fleet, not the code. It belongs with the other self-scan
contamination already recorded: a local or concurrent-load result is evidence
about the machine, not the repository. Decide whether the advisory should affect
the exit code at all -- I suspect it should not, and if so THAT is the real defect
here rather than the test.

WHAT TO DO
  1. Register BARETOOL001 in the known-rules set, the new package in the package
     audit, the new vet symbols in the exports policy, and the new gate in the
     stage groups. The failure messages name each remedy precisely.
  2. Then answer the durable question: enumerate every list that claims to
     enumerate gates, rules, packages or exports, and report how many there are.
     A contributor adding a gate should not have to know that number.
  3. Decide whether the advisory concurrency notice should influence an exit code.
     If not, fix that rather than the test.
  4. Re-run the affected modules and confirm the clean-project check exits zero.

MUST-FIRE FIXTURE:   adding a gate rule literal without registering it fails a
                     check locally, with a message naming every list it must
                     appear in.
MUST-STAY-QUIET:     the previously green suite returns to zero failures.
THIRD FIXTURE:       a check run while another check runs on the same host exits
                     zero, with the advisory still printed.

ACCEPTANCE
- All six registration failures cleared at their named remedies.
- The number of enumerating lists reported, and a single point of registration
  proposed or the reason one is impractical recorded.
- The advisory-versus-exit-code question decided, and the test not weakened to
  accommodate a wrong answer.
- All three fixtures committed.
