## Done report

Shipped the per-PROJECT half of T-0405's conformance contract as two new
gate rules, both on by default via additive registration in gates/__init__.py
(a sibling agent owns that file's own-module content; only import lines,
frozenset entries, and dict entries were appended):

- LANG002 (ERROR, always): frob.gates._lang_conformance.
  project_lang_conformance_gate scans the repo's real tracked file tree
  (via frob.excludes.iter_files) for well-known candidate-language
  extensions (Kotlin/Swift/Go/Java/Ruby/C#) frob has ZERO frob.lang
  grammar registration for at all -- a file matching one gets a named,
  per-file ERROR finding instead of silent zero coverage.

- LANG003: for a registered language's KNOWN_GAP facet cell (T-0405)
  whose language is actually PRESENT in the repo's tree, the gate
  verifies the cell's `detail` against the LIVE ticket queue (the same
  anti-lie check frob.gates._registry_exhaustiveness performs for
  handled_by/deferred): a real, currently-open tracking ticket keeps it a
  WARN (honestly tracked, loud but not a build-breaker); a missing,
  unparseable, or already-closed/dropped ticket reference escalates to
  ERROR (a claimed gap that does not verify is unsound coverage
  masquerading as tracked coverage). NOT_APPLICABLE cells never need a
  ticket (the facet genuinely does not apply).

frob's own repo currently shows 5 LANG003 WARNs (c/cpp docblock ->
T-draft-78a0f919 filed this session; typescript/rust/c arch -> T-0329,
already open) and 0 LANG002 findings (no Kotlin/Swift/Go/Java/Ruby/C# in
this tree) -- all honestly accounted for, gate passes with 0 errors.

Counterexample proof (tests/test_lang_conformance_gate.py::
TestProjectLangConformanceGate, synthetic tmp_path fixture repos, same
posture as tests/test_registry_exhaustiveness.py's synthetic manifests):
a repo with only a .kt file fails LANG002 by name; a repo with only
python passes cleanly; a repo with rust files warns while the arch gap's
tracking ticket (T-0329) stays open in the fixture queue, and escalates
to ERROR the moment that same fixture ticket is marked done.

Cuts: requirement (2) in the ticket body ("the other structural
remediations... likewise ship as gate families") is already satisfied by
gates that exist and are wired on by default today (REG001-007 registry
exhaustiveness/T-0343, REF001-003 orphan gate/T-0396, TEST001-011 test
coverage) -- no new work was needed there; this ticket's actual net-new
scope was requirement (1), LANG002/LANG003. Did NOT verify against a real
sibling repo checkout -- the worktree sandbox refuses git/file operations
that redirect outside this worktree, so verification is via synthetic
tmp_path fixture repos instead (the same convention this suite already
uses for frob.gates._registry_exhaustiveness's synthetic manifests).
REL001 required a second version bump this session (0.67.0 -> 0.68.0);
frob release stamp run, pyproject.toml/.frob-release.json/uv.lock scope-
widened onto T-0406 with a recorded scope_changes reason.

Housekeeping: doing two tickets sequentially in one worktree surfaced a
real gap in the playbook's section 10b ledger-finalization recipe -- its
`git checkout main -- tickets.md` step assumes "main" already reflects
any PRIOR ticket you closed in this same session; it does not, when the
prior ticket's closure lives only on this worktree's own branch (not yet
landed anywhere else). Running that recipe for T-0406 silently reverted
T-0405's already-committed closure back to queued. Caught immediately via
`git checkout <pre-restore-commit> -- tickets.md` (not another `main`
checkout, not a stash) before writing this Done report; verified both
T-0405 (done) and T-0406 (in-progress) are correct afterward. Left as-is
rather than running the restore-to-main dance a second time, since no
OTHER agent's tickets are at stake in this solo two-ticket session -- the
ledger already reflects reality accurately without it.

### Changed
```
 .frob-release.json                  |  17 +-
 docs/modules/lang.md                |  85 +++++++++
 pyproject.toml                      |   2 +-
 src/frob/gates/__init__.py          |  32 ++++
 src/frob/gates/_lang_conformance.py | 256 +++++++++++++++++++++++++
 src/frob/lang/__init__.py           |  14 ++
 src/frob/lang/_support.py           | 365 ++++++++++++++++++++++++++++++++++++
 tests/test_lang_conformance_gate.py | 110 +++++++++++
 tests/test_lang_support.py          | 110 +++++++++++
 tickets.md                          | 196 ++++++++++++++++++-
 uv.lock                             |   2 +-
 11 files changed, 1181 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_unregistered_language_file_fails` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_all_conformant_project_passes` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_present_known_gap_with_open_ticket_warns` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_present_known_gap_with_bad_ticket_ref_errors` (pytest node id, verified passing when recorded)
