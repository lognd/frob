---
id: T-2369
title: Burn REF001/REF002 + REG008 WARN gates to zero, then promote to error
state: in-progress
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/test005-ratchet-schedule.md
- docs/index.md
- docs/investigations/T-2782-land-serialization.md
- docs/investigations/T-2790-check-stage-profile.md
- docs/investigations/T-2796-backlog-reproduction.md
- docs/modules/gates.md
- docs/modules/tickets-data-storage.md
- frob.toml
- src/frob/gates/_refs.py
- tests/test_refs_gate.py
- tests/unit/gates/test_refs.py
- src/frob/app/_check_chunking.py
- src/frob/app/check_runner.py
- src/frob/check/__init__.py
- src/frob/check/_python.py
- src/frob/deploy/_conform.py
- src/frob/gates/_exhaustive_handling.py
- src/frob/gates/_registry_exhaustiveness.py
- src/frob/gates/_sys_selfaudit.py
- src/frob/strata/_capacity.py
- src/frob/strata/_cve_fingerprint.py
- src/frob/strata/_selfconform.py
- tests/test_registry_exhaustiveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: rollup epic burning REF001/REF002/REG008 to zero then promoting
  WARN->error; batched per T-2359/T-2373/T-2370 precedent into child tickets, each
  with its own real scope
scope_changes:
- op: add
  glob: docs/design/test005-ratchet-schedule.md
  reason: REF001/REF002 systematic-cause collapse (glob entrypoints + doc fixes) +
    severity promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/index.md
  reason: REF001/REF002 systematic-cause collapse (glob entrypoints + doc fixes) +
    severity promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/investigations/T-2782-land-serialization.md
  reason: REF001/REF002 systematic-cause collapse (glob entrypoints + doc fixes) +
    severity promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/investigations/T-2790-check-stage-profile.md
  reason: REF001/REF002 systematic-cause collapse (glob entrypoints + doc fixes) +
    severity promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/investigations/T-2796-backlog-reproduction.md
  reason: REF001/REF002 systematic-cause collapse (glob entrypoints + doc fixes) +
    severity promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/modules/gates.md
  reason: REF001/REF002 systematic-cause collapse (glob entrypoints + doc fixes) +
    severity promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: REF001/REF002 systematic-cause collapse (glob entrypoints + doc fixes) +
    severity promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: frob.toml
  reason: REF001/REF002 systematic-cause collapse (glob entrypoints + doc fixes) +
    severity promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_refs.py
  reason: REF001/REF002 systematic-cause collapse (glob entrypoints + doc fixes) +
    severity promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/test_refs_gate.py
  reason: REF001/REF002 systematic-cause collapse (glob entrypoints + doc fixes) +
    severity promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/unit/gates/test_refs.py
  reason: REF001/REF002 systematic-cause collapse (glob entrypoints + doc fixes) +
    severity promotion
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/app/_check_chunking.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/app/check_runner.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/check/_python.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/deploy/_conform.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_exhaustive_handling.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_registry_exhaustiveness.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_sys_selfaudit.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/strata/_capacity.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/strata/_cve_fingerprint.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: 'REG008 burn-down (T-2369 remaining): add missing frob:enforces directive
    at each entry''s real violation-emitting function; DOC012''s site (src/frob/gates/_docblocks.py)
    excluded, live-leased by in-progress T-2359'
  actor: logan
  at: '2026-08-21'
evidence:
- tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_exempts_matching_files
- tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_does_not_exempt_non_matching_files
- tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity
designated_repro_test: null
acceptance:
- text: given the family's WARN codes, when frob check --json runs, then zero findings
    remain
  evidence:
  - tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_exempts_matching_files
  - tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_does_not_exempt_non_matching_files
  - tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity
- text: given the family's gate module, when its severity is read, then it is ERROR
    not WARNING
  evidence:
  - tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_exempts_matching_files
  - tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_does_not_exempt_non_matching_files
  - tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral) piped through `scripts/check_summary.py`, 2026-08-18.

WARN-tier finding count, this family (reference-integrity + registry-coverage checks): 37 across codes REF001, REF002, REG008.

Do NOT hand-count with grep -- this repo has measured false zeros that way, including
one tonight. Re-measure with the same command above before starting and before
claiming done; treat any disagreement with the number in this body as the tree
having moved, not as your measurement being wrong.

Closure is two-part per the epic (T-0969):
1. Zero findings for every code above, verified via the same
   `frob check --json --budget 500 | python3 scripts/check_summary.py` command.
2. Each code above promoted from warning to error severity in its gate module
   (grep the gate module for its severity constant/mapping) -- a burn-down that
   stops at zero and leaves the gate advisory lets the debt silently reaccumulate.
   DOC012 and the T-1662 arc both closed correctly today by doing both; follow
   that shape, not a zero-only burn-down.

Narrow `scope` to the actual files this family's findings live in once you've
run the gate and can see them -- do not take a broad blanket scope; this keeps
you disjoint from sibling children of T-0969.
