---
id: T-1872
title: 'Tier-A canonical ordering for interface= : group by resolved symbol kind,
  alphabetical within group, order-only'
state: done
kind: feature
origin: human
created: '2026-08-08'
priority: medium
blocked_by:
- T-1871
- T-1870
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine.py
- src/frob/gates/_fix_engine_sync.py
- docs/strata/surface.md
- tests/unit/gates/test_sys_interface_canonical_order.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/gates/test_sys_interface_canonical_order.py
  reason: T-1872 order-only Tier-A handler needs pytest evidence; test_gates.py is
    leased by T-1886 so a new dedicated test file is used instead
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_groups_by_kind_then_alpha
  new_node: tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails
  reason: 'T-1916 retired fix_sys_interface_canonical_order (SYS-IFACE-ORDER) entirely

    -- deleted the handler, its TIER_A_HANDLERS entry, and this ticket''s own

    evidence file tests/unit/gates/test_sys_interface_canonical_order.py --

    because the id was never backed by a real gate/policy rule (REG002 caught

    the registry''s false claim). The order-only canonical-interface behavior

    this evidence proved no longer exists anywhere on main; there is no

    surviving code path to re-point this evidence at. Rebinding to the

    regression guard that keeps SYS-IFACE-ORDER retired

    (tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails,

    added by T-1916 itself) rather than fabricating a replacement test for

    dead code or leaving COV003 permanently red. This is an explicit

    "evidence for removed behavior, retired alongside the code" case, not a

    renamed/relocated test.

    '
  actor: logan
  at: '2026-08-09'
- old_node: tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_order_only_multiset_preserved_and_idempotent
  new_node: tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails
  reason: 'T-1916 retired fix_sys_interface_canonical_order (SYS-IFACE-ORDER) entirely

    -- deleted the handler, its TIER_A_HANDLERS entry, and this ticket''s own

    evidence file tests/unit/gates/test_sys_interface_canonical_order.py --

    because the id was never backed by a real gate/policy rule (REG002 caught

    the registry''s false claim). The order-only canonical-interface behavior

    this evidence proved no longer exists anywhere on main; there is no

    surviving code path to re-point this evidence at. Rebinding to the

    regression guard that keeps SYS-IFACE-ORDER retired

    (tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails,

    added by T-1916 itself) rather than fabricating a replacement test for

    dead code or leaving COV003 permanently red. This is an explicit

    "evidence for removed behavior, retired alongside the code" case, not a

    renamed/relocated test.

    '
  actor: logan
  at: '2026-08-09'
threat: null
component: null
anchor: false
anchor_reason: null
---
OWNER DIRECTIVE, 2026-08-08: "a tier-A format fix should be alphabetizing
the interface (although splitting capital vs. non-capital to make parsing
functions vs. classes easier) in a canonical fashion."

WHY THIS IS NOT A REVIVAL OF sync-interface, and say so in the code. The
distinction is the whole point and a future reader WILL be tempted to
delete this as leftover auto-writing machinery:

- `sync-interface` (deleted by T-1870) DERIVED THE CONTENT: it measured
  the real public surface and wrote it in, so the declaration mirrored
  the code and could never disagree with it. That is accounting, and it
  is why it had to go.
- This handler REORDERS WHAT A HUMAN ALREADY DECLARED. It never consults
  the code to decide membership. Content stays hand-authored; only
  presentation is normalised, exactly like `frob fmt` or ruff-format.

THE LOAD-BEARING INVARIANT: order-only. The handler MUST NOT add an
entry, remove an entry, or dedup. Assert the multiset of values is
identical before and after, and fail the fix rather than write a
different set. Two reasons this is not paranoia:

1. Adding or removing entries is precisely the sync-interface behaviour
   the owner removed.
2. T-1871 makes a duplicate value a PARSE ERROR. A formatter that
   silently dedups would swallow the very error T-1871 exists to raise,
   and the two changes would quietly cancel out. Do not dedup. Ever.

ORDERING, and a genuine design question the implementer must resolve
before coding:

The directive says split capital from non-capital "to make parsing
functions vs. classes easier". Capitalisation is a LEXICAL proxy for
what is actually being asked -- symbol KIND. This repo's deepest standing
rule is SYMBOLIC NEVER LEXICAL (T-1662 is a critical epic devoted to it),
and frob already resolves these names against bound code, so it can know
that `Ticket` is a class and `land` is a function rather than inferring
it from a capital letter.

Preferred: group by RESOLVED SYMBOL KIND -- classes, then functions,
then constants -- alphabetised within each group.

Fallback when a name cannot be resolved: do NOT guess silently. Emit the
unresolved names as a trailing group in stable alphabetical order and
report that they were unresolved, honouring "cannot verify is never
verified". A formatter that quietly guesses is a formatter that lies
about what it knows.

