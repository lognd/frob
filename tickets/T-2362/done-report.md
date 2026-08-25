## Done report

Changed: frob.gates._profile_boundary::profile_boundary_gate (new),
frob.gates._profile_boundary::_symbol_usages (new, private),
frob.gates.__init__ (import/registration in both --only orderings +
the gate dispatch dict + __all__), frob.gates._waive::_KNOWN_GATE_RULES
(registered PROFILE001), tests/unit/gates/test_profile_boundary.py (new),
docs/modules/gates.md (rule-catalog row + frob:enumerates members= entry),
docs/modules/tickets-verify-sweep.md (PROFILE001 paragraph under the
existing Land profile settings section)

Built PROFILE001 (frob.gates._profile_boundary.profile_boundary_gate):
flags every `src/frob/**` reference to `frob.tickets._profile.
ProfileName` outside `src/frob/tickets/_profile.py`/`src/frob/verify/
_backpressure.py` at `Severity.ERROR`. Uses `frob.xref.xref(symbol,
root, lang="python")` -- the SAME tree-sitter-backed identifier
resolution `frob explore xref` already runs by hand, per the standing
"symbolic, never lexical" constraint -- restricted to `.py` files, which
routes through `frob.lang.iter_identifiers`, not a text/regex scan.

Deliberately checks `ProfileName` ONLY, not `effective_profile`/
`configured_profile`: my first draft flagged those too and immediately
produced 14 false positives against the CURRENT clean tree (every
already-migrated call site legitimately calls `effective_profile(root)`
to obtain the resolved profile before handing it to `settings_for_
profile`; `frob.app.profile_runner`'s T-1681 CLI also legitimately
calls `configured_profile` to display raw config state). Caught this by
actually running the gate against the real repo before writing tests
for it, not by inspection -- disclosed in the module's own docstring so
a future reader does not "fix" this back to the broken shape.

Control fixtures (tests/unit/gates/test_profile_boundary.py):
- POSITIVE CONTROL: a deliberately reintroduced `if profile is
  ProfileName.RAPID` fixture (test_positive_control_reintroduced_
  branch_is_flagged) -- fires, >=3 hits.
- NEGATIVE CONTROL: the post-migration settings-record-only shape
  (test_negative_control_settings_layer_only_is_silent) -- silent.
- The settings-resolver layer's OWN files, which reference ProfileName
  constantly by construction, never self-flag
  (test_settings_resolver_layer_itself_is_never_flagged).
- tests/** is out of scope, matching T-2361's own xref exclusion
  (test_tests_directory_is_not_scanned).
- REAL pre-T-1696 source (not a synthetic fixture), verified separately:
  checked out src/frob/tickets/_land.py, _evidence.py, src/frob/app/
  ticket_runner/_land_cmd.py, _close_cmd.py from 62454eb7f~1 (the commit
  immediately before T-1696 landed the actual migration) into a scratch
  dir and ran the gate against that tree directly via an ad hoc script
  -- it fires at all 6 of the originally-measured seams (_land.py's two
  branches, _land_cmd.py's three, _evidence.py's one, _close_cmd.py's
  one; exact line numbers shifted slightly from T-2360's 2026-08-17
  measurement). Not committed as a permanent fixture (ad hoc, not
  reproducible without the scratch checkout) -- test_pre_t2361_shape_
  is_flagged instead embeds a hand-written excerpt of the same
  `_evidence.py` shape as a self-contained, permanent regression test.
- Verified 0 findings against the current post-T-2361 tree (`frob.gates.
  _profile_boundary.profile_boundary_gate(Path("."))` called directly).

Documented in BOTH docs/modules/gates.md's canonical rule-catalog table
(new PROFILE001 row + `frob:enumerates` members= update) and
docs/modules/tickets-verify-sweep.md's existing "Land profile settings
(T-2360)" section (a new paragraph explaining the design decision and
its verification). gates.md was under a live lease held by the
concurrent T-2891 (a portability fix) for the first half of this
ticket's working session; waited for it to land (confirmed via `frob
ticket show T-2891` -> [done], not by polling `frob check`) rather than
force a waiver or ship a stopgap-only doc, then added the file to scope
and wrote the real entry once the lease cleared. A draft follow-up
ticket (T-2904) filed while still blocked was dropped as
absorbed once the real entry landed directly in this ticket.

Evidence: tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_negative_control_settings_layer_only_is_silent
tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_positive_control_reintroduced_branch_is_flagged
tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_settings_resolver_layer_itself_is_never_flagged
tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_pre_t2361_shape_is_flagged
tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_tests_directory_is_not_scanned

Filed: none surviving -- T-2904 (the docs/modules/gates.md
follow-up) was filed then dropped as absorbed once the real entry
shipped in this same ticket; see its ticket.md for the drop reason.

Gates: frob check --only gates-fast --ticket T-2362 clean of this
ticket's own findings after two fix-and-rerun passes -- gate:SCOPE and
gate:PRE both went from 1 error to 0 (a dropped-draft ticket-dir edit
needed an explicit scope add; the pre-work sweep needed a re-run after
the scope changed), gate:DOC went from 5 to 4 unwaived (fixed a
malformed `frob.tickets._profile.py` doc-symbol-pointer typo in my own
prose; the remaining 4 are pre-existing hits in docs/commands/check.md,
docs/guides/coordinator-scripts.md, docs/modules/gates.md:6091 [T-2891's
own pre-existing broken link, not mine], and tickets/T-2886 -- none
touch this ticket's files), gate:DOCENUM went from 1 to 0 (the
frob:enumerates members= update fixed it directly). Remaining unwaived
findings (gate:COV's stale-attachment/COV006 bash-grammar hits,
gate:LANG's bash/c/rust/typescript LANG003 findings from the T-1604
bash-grammar merge) are pre-existing and repo-wide, confirmed via
targeted grep against the full check log, touching none of this
ticket's files.

### Changed
```
 docs/modules/tickets-verify-sweep.md      |  29 +++++
 src/frob/gates/__init__.py                |  11 ++
 src/frob/gates/_profile_boundary.py       | 172 +++++++++++++++++++++++++
 src/frob/gates/_waive.py                  |   6 +
 tests/unit/gates/test_profile_boundary.py | 205 ++++++++++++++++++++++++++++++
 tickets/T-2362/ticket.md                  |  14 ++
 tickets/T-2904/ticket.md        |  44 +++++++
 7 files changed, 481 insertions(+)
```

### Evidence
- `tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_negative_control_settings_layer_only_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_positive_control_reintroduced_branch_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_settings_resolver_layer_itself_is_never_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_pre_t2361_shape_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_tests_directory_is_not_scanned` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 22 error(s), 1127 warning(s), 847 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, I001@/home/logan/projects/frob/.claude/worktrees/t-2361-series/tests/unit/verify/test_backpressure.py, LANG003@src/frob/lang (facet=capability), LANG003@src/frob/lang (facet=docblock), LANG003@src/frob/lang (facet=dup), TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
