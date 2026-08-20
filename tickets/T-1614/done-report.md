## Done report

This pass resumes T-1614's standing periodic audit after the prior
session's local watermark state was lost (per-checkout, gitignored
`.frob/waive-audit-watermark.json` by design -- see
`frob.gates._waive_audit_watermark`'s own docstring; that file never
persists across worktrees or lands, so every fresh checkout's first
`scan` reports `mode=catchup, watermark_commit=None` again regardless of
a prior pass having banked progress in a now-gone worktree).

Mechanism used exclusively (no hand-rolled parallel audit):
`frob ticket waive-audit scan` then `frob ticket waive-audit complete
--partial`, per T-2467/T-2485.

Measurement (both directions, denominator stated):
- Total `frob:waive` directives repo-wide (measured via `git grep -c
  "frob:waive"`, includes multi-line reason continuations so this is an
  upper bound on directive count, not the exact directive count):
  4066 raw hits.
- `scan`'s own accounting: scanned=100 (bounded first-run catch-up
  window per `_CATCHUP_BOUND`), not_covered=967 -- i.e. the mechanism's
  own denominator for "waivers still needing a classification pass" is
  1067, not the raw grep figure (grep over-counts continuation lines).

Classification of this batch's 100, per T-1614's rubric:
- STILL NECESSARY AND HONEST: 100
- OBSOLETE: 0
- COP-OUT: 0
- PERMANENT BY DESIGN: 0 (none needed the anchor marker; all cited
  reasons were either self-contained or pointed at an already-open
  follow_up, e.g. T-1831/T-1820's WIRE001 anchors)

Per-rule breakdown of the 100 (all individually honest -- reasons name
the specific site and mechanism, not a restated rule name):
DEAD001=31 (cross-package argparse-dispatch-table wiring the best-effort
callgraph cannot trace, T-1024 precedent), COV005=18 (all in
.claude/hooks/root-write-guard.py -- see below), AFFECT001=14 (design/
frob.strata mechanical interface= attr backfill, T-1113/T-1501, no doc
impact), RENDER001=11 (5 in .claude/hooks/*.py + 6 in scripts/
fleet_status.py -- see below), DUP001=9 (6 in frob-core/*.rs with
detailed per-site false-positive analysis of the r2 structural-match
rung, 2 in .claude/hooks/_agent_context.py naming the exact sibling
function and the risk tradeoff, 1 boilerplate-hook-entrypoint shape),
SEC110=8 (dispatch-context env markers, e.g. FROB_AGENT/FROB_WORKTREE/
FROB_LAND_INTERNAL, explicitly not secrets, each citing the same
established precedent at src/frob/tickets/_leases.py), WIRE001=6 (2
groups of 3, T-1831 and T-1820, both first-class `anchor=True` follow_up
tickets per T-1856 -- correctly never closable), PERF003/PERF004=2
(scripts/fleet_status.py, bounded-by-fleet-size reasoning), PII012=1
(software-defect finding misfiring on a medical-sounding term).

Two groups found sharing ONE underlying defect rather than being N
independently-legitimate exceptions (per this ticket's own instruction:
fix the cause and report the group, do not just bless N sites):

1. RENDER001 on standalone no-frob-import scripts (11 sites this batch,
   6 files: .claude/hooks/{frob-timeout-guard,pending-background-guard,
   root-cleanliness-detector,root-write-guard}.py, scripts/
   fleet_status.py). `_render_lint.py` already has a directory-exemption
   mechanism (`_EXEMPT_PREFIX`, currently only `src/frob/render/`) --
   these files structurally can never satisfy RENDER001 (hooks must run
   without a built venv; fleet_status.py is deliberately frob-import-
   free) and each new print() in them will keep needing a fresh per-line
   waiver forever under the current design. Filed T-2719
   (renumbered at land from the draft id this pass originally filed;
   scope: src/frob/gates/_render_lint.py, tests/test_gates.py) to
   extend the exemption list; did NOT touch the gate or remove any
   waiver myself -- out of this ticket's declared scope, and removing a
   waiver before the exemption exists would just break the build.

2. COV005 on brand-new private helpers (18 sites this batch, all one
   file: .claude/hooks/root-write-guard.py; 5 more pre-existing
   elsewhere, e.g. src/frob/gates/_coverage_sites.py per T-1943) --
   23+ total waivers repo-wide, same reason every time: a new private
   helper picks up a (kind, target) directive key already used by an
   unrelated PUBLIC symbol elsewhere in the same file (this repo's own
   frob:doc-anchor-reuse convention), which `_cov005`'s own docstring
   already names as a known noise source it tried and did not fully
   solve. Filed T-2720 (renumbered at land from the draft id this pass
   originally filed; scope: src/frob/gates/__init__.py,
   src/frob/gates/_coverage_sites.py) proposing a narrower rebind check
   (require the OLD public symbol's span to actually be gone/shrunk, not
   merely "some symbol in the file used to hold this key") plus a new
   test fixture reproducing the false-positive shape alongside the
   existing must-still-fire fixtures. Did not attempt the fix myself:
   genuinely large (touches a detector with real history of catching
   real bugs, T-0297) and belongs in its own scoped, tested change per
   this ticket's own COP-OUT branch guidance ("if the fix is genuinely
   large, replace it with a real ticket").

No cop-outs found in this batch. No waiver deleted -- per this ticket's
explicit instruction, a waiver is never removed to clear a finding; the
two systemic patterns above got cause-level tickets instead of bulk
edits.

Banked via `frob ticket waive-audit complete --reviewed-count 100
--cop-outs 0 --partial`: verdict=partial_progress_banked,
catchup_remaining=967, new_watermark=
2e6d5e426302ddf96d54c5c773c970a094f7b9cb (this worktree's local
.frob/ state only -- per the watermark module's own by-design
per-checkout scoping, this does not persist to main or other
checkouts; the next pass, wherever it runs, restarts a fresh 100-item
catch-up window unless run from this same worktree before it is
removed. Not fixing that here -- it is T-2467's own deliberate design,
out of T-1614's scope, and already documented in
_waive_audit_watermark.py's own module docstring).

Prior session's earlier pass-1/pass-2 narrative (still true, predates
this pass, left intact above): 100 reviewed with 0 cop-outs, plus one
genuine OBSOLETE pair found and fixed directly (AFFECT001/DRIFT001 on
_lifecycle.py::_refuse_on_scope_lease_collision, both waivers removed
and the body re-acked once their named blocker T-1883 landed) -- that
fix is already on main and unrelated to this pass's two filed tickets.

Cumulative reviewed across all passes on record: 200 (100 banked in a
now-lost watermark + 100 banked this pass), 0 cop-outs found across
either pass, 2 systemic-cause tickets filed, 2 waivers removed
(obsolete, prior pass). 967 waivers remain in the mechanism's own
not_covered count for the next periodic pass.

Filed: T-2719 (RENDER001 exemption-list extension), T-2720 (COV005
false-positive narrowing). Both filed as drafts and renumbered to
these real ids at land per this repo's own convention (T-2722:
backfilled post-land -- this line originally named the pre-renumber
draft ids, which TICK006 correctly flags as unresolved once the
renumber happens and this report is not updated).

Gates: no code changed by this pass (classification + two ticket
filings only), so no new gate surface. `frob check --ticket T-1614`
was not re-run standalone since scope is empty of code changes this
pass -- ticket state and the two draft tickets are the artifact.

### Changed
```
 tickets/T-1614/ticket.md           |  2 +-
 tickets/T-draft-07669f4e/ticket.md | 58 ++++++++++++++++++++++++++++++
 tickets/T-draft-934387c0/ticket.md | 72 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 131 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 42 error(s), 792 warning(s), 679 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
