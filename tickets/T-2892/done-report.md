## Done report

Changed: tickets/T-2384/ticket.md (evidence bindings only, no src/ change)

Re-verified before binding (per playbook: never trust cited evidence without
re-collecting it):
- Ran `pytest --collect-only` against all 7 test node ids cited in T-2892's
  own measurement note. The two gate-fixture tests
  (tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires_for_a_differently_named_project,
  tests/test_gates.py::TestRootAssetDirGate::test_unreferenced_root_directory_fires_for_a_differently_named_project)
  collected as cited. The five skills_sync ids as cited in the ticket body
  (bare function names) did NOT collect -- they are methods of
  TestSyncSkillsProvenance, not module-level functions. Corrected to the
  Class.method qualname form (tests/unit/test_skills_sync.py::TestSyncSkillsProvenance::<name>)
  and all 5 collected and passed.
- Ran all 7 corrected node ids: 7 passed, 0 failed.
- Re-ran `uv run frob check --only gates --json` against frob's own tree:
  grepped the full JSON output for ENV001/ROOT001/PORT001 -- zero hits,
  confirming the must-still-pass control cited in T-2892's measurement.
- For criterion 4 (single resolver, no second implementation), the ticket
  body cited no specific pytest node id (only a live PORT001 zero-finding
  run). Bound tests/unit/gates/test_port_selfcheck.py::TestPort001's
  test_hardcoded_path_prefix_is_flagged, test_hardcoded_identity_literal_in_tuple_is_flagged,
  and test_clean_gate_module_is_silent instead -- these are the PORT001
  meta-guard's own regression tests proving a reappearing second
  implementation is caught. Ran and confirmed: 3 passed.

Evidence: bound via `frob ticket evidence T-2384 <node-ids> --accepts N`,
one call per acceptance index (0-3). All 4 acceptance criteria on T-2384
now show bound(...) with the corrected node ids above.

Filed: none (no new out-of-scope work found)

Gates: no src/ change made (measurement did not contradict the recorded
premise, so scope stayed doc/ticket-hygiene only per the ticket's own
instruction).

### Changed
```
 tickets/T-2384/ticket.md | 34 ++++++++++++++++++++++++++++++----
 tickets/T-2892/ticket.md |  2 +-
 2 files changed, 31 insertions(+), 5 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 21 error(s), 437 warning(s), 847 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, I001@/home/logan/projects/frob/.claude/worktrees/t-2892/tests/unit/verify/test_backpressure.py, LANG003@src/frob/lang (facet=capability), LANG003@src/frob/lang (facet=docblock), LANG003@src/frob/lang (facet=dup), TICK004@tickets.md
