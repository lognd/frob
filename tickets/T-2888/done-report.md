## Done report

Fixed OPAQUE001 (src/frob/gates/_refs.py:31) narrowly via an inline
frob:waive citing T-2885 (the newly-filed systemic ticket for the
underlying shared-primitive bug: `_PY_DOCSTRING_QUERY_SRC`'s
module-docstring anchor breaks whenever a comment precedes the
docstring, so `_non_executable_byte_spans` fails to exclude the
docstring's prose and OPAQUE001's needle-scan picks up a textual
`importlib.import_module(...)` example mention as if it were a real
call). Reproduced the root cause empirically (stripped the leading
comment from a copy of the file, re-ran the finder: 0 findings without
it, 1 with it) before writing anything, and grepped for 3 more files
sharing the same vulnerable shape (`_config_external.py`,
`check_runner.py`, `config.py`) to size the blast radius. Did not touch
the shared query itself -- that fix needs positive/negative fixtures
and a repo-wide before/after count this ticket's scope did not cover;
T-2885 carries the full root cause and a suggested fix shape for
whoever takes it.

Characterized, did not fix, the other three assigned findings:

LANG004 (src/frob/lang/_support.py): reliably PASSES via two different
direct in-process reproductions of the exact gate logic (a bare
`_behavioral_capability_check` call and the full `capability_
conformance_gate(repo_root)` call), reliably FAILS via the actual `uv
run frob check` CLI -- twice, once with the gate-cache moved aside to
rule out T-2723-style stale-cache replay. This is a real,
execution-context-dependent discrepancy (not random flapping) between
the CLI pipeline and a direct script invocation of the identical
source tree. Named the strongest lead (a stale globally `uv tool
install`ed frob 0.0.5 at ~/.local/bin/frob, predating T-2410 entirely)
without claiming it as the confirmed mechanism, since the actual
subprocess call site reaching it in the default check path was not
found within this ticket's budget. Recorded as environment-dependent
rather than guessed at with an unproven fix.

TICK003 (882 un-archived, tickets.md): re-verified against T-2801's own
Done report -- identical shape, same "needs a quiet window, no
in-flight worktrees" gate message, not quiet tonight (concurrent lands
observed directly). Correctly left alone, not overriding that judgment.

TICK006 (T-2796's Done report cites T-draft-b1ac02d7, unresolved):
recovered the original content from git history (commit 94763205f) --
a genuine T-0577 draft-loss-at-land case, not a Done-report typo.
Attempting to re-file it hit `frob ticket new`'s 100%-title-match
duplicate guard: T-2803 (queued, filed 2026-08-21) is already the real
successor -- no new ticket needed. For T-2796's own Done report:
checked established precedent (T-2722's Done report, docs/modules/
gates.md's TICK006 section, archived T-0741) before deciding NOT to
hand-edit or waive it -- TICK006's Violation carries no symref
(file-scoped to tickets.md only), so a per-instance waiver here would
blanket-suppress every current AND future TICK006 finding across the
whole ledger, exactly what T-2722 already ruled out for the same
reason; T-0741 documents ~97 other pre-existing instances of this
identical shape, left unresolved today pending its own proposed
structural fix (TICK006 symref support, or a documented backfill-note
convention). This is one more instance of that already-tracked debt
class, correctly left alone rather than mechanically waived or
hand-patched.

Filed: T-2885 (OPAQUE001/sys docstring-exclusion systemic bug,
investigation-only). No other new tickets -- T-2803 already covers the
TICK006 recovery.

frob:no-behavior-change reason="The only production-code change is one inline frob:waive OPAQUE001 comment naming T-2885 -- no executable behavior changes. LANG004/TICK003/TICK006 are investigation and characterization only."

### Changed
```
 tickets/T-2888/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 8 error(s), 443 warning(s), 846 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, DOC006@tickets/T-2880/ticket.md, DOC006@tickets/T-2884/ticket.md, PRE001@tickets/T-2888, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
