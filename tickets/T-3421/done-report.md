## Done report

CURRENT MATCHER (read before any change, per acceptance criterion):
`_REDIRECT_TARGET_RES` was three raw regexes searched against the RAW
command STRING (`>`/`>>`, `tee`, `sed -i`), with no quote-awareness and
no heredoc-awareness at all -- a redirect-looking character sequence
inside single quotes, double quotes, or a heredoc body matched exactly
the same as a real redirect operator, because the scanner never knew
those characters were inside a string the shell treats as literal data.

FIX: tokenized, not a refined regex. `_shell_tokens` runs the command
through `shlex.shlex(..., posix=True, punctuation_chars=True)` after
blanking heredoc BODIES (data, never program text -- shlex has no
heredoc concept of its own). With `punctuation_chars=True`, `shlex`
only ever splits `>`/`>>`/`&>`/`&>>`/`>&` into their own operator
tokens when the shell itself would treat them as operators; the
identical character sequence inside a quoted string or (now-blanked)
heredoc body is just part of an ordinary word token. `_redirect_targets`
walks the token list for real write-target candidates (the argument
right after a write-redirect operator, `tee`'s non-flag args, `sed -i`'s
last non-flag arg in its own pipeline segment via `_segments`), skipping
fd-duplication operators (`>&`) and any target starting with `&`.
`_resolve_var_ref`/`_simple_var_assignments` additionally trace a
same-command `NAME=value` assignment so `$NAME`/`${NAME}` redirect
targets resolve to their real value instead of falling through to the
existing `$`-is-ambiguous-so-allow rule -- the "redirect from a
variable" must-fire case, which the pre-fix regex could not satisfy
either (it treated any `$` as ambiguous and allowed unconditionally).
Every existing resolution step downstream (`_unambiguous_target`,
`_resolve_relative`, `_under_any`, worktree exclusion) is UNCHANGED --
only how a candidate target string is FOUND changed, not how it is
judged once found.

MUST-FIRE (still refused): plain `>`, `>>`, `tee`, a heredoc-target
`cat > file <<EOF`, a relative-path redirect resolving into the
checkout, and (new capability) a same-command variable-traced target.
MUST-STAY-QUIET (still allowed): the exact minimal positive control
(`echo 'x > y'`), the same in double quotes, a heredoc BODY quoting an
example redirect, and a genuine fd-duplication redirect (`2>&1`).

Evidence: tests/test_hook_root_write_guard.py: 39/39 pass under
-p no:xdist (29 pre-existing + 10 new T-3421 fixtures: 4 must-stay-quiet,
6 must-fire).

### Changed
```
 tickets/T-3421/ticket.md | 13 ++++++++++++-
 1 file changed, 12 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_hook_root_write_guard.py::test_bash_quoted_redirect_text_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_double_quoted_redirect_text_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_heredoc_body_mentioning_redirect_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_fd_duplication_redirect_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_truncating_redirect_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_appending_redirect_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_variable_redirect_target_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_tee_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_heredoc_redirected_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_relative_redirect_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 13 error(s), 4022 warning(s), 857 waived
- error-findings: AFFECT001@.claude/hooks/root-write-guard.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3421, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
