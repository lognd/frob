## Done report

Changed: both deferred-work directives now self-reference this ticket
(`src/frob/fuzz/_run.py:28 # frob:todo T-0300`, `src/frob/fuzz/_arbitrary.py:41
# frob:todo T-0300`) instead of the dropped T-0002. The rebind was already
carried in a prior commit on this branch (`0f25766` "finalize T-0300
fuzz-todo tracker", landed via the T-0294 chain and pulled forward by this
worktree's `git merge main`); this pass verified it is still correct after
the merge and closed the bookkeeping loop (Done report + close), which had
not been recorded. Both deferrals remain genuinely open v1 limits (process-
global generator registry; budget_s is example-count not wall-clock), not
resolved work -- rebinding onto T-0300 itself is correct since T-0300 IS the
"track these as real open work" ticket; no further successor ticket is
needed unless someone picks up the wall-clock-budget or per-project-registry
work, at which point it should be re-rebound onto that new ticket.
Evidence: recorded via `frob ticket evidence T-0300` (exit=0):
`tests/test_fuzz.py::TestResolve::test_registered_type_resolves` (exercises
`_arbitrary.py`'s `register`/`resolve` against `_REGISTRY`, the process-
global-registry TODO's owning symbol), plus
`tests/test_fuzz.py::TestRunFuzz::test_derived_model_produces_examples` and
`tests/test_fuzz.py::TestRunFuzz::test_digests_map_is_stamped_onto_matching_ref`
(exercise `_run.py`'s `run_fuzz`/`_examples_for_budget`, the budget_s TODO's
owning functions). Full `tests/test_fuzz.py` run: 36 passed, 1 skipped.
Filed: none -- no out-of-scope work found.
Gates: `uv run frob check --ticket T-0300` clean (0 errors, 133 warnings
none new, 43 waived; TODO001 does not fire for either directive). The lone
ruff-check E501 seen in a full `uv run ruff check .` run is in
`src/frob/testing/_select.py`, outside this ticket's `src/frob/fuzz/**`
scope, pre-existing, untouched.
