## Done report

Changed:
- tests/system/test_frob_self_model.py::TestFrobSelfModel.test_sys_gate_zero_violations

Disposition, TEST009 (fresh worktree showed 1 finding, not 2 -- see honest
summary below):
- `design/frob.strata` had zero e2e edges by `_edges_for_design_file`'s
  target-match rule (`target == design_file` or
  `target.startswith(design_file + "::")`), even though
  `TestFrobSelfModel` already carries three `kind="e2e"` directives (lines
  48, 116, 178). Root cause: all three target the TEST METHOD's own
  symref (`tests/system/test_frob_self_model.py::TestFrobSelfModel.test_*`)
  -- a repo-wide idiom (also used in `tests/system/test_cli_check.py:328`)
  for marking a test as self-covering for TEST001/002 purposes -- not the
  design file itself, so none of the three ever matched TEST009's
  design-file prefix check. This is a real gap, not a gate false-positive:
  no existing e2e edge actually named `design/frob.strata` as its target.
  Fix: added a second directive, `frob:tests design/frob.strata
  kind="e2e"`, on `test_sys_gate_zero_violations` -- the one test in the
  module that runs frob's real `build_graph` + `sys_gate` path against
  this repo's own live `design/frob.strata` (not a synthetic fixture),
  making it the genuinely correct e2e evidence for the design file as a
  deployable artifact. Verified: TEST009 no longer appears in `frob check
  --only test` output.

Disposition, TEST006 (1 finding, both before and after -- the "no
coverage stamp found" variant, not a per-file staleness variant):
- `.frob/coverage-stamp` does not exist in this fresh worktree (confirmed:
  it is not a tracked/committed path -- `git ls-files | grep
  coverage-stamp` and `git log --all -- .frob/coverage-stamp` both return
  nothing; it is local, gitignored, per-checkout state written only by
  `stamp_coverage`/`make coverage`). This is the structural "missing
  stamp" branch of TEST006 (`src/frob/gates/__init__.py`'s
  `_missing_stamp_violation`), not the "stale stamp for file X" branch
  (`_stale_stamp_violations`) the ticket's "is a file excluded from
  coverage.xml? a native module?" framing anticipated investigating --
  there is no stamp at all to compare file hashes against, so there is no
  per-file root cause to chase in this checkout.
- This exact condition and its handling is extensively precedented across
  `tickets-archive.md` (e.g. T-0172, T-0234, T-0250 Done reports) as
  standing, campaign-wide debt that no single ticket resolves: the agent
  playbook (`docs/guides/agent-playbook.md` section 6b) explicitly
  forbids running `make coverage` as a dispatched sub-agent (backgrounds
  past the foreground cap; completion routes to the coordinator, not this
  agent) -- the coordinator is the one that runs `make coverage` +
  `frob check --stamp-coverage` at land, against the merged result.
  Producing a stamp here would mean either violating that rule, or
  fabricating/partially-stamping coverage data, which would be dishonest
  evidence.
- No `frob:waive TEST006` was added: `.frob/coverage-stamp` is not a
  scanned source location the comment-DSL can bind a waiver to (waiver
  matching is by `violation.file`/`violation.symref` against a real
  source file's directive), and no prior ticket in this repo's history has
  ever waived TEST006 for this reason -- consistent with treating it as
  self-resolving at land rather than something to suppress.
- Honest summary: TEST006 is NOT at 0 and was not driven to 0 in this
  worktree; it is the well-understood, pre-existing "no local coverage
  stamp yet" condition that always accompanies a fresh worktree and
  clears itself once the coordinator runs `make coverage` +
  `--stamp-coverage` at land. This was investigated (not assumed) and is
  not a per-file staleness bug, not a coverage.xml exclusion issue, and
  not a native-module gap.

Filed: T-draft-40bc61f0 (never refiled) ("TEST001: collect_file_dispatch_refs missing
unit test binding") -- found while measuring `frob check --only test`
before/after; a pre-existing, unrelated TEST001 error introduced by
T-0360 (`fix(arch): make dispatch-family linking structural, not
textual`), out of this ticket's TEST006/TEST009 scope. Off-default-branch
provisional id per `frob ticket new`'s own behavior; will renumber at
land.

Evidence: `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations`
(recorded via `frob ticket evidence T-0365`; full module run --
`uv run pytest tests/system/test_frob_self_model.py -p no:cacheprovider -q`
-- 4 passed).

Before/after (`uv run frob check --only test 2>&1 | grep -vE "waived" |
grep -cE "TEST006|TEST009"`): before 2 (1 TEST006 + 1 TEST009 in this
worktree -- not the ticket's originally-filed 2+2, already partly
resolved upstream of this worktree), after 1 (the TEST006 "no coverage
stamp" structural condition described above; TEST009 is 0).

Gates: `uv run frob check --ticket T-0365` -- gates scoped to this
ticket's touched file pass (TEST009 resolved); `uv run frob check`
(repo-wide) still reports the pre-existing TEST006 warning above and 4
unrelated errors (including the newly-not filed T-draft-40bc61f0 (never refiled) TEST001
gap), none introduced by this change. No waiver added; none applicable
per the reasoning above.

Not closing -- review-gated per the agent playbook; leaving for the
reviewer.
