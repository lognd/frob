## Done report

Decision: worktree.baseRef=head, applied in .claude/settings.json (untracked; .claude/ is gitignored in this repo, so the setting is machine-local by design). Rationale: T-1030 confirmed the dispatch tool cuts worktrees from origin/main, which lags local main by hundreds of deliberately-unpushed commits; baseRef=head cuts from local HEAD and removes the stale-base class at the source. The push-main-before-dispatch alternative stays rejected while main is intentionally unpushed (user directive). The playbook section 1 warm-up merge stays mandatory as defense in depth. Verified: settings JSON parses and worktree.baseRef reads back 'head'.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 2448 warning(s), 509 waived
- error-findings: none (measured, zero errors)
