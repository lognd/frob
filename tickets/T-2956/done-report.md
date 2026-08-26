## Done report

Re-measured unscoped (uv run frob check --json --only static, tool==
"frob-dup") before starting work: 28 groups touch src/frob/gates (1
already waived from a prior ticket = 27 unaccounted), out of 558
repo-wide (39 exact, 519 renamed) -- close to the parent's 557/20
figures; main has moved since that measurement, and this ticket's own
"20" count undercounted the cross-package fragments that also touch
src/frob/gates (28 is the honest re-measured figure).

Disposition applied this ticket:

- WAIVE, 4 groups (the T-2390-epic *_schema.py config-table-validator
  family: the 44/21/17/11-line blocks spanning _refs_schema.py,
  _arch_schema.py, _test_runner_schema.py, _gates_schema.py,
  _native_schema.py, _toplevel_scalar_schema.py, _docblocks_schema.py,
  _profile_schema.py, _testing_schema.py, plus the same idiom bleeding
  into _flag_coverage.py/_docblocks.py/__init__.py). VERIFIED against
  the code, not accepted on the docstring's word alone: read
  _refs_schema.py and _arch_schema.py's _resolve_known_keys bodies in
  full -- structurally identical control flow, but each file is its
  own T-2390-epic child ticket with its own frob:ticket/frob:tests
  bindings, own rule code, and own message text naming its own config
  surface. 22 `# frob:waive DUP001 reason=...` directives added (one
  per fragment; the gate requires full-group coverage, not a single
  waiver per group -- frob.check._python._dup_group_covering_waivers).

Re-measured after: unscoped frob-dup summary went from "558 duplicate
groups (1 waived)" to "553 duplicate groups (5 waived)" -- the 4
schema-family groups are now excluded from the headline count and
listed as `note` diagnostics (never hidden).

NOT reached zero. 23 groups remain unaccounted in src/frob/gates.
Two of those got a code-verified disposition this ticket did not have
budget to apply as directives:

- EXTRACT (genuine, verified real duplication, not a false positive):
  `_tracked_gate_files` in _port_selfcheck.py:212 and
  _lexical_selfcheck.py:270 -- byte-identical bodies, both files' own
  docstrings say the composition is meant to be shared, not
  re-hardcoded.
- WAIVE (confirmed in-code): the two _exhaustive_handling.py /
  arch/_mayraise.py groups -- _exhaustive_handling.py's own docstring
  states this is a deliberate narrow local duplicate, not an import of
  a private cross-module name.

The remaining ~19 groups follow the same "sibling rule-builder /
violation-builder idiom" shape seen throughout src/frob/gates
(structurally alike scaffolding, different rule code and domain
content per instance) but each needs the same per-group code check
before waiving -- not assumed from the pattern alone.

Filed: T-2966 (frob-dup: finish src/frob/gates cluster
triage, 23 residue groups) -- carries the full remaining group list,
the two pre-verified dispositions above, and the exact re-measure
command.

T-2957 is NOT unblocked by this ticket alone -- the src/frob/gates
cluster has real residue (23 groups) and T-2955 (tests/ cluster) is
the much larger remaining piece.

Evidence: tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waived_group_excluded_from_headline_but_listed
(and the sibling 5 tests in the same -k dup001 run, all passing,
6 collected / 0 failed) -- this class is the existing coverage for the
exact waiver full-coverage mechanism (_dup_group_covering_waivers)
this ticket's `frob:waive DUP001` directives rely on; the ticket adds
no new production behavior, only waiver comments, so no new test
surface of its own.

Gates: frob check --only static (unscoped) re-run clean of the 22
new-waiver-adjacent findings; ruff/format applied via `frob fmt`, then
reverted the 6 files it touched outside this ticket's scope
(frob-core/*.rs, strata-core/*.rs, _walk_lint.py -- pre-existing
formatting drift unrelated to this change).

### Changed
```
 src/frob/gates/__init__.py                |  16 +++++
 src/frob/gates/_arch_schema.py            |  24 +++++++
 src/frob/gates/_docblocks.py              |   8 +++
 src/frob/gates/_docblocks_schema.py       |  32 +++++++++
 src/frob/gates/_flag_coverage.py          |  16 +++++
 src/frob/gates/_gates_schema.py           |  32 +++++++++
 src/frob/gates/_native_schema.py          |  24 +++++++
 src/frob/gates/_profile_schema.py         |  24 +++++++
 src/frob/gates/_refs_schema.py            |  32 +++++++++
 src/frob/gates/_test_runner_schema.py     |  32 +++++++++
 src/frob/gates/_testing_schema.py         |  24 +++++++
 src/frob/gates/_toplevel_scalar_schema.py |  24 +++++++
 tickets/T-2956/ticket.md                  |  97 ++++++++++++++++++++++++++-
 tickets/T-2966/ticket.md        | 105 ++++++++++++++++++++++++++++++
 14 files changed, 489 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waived_group_excluded_from_headline_but_listed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 27 error(s), 897 warning(s), 853 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2962/ticket.md, DOC008@docs/commands/check.md, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
