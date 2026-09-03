## Done report

ARCH103 waivers for refactor._verify._import_check_env (src/frob/refactor/_verify.py:147) and app._version_guard._git_head_sha (src/frob/app/_version_guard.py:39) were already present on main at commit 55a6ad3ed, before this ticket's worktree was created -- no code change needed. Evidence: uv run frob check --only arch shows gate:ARCH 0 errors, 0 warnings on both symbols (waived, note-severity mixed-concern-function findings only). Filed: none.

### Changed
```
 tickets/T-3395/ticket.md | 27 +++++++++++++++++++++++++--
 1 file changed, 25 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 9 error(s), 3973 warning(s), 857 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
