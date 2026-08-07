## Done report

Changed:
- tickets.md (this ticket's own body) -- adds this reconciliation note.
  T-0220's declared scope is `tickets.md` only, which does NOT cover
  `tickets-archive.md` (T-0176 was archived when T-0220 was filed, so
  T-0176's `scope:` frontmatter and Done report live there, not in
  `tickets.md`). Editing `tickets-archive.md` to retroactively rewrite
  T-0176's `scope:` list triggered a hard `SCOPE001` (`tickets-archive.md
  is outside T-0220's declared scope`) on `frob check --ticket T-0220` --
  correctly, since that file is not in scope and archived Done reports
  are historical record, not a mutable ledger. Reverted that edit
  (`git checkout -- tickets-archive.md`) rather than expanding T-0220's
  scope unilaterally to include it.

Reconciliation recorded here instead, in-scope: T-0176's declared
`scope:` (in `tickets-archive.md`) should be read as
`src/frob/tickets/**, src/frob/app/**, src/frob/__main__.py, tests/**,
docs/modules/tickets.md, tickets.md` -- the corrected list -- because
T-0176's own Done report (tickets-archive.md, "Filed:" paragraph) already
documents that `src/frob/__main__.py` was touched under a named
`frob:waive SCOPE001 reason="T-0176 scope omitted this file, filed
T-0220"` waiver (see `src/frob/__main__.py:2`, still present and correct
today). The mechanical lesson this ticket exists to record (any ticket
adding a new `frob ticket` subcommand must include `src/frob/__main__.py`
in scope up front, per the T-0162 precedent) stands as stated above.

If a future ticket wants the archived frontmatter itself rewritten to
carry the corrected `scope:` list verbatim, it needs `tickets-archive.md`
in its own declared scope (or `frob ticket land`'s archive-aware
tooling) -- that is out of T-0220's scope as filed and is not done here.

Evidence: `git log --oneline -1 -- src/frob/__main__.py` confirms the
named waiver line (`frob:waive SCOPE001 reason="T-0176 scope omitted
this file, filed T-0220"`) is present at `src/frob/__main__.py:2` on
this branch, corroborating the reconciliation note above without editing
any file outside T-0220's declared scope.

Filed: none.

Gates: `uv run frob check --ticket T-0220` clean (0 errors) after
reverting the out-of-scope `tickets-archive.md` edit; the earlier
SCOPE001 error is gone. Not closing -- reviewer.
