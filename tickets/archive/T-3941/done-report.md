## Done report

- src/frob/xref/__init__.py::xref (rel path built with .as_posix() instead of str(), both the relative-to-root case and both fallback branches)
- tests/unit/test_xref.py::test_definition_and_usage_file_fields_are_posix_style (new, the third fixture the ticket calls for)

Evidence:
- tests/unit/test_xref.py::test_definition_and_usage_file_fields_are_posix_style
- tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_positive_control_reintroduced_branch_is_flagged
- tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_pre_t2361_shape_is_flagged
- Also run (not bound as evidence, all pass, 120 total): tests/unit/test_xref.py, tests/unit/gates/test_profile_boundary.py, tests/unit/test_app_runners.py, tests/unit/test_exports.py, tests/system/test_cli_xref.py

Fix chosen: (a), normalize at the xref() producer via .as_posix(), per
the ticket's own preference and reasoning. Not overridden.

Audit result (per-site, per acceptance criterion 3):
- frob.app.xref_runner: display only (xr.as_text()/as_json()), no comparison -- safe.
- frob.exports.exports_consumers: passes usage.file through to ConsumerRef.file, display only in its one caller (exports_runner) -- safe.
- frob.gates._prework: computes its own scan_path_rel via .as_posix() already; only reads xref_result.danger_ok.symbol (a name, not usage.file) -- safe, unaffected by the bug either way.
- frob.gates._profile_boundary: the confirmed defect, fixed at the producer per above.

Wider audit result (acceptance criterion 4, "how many other gates silently return zero on Windows"):
Method: git grep for every `str(...relative_to(...))` site under src/frob/gates/ (7 files, 9 call sites total), then traced each site's `rel` variable to its actual downstream use (a forward-slash literal comparison = confirmed risk; a git pathspec argument = lower/different risk since git accepts native separators; display-only = no risk).

Confirmed same-class defects (rel fed unnormalized into frob.excludes.is_excluded/is_test_file, both of which require POSIX-style input by their own documented contract):
  - src/frob/gates/_exhaustive_handling.py (EXHAUST001/2/3) -- filed T-3948
  - src/frob/gates/_ffi_boundary.py, the FFI002 site only (_ffi002_violations); the FFI001 site's rel/rs_rel are display-only, not compared -- filed T-3947

Checked clean (already .as_posix()-normalized or sourced from git ls-files, which is always forward-slash on every platform):
  _vmodel.py, _waive_comments.py, _policy_weakening_gate.py (as_posix already);
  _refs.py, _cve_fingerprint_scan.py, _pii_structural, _comment_placement.py,
  _exclude_hazard.py, _narrative_blocks.py, _opaque.py (git ls-files backed);
  _parse_failures.py (frob.lang._display_path already uses as_posix()).

Lower-confidence, not counted as a confirmed hit: _decisions_compliance.py
and _registry_exhaustiveness.py's remaining relative_to() sites pass their
rel string to `git log -- <path>` as a pathspec argument (path_ever_tracked),
not to a Python string-literal comparison; git generally accepts native
path separators in a pathspec on Windows, a materially different (and
likely lower) risk profile than PROFILE001's direct string compare. Not
verified against real Windows git.

TOTAL COUNT: 3 confirmed same-class defects found this audit (PROFILE001,
fixed in this ticket; EXHAUST001/2/3 and FFI002, filed as follow-ups).
This is not a claim of exhaustive coverage of the entire ~96-file gate
catalog -- it covers every site that builds a relative path via
relative_to() the same way PROFILE001 did; a gate deriving its path
strings by some other means (not audited here) could still be at risk
of a different-shaped version of the same class.

Filed: T-3948 (EXHAUST001/2/3), T-3947 (FFI002) -- both routed to production code outside this ticket's scope, not picked up.

Gates: frob check --ticket T-3941 --only gates ran to completion (~9 min
under noted high machine load); 12 pre-existing errors, all in
gate:DOC/DRIFT/PRE/SCOPE against ticket T-3116 and src/frob/app/
ticket_runner/_land_cmd.py -- unrelated to this ticket's scope, present
before this change. gate:profile_boundary and the touched-set pytest run
both report clean.

Not verified: this fix has not been run against real Windows CI. The
mechanism was confirmed directly (PureWindowsPath reproduction showing
the pre-fix str() output fails _SRC_PREFIX.startswith() and the post-fix
as_posix() output passes it), not inferred, but a real Windows run is
still the acceptance criterion's own stated bar ("proven by the existing
positive controls" on Windows) and has not happened yet.

### Changed
```
 src/frob/xref/__init__.py          | 15 +++++++-
 tests/unit/test_xref.py            | 31 +++++++++++++++
 tickets/T-3941/ticket.md           |  4 ++
 tickets/T-3947/ticket.md | 64 ++++++++++++++++++++++++++++++
 tickets/T-3948/ticket.md | 79 ++++++++++++++++++++++++++++++++++++++
 5 files changed, 191 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_xref.py::test_definition_and_usage_file_fields_are_posix_style` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_positive_control_reintroduced_branch_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_pre_t2361_shape_is_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 4 error(s), 4395 warning(s), 931 waived
- error-findings: DOC006@tickets/T-3931/ticket.md, DRIFT001@src/frob/xref/__init__.py, PRE001@tickets/T-3941, SCOPE002@tickets.md
