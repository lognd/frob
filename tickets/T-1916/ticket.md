---
id: T-1916
title: 'REG002 red on main: CHK-GATE-SYS-IFACE-ORDER claims an enforced gate rule,
  but SYS-IFACE-ORDER is only a Tier-A auto-fix handler'
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
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