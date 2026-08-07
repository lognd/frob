---
id: T-0784
title: 'gitio: promote git_common_dir to the single git seam (3 divergent copies)
  + batch the lease-write double spawn'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gitio.py
- src/frob/tickets/_leases.py
- src/frob/gates/_exclude_hazard.py
- tests/test_gitio.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir
- tests/test_gitio.py::TestGitCommonDir::test_err_when_not_a_repo
- tests/test_gitio.py::TestGitCommonDir::test_memoized_per_root
- tests/test_gitio.py::TestGitCommonDir::test_reset_clears_cache
- tests/test_gitio.py::TestCommonDirAndBranch::test_single_spawn_parses_both_lines
- tests/test_gitio.py::TestCommonDirAndBranch::test_err_when_not_a_repo
designated_repro_test: null
acceptance:
- text: GIVEN the repo WHEN searched for rev-parse --git-common-dir call sites THEN
    exactly one implementation exists (frob.gitio) and _leases/_exclude_hazard delegate
    to it; GIVEN record_lease THEN common-dir and branch are fetched in one spawn
    not two
  evidence:
  - tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir
threat: null
component: null
---
Audit M3 + L1: three near-identical git-common-dir resolvers (Result vs Path|None error channels) violate the single-seam claim in gitio's own docstring; a fix to one silently desyncs the others. Promote git_common_dir(root) -> Result into frob.gitio; batch record_lease's two spawns (rev-parse --git-common-dir + branch --show-current) into one. COORDINATE: T-0773 adds memoization for the same function -- land T-0773 first, then this refactor moves the memoized seam, or merge scopes if the same implementer takes both.