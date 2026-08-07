---
id: T-1067
title: 'arch: abstraction-opportunity per-package extraction pass (T-0393 remainder)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
- tests/test_vet_containment.py
- docs/modules/testing.md
- docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_vet_containment.py
  reason: T-1067 extracted a shared vet TTL-cache helper and gitio.excerpt; needed
    to update this test fixture and these docs' Public API sections
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/testing.md
  reason: T-1067 extracted a shared vet TTL-cache helper and gitio.excerpt; needed
    to update this test fixture and these docs' Public API sections
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/vet.md
  reason: T-1067 extracted a shared vet TTL-cache helper and gitio.excerpt; needed
    to update this test fixture and these docs' Public API sections
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gitio.py::TestWorkingDiff::test_bad_base_ref_is_git_failed
- tests/test_gitio.py::TestWorkingDiff::test_diff_command_failure_propagates
- tests/test_testing.py::TestRunners::test_exit_code_is_data
- tests/test_vet_containment.py::TestFetchCweForCve::test_cached_body_parses_cwe_ids
- tests/test_vet_containment.py::TestFetchCweForCve::test_malformed_cached_body_degrades_without_raising
- tests/test_vet_containment.py::TestFetchCweForCve::test_expired_cache_entry_triggers_a_fresh_fetch
designated_repro_test: null
threat: null
component: null
---
Filed from T-0393 (failed as too large for one pass). After the sibling
language-parity detector-precision ticket lands (arch/_kotlin.py,
arch/_async_hazards.py, arch/_concurrency_model.py, arch/_cpp.py family),
re-measure `uv run frob check --only arch --json` for abstraction-opportunity
and split the remaining single-file groups (src/frob/app/**,
src/frob/gates/__init__.py's several groups, src/frob/check/**,
src/frob/lang/**, src/frob/tickets/__init__.py, src/frob/render/_renderer.py,
src/frob/dup/**, src/frob/perf/**, src/frob/gitio.py,
src/frob/process/parsers/cargo.py, src/frob/serve/_tools.py,
src/frob/testing/_collect.py -- ~35-40 groups after the language-parity
family is removed from the count) into per-package-sized follow-up tickets,
each genuinely extracting shared code or accepting the coincidental-
signature collision is correctly un-flaggable (raise as a T-0370-style
detector refinement if a whole additional false-positive class turns up,
same "teach the detector" path, not a code-comment waiver -- category is
unwaivable). Do not attempt all ~40 in one ticket; src/frob/gates/__init__.py
alone carries ~15 of these groups and is a large-file residue candidate in
its own right (see T-0395's sibling ticket).