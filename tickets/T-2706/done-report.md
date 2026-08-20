## Done report

Decision: (a) -- suppress LANG004's self-conformance half outside frob's
own tree. `capability_conformance_gate` now takes `repo_root: Path` and
returns `()` immediately unless `frob.repo_meta.is_frob_own_repo(repo_root)`
is True (repo_root's own pyproject.toml declares `[project] name = "frob"`),
reusing the PORT001 declare-not-hardcode pattern `_declared_frob_version`
already established. Option (b) (anchor somewhere meaningful to the
consumer) does not apply: this gate is an assertion about frob's OWN
`frob.lang` adapter table, not about anything a consumer repo controls, so
there is no consumer-meaningful anchor to move it to.

Changed:
src/frob/repo_meta.py::_read_pyproject_project (new, private)
src/frob/repo_meta.py::is_frob_own_repo (new, public)
src/frob/repo_meta.py::_declared_frob_version (refactored to share the read)
src/frob/gates/_lang_conformance.py::capability_conformance_gate (signature: repo_root: Path)
src/frob/gates/__init__.py (both call sites now pass st.repo_root; moved
  "capability_conformance" out of _CACHEABLE_GATES since it now reads
  repo_root, same reasoning as the existing T-0639 "deprecated" removal)

Evidence:
tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_real_registry_is_behaviorally_clean
tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_wrong_implemented_claim_fails
tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_consumer_repo_is_silent_even_with_a_broken_claim (new -- must-fail positive control, consumer direction)
tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_repo_root_with_no_pyproject_is_silent (new)
tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_fires_through_real_gate_dispatch

Manual verification against the real corpora (both positive controls,
read-only against aprog-public, no edits made there):
- `frob check --no-cache` in /home/logan/projects/aprog-public: 0 findings
  anchored at src/frob/lang/_support.py or mentioning LANG004 (the repo's
  gate-cache.db had a stale pre-fix entry; --no-cache bypasses it -- a
  land onto main naturally invalidates every consumer's cache since the
  content key changes, this was purely a local pre-fix cache artifact).
- global `frob` (rebuilt via `make install-tool` from this fix) run
  against frob's own source repo: still reports the 4 LANG004
  strata-capability findings unchanged (packaged wheel has no design/
  litmus/chirp.strata, so the strata behavioral fixture genuinely cannot
  build -- real self-conformance debt, confirmed NOT suppressed).
- `uv run frob check --only capability_conformance` (dev checkout, native
  strata_core built, design/ tree present): clean, 0 findings -- the
  fully-built dev-checkout case was already clean before this ticket and
  is unchanged by it.

Filed: none

Gates: capability_conformance=0.03s, lang_conformance clean in
`frob check --only capability_conformance --only lang_conformance --only
drift --only docanchor` (T-2706's own touched files clean; the DRIFT001/
DOC002/CLAUDE001 findings in that run are pre-existing, in files outside
T-2706's scope, unrelated to this change).

### Changed
```
 docs/modules/lang.md                | 22 +++++++++++
 rapid-debt.jsonl                    |  3 ++
 src/frob/gates/__init__.py          | 22 ++++++++---
 src/frob/gates/_lang_conformance.py | 11 +++++-
 src/frob/repo_meta.py               | 45 ++++++++++++++++++----
 tests/test_lang_conformance_gate.py | 55 ++++++++++++++++++++++++--
 tickets/T-2706/done-report.md       | 77 +++++++++++++++++++++++++++++++++++++
 7 files changed, 218 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_real_registry_is_behaviorally_clean` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_wrong_implemented_claim_fails` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_consumer_repo_is_silent_even_with_a_broken_claim` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_repo_root_with_no_pyproject_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_fires_through_real_gate_dispatch` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 43 error(s), 1123 warning(s), 679 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
