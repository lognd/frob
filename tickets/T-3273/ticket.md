---
id: T-3273
title: 'frob.toml boilerplate: seven *_schema tables exist only to name frob''s own
  internal constants, and omitting them silently reports UNMEASURED'
state: done
kind: feature
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/shared/python/frob.toml.j2
- src/frob/gates/_arch_schema.py
- src/frob/gates/_docblocks_schema.py
- src/frob/gates/_dup_graph_schema.py
- src/frob/gates/_gates_schema.py
- src/frob/gates/_native_schema.py
- src/frob/gates/_profile_schema.py
- src/frob/gates/_refs_schema.py
- src/frob/gates/_test_runner_schema.py
- src/frob/gates/_testing_schema.py
- src/frob/gates/_toplevel_scalar_schema.py
- docs/modules/gates.md
- tests/unit/test_arch_table_schema.py
- tests/unit/test_docblocks_table_schema.py
- tests/unit/test_dup_graph_table_schema.py
- tests/unit/test_gates_table_schema.py
- tests/unit/test_native_table_schema.py
- tests/unit/test_profile_table_schema.py
- tests/unit/test_refs_schema.py
- tests/unit/test_test_table_schema.py
- tests/unit/test_testing_table_schema.py
- tests/unit/test_toplevel_scalar_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_arch_schema.py
  reason: 'T-3273''s actual fix: default each *_schema table''s known_keys internally
    when undeclared, resolved in the gate modules themselves, not just the scaffold
    template that references them'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_docblocks_schema.py
  reason: 'T-3273''s actual fix: default each *_schema table''s known_keys internally
    when undeclared, resolved in the gate modules themselves, not just the scaffold
    template that references them'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_dup_graph_schema.py
  reason: 'T-3273''s actual fix: default each *_schema table''s known_keys internally
    when undeclared, resolved in the gate modules themselves, not just the scaffold
    template that references them'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_gates_schema.py
  reason: 'T-3273''s actual fix: default each *_schema table''s known_keys internally
    when undeclared, resolved in the gate modules themselves, not just the scaffold
    template that references them'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_native_schema.py
  reason: 'T-3273''s actual fix: default each *_schema table''s known_keys internally
    when undeclared, resolved in the gate modules themselves, not just the scaffold
    template that references them'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_profile_schema.py
  reason: 'T-3273''s actual fix: default each *_schema table''s known_keys internally
    when undeclared, resolved in the gate modules themselves, not just the scaffold
    template that references them'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_refs_schema.py
  reason: 'T-3273''s actual fix: default each *_schema table''s known_keys internally
    when undeclared, resolved in the gate modules themselves, not just the scaffold
    template that references them'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_test_runner_schema.py
  reason: 'T-3273''s actual fix: default each *_schema table''s known_keys internally
    when undeclared, resolved in the gate modules themselves, not just the scaffold
    template that references them'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_testing_schema.py
  reason: 'T-3273''s actual fix: default each *_schema table''s known_keys internally
    when undeclared, resolved in the gate modules themselves, not just the scaffold
    template that references them'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_toplevel_scalar_schema.py
  reason: 'T-3273''s actual fix: default each *_schema table''s known_keys internally
    when undeclared, resolved in the gate modules themselves, not just the scaffold
    template that references them'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-3273''s actual fix: default each *_schema table''s known_keys internally
    when undeclared, resolved in the gate modules themselves, not just the scaffold
    template that references them'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_arch_table_schema.py
  reason: existing 'no schema declared' fixtures assert UNRESOLVED, which T-3273 changes
    to MEASURED-with-defaults; must update in the same change
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_docblocks_table_schema.py
  reason: existing 'no schema declared' fixtures assert UNRESOLVED, which T-3273 changes
    to MEASURED-with-defaults; must update in the same change
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_dup_graph_table_schema.py
  reason: existing 'no schema declared' fixtures assert UNRESOLVED, which T-3273 changes
    to MEASURED-with-defaults; must update in the same change
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_gates_table_schema.py
  reason: existing 'no schema declared' fixtures assert UNRESOLVED, which T-3273 changes
    to MEASURED-with-defaults; must update in the same change
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_native_table_schema.py
  reason: existing 'no schema declared' fixtures assert UNRESOLVED, which T-3273 changes
    to MEASURED-with-defaults; must update in the same change
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_profile_table_schema.py
  reason: existing 'no schema declared' fixtures assert UNRESOLVED, which T-3273 changes
    to MEASURED-with-defaults; must update in the same change
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_refs_schema.py
  reason: existing 'no schema declared' fixtures assert UNRESOLVED, which T-3273 changes
    to MEASURED-with-defaults; must update in the same change
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_test_table_schema.py
  reason: existing 'no schema declared' fixtures assert UNRESOLVED, which T-3273 changes
    to MEASURED-with-defaults; must update in the same change
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_testing_table_schema.py
  reason: existing 'no schema declared' fixtures assert UNRESOLVED, which T-3273 changes
    to MEASURED-with-defaults; must update in the same change
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_toplevel_scalar_schema.py
  reason: existing 'no schema declared' fixtures assert UNRESOLVED, which T-3273 changes
    to MEASURED-with-defaults; must update in the same change
  actor: logan
  at: '2026-08-28'
