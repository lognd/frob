## Done report

CONCLUSION: `_CACHEABLE_PROCESS_GATES` membership stays CURATED, not fully
derived. "Cacheable" depends on whether a gate reads anything beyond
`st.root`/`st.repo_root`/`st.snapshot` (unconditionally covered by
`root_content_key`) plus a scalar side channel folded via
`_process_gate_extra` -- verifying that is true for a given gate requires
reading its body (does it also touch env vars, wall-clock time, or other
un-modeled state), which is exactly the judgement call that got
"deprecated"/"capability_conformance" explicitly EXCLUDED from the sibling
`_CACHEABLE_GATES` despite superficially similar signatures. A mechanical
check over `_ProcessJob.args` cannot see inside the gate function to rule
that out, so full derivation would be unsound in general -- this is one of
the "must stay curated" cases T-4333 flagged, not a "genuinely derivable"
one. What IS derivable, and now derived rather than hand-copied, is the
SET OF NAMES a completeness check needs to cover: `_PROCESS_JOB_NAMES` is
built by calling the real `_build_process_jobs` with a placeholder
`_GateInputs` (cheap -- the function only forwards `st` fields by
reference into `_ProcessJob.args`, never dereferencing them), so this
completeness check can never itself drift from `_build_process_jobs` the
way `_CACHEABLE_PROCESS_GATES` silently did.

Implemented the T-4336 model requested in the ticket's own plan: an
import-time assert requiring every `_build_process_jobs` entry to be
categorized in exactly one of `_CACHEABLE_PROCESS_GATES` (existing) or a
new, empty-today `_KNOWN_UNCACHEABLE_PROCESS_GATES` (new, documented
allowlist for a future real exception), plus a disjointness assert.

Fixing the check to be non-trivial immediately surfaced the real drift the
ticket's parent survey predicted: twelve `_build_process_jobs` entries
(the T-2390-epic schema gates plus `flag_coverage`) were already missing
from `_CACHEABLE_PROCESS_GATES` despite each reading only `st.repo_root` --
exactly the shape the frozenset's own docstring already claimed was fully
covered. Added all twelve.

Verified by forcing the condition per the ticket's instruction, not just
checking the currently-correct state:
- `test_completeness_check_fires_when_a_gate_is_unregistered` removes one
  real gate from both curated sets and asserts the completeness equality
  goes FALSE.
- `test_completeness_check_is_silent_once_a_gate_is_registered` adds a
  hypothetical new gate to `_KNOWN_UNCACHEABLE_PROCESS_GATES` and asserts
  equality is restored.
- `test_import_time_assert_is_clean_on_the_real_module` pins today's real
  state as clean (the module already imports without raising).
- `test_process_job_names_is_derived_not_hand_copied` asserts
  `_PROCESS_JOB_NAMES` is produced by calling the real function, not a
  second hand-maintained literal.

Changed:
- src/frob/gates/__init__.py::_CACHEABLE_PROCESS_GATES (12 gates added)
- src/frob/gates/__init__.py::_process_job_names_gate_inputs (new)
- src/frob/gates/__init__.py::_PROCESS_JOB_NAMES (new)
- src/frob/gates/__init__.py::_KNOWN_UNCACHEABLE_PROCESS_GATES (new)
- tests/test_gate_cache.py::TestCacheableProcessGatesCompleteness (new, 4 tests)

Evidence: `uv run pytest tests/test_gate_cache.py -q` (50 passed, includes
the 4 new tests); `uv run frob check --ticket T-4361` (0 errors across all
gates, `ty`/`ruff-check`/`ruff-format` clean); `uv run frob test --base main`
(python exit=0, 3 outcomes recorded).

Filed: none -- no out-of-scope work found; the twelve-gate fix was inside
this ticket's own scoped declaration (`_CACHEABLE_PROCESS_GATES`).

Gates: `frob check --ticket T-4361` clean, 0 errors, no waivers added for
this change.

### Changed
```
 src/frob/gates/__init__.py    | 95 ++++++++++++++++++++++++++++++++++++++++++-
 tests/test_gate_cache.py      | 84 ++++++++++++++++++++++++++++++++++++++
 tickets/T-4361/done-report.md | 82 +++++++++++++++++++++++++++++++++++++
 tickets/T-4361/ticket.md      | 15 ++++++-
 4 files changed, 274 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gate_cache.py::TestCacheableProcessGatesCompleteness::test_import_time_assert_is_clean_on_the_real_module` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestCacheableProcessGatesCompleteness::test_completeness_check_fires_when_a_gate_is_unregistered` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestCacheableProcessGatesCompleteness::test_completeness_check_is_silent_once_a_gate_is_registered` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestCacheableProcessGatesCompleteness::test_process_job_names_is_derived_not_hand_copied` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 4814 warning(s), 958 waived
- error-findings: none (measured, zero errors)
