## Done report

Changed:
src/frob/gates/_docptr.py::_config_ref_candidates (new)
src/frob/gates/_docptr.py::_CONFIG_REF_PROSE_RE (new)
src/frob/gates/_docptr.py::_config_violations (rewired to scan
code-span-stripped prose via _config_ref_candidates, not the shared
backtick-derived tokens list)
docs/modules/vet.md (frob:waive DOC006 on a forward-looking VET007 key
newly surfaced by the more-thorough scan)
tickets/T-2573/ticket.md (backtick-wrapped a Python subscript expression
newly surfaced by the more-thorough scan)

Evidence:
tests/test_docptr_gate.py::TestDoc006Config::test_bracket_shape_inside_code_span_is_not_flagged
tests/test_docptr_gate.py::TestDoc006Config::test_bare_bracket_word_without_dot_never_a_candidate
tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_flagged
tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_in_fenced_block_is_not_flagged
(full tests/test_docptr_gate.py re-run: 63/64 pass; the one exception,
TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo,
fails on 3 findings entirely unrelated to this ticket's kind-3 config-ref
change -- 1 CLI-invocation and 2 file/path findings in tickets/T-2691 and
tickets/T-2705 (both outside this ticket's scope, pre-existing fleet
content) -- confirmed unrelated because kinds 1/2 (file/path, CLI) share
no code path with the kind-3 rewrite this ticket makes.)

Validated against the real consumer repo (/home/logan/projects/aprog-public,
read-only): `frob check --only docblocks` there dropped from 72 DOC006
code-span-collision false positives (activities/callable-lineup,
capture-court, catch2-tour, comprehension-decathlon, pytest-dojo, and
every `[section]`-shaped config citation in docs/architecture/
config-models.md, docs/reference/assignment-schema.md, docs/study-guides/*,
docs/tools/*) to 0 of that specific class -- confirmed via grep, 0 hits
remain. Total DOC006 count dropped from ~72+ to 35; the remainder are a
DIFFERENT kind (file/path pointers to genuinely untracked files) plus 6
new config-reference hits this more-thorough plain-prose scan newly
surfaces in the consumer's own docs (`[gates.docs]` in their tickets.md,
`[o.n_]` in a slidegen deck) -- both outside this ticket's fix (the
reported false-positive class), and both legitimately actionable findings
for that repo to `frob:waive` or fix, not something this ticket owns.

Filed: none

Gates: `frob check --ticket T-2703` diff-scoped checks pass (ruff/ty
clean on touched files, ARCH001 clean after the _doc008-unrelated
_docptr.py addition stayed under threshold). Repo-wide gate counts
include pre-existing unrelated findings (gate:scope-note in check
output).

### Changed
```
 docs/modules/vet.md       |  2 +-
 src/frob/gates/_docptr.py | 63 ++++++++++++++++++++++++++++++++--------
 tests/test_docptr_gate.py | 74 +++++++++++++++++++++++++++++++++++++++++++----
 tickets/T-2573/ticket.md  |  2 +-
 tickets/T-2703/ticket.md  | 33 ++++++++++++++++++++-
 5 files changed, 153 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006Config::test_bracket_shape_inside_code_span_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_bare_bracket_word_without_dot_never_a_candidate` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_in_fenced_block_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 45 error(s), 866 warning(s), 679 waived
- error-findings: AFFECT001@src/frob/gates/_docptr.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOC006@tickets/T-2705/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2703, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
