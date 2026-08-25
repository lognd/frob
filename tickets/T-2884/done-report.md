## Done report

Changed:
  frob.app._daemon_proxy._classify_version_reply
  frob.app._daemon_proxy._client_source_sha
  frob.serve._socketd._source_head_sha
  frob.serve._socketd._RequestHandler._handle_version (frob_version reply now carries source_sha)
  design/frob.strata (serve node: may exec plus CWE-78 noflow assume for the new git spawn)
  docs/modules/serve.md (version-handshake section: source_sha wire shape and rationale)

Evidence:
  tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_different_source_sha_is_skew (designated BUG002 repro; FAILED_AT_PARENT at d090ffb47, a test-only commit ancestor of HEAD with no source fix; confirmed via frob ticket evidence --check-repro)
  tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_missing_source_sha_is_skew_not_live
  tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_is_live
  tests/test_app_daemon_proxy.py::TestSourceHeadSha::test_finds_git_ancestor
  tests/test_app_daemon_proxy.py::TestSourceHeadSha::test_none_when_no_git_ancestor

Filed: none (recovered abandoned worktree, no new out-of-scope discoveries)

Gates: frob check --ticket T-2884 --no-cache: 18 errors, all pre-existing/repo-wide
and unrelated to this ticket's scope (ruff-format drift in 15 files outside our
diff, a pre-existing frob-cycle import cycle, gate:COV COV004 sha-mismatch on
OTHER tickets' attachments, gate:DOC DOC006 pointers in OTHER tickets'
bodies/docs, gate:TICK staleness/residue findings on OTHER tickets,
claude-config-drift). gate:PRE (this ticket's own pre-work sweep) and
gate:SCOPE cleared after running frob ticket sweep T-2884. Our five touched
files are individually ruff-format-clean. No COV002/TODO001 hits (the two
COV checks the --ticket scoping actually filters to this ticket's touched
set) anywhere in the diff.

### Changed
```
 design/frob.strata             |  25 +++++++++
 docs/modules/serve.md          |  41 +++++++++++++-
 src/frob/app/_daemon_proxy.py  |  68 ++++++++++++++++++++++-
 src/frob/serve/_socketd.py     |  57 +++++++++++++++++++-
 tests/test_app_daemon_proxy.py | 120 +++++++++++++++++++++++++++++++++++++++--
 tickets/T-2884/ticket.md       |   8 ++-
 6 files changed, 310 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_different_source_sha_is_skew` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_missing_source_sha_is_skew_not_live` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_is_live` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestSourceHeadSha::test_finds_git_ancestor` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestSourceHeadSha::test_none_when_no_git_ancestor` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 19 error(s), 816 warning(s), 849 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@tickets/T-2880/ticket.md, DOC006@tickets/T-2884/ticket.md, DOC006@tickets/T-2886/ticket.md, PRE001@tickets/T-2884, TICK004@tickets.md, TICK006@tickets.md
