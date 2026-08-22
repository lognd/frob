## Done report

Investigation, per rule group (re-measured every one of the 137 quarantined
(rule, file) identities against the current tree with `frob check --json
--no-cache`, filtered by exact (rule_id, file) pair -- see
`scripts/check_summary.py` traversal):

- 136 of 137 identities matched a diagnostic that IS still produced by the
  detector, but every one of those 136 already carries a pre-existing
  `frob:waive` directive (severity downgraded to `note`, non-blocking).
  None of the 136 were newly introduced code; they are pre-existing,
  already-reviewed debt that the T-2713/T-2715 measurement repair simply
  observed for the first time under a complete (not budget-truncated) run.
  This matches the ticket's own "detection event, not a regression"
  analysis exactly: one underlying cause (a measurement gap, now fixed
  upstream of this ticket) explains all 136, not 136 independent code
  problems. No code change was needed or made for these 136 -- forcing a
  fix or a fresh waiver on an already-legitimately-waived site would be
  waiver churn with no debt-reduction value, and this repo has a standing
  policy against exactly that (T-1614's audit; see T-2719/T-2720).
- 1 of 137 identities (`E501  src/frob/_cli_parsers/_ticket/_closeout.py`)
  was genuinely unwaived: line 23's docstring was 93 chars against ruff's
  88-char limit. This is the "1 actual finding" the ticket's own
  independent re-measurement already called out. Fixed by wrapping the
  docstring across two lines; no detector logic touched.

Verified both directions per the ticket's hazard warning:
- The named site (`_closeout.py:23`) no longer reproduces E501 after the
  fix (`frob check --json --no-cache --only ruff`, confirmed empty for
  that file/rule pair).
- A planted genuine E501 violation still fires: this repo already carries
  a dedicated positive-control fixture for exactly this
  (`tests/fixtures/bad_python/src/bad_python/errors.py`, an over-length
  line) exercised by `tests/unit/test_executable.py::TestRuffExecutable::
  test_ruff_finds_errors_in_bad_python`, which passed unmodified after the
  fix -- ruff's own E501 detector was not touched by this change at all,
  so there was no risk of a narrowing regression, but the control was run
  to be sure.

No group required a code-level "fix the cause" the way T-1614's audit did,
because 136/137 needed no fix at all (already legitimately waived) and the
1 remaining was a single independent formatting slip, not a systemic
pattern.

Changed:
- src/frob/_cli_parsers/_ticket/_closeout.py::_add_ticket_attach_and_lifecycle_end_parsers (docstring only, wrapped to fit E501's 88-char limit)

Evidence: tests/unit/test_executable.py::TestRuffExecutable::test_ruff_finds_errors_in_bad_python (pre-existing positive-control test for ruff's E,F,W rule family including E501; passed post-fix)

Filed: none -- no out-of-scope work discovered

Gates: `frob check --json --no-cache --only ruff` clean for the fixed
file/rule pair; `frob check --json --no-cache --only arch --only gates`
confirms all 136 other quarantined identities sit at `note` severity
(non-blocking, correctly waived) with zero non-note-severity hits among
them. The repo-wide error floor unrelated to this ticket's 137 identities
(COV/DOC/DRIFT/PII/RENDER/etc., ~80+ errors) predates this ticket and is
out of scope for T-2732.
