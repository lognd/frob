---
id: T-draft-2b8e73e2
title: 'T-3350''s land left frob.nodeid outside the design model: 3 SYS003, SYS102,
  2 TEST001, 1 WIRE002 all reproduce on main'
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/nodeid.py
- design/frob.strata
- src/frob/lang/_extract.py
- src/frob/lang/__init__.py
- src/frob/gates/__init__.py
- src/frob/tickets/_scope_coverage.py
- tests/unit/test_extract_import_edges.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: removed the alias-to-old-private-name import so WIRE001 attribution is real,
    not waived; added unit tests for extract_import_edges
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_scope_coverage.py
  reason: removed the alias-to-old-private-name import so WIRE001 attribution is real,
    not waived; added unit tests for extract_import_edges
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_extract_import_edges.py
  reason: removed the alias-to-old-private-name import so WIRE001 attribution is real,
    not waived; added unit tests for extract_import_edges
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3350's land (a07433b72) introduced six gate findings that all REPRODUCE on
main. They were not caught pre-land because deferred verification was on, so
they surfaced only when the post-land quarantine batch was triaged.

MEASURED on main 2026-08-29, caches cleared (--no-cache), no REPLAY:

  SYS003 x3 -- undeclared cross-component import of the new `frob.nodeid`:
      src/frob/gates/__init__.py:284        (gates -> __foreign__)
      src/frob/tickets/_scope_coverage.py:4 (tickets_ledger -> __foreign__)
      tests/unit/test_nodeid.py:11          (testsuite -> __foreign__)
  SELFAUDIT001 SYS102 -- src/frob/nodeid.py has no node's code= glob binding it
  TEST001 x2 -- the new public API has no unit test:
      src/frob/lang/__init__.py:1090::extract_import_edges
      src/frob/lang/_extract.py:538::extract_import_edges
  WIRE002 -- src/frob/nodeid.py:25, the `frob:waive WIRE001` on
      symref_to_nodeid is missing `follow_up="T-####"`; a WIRE001 waiver must
      bind to a real, open follow-up ticket

ROOT CAUSE OF THE CLUSTER, and it is one thing, not six. Creating
`src/frob/nodeid.py` added a new module to the tree without adding it to the
DESIGN MODEL. The design model is what SYS003 checks imports against and what
SYS102 checks file placement against, so a module that exists in the filesystem
but not in the model is `__foreign__` to every component that imports it. The
extraction itself was correct and was exactly what the ticket asked for -- the
gap is that a new leaf module is a design-model change, not only a code change.

THE FIX IS A DECISION, SO MAKE IT EXPLICITLY. Either:
  (a) declare `frob.nodeid` as its own node in the design model, with the Flows
      that let `gates`, `tickets_ledger` and `testsuite` import it; or
  (b) place the symbol inside an existing component that all three may already
      reach, which may mean the extraction target was wrong.
(a) is probably right -- a dependency-free string helper shared by three
components is the textbook shared-leaf -- but say why, because (b) would mean
undoing part of the extraction and that is worth ruling out deliberately rather
than by default.

TEST001 is straightforward and non-negotiable: `extract_import_edges` is the new
public API this whole fix rests on, and it currently has no unit test. It is
also the exact function whose correctness determines whether CYCLE001 counts an
edge, so it needs tests of its own regardless of the system-level positive
controls already committed in tests/system/test_cli_cycle.py. Test the
import_time flag directly: module-level import, function-local import, class-
body import, `if TYPE_CHECKING:` import, module-level import inside
try/except ImportError (which IS import-time), and a conditional
`if sys.version_info` import at module level (also import-time).

WIRE002 wants a real open follow-up ticket id on the WIRE001 waiver. Do not
invent one or point it at a closed ticket; if the waiver is genuinely permanent
then WIRE001 may be the wrong mechanism and a different discharge is needed.

WHAT THIS IS NOT: this is not a reason to revert T-3350. That land fixed a real
detector defect, collapsed four genuine cycles, and committed positive-control
fixtures. This ticket finishes the accounting the land left open.

ACCEPTANCE
- All six findings measured absent on main after the fix, caches cleared, no
  REPLAY, with the before/after numbers stated.
- The (a)-vs-(b) design choice stated with reasoning.
- extract_import_edges unit tests covering all six import shapes listed above.
