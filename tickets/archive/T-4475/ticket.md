---
id: T-4475
title: 'T-4179 regression: directive canonicalizer emits over-limit lines for long
  node ids, every land then refuses on NEW E501'
state: done
kind: bug
origin: agent
created: '2026-09-13'
priority: critical
parent: T-4410
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fmt_directives.py
- tests/test_gates_fmt_directives.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land_dry_run*.py
- src/frob/tickets/_land_git_ops.py
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'the waive-deletion block normalizer (_normalize_waive_fragments) joins
    each fragment''s stripped text verbatim, including a trailing # noqa: E501 T-4475''s
    own auto-suffix introduces on an unbreakable-token final line, so a legitimate
    rewrap now reads as a semantic content change and refuses the land (the exact
    defect this ticket closes must not resurface one call site downstream) -- the
    directive parser this ticket''s own text names must strip that marker too'
  actor: logan
  at: '2026-09-13'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001/SYS100 capability declaration for tests/test_gates_fmt_directives.py's
    new real ruff subprocess spawn (TestUnbreakableTokenGetsNoqaE501T4475.test_ruff_check_e501_is_clean_on_the_result)
  actor: logan
  at: '2026-09-13'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SELFAUDIT001/SYS100 capability declaration for tests/test_gates_fmt_directives.py's
    new real ruff subprocess spawn (TestUnbreakableTokenGetsNoqaE501T4475.test_ruff_check_e501_is_clean_on_the_result)
  actor: logan
  at: '2026-09-13'
evidence:
- tests/test_gates_fmt_directives.py::TestUnbreakableTokenGetsNoqaE501T4475::test_long_node_id_canonicalizes_to_one_line_ending_in_noqa
- tests/test_gates_fmt_directives.py::TestUnbreakableTokenGetsNoqaE501T4475::test_idempotent_on_a_second_canonicalize_pass
- tests/test_gates_fmt_directives.py::TestUnbreakableTokenGetsNoqaE501T4475::test_directive_still_parses_to_the_same_node_id
- tests/test_gates_fmt_directives.py::TestUnbreakableTokenGetsNoqaE501T4475::test_ruff_check_e501_is_clean_on_the_result
- tests/test_ticket_land_dry_run.py::TestRestoreAbsorbedPathsOnRefusal::test_restore_absorbed_paths_reverts_a_real_rewrite
- tests/test_ticket_land_dry_run.py::TestRestoreAbsorbedPathsOnRefusal::test_pre_land_refusal_restores_the_absorbed_rewrite
- tests/test_ticket_land_dry_run.py::TestRestoreAbsorbedPathsOnRefusal::test_pre_land_success_leaves_the_absorbed_rewrite_in_place
- tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewrap::test_a_rewrap_that_stays_parseable_does_not_refuse_at_all
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REGRESSION from T-4179 (landed 07f1735ed, 2026-09-13 20:23): the pre-land `frob fmt` directive canonicalizer now keeps an unsplittable token whole and accepts an over-limit physical line (the F-380 fix in src/frob/gates/_fmt_directives.py::_wrap_cut_point), so any file whose frob:tests/frob:doc directive names a node id longer than the 88-column budget is rewritten at land time into lines like `# tests/unit/test_artifact_smoke_script.py::TestCheckBaseInstall.test_failing_doctor_raises_smoke_check_error` (109 chars). The land's own pre-land `ruff check` then reports every such line as a NEW E501 violation and refuses: T-4473's land was refused twice (00:28 and 00:41 UTC, "33 NEW violation(s) ... scripts/artifact_smoke.py:52: E501 Line too long (109 > 88)") although the worktree file is E501-clean before the land touches it ("pre-land frob fmt canonicalized 1 file(s)" is the rewrite; the worktree was left dirty with 54/86 changed lines afterwards). Before T-4179 the canonicalizer split the node id mid-token (E501-clean but a broken directive, the original bug), so this was latent. Every future land that touches a file with a long directive token is blocked. FIX (token/grammar, not lexical): when a directive token cannot fit within the budget, the canonical physical line carries a trailing `  # noqa: E501` marker (ruff honours noqa on comment lines) so the directive stays whole AND E501-clean; strip/re-add the marker idempotently so re-canonicalizing is a no-op; the directive parser must ignore the marker. Add tests: a 109-char node id canonicalizes to one line ending in `# noqa: E501`, re-running is a no-op, `ruff check --select E501` on the result is clean, and the directive still parses to the same node id. Also: the land must not leave the caller's worktree dirty after a refused pre-land canonicalization (restore or apply-and-commit consistently) -- state which in the Done report. ACCEPTANCE: T-4473's worktree lands without an E501 refusal. Sprint v0.531.0 (blocks lands and the release).