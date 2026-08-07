## Done report

Root cause: `frob.gitio.working_diff` (the ONE diff seam this repo uses
everywhere) diffs the working tree against `merge-base(HEAD, base_ref)`,
never against `base_ref`'s CURRENT tip. `_touched_python_files`
(src/frob/tickets/_mutation_evidence.py) fed this diff straight into the
T-0755 mutation-evidence obligation without correcting for that. In a
stacked multi-ticket worktree, once a sibling ticket committed earlier on
this same branch has separately LANDED (squash-applied onto the real
`base_ref` elsewhere by `frob ticket land`), the merge-base still
predates that land -- the sibling's file keeps enumerating as "touched"
relative to the stale merge-base even though `base_ref`'s tip now already
carries identical content. The mutation-evidence check then mutates code
this ticket did not actually change, kills zero mutants of it (nothing in
the ticket's own bound evidence targets unrelated sibling logic), and
wrongly refuses the land as TEST016 EvidenceConfirmatoryOnly -- exactly
the T-0847/T-0848/T-0850 incident the ticket names.

Fix: added `_matches_base_ref_tip` (src/frob/tickets/_mutation_evidence.py),
which compares a candidate file's CURRENT on-disk content against
`git show <base_ref>:<file>` (the tip, not the merge-base). Best-effort:
any git failure (file absent at base_ref, unresolvable ref) returns
`False`, never silently exempting a file this check cannot actually
verify. `_touched_python_files` now excludes any candidate this returns
`True` for, even though `working_diff`'s merge-base-relative diff still
lists it -- stacked-worktree noise, not a genuine unlanded change. A
genuinely still-unlanded file (this ticket's own real diff) is
unaffected: `base_ref`'s tip does not yet have its content, so the
comparison correctly returns `False` and it stays in the candidate set.

Direction taken vs the ticket's own two suggestions ("run the precheck
against the post-merge state" or "skip files whose worktree content is
identical to main's blob"): implemented the second -- narrower, entirely
within `_mutation_evidence.py`'s own scope, and does not require
reordering `_land.py`'s precheck-before-merge sequencing (which several
other pre-merge checks, e.g. T-0854's live-tracker citation check, also
depend on running BEFORE any git mutation).

Added TestTouchedPythonFiles::test_already_landed_sibling_content_excluded
(tests/test_tickets_mutation_evidence.py): a real git-fixture repro of
the exact incident -- a sibling-ticket file changed identically on both
this branch and a divergent `main` (different commits, same content) is
excluded, while a genuinely still-unlanded file on this same branch is
still reported. Plus two direct unit tests for `_matches_base_ref_tip`
(identical / differing content). Scope extended by one file,
tests/test_tickets_mutation_evidence.py (reason recorded via `frob
ticket scope --add`) -- the module's existing test home, not a new file.

Verified: `uv run pytest tests/test_tickets_mutation_evidence.py::
TestTouchedPythonFiles tests/test_tickets_mutation_evidence.py::
TestEvidenceTestIds -p no:cacheprovider -q` -- 7 passed. `uv run frob
check --only lint/static/gates-fast/gates-native/gates-security --ticket
T-0855` (chunked per playbook 3b): all five stage groups report 0 errors
(gates-fast needed a `frob ticket scope T-0855 --add
tests/test_tickets_mutation_evidence.py` plus a `frob:ticket T-0855`
class-level marker on the new test class to clear SCOPE001/COV002, then
0 errors). ruff clean on both PATH ruff and `uv run ruff` for both
touched files.

Deliberately NOT run as part of this verification pass: the pre-existing
`TestCheckTicketMutationEvidence` class in the same test file (including
its own `test_self_check_t0755_own_diff_zero_error_findings` self-check),
which mutates this repo's OWN real source files in place
(src/frob/tickets/_mutation_evidence.py, src/frob/tickets/_land.py) as
part of its dogfooding design. Running the FULL test file under this
session's heavy concurrent machine load corrupted
src/frob/tickets/_mutation_evidence.py on disk twice -- once when an
external `timeout` wrapper killed the run mid-mutation, once when a
pytest-xdist worker crashed outright mid-mutation -- in both cases
leaving a mutant applied with no automatic revert. Recovered both times
via `git show HEAD:<path>` (the file was never committed in the
corrupted state). This is a real, pre-existing reliability gap
(T-0857 covers frob.mutate's own internal crash detection/restore, but
neither an external SIGTERM nor an xdist worker crash goes through that
path) -- filed as T-0890 (refiled: the original draft did not survive a later git merge main, the T-0577 draft-loss class) rather than fixed here (out of
T-0855's declared scope, which is `_land.py`/`_mutation_evidence.py`'s
OWN logic, not `frob.mutate`'s crash-recovery machinery). My own new
`_touched_python_files`/`_matches_base_ref_tip` code and its 5 tests were
verified clean and complete without needing that class at all.

### Changed
```
 tickets.md | 114 +++++++++++++++++++++++++++++++++++++++++++++++++++++++------
 1 file changed, 103 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_already_landed_sibling_content_excluded` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_matches_base_ref_tip_true_for_identical_content` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_matches_base_ref_tip_false_for_differing_content` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_filters_to_scope_and_python` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestPlannedStateAutoAdvanceOnLand::test_planned_ticket_with_full_evidence_lands_to_done` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 2229 warning(s), 220 waived
- error-findings: TICK003@tickets.md
