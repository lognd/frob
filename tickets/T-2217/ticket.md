---
id: T-2217
title: Wire frob.verify._quarantine.retire_unidentifiable_findings into frob verify
  dispose CLI
state: done
kind: feature
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/verify_runner.py
- src/frob/_cli_parsers/_verify.py
- src/frob/app/_config_external.py
- tests/unit/test_app_config_flag_coverage.py
- docs/modules/tickets-verify-sweep.md
- tests/unit/verify/test_verify_runner.py
- src/frob/verify/_quarantine.py
- tests/unit/verify/test_quarantine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_verify.py
  reason: 'Measured: every existing frob verify dispose flag (--file-ticket, --dismiss,
    --reason, --actor) is registered in src/frob/_cli_parsers/_verify.py''s _add_verify_parser,
    not in verify_runner.py, and forwarded to AppConfig via the _BOOL_FLAGS/_STRING_FIELDS
    allowlists in src/frob/app/_config_external.py (T-1697 marker) -- --retire-unidentifiable
    needs the same two wiring points to be reachable from the CLI at all. src/frob/app/config.py
    is already covered by this ticket''s implicit_scope FEATURE-kind CLI-wiring grant
    (T-0446/T-1848), confirmed via ''frob ticket show T-2217''.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'Measured: every existing frob verify dispose flag (--file-ticket, --dismiss,
    --reason, --actor) is registered in src/frob/_cli_parsers/_verify.py''s _add_verify_parser,
    not in verify_runner.py, and forwarded to AppConfig via the _BOOL_FLAGS/_STRING_FIELDS
    allowlists in src/frob/app/_config_external.py (T-1697 marker) -- --retire-unidentifiable
    needs the same two wiring points to be reachable from the CLI at all. src/frob/app/config.py
    is already covered by this ticket''s implicit_scope FEATURE-kind CLI-wiring grant
    (T-0446/T-1848), confirmed via ''frob ticket show T-2217''.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/test_app_config_flag_coverage.py
  reason: find_dropped_cli_flags (COV/flag-coverage gate) cross-references src/frob/app/_config_external.py
    against tests/unit/test_app_config_flag_coverage.py -- a new _BOOL_FLAGS entry
    needs that test's own coverage kept in sync. docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697
    documents the existing dispose flags this ticket extends. tests/test_verify_dispose.py
    (if present) is the existing CLI-level dispose test file the new flag's own test
    belongs beside.
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: find_dropped_cli_flags (COV/flag-coverage gate) cross-references src/frob/app/_config_external.py
    against tests/unit/test_app_config_flag_coverage.py -- a new _BOOL_FLAGS entry
    needs that test's own coverage kept in sync. docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697
    documents the existing dispose flags this ticket extends. tests/test_verify_dispose.py
    (if present) is the existing CLI-level dispose test file the new flag's own test
    belongs beside.
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_verify_dispose.py
  reason: find_dropped_cli_flags (COV/flag-coverage gate) cross-references src/frob/app/_config_external.py
    against tests/unit/test_app_config_flag_coverage.py -- a new _BOOL_FLAGS entry
    needs that test's own coverage kept in sync. docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697
    documents the existing dispose flags this ticket extends. tests/test_verify_dispose.py
    (if present) is the existing CLI-level dispose test file the new flag's own test
    belongs beside.
  actor: logan
  at: '2026-08-16'