Note that three casing classes exist in Python, not two: `CapWords`
classes, `snake_case` functions, and `SCREAMING_SNAKE` constants -- and
constants are capital-initial, so a naive capital/non-capital split
buckets `REPO` with `Ticket`. That alone shows the lexical split is the
wrong axis. If kind resolution proves impractical, come back with what
you measured rather than shipping the two-way casing split.

WIRING:

- Register in `TIER_A_HANDLERS` (`src/frob/gates/_fix_engine.py`). The
  ordering contract in that module's comment block is load-bearing --
  read it and justify the slot chosen.
- T-1775's lesson is mandatory here: a Tier-A fix runs in ROOT against
  ROOT's PRE-land build, and must subtract paths the landing changeset
  has already staged, or it will overwrite the very change being landed.
  A rule-deleting ticket was structurally unlandable for exactly this
  reason. Reuse `_worktree_touched_paths`.
- Formatting a bracket list means rewriting a `.strata` source line.
  `_render_interface_block`/`NAMES_PER_LINE` in `_sync_interface.py` do
  line-wrapping today and are being deleted by T-1870 -- if that wrapping
  logic is worth keeping, EXTRACT it before T-1870 lands rather than
  reimplementing it afterwards, and coordinate with that ticket.

SEQUENCING: after T-1870 and T-1871.

## Done report

Changed:
src/frob/gates/_fix_engine_sync.py::fix_sys_interface_canonical_order
src/frob/gates/_fix_engine_sync.py::_reorder_iface_one_file
src/frob/gates/_fix_engine_sync.py::_reorder_node_interface_block
src/frob/gates/_fix_engine_sync.py::_render_interface_block
src/frob/gates/_fix_engine_sync.py::_canonical_interface_key
src/frob/gates/_fix_engine_sync.py::_node_symbol_kinds
src/frob/gates/_fix_engine_sync.py::_iface_find_spans
src/frob/gates/_fix_engine_sync.py::_iface_node_body_span
src/frob/gates/_fix_engine.py::TIER_A_HANDLERS (added SYS-IFACE-ORDER entry)
docs/strata/surface.md#interface-canonical-order-tier-a-t-1872 (new section)
tests/unit/gates/test_sys_interface_canonical_order.py (new test file, added to scope)

Evidence:
tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder.test_groups_by_kind_then_alpha
tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder.test_order_only_multiset_preserved_and_idempotent
(both pass: `uv run pytest tests/unit/gates/test_sys_interface_canonical_order.py -q` -> 2 passed)

The second test asserts BOTH the order-only invariant (declared name
Counter, including a duplicate, is identical before/after) AND
idempotency (a second run applies zero fixes). `_reorder_node_interface_
block` itself independently refuses (no-op) if its own recomputed
Counter comparison ever disagreed -- defense in depth beyond the test.

Filed: T-1895 (extract the shared .strata node-body brace-
depth scanner duplicated between this ticket's `_iface_node_body_span`
and `_sync_may.py::_node_body_span` -- DUP001 waived here since the
extraction needs a shared module neither in this ticket's declared
scope, out of scope for an order-only ticket)

Gates: `uv run frob check --ticket T-1872` -- gate:AFFECT/COV/TEST/DUP/
PRE/SCOPE/FMT all clean. Three unrelated FAILs remain, confirmed
pre-existing and outside this ticket's scope:
  - gate:ARCH: src/frob/refactor/_verify.py::verify_import_resolution
    (106 lines) -- unrelated file, not touched by T-1872
  - gate:REG: REG002/REG008/REG011 dangling CHK-GATE-SYS104 registry
    rows -- leftover from T-1870's SYS104 deletion, tracked there
  - gate:SELFAUDIT: 4 fs.read/fs.write findings against the NEW test
    file tests/unit/gates/test_sys_interface_canonical_order.py --
    design/frob.strata's `testsuite` node's may grants were not hand-
    edited (design/frob.strata is not in this ticket's scope); this is
    exactly what `fix_sys100_may_via_union` (already wired in
    TIER_A_HANDLERS) auto-repairs at land time, same as every other new
    test file in this repo's history.
Also waived inline (both scoped to files this ticket touches):
  - AFFECT001 on TIER_A_HANDLERS: docs/modules/gates.md is held by
    T-1877's live cross-worktree lease, could not be scope --add'ed;
    docs/strata/surface.md#interface-canonical-order-tier-a-t-1872
    documents the handler in full in the meantime.
  - DUP001 on _iface_node_body_span: see T-1895 above.

### Changed
```
 tickets/T-1872/ticket.md           | 10 +++++++++-
 tickets/T-1895/ticket.md | 25 +++++++++++++++++++++++++
 2 files changed, 34 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 4 error(s), 922 warning(s), 696 waived
- error-findings: ARCH001@src/frob/refactor/_verify.py, REG002@docs/design/registry/check-coverage.yaml, SELFAUDIT001@design, invalid-argument-type@tests/unit/gates/test_sys_interface_canonical_order.py