evidence:
- tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_no_schema_declared_defaults_to_frobs_own_keys_must_fire
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER OBSERVATION 2026-08-28, from first real use of frob in a new repo
(../diax): "there's a lot of boilerplate in frob.toml".

MEASURED. The scaffold template
`src/frob/scaffold/data/shared/python/frob.toml.j2` is 24 lines. The frob.toml
a working consumer repo actually needs is 160 lines. Most of the difference is
this shape, repeated once per gate family:

    [toplevel_scalar_schema]
    known_keys = "frob.gates._toplevel_scalar_schema:TOPLEVEL_SCALAR_KNOWN_KEYS"

    [dup_schema]
    known_keys = "frob.gates._dup_graph_schema:DUP_KNOWN_KEYS"

    [graph_schema]
    known_keys = "frob.gates._dup_graph_schema:GRAPH_KNOWN_KEYS"

    [arch_schema]
    known_keys = "frob.gates._arch_schema:arch_known_keys"

    [docblocks_schema]
    known_keys = "frob.gates._docblocks_schema:DOCBLOCKS_COMMAND_KNOWN_KEYS"

    [testing_schema]
    known_keys = "frob.gates._testing_schema:testing_known_keys"

    [test_runner_schema]
    ...

THE POINT: every one of those values is a path to FROB'S OWN INTERNAL
CONSTANT, resolved inside frob's own process. There is no project-specific
decision in any of them. A consumer repo is being asked to copy frob's private
module layout into its configuration file, and if it does not, the *SCHEMA001
gates report the project as UNMEASURED rather than clean.

That is the worst of both worlds. It is boilerplate that cannot be reasoned
about by the person writing it, AND its absence produces a silent
non-measurement rather than an error -- this project's dominant defect class,
in the default configuration of every new repo.

It also couples every consumer's config to frob's internal module paths. Any
refactor that moves `frob.gates._arch_schema` breaks every downstream repo's
frob.toml, and the breakage surfaces as UNMEASURED, not as an import error.

WHAT TO BUILD:
  1. These known-key sets should be the DEFAULT, resolved internally, with no
     declaration required. A repo that says nothing gets frob's own constants
     and is MEASURED.
  2. Keep the override. A consumer with a genuine reason to declare a
     different key set must still be able to; this is about the default, not
     about removing the knob.
  3. Then shrink the scaffold template to what a project actually has to
     decide -- check_base, profile, test runner, testing thresholds. State
     what you kept and why each survivor is a real decision rather than a
     default.

CHECK THE WHOLE TABLE, DO NOT FIX ONLY THE SEVEN ABOVE. Enumerate every
frob.toml table whose only content is a pointer into frob's own internals, and
report the count. Some may have real per-project meaning; say which and why.

DO NOT FIX THIS BY MAKING THE GATES SILENT WHEN UNDECLARED. UNMEASURED exists
so a missing key set is visible. The fix is that the default is correct, not
that the absence stops being reported.

MUST-FIRE FIXTURE: a repo declaring nothing is MEASURED, with frob's own key
sets in effect.
MUST-STAY-QUIET FIXTURE: a repo declaring its own known_keys still gets its
own, overriding the default.
THIRD FIXTURE: a repo declaring a BROKEN pointer still reports loudly rather
than silently falling back to the default -- a typo must not be indistinguishable
from an intentional omission.

ACCEPTANCE
- A stated count of the tables that became defaultable, and of any that did not
  with the reason.
- The scaffold template regenerated; state its new line count versus 24 today
  and versus the 160 a working repo needed.
- Docs updated in the same change.