- op: remove
  glob: tests/test_verify_dispose.py
  reason: tests/test_verify_dispose.py does not exist; the real existing dispose CLI
    test home is tests/unit/verify/test_verify_runner.py (confirmed via git grep for
    verify_dispose/_run_dispose across tests/).
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/verify/test_verify_runner.py
  reason: tests/test_verify_dispose.py does not exist; the real existing dispose CLI
    test home is tests/unit/verify/test_verify_runner.py (confirmed via git grep for
    verify_dispose/_run_dispose across tests/).
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/verify/_quarantine.py
  reason: 'frob ticket land refused close: LiveTrackerCited -- two frob:waive WIRE001
    directives cite follow_up=T-2217 (the CLI-wiring gap this ticket exists to close).
    retire_unidentifiable_findings is now genuinely wired to the CLI, so its waiver
    is obsolete and must be removed; _seed_stuck_store''s waiver reason (test-only
    helper) was always independent of this ticket and just needs its stale follow_up
    citation dropped. Land''s own error message is the measurement.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/verify/test_quarantine.py
  reason: 'frob ticket land refused close: LiveTrackerCited -- two frob:waive WIRE001
    directives cite follow_up=T-2217 (the CLI-wiring gap this ticket exists to close).
    retire_unidentifiable_findings is now genuinely wired to the CLI, so its waiver
    is obsolete and must be removed; _seed_stuck_store''s waiver reason (test-only
    helper) was always independent of this ticket and just needs its stale follow_up
    citation dropped. Land''s own error message is the measurement.'
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_retires_and_clears
- tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_rejects_combination_with_dismiss
- tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_still_blocks_on_a_well_formed_sibling
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2207 fixed the core identity-less quarantine finding defect
(producer filter in raise_quarantine, consumer recovery verb
retire_unidentifiable_findings) but could not wire it to the CLI --
src/frob/app/verify_runner.py is outside T-2207's declared scope
(src/frob/verify/_quarantine.py only).

Add a `frob verify dispose --retire-unidentifiable` flag (or similar)
that calls frob.verify._quarantine.retire_unidentifiable_findings
directly, so an operator hitting a stuck identity-less quarantine
record again does not need a Python REPL / ad hoc script to invoke the
recovery verb -- only a direct import currently reaches it.

## Done report

Premise check first: `git grep -n "retire_unidentifiable_findings|retire-unidentifiable"
-- src/frob/app/verify_runner.py src/frob/_cli_parsers/_verify.py src/frob/app/config.py
src/frob/app/_config_external.py` returned nothing on the un-touched tree -- the wiring
genuinely did not exist yet.

Lease: T-2217 carried a stranded lease from an earlier abandoned `frob ticket work`
(recorded 2026-08-16T17:57, no live process, no uncommitted work, only a lone
"record T-2217 start transition" commit ahead of main). Verified independently before
stealing: scanned every /proc/<pid>/cwd for a match under .claude/worktrees/t-2217 (none),
confirmed `git status --porcelain` empty and `git log main..HEAD` = one no-op commit.
Stole with `frob ticket work T-2217 --steal`.

Scope: the declared scope (src/frob/app/verify_runner.py alone) could not reach the CLI.
Widened via `frob ticket scope --add` (measured reasons recorded) to also cover
src/frob/_cli_parsers/_verify.py (every other dispose flag -- --file-ticket, --dismiss,
--reason, --actor -- is registered there) and src/frob/app/_config_external.py
(_BOOL_FLAGS CLI->config forwarding allowlist, T-1697 marker) plus
tests/unit/test_app_config_flag_coverage.py and docs/modules/tickets-verify-sweep.md.
src/frob/app/config.py was already covered by this ticket's implicit_scope (FEATURE-kind
CLI-wiring grant, T-0446/T-1848) -- confirmed via `frob ticket show T-2217` before touching
it, no separate --add needed there.

Implementation: `--retire-unidentifiable` is a new, mutually-exclusive dispose mode.
`_run_dispose` refuses outright (exit 1, no partial action) if combined with
`--file-ticket`/`--dismiss`. Otherwise it calls
`frob.verify._quarantine.retire_unidentifiable_findings(root, reason=..., actor=...)`
directly -- NOT threaded through `--dismiss`'s existing RULE:FILE:LINE addressing (that
path was explicitly rejected already: an empty `file` component can never parse to a
valid key). `retire_unidentifiable_findings` enforces the identical "clear only if every
finding ends up disposed" rule `clear_quarantine` itself does; a well-formed undisposed
sibling still returns `Err(FindingsNotDisposed)`, handled by the SAME generic
`result.is_err` branch as the ordinary path -- no special-cased bypass exists for it.

