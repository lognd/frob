---
id: T-2380
title: Decompose SYS003 (undeclared cross-component import) WARN campaign -- 4834
  findings, 603 files
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: T-0969
tier: epic
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN the corrected architecture model (testsuite->component Flows declared
    explicitly per T-2380's investigation, frob.excludes/yaml_io/tomlio reclassified
    from cli to core, refactor/registry_model/verify->core Flows added) THEN a fresh
    unscoped frob check reports the TRUE production-only SYS003 count, and that count
    is either burned down in one dispatch or split into disjoint children
  evidence: []
- text: given every SYS003 child, when all have landed clean, then SYS003 is promoted
    from warning to error
  evidence: []
acceptance_amendments:
- op: replace
  index: 0
  old_text: given a fresh SYS003 measurement, when findings are grouped by (from_component,
    to_component), then one or more disjoint-scope children are filed covering the
    full 4834
  new_text: GIVEN the corrected architecture model (testsuite->component Flows declared
    explicitly per T-2380's investigation, frob.excludes/yaml_io/tomlio reclassified
    from cli to core, refactor/registry_model/verify->core Flows added) THEN a fresh
    unscoped frob check reports the TRUE production-only SYS003 count, and that count
    is either burned down in one dispatch or split into disjoint children
  reason: criterion 0 assumed 4834 genuine findings needing distribution across children;
    the coordinator-accepted verdict is that ~95%+ of that count is gate over-firing
    (testsuite importing tested production code, plus 3 misplaced leaf utilities),
    so 'file children covering the full 4834' is now the wrong instruction -- the
    model must be corrected FIRST, then the true remainder measured and only then
    decomposed
  actor: logan
  at: '2026-08-18'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral), gate:SYS rule SYS003 ("undeclared cross-component
import"), 2026-08-18: **4834 WARN-tier findings across 603 distinct files**.

This dwarfs every other WARN-tier family in T-0969 by more than an order of
magnitude (the next largest, EXHAUST002/003, is 179) and cannot be filed as a
single dispatchable child -- it needs its own decomposition pass, the same way
T-0969 itself needed one before any child could be filed. Do NOT hand it to one
agent as a single ticket.

Recommended next step: measure SYS003 findings grouped by the (from_component,
to_component) pair the message names (e.g. "scripts_ops -> core") and file one
child per pair or per cluster of related pairs, so each child's scope stays a
disjoint set of files. A rough per-component breakdown from this measurement
run:

    python3 -c "
    import json, collections
    d = json.load(open('<path to a fresh --json capture>'))
    c = collections.Counter()
    for r in d['results']:
        for x in r.get('diagnostics', []):
            if x.get('code') == 'SYS003':
                # message ends '... (from -> to); declare a Flow ...'
                msg = x['message']
                pair = msg.split('(')[-1].split(')')[0]
                c[pair] += 1
    for k, v in c.most_common(30):
        print(v, k)
    "

Given the volume, seriously consider whether SYS003's underlying Flow-
declaration model itself needs a bulk/generated-Flow mechanism (e.g. an
allowlist migration tool) rather than 4834 hand-edits -- that is a design
question for whoever picks up the decomposition, not something to assume here.

Closure is two-part per the epic (T-0969) and applies to whatever decomposition
this produces: zero SYS003 findings across all resulting children, AND SYS003
promoted from warning to error severity only once the whole family is clean --
never promote while any child still carries findings, or every remaining
finding becomes a hard build break for everyone.