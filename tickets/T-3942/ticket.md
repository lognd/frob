---
id: T-3942
title: 'F-175..F-185: backend delta audit -- and the recurrence signal that 3 first-audit
  asks were never built'
state: queued
kind: security
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic: this is a decomposition container for eleven
  consumer audit items; the scope lives on its children, which must be filed before
  any code is written'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2, F-175..F-185, copied verbatim from their
docs/security/audit-2026-09-05-backend-delta.md. This is the FOURTH audit list
from that repo; T-3919 covers their first backend audit, T-3920 the threat
model, T-3928 the edge/ops and frontend passes.

THE HEADLINE IS NOT ANY INDIVIDUAL ITEM. It is the consumer's own framing:

  "Items 1-4 are new; 5-7 are first-audit asks that were never implemented and
   would each have caught a finding here, which is itself the strongest signal
   in this report."

Read that as the finding it is. We accepted three asks from their first audit,
filed them, did not build them, and the same defect classes recurred in the very
next slice of code they wrote. Item 5 (ASSERT001, "the cheapest rule in either
report") reappeared VERBATIM in the newest module written. That is a measurement
of our own decomposition backlog, not of their code -- and it is the reason this
epic exists rather than another flat list.

SO THE FIRST ACTION IS NOT TO BUILD ITEM 1. It is to answer: what happened to
the first audit's items 3 and 4 on T-3919? Are they decomposed into leaves and
starved, or never decomposed at all? Report that before opening any new work.
Four undecomposed audit epics is itself the risk this ticket documents.

THE ELEVEN ITEMS (F-175..F-185 in their numbering, items 1-11 in the audit):

1. F-175 A security-relevant constant must be consulted by EVERY path that can
   reach what it protects. EXCLUDED_TABLES/FORBIDDEN_COLUMNS are checked on
   three write paths and skipped on the fourth (revert_change). They note this
   is a call-graph reachability question frob ALREADY has machinery for, via a
   frob:invariant plus `frob check --only invariant`. Generalise: a module-level
   frozenset named *_FORBIDDEN/*_EXCLUDED/*_ALLOWED must be read on every path
   to the sink it guards. VERIFY THE "already has machinery" CLAIM before
   building anything new -- that is a claim about our code.

2. F-176 TAINT-IDENT001: data read from a store and later used as an IDENTIFIER
   (table name, column name, values(**...) expansion) is tainted and must pass
   an allowlist between read and use.

3. F-177 An audit/evidence dataset must be append-only and strata should be able
   to SAY so. Today strata models postgres as one store with one capability;
   there is no way to declare "this dataset is append-only from this node". They
   argue a `dataset` construct under a store, with its own carries and an
   append_only attribute resolved by SYS100, closes four findings across two
   audits at the root. This is the most structural item and the one most clearly
   ours rather than theirs.

4. F-178 Run shellcheck over ops/**.sh as a frob stage. Their D-M9 is SC2097/
   SC2098 -- a rule shellcheck already ships. Cheap, and note it pairs with the
   ops shell-grammar ask already recorded on T-3928.

5. F-179 ASSERT001: no bare assert in src/**. Proposed in the first audit, never
   implemented, and the pattern reappeared verbatim in their newest module.
   Their words: "the cheapest rule in either report."

6. F-180 Docstring-derived invariant obligations. Still the highest-yield
   unimplemented ask. In THIS delta alone it would have flagged five false
   docstring claims, which they list. Already recorded as a convergence on
   T-3928 (where the frontend audit reached the same ask by a different and more
   implementable route -- binding a SENTENCE to a TEST rather than inferring an
   invariant). Prefer that framing.

7. F-181 RACE001 / concurrency test obligations. Also from the first audit, also
   unimplemented; two findings in this delta are in its scope.

8. F-182 ENVVAR003: a config field read off a LOCALLY-CONSTRUCTED default
   instance is a finding. Note why this one matters out of proportion to its
   size: it SILENTLY DEFEATED A LANDED SECURITY FIX, and it passes both the
   existing env-var sync gate and the first audit's proposed ENVVAR002. Narrow
   and mechanical -- flag construction of the settings class outside
   from_external/tests.

9. F-183 RESULT001: an async def performing network I/O may not return None.
   Their notify_admin_alert -> None let a caller mark alerts digested after a
   FAILED send. They note it violates the repo's own stated typani rule that no
   gate enforces -- an intent-in-prose instance.

10. F-184 Extend the SIT-011 route inventory to a third axis: the confirm-gate
    axis and a pagination axis, both readable from the route's pydantic model
    and signature.

11. F-185 Doubles-vs-SQL semantic parity as an obligation, not a convention.
    Three findings in ONE module are the same failure: the real adapter and the
    in-memory double diverge (range, pagination, transactional atomicity). Rule:
    every Protocol with both a double and a real adapter carries at least one
    shared behavioural test run against BOTH, or a declared invariant where it
    cannot. THIS ONE BEARS ON FROB'S OWN TEST INTEGRITY -- we use doubles
    heavily, and T-3933 is a live instance of exactly this shape (a synthetic
    LANGUAGE_COLLECTORS["ts"] lambda standing in for a real collector, proving
    binding while execution stayed unproven).

GUIDANCE, same as the other three audit epics: DO NOT BUILD ALL OF IT. Decompose
into leaves, keep the audit's own ordering as priority order, and file each child
naming the finding it would have caught. VERIFY EACH AGAINST WHAT EXISTS FIRST --
"nothing enforces X" is a claim about code that must be grepped before it is
believed, and item 1 explicitly asserts we already have the machinery.

START WITH 5, 6 AND 7, NOT WITH 1. They are the ones with two independent
arrivals and a demonstrated recurrence cost, and item 5 is the cheapest rule in
either report.

ACCEPTANCE
- The status of T-3919's items 3 and 4 reported FIRST, before new work opens.
- Eleven children filed, each naming the finding it would have caught.
- Items 6 and 11 cross-referenced to T-3928 and T-3933 rather than duplicated.