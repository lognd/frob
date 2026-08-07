## Done report

Root cause: the T-0265 evidence id (tests/test_gates.py::TestSelfReferentialTestsDirectiveScopeAgreement::test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff) does NOT correspond to a test class/method that was ever removed from tests/test_gates.py. `git log -S"TestSelfReferentialTestsDirectiveScopeAgreement" -- tests/test_gates.py` shows exactly two commits touching that string, both ADDING it (56e108a6 and 3d798536, T-0265's own landing), never deleting it. The class and its one test method (test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff) are present at this worktree's own base commit (d27fbcec, before any merge in this session) and remain present now. `uv run pytest tests/test_gates.py --collect-only -q -o addopts=""` (the exact invocation frob.testing._collect.collect_python_tests uses) collects the node id cleanly, and `uv run pytest "tests/test_gates.py::TestSelfReferentialTestsDirectiveScopeAgreement::test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff" -q` passes.

T-0704's own body was filed "while working T-0340 (native-rebuild Makefile guard)" -- a ticket specifically about broken/stale native rebuilds. The most likely explanation for the "grep confirms zero hits" claim at filing time is an environment artifact in that session (an un-rebuilt-natives worktree, or a stale .frob/pytest-collect.json collection cache causing a bogus COV003 read), not an actual removal from source -- consistent with docs/guides/agent-playbook.md section 1's own warning that a collection failure in a fresh/stale worktree "is an environment artifact, not a regression."

Remedy: no code or test change was needed -- the tested behavior still exists under the exact recorded evidence id, and it resolves. Verified with `uv run frob check --only gates-fast`: `gate:COV 0 errors, 21 warnings, 87 waived` in the Tool summary, and zero occurrences of the string "COV003" anywhere in that command's full output (i.e. it does not fire for T-0265 or anything else). This directly demonstrates the acceptance criterion (zero COV003 for T-0265 on a full check pass covering the coverage gate).

T-0265's own ticket block lives in tickets-archive.md, which is outside T-0704's declared scope (tickets.md, tests/test_gates.py) -- no edit to T-0265's evidence was made or was needed, since the recorded id already resolves and was never stale. This finding is "does not reproduce": T-0704's own evidence below (a fresh, targeted collection+run of the exact node id) is what proves it.

### Changed
```
 tickets.md | 512 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 504 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestSelfReferentialTestsDirectiveScopeAgreement::test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff` (pytest node id, verified passing when recorded)