Must-still-pass control: `test_retire_unidentifiable_flag_still_blocks_on_a_well_formed_
sibling` mirrors T-2207's own `test_retire_unidentifiable_findings_still_blocks_on_a_well_
formed_sibling` at the CLI layer -- seeds an identity-less finding alongside a real
well-formed one, asserts the identity-less one is retired but quarantine stays RAISED
until the real one is disposed too.

Repro discipline: the three new tests committed alone first (7a68d4741), confirmed
FAILED_AT_PARENT via `frob ticket evidence --check-repro ... --base-ref 7a68d4741` for
both the success-path test and the must-still-pass test, then the implementation
committed separately (c1560230a).

Real end-to-end smoke test (not just unit-level): built a throwaway repo with a
`.frob/quarantine.json` in the exact "stuck" shape the live incident described
(rule_id="", file="", RAISED), ran `frob verify status` (showed the same UNDISPOSED
identity-less row the incident report describes), then
`frob verify dispose --retire-unidentifiable --reason ... --actor ...` against it, then
`frob verify status` again -- confirmed `quarantine: clear`.

Changed:
  src/frob/_cli_parsers/_verify.py (new --retire-unidentifiable argparse flag)
  src/frob/app/config.py::AppConfig.verify_dispose_retire_unidentifiable (new field,
    implicit-scope-covered)
  src/frob/app/_config_external.py::_BOOL_FLAGS (forwarding entry)
  src/frob/app/verify_runner.py::_run_dispose (new mutually-exclusive branch)
  tests/unit/verify/test_verify_runner.py::TestDispose (3 new tests + seed helper)
  docs/modules/tickets-verify-sweep.md (new subsection, frob:describes _run_dispose)

Evidence:
  tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_retires_and_clears
  tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_rejects_combination_with_dismiss
  tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_still_blocks_on_a_well_formed_sibling
  Full tests/unit/verify/test_verify_runner.py + test_quarantine.py +
  test_app_config_flag_coverage.py run: 35 passed.

Filed: none -- no out-of-scope work discovered.

Gates: gate:FMT/gate:PRE/gate:SCOPE/gate:doclink/gate:docanchor all clean for this
ticket (`frob check --only <group> --ticket T-2217`, re-run after `frob fmt` fixed
directive line-wrapping and `frob ticket sweep T-2217` refreshed the stale pre-work
sweep post-scope-widen). The only unscoped ERROR-level findings anywhere in the tree
(3 DRIFT001 digest-moved findings in _land_cmd.py/_rapid_sweep.py/lang/_nodes.py) are
PRE-EXISTING on `main` itself -- `git diff main --stat` for each is empty; not touched
by this ticket. `git diff main --diff-filter=D --stat` is empty after a fresh
`git merge main` (no deletions).

### Changed
```
 docs/modules/tickets-verify-sweep.md    |  16 +++++
 src/frob/_cli_parsers/_verify.py        |  14 +++-
 src/frob/app/_config_external.py        |   2 +
 src/frob/app/config.py                  |   5 ++
 src/frob/app/verify_runner.py           |  67 +++++++++++++++----
 tests/unit/verify/test_verify_runner.py | 115 ++++++++++++++++++++++++++++++--
 tickets/T-2217/ticket.md                |  78 +++++++++++++++++++++-
 7 files changed, 276 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_retires_and_clears` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_rejects_combination_with_dismiss` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_still_blocks_on_a_well_formed_sibling` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH001@src/frob/app/verify_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2217/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2217/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2217, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, WIRE001@tests/unit/verify/test_verify_runner.py
