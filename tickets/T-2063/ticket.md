---
id: T-2063
title: README/cli.md docs stale after T-1584 (frob profile CLI)
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- README.md
- docs/modules/cli.md
evidence_scope:
- tests/test_docblocks_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_missing_row_for_real_command_fails
- tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_count_claim_mismatch_fails
kind_history:
- 2026-08-10 bug->docs evidence=2 done_report=yes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1584 (99ecae11dff1, "Wire frob profile CLI (show/downgrade) to
frob.tickets._profile") is `done` and landed. It never touched
README.md or docs/modules/cli.md (confirmed: `git show --stat
99ecae11dff1` lists 18 changed files, neither of the two). Its own
Done report claimed `frob check --land-parity: clean -- 0 unscoped
error(s)`.

MEASURED against current unscoped `frob check --json`
(python3 scripts/check_summary.py): 8 residue errors trace to this
land:

    DOC005 README.md:0    real subcommand `frob profile` has no command-table row in README.md
    DOC005 README.md:54   README.md claims 43 commands but the live registry has 44
    DOC005 docs/modules/cli.md:298  generated command table is stale
    SELFAUDIT001 design:1  SYS100 node=cli: capability 'fs.read' observed at src/frob/app/profile_runner.py:44 but not declared
    SELFAUDIT001 design:1  SYS100 node=testsuite: capability 'fs.write' observed at tests/unit/test_profile_runner.py (x4)

RE-VERIFIED by checking out the exact land commit 99ecae11dff1 into a
throwaway detached worktree and running `frob check --only docblocks
--json` and `frob check --only sys --json` there directly (both
unscoped, no --ticket, no --delta): all 3 DOC005 findings above fire
at that exact commit (2.84s runtime), and SELFAUDIT001 fires 6 times
(1 node=cli fs.read + 5 node=testsuite fs.write instances) at that
same commit. Both "docblocks" and "sys" are ordinary gates-fast/
gates-security stage-group members that a `--budget`-based unscoped
run (the mechanism `--land-parity` itself uses) covers.

This is scoped narrowly to closing that residue:
- README.md: add a `frob profile` command-table row, fix the claimed
  command count (43 -> 44).
- docs/modules/cli.md: regenerate the stale generated command table.
- design/frob.strata: declare the observed `fs.read`/`fs.write`
  capabilities for src/frob/app/profile_runner.py and
  tests/unit/test_profile_runner.py.

NOTE: by the time this ticket was filed, current main (T-1344's land,
a523fa4f5) had ALREADY incidentally declared both capabilities in
design/frob.strata (profile_runner.py's fs.read, test_profile_runner.py's
fs.write) as a side effect of unrelated work -- re-measured on current
main: `frob check --only sys` now reports ZERO SELFAUDIT001 findings.
Only the 3 DOC005 findings remain live and need this ticket's fix.