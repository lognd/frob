---
id: T-2053
title: Cheapen land's post-merge check_gates re-verification spawn (T-0754)
state: done
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_verify.py
- tests/unit/test_ticket_runner_designate_repro.py
- tests/unit/test_ticket_runner_gate_findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_designate_repro.py
  reason: 'T-1344 follow-up: _verify.py''s test coverage lives in these files'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: 'T-1344 follow-up: _verify.py''s test coverage lives in these files'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_check_gates_summary_fn_and_check_gate_findings_fn_share_one_spawn
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-1344 (investigation, landed a523fa4f5620): land()'s
post-merge re-verification (_check_gates_summary_fn, T-0754) spawns a
fresh, effectively-unscoped `frob check --ticket <id> --json` inside the
land lock on every land -- measured 208.7s live, sitting between the
land-path's own measured median (95.4s) and p75 (322.6s). This is the
single largest directly-measured cost inside a typical land.

Coordinator has asked this be worked in-scope of _verify.py only (owned,
free), without weakening what T-0754 actually verifies (ClaimDivergence
detection between a Done report's captured gate state and the post-merge
tree). See docs/guides/agent-playbook.md section 13 for the full writeup.

## Done report

Investigated whether _check_gates_summary_fn/_shared_check_spawn_fn's
land-time re-verification spawn (measured ~209s in T-1344, the single
largest line item in a typical land) can be cheapened or cached, confined
to src/frob/app/ticket_runner/_verify.py per the coordinator's explicit
constraint, without weakening what T-0754's ClaimDivergence check
actually verifies.

CONCLUSION: no safe wall-clock change exists inside _verify.py alone.
Measured, not guessed:

1. `--only`/family-skipping is unsafe: _parse_error_findings_from_json
   counts an error-severity diagnostic from ANY ToolResult (ruff/ty/
   frob-arch/frob-exports/frob-cycle/frob-dup included, not just gate:*
   families) toward the compared claim. There is no stage this spawn
   could skip without silently narrowing what gets verified.
2. `--delta` does not reduce wall-clock. Read check/_python.py directly:
   delta filtering happens to the already-computed violation list, after
   every check already ran in full.
3. The existing gates/_gate_cache.py digest-keyed per-gate cache (T-1346,
   on by default) genuinely works: two consecutive runs against an
   IDENTICAL, unchanged tree measured 231s then 150s (35% faster), with
   the highest-cost gate families (archgate 32.5s->0.0s, perf 44.8s->
   0.0s, dead_symbols 12.8s->0.0s, pii_structural 11.9s->0.0s, clones
   13.0s->0.0s) dropping to zero on the hit. But this spawn never gets
   that benefit at land time: it always runs against a freshly merged
   tree that has never been measured before, and the highest-cost gate
   families read broadly enough that almost any land's own diff
   intersects their tracked file set -- so the cache structurally
   near-always misses in the real land path even though the mechanism
   itself works.
4. The remaining ~150s floor (identical-tree, fully warm gate cache) is
   spent entirely in the ruff/ty/frob-arch/frob-cycle/frob-dup/
   frob-exports lint/static tool layer (check/_python.py), which the
   T-1346 gate cache never covers -- those tools re-run in full every
   time, cached or not.

Recorded all four findings, with the measured numbers, directly in
_shared_check_spawn_fn's docstring (src/frob/app/ticket_runner/
_verify.py) so a future reader does not have to re-derive them, and
named the two concrete changes that WOULD cheapen this along with
exactly where they live -- both outside this ticket's scope:

- Extend an equivalent touched-file digest cache to the lint/static tool
  layer in check/_python.py (the largest remaining floor once the
  existing gate cache is warm).
- Thread the land's own diff (already computed inside
  src/frob/tickets/_land.py/_land_cmd.py as pre_land_tip vs the squashed
  tree) into this spawn as an --only selection, so a small diff only
  re-verifies gate/tool families whose dependency it could plausibly
  touch -- the change that could turn near-always-cache-miss into
  near-always-cache-hit. Needs _land.py, out of scope here.

Also surfaced, not fixed: _land_cmd.py's _land_gate_claims_fn (T-1410)
runs a SEPARATE, comparably-sized `frob check --only gates` spawn
against `worktree` (not `root`) for the acceptance-criteria gate-claim
check -- a second, independent cost this investigation did not attempt
to quantify or fix, since _land_cmd.py is outside this ticket's scope
too. Worth its own follow-up ticket if the coordinator wants it measured.

No wall-clock improvement was safely achievable inside this ticket's own
scope. The diff is documentation only (a docstring addendum), verified
against tests/unit/test_ticket_runner_gate_findings.py (19 passed).

### Changed
```
 src/frob/app/ticket_runner/_verify.py | 59 ++++++++++++++++++++++++++++++++++-
 tickets/T-2053/ticket.md    | 48 ++++++++++++++++++++++++++++
 2 files changed, 106 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_check_gates_summary_fn_and_check_gate_findings_fn_share_one_spawn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, DOC005@README.md, DOC005@docs/modules/cli.md, DRIFT002@src/frob/app/ticket_runner/_rapid_sweep.py, PII012@src/frob/testing/_coverage_refresh.py, PRE001@tickets/T-2053
